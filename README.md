# HAL

An autonomous WhatsApp chatbot running on a local Ubuntu VM. Users send WhatsApp messages via the Twilio Sandbox; the agent polls for new messages, generates responses using GPT-5.2 through the `opencode` CLI, and replies through the Twilio API.

## How It Works

```
You (WhatsApp) --> Twilio Sandbox (<YOUR_TWILIO_NUMBER>)
                        |
                        | polled every 5s
                        v
                   agent.py (VM)
                        |
                        | opencode run --> GPT-5.2
                        v
                   Twilio API
                        |
                        v
You (WhatsApp) <-- Twilio Sandbox
```

No webhooks, no public ports. The agent polls the Twilio Messages API for inbound messages and responds through the same API.

## Chat Commands

| Command | Description |
|---|---|
| `--id` | Show current session ID and alias |
| `--new` | Start a fresh conversation (clears session) |
| `--rename <name>` | Give the current session a memorable alias |
| `--resume <name or id>` | Switch back to a previous session by alias or ID |

Session memory is persistent. HAL remembers what you talked about within a session. Use `--new` to start fresh and `--resume` to pick up where you left off.

## Project Structure

```
.
├── whatsapp/
│   ├── agent.py              # Main agent loop (v11) — polls, generates, replies
│   ├── HAL_IDENTITY.md       # System prompt / persona definition
│   └── requirements.txt      # Python dependencies (twilio, etc.)
├── runopencode.py            # Wrapper for the opencode CLI
├── config/
│   └── twilio.env.example    # Template for Twilio credentials
├── systemd/
│   └── whatsapp-poller.service  # systemd user service definition
├── scripts/
│   ├── apply_whatsapp_poller.sh # One-shot setup: venv, systemd, linger
│   └── deploy_twilio_function.sh
├── twilio/
│   └── whatsapp-receiver/    # Twilio Function (empty TwiML to silence auto-reply)
├── docs/
│   ├── HAL_Description.md    # Full system and VM documentation
│   └── twilio.md             # Twilio account, sandbox, and WhatsApp group limitations
├── INSTRUCTIONS.md           # SSH and git workflow reference for LLM agents
└── TODO.md                   # Improvement tracker
```

## VM Environment

| Property | Value |
|---|---|
| Hostname | `<YOUR_USER>` |
| OS | Ubuntu 24.04.3 LTS |
| SSH | `ssh <YOUR_USER>@<ip>` (key auth) |
| Shell | fish 3.7.0 |
| Python | 3.12.3 |
| Service | `systemctl --user status whatsapp-poller` |

## Key Design Decisions

**Polling over webhooks** — The VM has no public IP. Polling every 5 seconds avoids tunneling, port forwarding, or exposing the machine to the internet.

**Per-user sessions** — Each WhatsApp user gets a persistent conversation session stored in `agent_state.json`. Sessions are managed via opencode's `--session` flag. The identity prompt (HAL_IDENTITY.md) is sent only on the first message of a session to save tokens.

**Session aliases** — Session IDs are opaque (`ses_abc123...`). Users can assign memorable names with `--rename` and switch between sessions with `--resume`.

## Setup

1. Clone to the VM:
   ```
   git clone <YOUR_REPO_URL> ~/instructions
   ```

2. Create the credentials file:
   ```
   cp config/twilio.env.example ~/.config/whatsapp-agent/twilio.env
   # Edit with your TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
   ```

3. Run the deploy script:
   ```
   bash scripts/apply_whatsapp_poller.sh
   ```

4. Join the Twilio WhatsApp Sandbox from your phone (see the join keyword in your Twilio Console).

## Development Workflow

Changes are made on the Windows host and deployed via git:

```
[Windows]  git push origin main
[VM]       cd ~/instructions && git pull origin main
[VM]       systemctl --user restart whatsapp-poller
```
