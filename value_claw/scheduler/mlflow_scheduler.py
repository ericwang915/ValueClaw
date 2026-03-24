"""
MLflow-backed cron scheduler for value_claw.

Architecture
------------
- **APScheduler** handles timing (cron triggers, job registration).
- **MLflow Tracking** records every job execution as a Run, enabling
  a full audit trail with parameters, metrics, and response artifacts.
- **MLflow UI** is started as a background subprocess, giving the user
  a rich web dashboard for inspecting job history.

Two sources of jobs (same as the legacy CronScheduler)
------------------------------------------------------
1. Static jobs   — ``context/cron/jobs.yaml``
2. Dynamic jobs  — ``context/cron/dynamic_jobs.json``

Configuration (value_claw.json)
-------------------------------
  mlflow.port           / MLFLOW_PORT            — UI port  (default 5000)
  mlflow.host           / MLFLOW_HOST            — UI host  (default 127.0.0.1)
  mlflow.trackingUri    / MLFLOW_TRACKING_URI    — explicit tracking URI (overrides auto)
  mlflow.artifactRoot   / MLFLOW_ARTIFACT_ROOT   — artifact storage path
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

if TYPE_CHECKING:
    from ..channels.telegram_bot import TelegramBot
    from ..session_manager import SessionManager

logger = logging.getLogger(__name__)


# ── Path helpers ──────────────────────────────────────────────────────────────

def _cron_dir() -> str:
    from .. import config as _cfg
    return os.path.join(str(_cfg.VALUE_CLAW_HOME), "context", "cron")


def _dynamic_jobs_file() -> str:
    return os.path.join(_cron_dir(), "dynamic_jobs.json")


def _default_jobs_path() -> str:
    return os.path.join(_cron_dir(), "jobs.yaml")


def _mlflow_backend_dir() -> str:
    from .. import config as _cfg
    return os.path.join(str(_cfg.VALUE_CLAW_HOME), "mlflow")


def _parse_cron(expr: str) -> CronTrigger:
    """Convert a 5-field cron expression into an APScheduler CronTrigger."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (expected 5 fields): '{expr}'")
    minute, hour, day, month, day_of_week = parts
    return CronTrigger(
        minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week,
    )


