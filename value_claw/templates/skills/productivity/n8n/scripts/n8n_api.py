#!/usr/bin/env python3
"""n8n REST API client for value_claw.

Supports: list/trigger/activate workflows, list/inspect executions,
and fire webhook-triggered workflows.

Configuration is read from value_claw.json (skills.n8n.baseUrl / apiKey)
or from N8N_BASE_URL / N8N_API_KEY environment variables.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests

# ── Config ───────────────────────────────────────────────────────────────────

def _load_config() -> tuple[str, str]:
    """Return (base_url, api_key) from value_claw.json or env."""
    base_url = os.environ.get("N8N_BASE_URL", "")
    api_key = os.environ.get("N8N_API_KEY", "")

    if not base_url or not api_key:
        try:
            cfg_path = os.path.expanduser("~/.value_claw/value_claw.json")
            if not os.path.exists(cfg_path):
                cfg_path = os.path.join(os.getcwd(), "value_claw.json")
            if os.path.exists(cfg_path):
                with open(cfg_path) as f:
                    cfg = json.load(f)
                n8n_cfg = cfg.get("skills", {}).get("n8n", {})
                base_url = base_url or n8n_cfg.get("baseUrl", "")
                api_key = api_key or n8n_cfg.get("apiKey", "")
        except Exception:
            pass

    if not base_url:
        base_url = "http://localhost:5678"

    return base_url.rstrip("/"), api_key


def _headers(api_key: str) -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        h["X-N8N-API-KEY"] = api_key
    return h


def _api(method: str, path: str, base_url: str, api_key: str, **kwargs) -> Any:
    """Make an API request to n8n and return JSON."""
    url = f"{base_url}/api/v1{path}"
    resp = requests.request(method, url, headers=_headers(api_key), timeout=30, **kwargs)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        return {"status": resp.status_code, "text": resp.text[:500]}


# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_workflows(base_url: str, api_key: str, **_kw) -> None:
    data = _api("GET", "/workflows", base_url, api_key)
    workflows = data.get("data", data) if isinstance(data, dict) else data
    if not workflows:
        print("No workflows found.")
        return
    items = workflows if isinstance(workflows, list) else [workflows]
    for wf in items:
        active = "✅" if wf.get("active") else "⏸️"
        print(f"  {active} [{wf.get('id')}] {wf.get('name', '?')}")


def cmd_workflow(base_url: str, api_key: str, workflow_id: str, **_kw) -> None:
    data = _api("GET", f"/workflows/{workflow_id}", base_url, api_key)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_trigger(base_url: str, api_key: str, workflow_id: str, data: str | None = None, **_kw) -> None:
    """Trigger a workflow execution via the API (requires workflow to be active)."""
    body = json.loads(data) if data else {}
    result = _api("POST", f"/workflows/{workflow_id}/run", base_url, api_key, json=body)
    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_webhook(base_url: str, api_key: str, webhook_path: str, data: str | None = None, **_kw) -> None:
    """Fire a webhook-triggered workflow."""
    body = json.loads(data) if data else {}
    url = f"{base_url}/webhook/{webhook_path}"
    resp = requests.post(url, json=body, timeout=30)
    try:
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(f"Status: {resp.status_code}\n{resp.text[:500]}")


def cmd_activate(base_url: str, api_key: str, workflow_id: str, **_kw) -> None:
    result = _api("PATCH", f"/workflows/{workflow_id}", base_url, api_key, json={"active": True})
    print(f"Workflow {workflow_id} activated." if result.get("active") else json.dumps(result))


def cmd_deactivate(base_url: str, api_key: str, workflow_id: str, **_kw) -> None:
    result = _api("PATCH", f"/workflows/{workflow_id}", base_url, api_key, json={"active": False})
    print(f"Workflow {workflow_id} deactivated." if not result.get("active") else json.dumps(result))


def cmd_executions(base_url: str, api_key: str, limit: int = 10, workflow: str | None = None, **_kw) -> None:
    params: dict[str, Any] = {"limit": limit}
    if workflow:
        params["workflowId"] = workflow
    data = _api("GET", "/executions", base_url, api_key, params=params)
    execs = data.get("data", data) if isinstance(data, dict) else data
    if not execs:
        print("No executions found.")
        return
    items = execs if isinstance(execs, list) else [execs]
    for ex in items:
        status = ex.get("status", ex.get("finished", "?"))
        icon = "✅" if status in ("success", True) else "❌" if status in ("error", "failed", "crashed") else "⏳"
        wf_name = ex.get("workflowData", {}).get("name", "") or ex.get("workflowId", "")
        started = str(ex.get("startedAt", ""))[:19]
        print(f"  {icon} [{ex.get('id')}] {wf_name} | {started} | {status}")


def cmd_execution(base_url: str, api_key: str, execution_id: str, **_kw) -> None:
    data = _api("GET", f"/executions/{execution_id}", base_url, api_key)
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="n8n API client")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("workflows", help="List all workflows")

    p = sub.add_parser("workflow", help="Get workflow details")
    p.add_argument("workflow_id")

    p = sub.add_parser("trigger", help="Trigger a workflow")
    p.add_argument("workflow_id")
    p.add_argument("--data", default=None, help="JSON payload")

    p = sub.add_parser("webhook", help="Fire a webhook")
    p.add_argument("webhook_path")
    p.add_argument("--data", default=None, help="JSON payload")

    p = sub.add_parser("activate", help="Activate a workflow")
    p.add_argument("workflow_id")

    p = sub.add_parser("deactivate", help="Deactivate a workflow")
    p.add_argument("workflow_id")

    p = sub.add_parser("executions", help="List recent executions")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--workflow", default=None, help="Filter by workflow ID")

    p = sub.add_parser("execution", help="Get execution details")
    p.add_argument("execution_id")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    base_url, api_key = _load_config()
    if not api_key:
        print("Warning: No n8n API key configured. Set N8N_API_KEY or skills.n8n.apiKey in value_claw.json",
              file=sys.stderr)

    dispatch = {
        "workflows": cmd_workflows,
        "workflow": cmd_workflow,
        "trigger": cmd_trigger,
        "webhook": cmd_webhook,
        "activate": cmd_activate,
        "deactivate": cmd_deactivate,
        "executions": cmd_executions,
        "execution": cmd_execution,
    }

    fn = dispatch[args.command]
    kwargs = vars(args)
    kwargs.pop("command")
    try:
        fn(base_url=base_url, api_key=api_key, **kwargs)
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to n8n at {base_url}. Is n8n running?", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
