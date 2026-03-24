---
name: n8n
description: >
  Interact with n8n workflow automation via its REST API. Use when: user asks to
  trigger workflows, list executions, manage workflows, check n8n status, or
  automate tasks through n8n. NOT for: direct API calls (use http_request),
  cron scheduling (use cron_add tool), or one-off shell commands.
dependencies: requests
metadata:
  emoji: "⚡"
---

# n8n Workflow Automation

Trigger, manage, and monitor n8n workflows directly from the agent.

## When to Use

✅ **USE this skill when:**

- "Trigger my n8n data pipeline"
- "List all n8n workflows"
- "Check if the last workflow run succeeded"
- "Activate / deactivate a workflow"
- "Show recent n8n executions"
- "Create a webhook-triggered workflow"

## When NOT to Use

❌ **DON'T use this skill when:**

- Direct HTTP API calls → use `http_request`
- Scheduling agent tasks → use `cron_add` tool
- Shell scripts or one-off commands → use `run_command`

## Setup

1. Make sure n8n is running (self-hosted or cloud)
2. Get an API key from n8n: Settings → API → Create API Key
3. Configure in `value_claw.json`:

```json
"skills": {
  "n8n": {
    "baseUrl": "http://localhost:5678",
    "apiKey": "your-n8n-api-key"
  }
}
```

Or set environment variables:
```bash
export N8N_BASE_URL="http://localhost:5678"
export N8N_API_KEY="your-n8n-api-key"
```

## Commands

### List all workflows

```bash
python {skill_path}/scripts/n8n_api.py workflows
```

### Get workflow details

```bash
python {skill_path}/scripts/n8n_api.py workflow <workflow_id>
```

### Trigger a workflow (by ID or name)

```bash
python {skill_path}/scripts/n8n_api.py trigger <workflow_id> [--data '{"key": "value"}']
```

### Trigger via webhook (if workflow has a webhook trigger)

```bash
python {skill_path}/scripts/n8n_api.py webhook <webhook_path> [--data '{"key": "value"}']
```

### Activate / deactivate a workflow

```bash
python {skill_path}/scripts/n8n_api.py activate <workflow_id>
python {skill_path}/scripts/n8n_api.py deactivate <workflow_id>
```

### List recent executions

```bash
python {skill_path}/scripts/n8n_api.py executions [--limit 10] [--workflow <workflow_id>]
```

### Get execution details

```bash
python {skill_path}/scripts/n8n_api.py execution <execution_id>
```

## Workflow Patterns

### Data Pipeline
1. List workflows to find the pipeline → `workflows`
2. Trigger it with input data → `trigger <id> --data '{"source": "..."}'`
3. Check execution status → `executions --workflow <id> --limit 1`

### Monitoring
1. List recent executions → `executions --limit 20`
2. Filter for failures → look for `status: error` in output
3. Get error details → `execution <id>`

### Integration with Agent Cron
You can combine n8n with the agent's cron system:
- Use `cron_add` to schedule a periodic check
- The cron job triggers n8n workflows as needed
- Results are delivered via Telegram or stored in memory

## Resources

| File | Description |
|------|-------------|
| `scripts/n8n_api.py` | n8n REST API client |