class MLflowScheduler:
    """APScheduler + MLflow Tracking for scheduled LLM tasks.

    Drop-in replacement for CronScheduler with added MLflow capabilities:
    - Every job execution is tracked as an MLflow Run
    - MLflow UI available at http://{host}:{port}
    - Full run history queryable via API
    """

    def __init__(
        self,
        session_manager: "SessionManager",
        jobs_path: str | None = None,
        telegram_bot: "TelegramBot | None" = None,
    ) -> None:
        self._sm = session_manager
        self._jobs_path = jobs_path or _default_jobs_path()
        self._telegram_bot = telegram_bot
        self._scheduler = AsyncIOScheduler()
        self._mlflow_process: subprocess.Popen | None = None
        self._mlflow_ready = False
        self._jobs_meta: dict[str, dict] = {}

    # ── MLflow server lifecycle ───────────────────────────────────────────────

    @property
    def mlflow_port(self) -> int:
        from .. import config as _cfg
        return _cfg.get_int("mlflow", "port", env="MLFLOW_PORT", default=5000)

    @property
    def mlflow_host(self) -> str:
        from .. import config as _cfg
        return _cfg.get_str("mlflow", "host", env="MLFLOW_HOST", default="127.0.0.1")

    @property
    def tracking_uri(self) -> str:
        from .. import config as _cfg
        explicit = _cfg.get_str("mlflow", "trackingUri", env="MLFLOW_TRACKING_URI", default="")
        if explicit:
            return explicit
        return f"http://{self.mlflow_host}:{self.mlflow_port}"

    @property
    def mlflow_ui_url(self) -> str:
        return f"http://{self.mlflow_host}:{self.mlflow_port}"

    def _start_mlflow_server(self) -> None:
        """Start the MLflow tracking server as a background subprocess."""
        backend_dir = _mlflow_backend_dir()
        os.makedirs(backend_dir, exist_ok=True)

        from .. import config as _cfg
        artifact_root = _cfg.get_str(
            "mlflow", "artifactRoot", env="MLFLOW_ARTIFACT_ROOT",
            default=os.path.join(backend_dir, "artifacts"),
        )
        os.makedirs(artifact_root, exist_ok=True)

        db_path = os.path.join(backend_dir, "mlflow.db")
        backend_uri = f"sqlite:///{db_path}"

        cmd = [
            sys.executable, "-m", "mlflow", "server",
            "--host", self.mlflow_host,
            "--port", str(self.mlflow_port),
            "--backend-store-uri", backend_uri,
            "--default-artifact-root", artifact_root,
        ]

        try:
            self._mlflow_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            logger.info(
                "[MLflowScheduler] MLflow server starting: %s (pid=%d)",
                self.mlflow_ui_url, self._mlflow_process.pid,
            )
            self._wait_for_mlflow()
        except FileNotFoundError:
            logger.error(
                "[MLflowScheduler] MLflow not installed. Install with: pip install mlflow"
            )
            self._mlflow_ready = False
        except Exception as exc:
            logger.error("[MLflowScheduler] Failed to start MLflow server: %s", exc)
            self._mlflow_ready = False

    def _wait_for_mlflow(self, timeout: int = 30) -> None:
        """Poll the MLflow server until it responds or timeout."""
        import httpx

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = httpx.get(f"{self.tracking_uri}/health", timeout=2)
                if resp.status_code == 200:
                    self._mlflow_ready = True
                    logger.info("[MLflowScheduler] MLflow server is ready at %s", self.mlflow_ui_url)
                    return
            except Exception:
                pass
            time.sleep(1)

        logger.warning("[MLflowScheduler] MLflow server did not become ready within %ds", timeout)
        self._mlflow_ready = False

    def _stop_mlflow_server(self) -> None:
        """Stop the MLflow tracking server subprocess."""
        if self._mlflow_process and self._mlflow_process.poll() is None:
            try:
                os.killpg(os.getpgid(self._mlflow_process.pid), signal.SIGTERM)
                self._mlflow_process.wait(timeout=10)
                logger.info("[MLflowScheduler] MLflow server stopped.")
            except Exception as exc:
                logger.warning("[MLflowScheduler] Error stopping MLflow: %s", exc)
                try:
                    self._mlflow_process.kill()
                except Exception:
                    pass
            self._mlflow_process = None
            self._mlflow_ready = False

    def _configure_mlflow(self) -> None:
        """Set up MLflow tracking URI for the current process."""
        try:
            import mlflow
            mlflow.set_tracking_uri(self.tracking_uri)
        except ImportError:
            logger.warning("[MLflowScheduler] mlflow package not installed — tracking disabled")

    # ── MLflow tracking helpers ───────────────────────────────────────────────

    def _get_or_create_experiment(self, job_id: str) -> str | None:
        """Get or create an MLflow experiment for a cron job."""
        try:
            import mlflow
            experiment_name = f"cron/{job_id}"
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                return mlflow.create_experiment(experiment_name)
            return experiment.experiment_id
        except Exception as exc:
            logger.warning("[MLflowScheduler] MLflow experiment error: %s", exc)
            return None

    def _log_run(
        self,
        job_id: str,
        prompt: str,
        response: str | None,
        duration_sec: float,
        success: bool,
        error: str | None = None,
    ) -> str | None:
        """Log a job execution as an MLflow run. Returns the run_id."""
        try:
            import mlflow

            self._configure_mlflow()
            experiment_id = self._get_or_create_experiment(job_id)
            if experiment_id is None:
                return None

            with mlflow.start_run(experiment_id=experiment_id) as run:
                mlflow.log_params({
                    "job_id": job_id,
                    "prompt": prompt[:250],
                    "trigger_time": datetime.now(timezone.utc).isoformat(),
                })

                mlflow.log_metrics({
                    "duration_seconds": round(duration_sec, 2),
                    "success": 1.0 if success else 0.0,
                    "response_length": len(response) if response else 0,
                })

                mlflow.set_tags({
                    "status": "success" if success else "failed",
                    "job_id": job_id,
                })

                if error:
                    mlflow.set_tag("error", error[:500])

                if response:
                    mlflow.log_text(response, "response.md")

                if not success and error:
                    mlflow.log_text(error, "error.txt")

                return run.info.run_id
        except ImportError:
            logger.debug("[MLflowScheduler] mlflow not available for tracking")
            return None
        except Exception as exc:
            logger.warning("[MLflowScheduler] MLflow logging error: %s", exc)
            return None

    # ── YAML loading ──────────────────────────────────────────────────────────

    def _load_jobs(self) -> list[dict]:
        if not os.path.exists(self._jobs_path):
            logger.info("[MLflowScheduler] No jobs file at %s — skipping.", self._jobs_path)
            return []
        with open(self._jobs_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("jobs", [])

    # ── Job execution ─────────────────────────────────────────────────────────

    async def _run_job(
        self,
        job_id: str,
        prompt: str,
        deliver_to: str | None,
        chat_id: int | None,
    ) -> None:
        session_id = f"cron:{job_id}"
        logger.info("[MLflowScheduler] Running job '%s' (session='%s')", job_id, session_id)

        agent = self._sm.get_or_create(session_id)
        loop = asyncio.get_event_loop()

        start_time = time.time()
        response = None
        error_msg = None
        success = True

        try:
            response = await loop.run_in_executor(None, agent.chat, prompt)
            logger.info("[MLflowScheduler] Job '%s' completed.", job_id)
        except Exception as exc:
            logger.exception("[MLflowScheduler] Job '%s' failed: %s", job_id, exc)
            error_msg = str(exc)
            response = f"[Cron job '{job_id}' failed]\n{exc}"
            success = False

        duration = time.time() - start_time

        run_id = await loop.run_in_executor(
            None, self._log_run, job_id, prompt, response, duration, success, error_msg,
        )
        if run_id:
            logger.info("[MLflowScheduler] Job '%s' logged as MLflow run %s", job_id, run_id)

        if deliver_to == "telegram" and chat_id and self._telegram_bot:
            try:
                status_icon = "✅" if success else "❌"
                header = f"{status_icon} Cron job: {job_id} ({duration:.1f}s)\n\n"
                await self._telegram_bot.send_message(chat_id, header + (response or ""))
            except Exception as exc:
                logger.error(
                    "[MLflowScheduler] Failed to deliver job '%s' to Telegram: %s", job_id, exc,
                )

    # ── Scheduler lifecycle ───────────────────────────────────────────────────

    def load_and_register_jobs(self) -> int:
        """Parse jobs.yaml and register enabled jobs with APScheduler."""
        jobs = self._load_jobs()
        registered = 0
        for job in jobs:
            job_id = job.get("id", "unnamed")
            if not job.get("enabled", True):
                logger.info("[MLflowScheduler] Skipping disabled job '%s'", job_id)
                continue

            cron_expr = job.get("cron")
            prompt = job.get("prompt")
            if not cron_expr or not prompt:
                logger.warning("[MLflowScheduler] Job '%s' missing 'cron' or 'prompt' — skipped.", job_id)
                continue

            deliver_to = job.get("deliver_to")
            chat_id = job.get("chat_id")

            trigger = _parse_cron(cron_expr)
            self._scheduler.add_job(
                self._run_job,
                trigger=trigger,
                id=job_id,
                kwargs={
                    "job_id": job_id, "prompt": prompt,
                    "deliver_to": deliver_to, "chat_id": chat_id,
                },
                replace_existing=True,
            )
            self._jobs_meta[job_id] = {
                "cron": cron_expr, "prompt": prompt,
                "deliver_to": deliver_to, "chat_id": chat_id,
                "source": "static",
            }
            logger.info("[MLflowScheduler] Registered static job '%s' cron='%s'", job_id, cron_expr)
            registered += 1

        return registered

    def start(self) -> None:
        """Start MLflow server and APScheduler."""
        self._start_mlflow_server()
        self._configure_mlflow()

        static_count = self.load_and_register_jobs()
        dynamic_count = self._register_dynamic_jobs()
        total = static_count + dynamic_count

        if total == 0:
            logger.info("[MLflowScheduler] No jobs to schedule — scheduler idle.")

        self._scheduler.start()
        logger.info(
            "[MLflowScheduler] Started: %d static + %d dynamic jobs. MLflow UI: %s",
            static_count, dynamic_count, self.mlflow_ui_url,
        )



    def stop(self) -> None:
        """Stop APScheduler and MLflow server."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("[MLflowScheduler] Scheduler stopped.")
        self._stop_mlflow_server()

    def reload_jobs(self) -> int:
        """Hot-reload static jobs from YAML without stopping."""
        self._scheduler.remove_all_jobs()
        self._jobs_meta.clear()
        count = self.load_and_register_jobs()
        count += self._register_dynamic_jobs()
        return count

    # ── Dynamic job management ────────────────────────────────────────────────

    def _load_dynamic_jobs(self) -> dict[str, dict]:
        djf = _dynamic_jobs_file()
        if not os.path.exists(djf):
            return {}
        try:
            with open(djf, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("[MLflowScheduler] Failed to load dynamic jobs: %s", exc)
            return {}

    def _save_dynamic_jobs(self, jobs: dict[str, dict]) -> None:
        djf = _dynamic_jobs_file()
        os.makedirs(os.path.dirname(djf), exist_ok=True)
        with open(djf, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2, ensure_ascii=False)

    def _register_dynamic_jobs(self) -> int:
        jobs = self._load_dynamic_jobs()
        registered = 0
        for job_id, job in jobs.items():
            try:
                self._scheduler.add_job(
                    self._run_job,
                    trigger=_parse_cron(job["cron"]),
                    id=job_id,
                    kwargs={
                        "job_id": job_id, "prompt": job["prompt"],
                        "deliver_to": job.get("deliver_to"), "chat_id": job.get("chat_id"),
                    },
                    replace_existing=True,
                )
                self._jobs_meta[job_id] = {**job, "source": "dynamic"}
                registered += 1
                logger.info("[MLflowScheduler] Restored dynamic job '%s'", job_id)
            except Exception as exc:
                logger.error("[MLflowScheduler] Failed to restore job '%s': %s", job_id, exc)
        return registered

    def add_dynamic_job(
        self,
        job_id: str,
        cron_expr: str,
        prompt: str,
        deliver_to: str | None = None,
        chat_id: int | None = None,
    ) -> str:
        """Add a new dynamic job (called from Agent cron_add tool)."""
        try:
            trigger = _parse_cron(cron_expr)
        except ValueError as exc:
            return f"Invalid cron expression: {exc}"

        self._scheduler.add_job(
            self._run_job,
            trigger=trigger,
            id=job_id,
            kwargs={
                "job_id": job_id, "prompt": prompt,
                "deliver_to": deliver_to, "chat_id": chat_id,
            },
            replace_existing=True,
        )

        jobs = self._load_dynamic_jobs()
        jobs[job_id] = {
            "cron": cron_expr, "prompt": prompt,
            "deliver_to": deliver_to, "chat_id": chat_id,
        }
        self._save_dynamic_jobs(jobs)
        self._jobs_meta[job_id] = {**jobs[job_id], "source": "dynamic"}

        logger.info("[MLflowScheduler] Added job '%s' (cron='%s')", job_id, cron_expr)
        return (
            f"Job '{job_id}' scheduled: cron='{cron_expr}'.\n"
            f"Session: cron:{job_id}\n"
            f"MLflow tracking: {self.mlflow_ui_url}"
        )

    def remove_dynamic_job(self, job_id: str) -> str:
        """Remove a dynamic job (called from Agent cron_remove tool)."""
        jobs = self._load_dynamic_jobs()
        if job_id not in jobs and not self._scheduler.get_job(job_id):
            return f"Job '{job_id}' not found."
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass
        jobs.pop(job_id, None)
        self._save_dynamic_jobs(jobs)
        self._jobs_meta.pop(job_id, None)
        logger.info("[MLflowScheduler] Removed job '%s'", job_id)
        return f"Job '{job_id}' removed."

    def list_jobs(self) -> str:
        """Return a human-readable list of all active jobs."""
        scheduler_jobs = self._scheduler.get_jobs()
        dynamic = self._load_dynamic_jobs()
        if not scheduler_jobs:
            return f"No scheduled jobs.\nMLflow UI: {self.mlflow_ui_url}"

        lines = []
        for job in scheduler_jobs:
            tag = "[dynamic]" if job.id in dynamic else "[static]"
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M %Z") if job.next_run_time else "paused"
            lines.append(f"  {tag} {job.id} | next: {next_run}")

        return (
            "Active cron jobs:\n"
            + "\n".join(lines)
            + f"\n\nMLflow UI: {self.mlflow_ui_url}"
        )

    # ── Extended API (for REST endpoints and agent tools) ─────────────────────

    async def trigger_job(self, job_id: str) -> str:
        """Manually trigger a job immediately."""
        meta = self._jobs_meta.get(job_id)
        if meta is None:
            dynamic = self._load_dynamic_jobs()
            meta = dynamic.get(job_id)
        if meta is None:
            return f"Job '{job_id}' not found."

        asyncio.create_task(
            self._run_job(
                job_id=job_id,
                prompt=meta["prompt"],
                deliver_to=meta.get("deliver_to"),
                chat_id=meta.get("chat_id"),
            )
        )
        return f"Job '{job_id}' triggered. Check MLflow for results: {self.mlflow_ui_url}"

    def get_job_runs(self, job_id: str, max_results: int = 20) -> list[dict]:
        """Get recent MLflow runs for a specific job."""
        try:
            import mlflow
            self._configure_mlflow()

            experiment_name = f"cron/{job_id}"
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                return []

            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                max_results=max_results,
                order_by=["start_time DESC"],
            )

            result = []
            for _, row in runs.iterrows():
                result.append({
                    "run_id": row.get("run_id", ""),
                    "status": row.get("tags.status", "unknown"),
                    "start_time": str(row.get("start_time", "")),
                    "duration_seconds": row.get("metrics.duration_seconds", 0),
                    "success": bool(row.get("metrics.success", 0)),
                    "response_length": int(row.get("metrics.response_length", 0)),
                })
            return result
        except ImportError:
            return []
        except Exception as exc:
            logger.warning("[MLflowScheduler] Error querying runs: %s", exc)
            return []

    def get_all_runs(self, max_results: int = 50) -> list[dict]:
        """Get recent runs across all jobs."""
        try:
            import mlflow
            self._configure_mlflow()

            experiments = mlflow.search_experiments()
            cron_experiments = [e for e in experiments if e.name.startswith("cron/")]

            if not cron_experiments:
                return []

            exp_ids = [e.experiment_id for e in cron_experiments]
            runs = mlflow.search_runs(
                experiment_ids=exp_ids,
                max_results=max_results,
                order_by=["start_time DESC"],
            )

            result = []
            for _, row in runs.iterrows():
                result.append({
                    "run_id": row.get("run_id", ""),
                    "job_id": row.get("tags.job_id", ""),
                    "status": row.get("tags.status", "unknown"),
                    "start_time": str(row.get("start_time", "")),
                    "duration_seconds": row.get("metrics.duration_seconds", 0),
                    "success": bool(row.get("metrics.success", 0)),
                })
            return result
        except ImportError:
            return []
        except Exception as exc:
            logger.warning("[MLflowScheduler] Error querying all runs: %s", exc)
            return []

    def get_jobs_detail(self) -> list[dict]:
        """Get all jobs with metadata and last run info (for REST API)."""
        scheduler_jobs = self._scheduler.get_jobs()
        dynamic = self._load_dynamic_jobs()

        result = []
        for job in scheduler_jobs:
            meta = self._jobs_meta.get(job.id, {})
            next_run = job.next_run_time.isoformat() if job.next_run_time else None
            last_runs = self.get_job_runs(job.id, max_results=1)

            entry = {
                "job_id": job.id,
                "cron": meta.get("cron", ""),
                "prompt": meta.get("prompt", ""),
                "source": "dynamic" if job.id in dynamic else "static",
                "next_run": next_run,
                "deliver_to": meta.get("deliver_to"),
                "chat_id": meta.get("chat_id"),
            }

            if last_runs:
                entry["last_run"] = last_runs[0]
            result.append(entry)

        return result

    def mlflow_status(self) -> dict:
        """Get MLflow server status."""
        return {
            "running": self._mlflow_ready,
            "ui_url": self.mlflow_ui_url,
            "tracking_uri": self.tracking_uri,
            "pid": self._mlflow_process.pid if self._mlflow_process else None,
        }
