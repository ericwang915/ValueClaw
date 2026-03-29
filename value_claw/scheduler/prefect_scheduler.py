"""
Prefect-backed cron scheduler for value_claw.

Architecture
------------
- **APScheduler** handles timing (cron triggers, job registration).
- **Prefect @flow** tracks every job execution as a Flow Run, enabling
  a full audit trail with parameters, metrics, and response artifacts.
- **Prefect Server** is started as a background subprocess, giving the user
  a rich web dashboard for inspecting job history.

Two sources of jobs (same as the legacy scheduler)
---------------------------------------------------
1. Static jobs   — ``context/cron/jobs.yaml``
2. Dynamic jobs  — ``context/cron/dynamic_jobs.json``

Configuration (value_claw.json)
-------------------------------
  prefect.port          / PREFECT_PORT           — UI/API port  (default 4200)
  prefect.host          / PREFECT_HOST           — UI/API host  (default 127.0.0.1)
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
from typing import TYPE_CHECKING

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

if TYPE_CHECKING:
    from ..channels.telegram_bot import TelegramBot
    from ..session_manager import SessionManager

logger = logging.getLogger(__name__)

# ── Optional Prefect imports ─────────────────────────────────────────────────

_HAS_PREFECT = False
_prefect_flow_fn = None

try:
    from prefect import flow as _pf
    from prefect import tags as _pt

    @_pf(name="cron-job", log_prints=True)
    def _tracked_execute(job_id: str, prompt: str) -> str:
        """Prefect-tracked flow that executes an agent prompt."""
        from value_claw.server import get_scheduler

        sched = get_scheduler()
        if sched is None:
            raise RuntimeError("Scheduler not available")
        agent = sched._sm.get_or_create(f"cron:{job_id}")
        response = agent.chat(prompt)
        print(f"Job '{job_id}' done | {len(response)} chars")
        return response

    _prefect_flow_fn = _tracked_execute
    _HAS_PREFECT = True
except ImportError:
    _pt = None


# ── Path helpers ─────────────────────────────────────────────────────────────

def _cron_dir() -> str:
    from .. import config as _cfg
    return os.path.join(str(_cfg.VALUE_CLAW_HOME), "context", "cron")


def _dynamic_jobs_file() -> str:
    return os.path.join(_cron_dir(), "dynamic_jobs.json")


def _default_jobs_path() -> str:
    return os.path.join(_cron_dir(), "jobs.yaml")


def _parse_cron(expr: str) -> CronTrigger:
    """Convert a 5-field cron expression into an APScheduler CronTrigger."""
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (expected 5 fields): '{expr}'")
    minute, hour, day, month, day_of_week = parts
    return CronTrigger(
        minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week,
    )


class PrefectScheduler:
    """APScheduler + Prefect Tracking for scheduled LLM tasks.

    Drop-in replacement for MLflowScheduler with Prefect capabilities:
    - Every job execution is tracked as a Prefect Flow Run
    - Prefect UI available at http://{host}:{port}
    - Full run history queryable via REST API
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
        self._prefect_process: subprocess.Popen | None = None
        self._prefect_ready = False
        self._jobs_meta: dict[str, dict] = {}

    # ── Prefect server lifecycle ─────────────────────────────────────────────

    @property
    def prefect_port(self) -> int:
        from .. import config as _cfg
        return _cfg.get_int("prefect", "port", env="PREFECT_PORT", default=4200)

    @property
    def prefect_host(self) -> str:
        from .. import config as _cfg
        return _cfg.get_str("prefect", "host", env="PREFECT_HOST", default="127.0.0.1")

    @property
    def prefect_api_url(self) -> str:
        return f"http://{self.prefect_host}:{self.prefect_port}/api"

    @property
    def prefect_ui_url(self) -> str:
        return f"http://{self.prefect_host}:{self.prefect_port}"

    def _start_prefect_server(self) -> None:
        """Start the Prefect server as a background subprocess."""
        cmd = [
            sys.executable, "-m", "prefect", "server", "start",
            "--host", self.prefect_host,
            "--port", str(self.prefect_port),
        ]

        try:
            self._prefect_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            logger.info(
                "[PrefectScheduler] Prefect server starting: %s (pid=%d)",
                self.prefect_ui_url, self._prefect_process.pid,
            )
            self._wait_for_prefect()
        except FileNotFoundError:
            logger.error(
                "[PrefectScheduler] Prefect not installed. Install with: pip install prefect"
            )
            self._prefect_ready = False
        except Exception as exc:
            logger.error("[PrefectScheduler] Failed to start Prefect server: %s", exc)
            self._prefect_ready = False

    def _wait_for_prefect(self, timeout: int = 30) -> None:
        """Poll the Prefect server until it responds or timeout."""
        import httpx

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = httpx.get(f"{self.prefect_api_url}/health", timeout=2)
                if resp.status_code == 200:
                    self._prefect_ready = True
                    logger.info(
                        "[PrefectScheduler] Prefect server is ready at %s",
                        self.prefect_ui_url,
                    )
                    return
            except Exception:
                pass
            time.sleep(1)

        logger.warning(
            "[PrefectScheduler] Prefect server did not become ready within %ds", timeout,
        )
        self._prefect_ready = False

    def _stop_prefect_server(self) -> None:
        """Stop the Prefect server subprocess."""
        if self._prefect_process and self._prefect_process.poll() is None:
            try:
                os.killpg(os.getpgid(self._prefect_process.pid), signal.SIGTERM)
                self._prefect_process.wait(timeout=10)
                logger.info("[PrefectScheduler] Prefect server stopped.")
            except Exception as exc:
                logger.warning("[PrefectScheduler] Error stopping Prefect: %s", exc)
                try:
                    self._prefect_process.kill()
                except Exception:
                    pass
            self._prefect_process = None
            self._prefect_ready = False

    def _configure_prefect(self) -> None:
        """Point the Prefect client at our server."""
        os.environ["PREFECT_API_URL"] = self.prefect_api_url

    # ── YAML loading ─────────────────────────────────────────────────────────

    def _load_jobs(self) -> list[dict]:
        if not os.path.exists(self._jobs_path):
            logger.info("[PrefectScheduler] No jobs file at %s — skipping.", self._jobs_path)
            return []
        with open(self._jobs_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("jobs", [])

    # ── Job execution ────────────────────────────────────────────────────────

    async def _run_job(
        self,
        job_id: str,
        prompt: str,
        deliver_to: str | None,
        chat_id: int | None,
    ) -> None:
        session_id = f"cron:{job_id}"
        logger.info("[PrefectScheduler] Running job '%s' (session='%s')", job_id, session_id)

        loop = asyncio.get_event_loop()
        start_time = time.time()
        response = None
        success = True

        try:
            if _HAS_PREFECT and self._prefect_ready:
                def _call():
                    with _pt(job_id, "cron"):
                        return _prefect_flow_fn(job_id=job_id, prompt=prompt)
                response = await loop.run_in_executor(None, _call)
            else:
                agent = self._sm.get_or_create(session_id)
                response = await loop.run_in_executor(None, agent.chat, prompt)
            logger.info("[PrefectScheduler] Job '%s' completed.", job_id)
        except Exception as exc:
            logger.exception("[PrefectScheduler] Job '%s' failed: %s", job_id, exc)
            response = f"[Cron job '{job_id}' failed]\n{exc}"
            success = False

        duration = time.time() - start_time

        if deliver_to == "telegram" and chat_id and self._telegram_bot:
            try:
                status_icon = "✅" if success else "❌"
                header = f"{status_icon} Cron job: {job_id} ({duration:.1f}s)\n\n"
                await self._telegram_bot.send_message(chat_id, header + (response or ""))
            except Exception as exc:
                logger.error(
                    "[PrefectScheduler] Failed to deliver job '%s' to Telegram: %s",
                    job_id, exc,
                )

    # ── Scheduler lifecycle ──────────────────────────────────────────────────

    def load_and_register_jobs(self) -> int:
        """Parse jobs.yaml and register enabled jobs with APScheduler."""
        jobs = self._load_jobs()
        registered = 0
        for job in jobs:
            job_id = job.get("id", "unnamed")
            if not job.get("enabled", True):
                logger.info("[PrefectScheduler] Skipping disabled job '%s'", job_id)
                continue

            cron_expr = job.get("cron")
            prompt = job.get("prompt")
            if not cron_expr or not prompt:
                logger.warning(
                    "[PrefectScheduler] Job '%s' missing 'cron' or 'prompt' — skipped.", job_id,
                )
                continue

            deliver_to = job.get("deliver_to")
            chat_id_val = job.get("chat_id")

            trigger = _parse_cron(cron_expr)
            self._scheduler.add_job(
                self._run_job,
                trigger=trigger,
                id=job_id,
                kwargs={
                    "job_id": job_id, "prompt": prompt,
                    "deliver_to": deliver_to, "chat_id": chat_id_val,
                },
                replace_existing=True,
            )
            self._jobs_meta[job_id] = {
                "cron": cron_expr, "prompt": prompt,
                "deliver_to": deliver_to, "chat_id": chat_id_val,
                "source": "static",
            }
            logger.info("[PrefectScheduler] Registered static job '%s' cron='%s'", job_id, cron_expr)
            registered += 1

        return registered

    def start(self) -> None:
        """Start Prefect server and APScheduler."""
        self._start_prefect_server()
        self._configure_prefect()

        static_count = self.load_and_register_jobs()
        dynamic_count = self._register_dynamic_jobs()
        strategy_count = self._restore_strategy_jobs()
        total = static_count + dynamic_count + strategy_count

        if total == 0:
            logger.info("[PrefectScheduler] No jobs to schedule — scheduler idle.")

        self._scheduler.start()
        logger.info(
            "[PrefectScheduler] Started: %d static + %d dynamic + %d strategy jobs. Prefect UI: %s",
            static_count, dynamic_count, strategy_count, self.prefect_ui_url,
        )

    def stop(self) -> None:
        """Stop APScheduler and Prefect server."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("[PrefectScheduler] Scheduler stopped.")
        self._stop_prefect_server()

    def reload_jobs(self) -> int:
        """Hot-reload static jobs from YAML without stopping."""
        self._scheduler.remove_all_jobs()
        self._jobs_meta.clear()
        count = self.load_and_register_jobs()
        count += self._register_dynamic_jobs()
        return count

    # ── Dynamic job management ───────────────────────────────────────────────

    def _load_dynamic_jobs(self) -> dict[str, dict]:
        djf = _dynamic_jobs_file()
        if not os.path.exists(djf):
            return {}
        try:
            with open(djf, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("[PrefectScheduler] Failed to load dynamic jobs: %s", exc)
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
                logger.info("[PrefectScheduler] Restored dynamic job '%s'", job_id)
            except Exception as exc:
                logger.error("[PrefectScheduler] Failed to restore job '%s': %s", job_id, exc)
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

        logger.info("[PrefectScheduler] Added job '%s' (cron='%s')", job_id, cron_expr)
        return (
            f"Job '{job_id}' scheduled: cron='{cron_expr}'.\n"
            f"Session: cron:{job_id}\n"
            f"Prefect UI: {self.prefect_ui_url}"
        )

    def update_dynamic_job(
        self,
        job_id: str,
        cron_expr: str | None = None,
        prompt: str | None = None,
        deliver_to: str | None = None,
        chat_id: int | None = None,
    ) -> str:
        """Update an existing dynamic job's schedule or prompt."""
        jobs = self._load_dynamic_jobs()
        if job_id not in jobs and not self._scheduler.get_job(job_id):
            return f"Job '{job_id}' not found."

        existing = jobs.get(job_id, self._jobs_meta.get(job_id, {}))
        new_cron = cron_expr or existing.get("cron", "")
        new_prompt = prompt or existing.get("prompt", "")
        new_deliver = deliver_to if deliver_to is not None else existing.get("deliver_to")
        new_chat = chat_id if chat_id is not None else existing.get("chat_id")

        try:
            trigger = _parse_cron(new_cron)
        except ValueError as exc:
            return f"Invalid cron expression: {exc}"

        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass

        self._scheduler.add_job(
            self._run_job,
            trigger=trigger,
            id=job_id,
            kwargs={
                "job_id": job_id, "prompt": new_prompt,
                "deliver_to": new_deliver, "chat_id": new_chat,
            },
            replace_existing=True,
        )

        jobs[job_id] = {
            "cron": new_cron, "prompt": new_prompt,
            "deliver_to": new_deliver, "chat_id": new_chat,
        }
        self._save_dynamic_jobs(jobs)
        self._jobs_meta[job_id] = {**jobs[job_id], "source": "dynamic"}

        logger.info("[PrefectScheduler] Updated job '%s'", job_id)
        return f"Job '{job_id}' updated: cron='{new_cron}'."

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
        logger.info("[PrefectScheduler] Removed job '%s'", job_id)
        return f"Job '{job_id}' removed."

    def list_jobs(self) -> str:
        """Return a human-readable list of all active jobs."""
        scheduler_jobs = self._scheduler.get_jobs()
        dynamic = self._load_dynamic_jobs()
        if not scheduler_jobs:
            return f"No scheduled jobs.\nPrefect UI: {self.prefect_ui_url}"

        lines = []
        for job in scheduler_jobs:
            tag = "[dynamic]" if job.id in dynamic else "[static]"
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M %Z") if job.next_run_time else "paused"
            lines.append(f"  {tag} {job.id} | next: {next_run}")

        return (
            "Active cron jobs:\n"
            + "\n".join(lines)
            + f"\n\nPrefect UI: {self.prefect_ui_url}"
        )

    # ── Strategy job management ─────────────────────────────────────────────

    def _restore_strategy_jobs(self) -> int:
        """Re-register cron jobs for all strategies with status='running'."""
        try:
            from ..core.strategy import list_strategies
        except ImportError:
            return 0
        count = 0
        for strat in list_strategies():
            if strat.get("status") == "running":
                sid = strat["id"]
                try:
                    self.register_strategy_job(sid, strat["schedule"])
                    count += 1
                except Exception as exc:
                    logger.error("[PrefectScheduler] Failed to restore strategy job '%s': %s", sid, exc)
        return count

    def register_strategy_job(self, strategy_id: str, cron_expr: str) -> None:
        """Register a strategy's cron job with APScheduler."""
        trigger = _parse_cron(cron_expr)
        job_id = f"strategy:{strategy_id}"
        self._scheduler.add_job(
            self._run_strategy_job,
            trigger=trigger,
            id=job_id,
            kwargs={"strategy_id": strategy_id},
            replace_existing=True,
        )
        self._jobs_meta[job_id] = {
            "cron": cron_expr, "source": "strategy", "strategy_id": strategy_id,
        }
        logger.info("[PrefectScheduler] Strategy job registered: '%s' cron='%s'", strategy_id, cron_expr)

    def remove_strategy_job(self, strategy_id: str) -> None:
        """Remove a strategy's cron job from APScheduler."""
        job_id = f"strategy:{strategy_id}"
        try:
            self._scheduler.remove_job(job_id)
        except Exception:
            pass
        self._jobs_meta.pop(job_id, None)
        logger.info("[PrefectScheduler] Strategy job removed: '%s'", strategy_id)

    async def _run_strategy_job(self, strategy_id: str) -> None:
        """Execute a strategy on its scheduled trigger."""
        from ..core.strategy import (
            execute_n8n_strategy,
            execute_script_strategy,
            get_strategy,
            process_signals,
            record_run,
        )

        strat = get_strategy(strategy_id)
        if not strat:
            logger.error("[PrefectScheduler] Strategy '%s' not found — skipping", strategy_id)
            return
        if strat.status != "running":
            logger.info("[PrefectScheduler] Strategy '%s' is stopped — skipping", strategy_id)
            return

        logger.info("[PrefectScheduler] Running strategy '%s' (type=%s)", strategy_id, strat.type)
        loop = asyncio.get_event_loop()
        result_summary = ""

        try:
            if strat.type == "script":
                signals = await loop.run_in_executor(None, execute_script_strategy, strat)
                summary = process_signals(strat, signals)
                result_summary = json.dumps(summary, ensure_ascii=False)

            elif strat.type == "prompt":
                session_id = f"strategy:{strategy_id}"
                agent = self._sm.get_or_create(session_id)
                prompt = strat.prompt_template or ""
                if strat.params:
                    prompt += f"\n\nStrategy parameters: {json.dumps(strat.params)}"
                response = await loop.run_in_executor(None, agent.chat, prompt)
                result_summary = response[:2000] if response else ""

            elif strat.type == "n8n":
                signals = await loop.run_in_executor(None, execute_n8n_strategy, strat)
                if signals:
                    summary = process_signals(strat, signals)
                    result_summary = json.dumps(summary, ensure_ascii=False)
                else:
                    result_summary = "n8n workflow triggered (async)"

            record_run(strategy_id, result_summary)
            logger.info("[PrefectScheduler] Strategy '%s' completed.", strategy_id)

        except Exception as exc:
            logger.exception("[PrefectScheduler] Strategy '%s' failed: %s", strategy_id, exc)
            record_run(strategy_id, f"ERROR: {exc}")

    async def trigger_strategy(self, strategy_id: str) -> str:
        """Manually trigger a strategy to run once."""
        from ..core.strategy import get_strategy
        strat = get_strategy(strategy_id)
        if not strat:
            return json.dumps({"ok": False, "error": f"Strategy '{strategy_id}' not found."})
        asyncio.create_task(self._run_strategy_job(strategy_id=strategy_id))
        return json.dumps({"ok": True, "message": f"Strategy '{strategy_id}' triggered."})

    # ── Extended API (for REST endpoints and agent tools) ────────────────────

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
        return f"Job '{job_id}' triggered. Check Prefect UI: {self.prefect_ui_url}"

    def _query_prefect_api(self, path: str, body: dict | None = None) -> list | dict | None:
        """Helper to query the Prefect REST API."""
        if not self._prefect_ready:
            return None
        try:
            import httpx
            url = f"{self.prefect_api_url}{path}"
            if body is not None:
                resp = httpx.post(url, json=body, timeout=10)
            else:
                resp = httpx.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as exc:
            logger.debug("[PrefectScheduler] Prefect API query failed: %s", exc)
        return None

    @staticmethod
    def _parse_run(run: dict) -> dict:
        """Convert a Prefect flow-run JSON object to our common dict format."""
        state = run.get("state", {}) or {}
        state_type = state.get("type", "UNKNOWN")
        start_time = run.get("start_time") or run.get("expected_start_time") or ""
        end_time = run.get("end_time") or ""
        duration = 0.0
        if start_time and end_time:
            try:
                from datetime import datetime as _dt
                st = _dt.fromisoformat(start_time.replace("Z", "+00:00"))
                et = _dt.fromisoformat(end_time.replace("Z", "+00:00"))
                duration = (et - st).total_seconds()
            except Exception:
                pass
        return {
            "run_id": run.get("id", ""),
            "status": state_type.lower(),
            "start_time": str(start_time)[:19] if start_time else "",
            "duration_seconds": round(duration, 2),
            "success": state_type == "COMPLETED",
            "name": run.get("name", ""),
        }

    def get_job_runs(self, job_id: str, max_results: int = 20) -> list[dict]:
        """Get recent Prefect flow runs for a specific job (filtered by tag)."""
        body = {
            "flow_runs": {"tags": {"all_": [job_id]}},
            "sort": "START_TIME_DESC",
            "limit": max_results,
        }
        data = self._query_prefect_api("/flow_runs/filter", body)
        if not data or not isinstance(data, list):
            return []
        return [self._parse_run(r) for r in data]

    def get_all_runs(self, max_results: int = 50) -> list[dict]:
        """Get recent runs across all cron jobs (tagged 'cron')."""
        body = {
            "flow_runs": {"tags": {"all_": ["cron"]}},
            "sort": "START_TIME_DESC",
            "limit": max_results,
        }
        data = self._query_prefect_api("/flow_runs/filter", body)
        if not data or not isinstance(data, list):
            return []
        results = []
        for r in data:
            parsed = self._parse_run(r)
            tags = r.get("tags", []) or []
            job_tag = next((t for t in tags if t != "cron"), "")
            parsed["job_id"] = job_tag
            results.append(parsed)
        return results

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

    def prefect_status(self) -> dict:
        """Get Prefect server status."""
        return {
            "running": self._prefect_ready,
            "ui_url": self.prefect_ui_url,
            "api_url": self.prefect_api_url,
            "pid": self._prefect_process.pid if self._prefect_process else None,
        }
