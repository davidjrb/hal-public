# HAL — System Description

## Overview

HAL is an autonomous WhatsApp chatbot running on a local VM. Users send WhatsApp messages via the Twilio Sandbox; the agent polls for new messages, generates a response using an LLM, and replies through the Twilio API.

The project name references HAL 9000 — the agent's git identity is literally "HAL 9000".

## VM Environment

| Property        | Value                                         |
|-----------------|-----------------------------------------------|
| Hostname        | `<YOUR_USER>`                                     |
| User            | `<YOUR_USER>` (passwordless sudo via sudoers.d)   |
| OS              | Ubuntu 24.04.3 LTS (Noble Numbat)             |
| Kernel          | Linux 6.8.0-100-generic (x86_64)              |
| Virtualization  | KVM (QEMU Standard PC Q35)                    |
| CPU             | AMD Ryzen 9 7950X — 8 vCPUs allocated         |
| RAM             | 32 GB (typically ~3.5 GB used)                |
| Disk            | 98 GB LVM volume, ~15 GB used                 |
| IP              | `<YOUR_SERVER_IP>/24`                          |
| Shell           | fish 3.7.0                                    |

## Installed Tools

| Tool       | Version   | Notes                                      |
|------------|-----------|--------------------------------------------|
| Python     | 3.12.3    | System python                              |
| Node.js    | 22.22.0   | Via nodesource                             |
| npm        | 10.9.4    |                                            |
| git        | 2.43.0    | User: "HAL 9000", email: <YOUR_USER>@<YOUR_SERVER_IP> |
| opencode   | 1.1.53    | `/usr/bin/opencode` (opencode-ai, Node-based) |
| fish       | 3.7.0     | Default shell                              |

## SSH Access

- From Windows host: `ssh <YOUR_USER>@<YOUR_SERVER_IP>`
- Authentication: Public key (Ensure your local SSH key is configured)
- GitHub deploy key: `~/.ssh/<YOUR_USER>_deploy_key` (configured in `~/.ssh/config`)

## Git Repository

- **Local path**: `~/instructions`
- **Remote**: `<YOUR_REPO_URL>`
- **Branch**: `main` (single branch)
- **Commits**: 6 commits, from initial README through agent v7

### Commit History

```
83df575 Update agent: add identity prompt and audit trail
f68d7f1 Update agent to v7: use opencode wrapper
6a31cad Update agent to v6: robust fallback parsing and TUI cleanup
0df1231 Implement autonomous WhatsApp agent with TUI wrapper and gpt-5.2
b6a438a Add INSTRUCTIONS.md for next LLM
d8f0fc4 Initial commit: add README.md
```

## Architecture

### Message Flow

```
WhatsApp User
    ↓
Twilio Sandbox (inbound webhook)
    ↓
Twilio Function (whatsapp.js) — returns empty TwiML to silence auto-reply
    ↓
agent.py polls Twilio Messages API every 5 seconds
    ↓
runopencode.py wrapper → `opencode run` CLI → GPT-5.2 (medium variant)
    ↓
Response sent back via Twilio Messages API → WhatsApp User
```

### Key Design Decisions

- **Polling, not webhooks**: Avoids exposing the VM to the internet (no public ports, no tunneling)
- **opencode CLI as LLM interface**: The agent shells out to `opencode run` rather than calling the OpenAI API directly. A Python wrapper (`runopencode.py`) handles ANSI stripping and output cleanup. This is intentional — opencode authenticates via OAuth against the existing ChatGPT Team subscription (`dberman@vestaautomation.com`), so there is no separate API billing required. A direct OpenAI API call was attempted and reverted because the API requires its own billing plan independent of ChatGPT Team.

### Components

| Component | Path | Purpose |
|-----------|------|---------|
| **agent.py** (v7) | `whatsapp/agent.py` | Main agent loop — polls, generates, replies |
| **runopencode.py** | `runopencode.py` | Wrapper to invoke `opencode run` cleanly |
| **HAL_IDENTITY.md** | `whatsapp/HAL_IDENTITY.md` | System prompt / persona definition |
| **whatsapp.js** | `twilio/whatsapp-receiver/functions/whatsapp.js` | Twilio Function — empty TwiML response |
| **systemd service** | `systemd/whatsapp-poller.service` | Manages agent process |
| **deploy script** | `scripts/apply_whatsapp_poller.sh` | One-shot setup: venv, systemd, linger |
| **twilio.env** | `~/.config/whatsapp-agent/twilio.env` | Runtime secrets (SID, token) |

### Agent Identity

The agent is named "HAL" with the role "Automation Assistant" under the project name "<YOUR_ORG_NAME>". Its core principles: keep it simple, reduce manual work, always leave a trail, no silent changes to core.

### Systemd Service

- **Unit**: `whatsapp-poller.service` (user-level)
- **Status**: Active and running (since Feb 9)
- **Restart policy**: `always`, 10s delay
- **Memory usage**: ~1.1 GB (peak 1.4 GB)
- **Linger**: Enabled (service persists after logout)

### State & Data Files

| File | Purpose |
|------|---------|
| `whatsapp/agent_state.json` | Tracks last processed message timestamp |
| `whatsapp/inbox.jsonl` | 10 logged inbound messages (from poll_inbound.py, not used by agent) |
| `whatsapp/trail.jsonl` | Audit trail (defined in agent.py but no file exists yet — may not have processed messages since trail was added) |

## Files on VM Not in the Zip

The following files exist on the server but were not in the uploaded zip:

- `V1_runopencode.py` — Earlier version of the wrapper script
- `whatsapp/test_agent_v7.py` — Another test variant of the agent
- `whatsapp/inbox.jsonl` — 10 inbound messages logged by poll_inbound.py
- `whatsapp/__pycache__/` — Python bytecode cache
- `~/opencode_smoke/` — Smoke test directory with a single text file
- `~/twilio-whatsapp-receiver/` — Duplicate of the Twilio function directory (outside the repo)
- `~/.twilio-cli/` — Twilio CLI configuration

## Authentication & Billing

- **Twilio**: Credentials (SID + auth token) stored in `~/.config/whatsapp-agent/twilio.env`, loaded by systemd. Auth token was rotated on 2026-02-13 after the old one was accidentally committed to git.
- **OpenAI (via opencode)**: Authenticated via OAuth, stored in `~/.local/share/opencode/auth.json`. Uses the ChatGPT Team subscription — no separate API billing. The OAuth token includes a refresh token for automatic renewal.
- **OpenAI API (direct)**: Not available. The `sk-proj-...` API key requires its own billing plan separate from ChatGPT Team. Attempted and reverted on 2026-02-13.

## Current Operational Notes

- The agent is **currently running** and actively polling Twilio every 5 seconds
- The Twilio sandbox number is `<YOUR_TWILIO_NUMBER>` (standard Twilio WhatsApp sandbox)
- The model in use is `openai/gpt-5.2` (medium variant)
- Known issue: `opencode run` child processes can occasionally stall/zombie if they hang past the timeout
