# AI agents and MCP

Claude, or any app that speaks the Model Context Protocol (MCP), can work in the ERP through **AI agents**. Each agent works as one staff login, so it sees and does only what that person may, and everything it does is in the activity log as *"Person (AI agent: Agent name)"*.

## Set one up

1. Sign in as the director or a super admin and open **Settings → AI agents & MCP**.
2. **New agent**: pick a job (business analyst, sales assistant, project monitor, procurement, collections, service desk, or your own), choose whose login it works as, and choose **Read only** or **Read & write**. An optional end date stops it working after that day.
3. Copy the key. It is shown once; the server keeps only a SHA-256 hash. Lost it? **New key** on the agent's card (the old one stops at once).
4. Add it to Claude:
   - **Claude (web, desktop, phone)**: Customize → Connectors → + Add → Add custom connector. Name *Sellandiamman Power Infra*, server address `https://www.sellandiammanpowerinfra.com/api/mcp`, authentication **No sign in**, and under **Request headers** add `Authorization` = `Bearer spi_…`. On Team and Enterprise plans an owner adds it under Organization settings → Connectors. Then switch it on in a chat from **+ → Connectors**.
   - **Claude Code**: `claude mcp add --transport http --scope user spi-power-infra https://www.sellandiammanpowerinfra.com/api/mcp --header "Authorization: Bearer spi_…"`
   - **Apps that only take an address**: `https://www.sellandiammanpowerinfra.com/api/mcp?key=spi_…` (the key then also appears in nginx's access log, so prefer the header).

## What an agent can and can't do

- The login's role decides what it can open, which branches it sees and which fields are hidden (cost prices, salaries…), the same as on screen.
- **Read only** agents look things up, run reports and read screens. **Read & write** agents can also add and change records and run status actions (submit for approval, start, complete…), with the usual numbering, totals, GST, routing, notifications and approval rules.
- Whatever the role, an agent **never** deletes, decides approvals, changes logins, keys or company settings, publishes the website, opens the password vault, checks in or out, applies for leave or runs payroll (`core.agent_blocked`).
- 240 calls a minute per agent. Every call is listed under **Activity** for 90 days; pausing or revoking an agent stops it at once.

## Tools the AI gets

| Tool | What it does |
|---|---|
| `whoami` | The agent, the login it works as, access level, today's date (IST), currency conventions |
| `overview` | The person's dashboard, approvals waiting, things expiring in 30 days |
| `list_record_types` / `describe_record_type` | The record types it may open; fields, choices, statuses and actions of one |
| `search` | One search across leads, clients, projects, POs, invoices, tickets, equipment… |
| `list_records` / `get_record` | Lists with text search, filters, dates, sorting and pages; one record in full (by id or code) with history |
| `create_record`, `update_record`, `run_action` | Read & write agents only |
| `list_reports` / `run_report` | The 24 reports as rows and columns |
| `list_endpoints` / `call_api` | Computed screens: CEO view, finance, stock, project hub, pipeline, service, expiries |

Ready-made prompts: *Daily brief*, *Lead follow-ups*, *Project risk review*, *Collections list*.

## How it works

- `POST /api/mcp`: JSON-RPC 2.0 over Streamable HTTP, plain JSON answers, no session (`GET` answers 405). Protocol versions 2025-06-18, 2025-03-26 and 2024-11-05. Code: `backend/routes_ai.py`.
- Each tool call runs as an ordinary request inside the server, signed with a two-minute token for the agent (`core.make_agent_token`), so the same permission checks and audit trail apply as in the app. The token is never handed out.
- Collections: `ai_agents` (key hash, prefix, version, who it works as, access, status, last use) and `ai_agent_calls` (tool, arguments with secrets masked, result, time, IP).
- Caddy answers `/.well-known/oauth-*` with 404, so Claude's connector setup sees there is no OAuth sign-in and uses the request header.
- Tests: `backend/tests/test_ai_mcp.py`. Checked with the official MCP Python SDK client over HTTP, with the key in a header and in the address.
