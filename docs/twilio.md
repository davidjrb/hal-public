# Twilio & WhatsApp Setup

## Account

- **Account SID**: `<YOUR_ACCOUNT_SID>`
- **Profile name**: David
- **Account type**: Free/trial (no purchased phone numbers)
- **CLI profile**: Configured on VM via `twilio profiles:list`

## WhatsApp Number

HAL uses the **Twilio WhatsApp Sandbox**, not a production sender.

- **Number**: `+1 (415) 523-8886` — this is a shared Twilio sandbox number, not owned by us
- **Your phone**: `+1 (431) 458-5769` — the only user currently opted in
- **Join keyword**: Users must text `join <your-keyword>` to the sandbox number to opt in (keyword is in the Twilio Console under Messaging > Try it out > Send a WhatsApp message)

## Sandbox Limitations

| Limitation | Details |
|---|---|
| **Shared number** | `<YOUR_TWILIO_NUMBER>` is shared across all Twilio sandbox users globally |
| **Opt-in required** | Every user must send the `join` keyword before receiving messages |
| **Sessions expire** | Users must re-join every 3 days |
| **24-hour window** | Can only send free-form replies within 24 hours of the user's last message |
| **No custom templates** | Only 3 pre-approved templates (appointment reminders, order notifications, verification codes) |
| **Rate limited** | Max 1 message every 3 seconds |
| **No group chats** | Cannot add the sandbox number to WhatsApp groups |
| **Testing only** | Twilio explicitly says the sandbox is not for production use |

## Can HAL Be Added to WhatsApp Groups?

**No. Not with the current setup, and not easily even with an upgrade.**

### Why it doesn't work now

The sandbox is a 1-to-1 messaging channel. The sandbox number cannot be added to WhatsApp groups. It can only exchange messages with individual users who have opted in via the `join` keyword.

### What about upgrading to production?

Even with a production WhatsApp Business number, native group support is extremely restricted:

- **Meta deprecated the WhatsApp Groups API in 2020**, removing it from the Business API entirely.
- **Meta reintroduced a Groups API in October 2025** via the Cloud API, but it's only available to accounts that either:
  - Have **Official Business Account (OBA) status** (green checkmark, verified by Meta), or
  - Handle **100,000+ business-initiated messages per month**
- Neither of those applies to this project.

### Workarounds that exist

1. **Twilio Conversations API** — simulates group chat by relaying messages between participants through a single Twilio number. Each person chats 1-on-1 with the bot, and Twilio routes messages between all participants. This is not a real WhatsApp group — it's a Twilio-managed fan-out. Participants don't see each other's numbers or a group name in their WhatsApp app.

2. **Unofficial APIs** (Whapi.Cloud, Maytapi, WaSenderAPI) — these connect a regular WhatsApp account (not Business API) to a server, giving full group support. They work but are not Meta-sanctioned, carry a risk of number bans, and require a separate phone number with WhatsApp installed.

## Upgrading to Production (If Needed Later)

To move from sandbox to a real WhatsApp Business sender via Twilio:

1. **Self Sign-Up** through Twilio Console (free)
2. **Meta Business Portfolio** — need admin access to one, or create a new one
3. **Meta Business Verification** — submit business docs, takes days to weeks
4. **Phone number** — need a number not already registered with WhatsApp (can use a Twilio-purchased number or your own)
5. **Cost**: Twilio charges $0.005/message + Meta's per-template fees (utility messages within the 24-hour window are free as of July 2025)

This unlocks: messaging any WhatsApp user (no join keyword), custom templates, automation at scale, and interactive buttons/lists.

## Architecture (Current)

```
Your Phone ──WhatsApp──> Twilio Sandbox (<YOUR_TWILIO_NUMBER>)
                              │
                              │ (polled every 5s via Twilio REST API)
                              ▼
                         agent.py (VM)
                              │
                              │ opencode run → GPT-5.2
                              ▼
                         Twilio REST API
                              │
                              ▼
Your Phone <──WhatsApp── Twilio Sandbox (<YOUR_TWILIO_NUMBER>)
```

No webhooks are used. The agent polls the Twilio Messages API for new inbound messages.
