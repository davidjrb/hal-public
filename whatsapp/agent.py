
import os
import time
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from twilio.rest import Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Twilio Configuration
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
FROM_WA = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:<YOUR_TWILIO_NUMBER>")

# Global paths
WRAPPER_SCRIPT = os.path.expanduser("~/instructions/runopencode.py")
OPENCODE_PATH = "/usr/bin/opencode"
PYTHON_PATH = sys.executable

# State file (stores last_processed_time + per-user session mappings)
STATE_FILE = "agent_state.json"

# Identity + audit trail
# Resolve relative to this file so systemd/cwd changes don't break it.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IDENTITY_FILE = os.path.join(SCRIPT_DIR, "HAL_IDENTITY.md")
TRAIL_FILE = "trail.jsonl"

# Chat commands
RESET_COMMANDS = {"--new", "!reset", "!new"}
RESUME_PREFIX = "--resume"
RENAME_PREFIX = "--rename"
ID_COMMAND = "--id"


def load_identity_text() -> str:
    try:
        if os.path.exists(IDENTITY_FILE):
            with open(IDENTITY_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        logging.error(f"Error reading identity file: {e}")
    return ""


def build_prompt(identity_text: str, user_text: str) -> str:
    if not identity_text:
        return user_text
    return (
        f"{identity_text}\n\n"
        "Instructions: Follow the principles and behavior rules above. "
        "Reply to the user message.\n\n"
        f"User message:\n{user_text}"
    )


def append_trail(event: dict) -> None:
    try:
        event = dict(event)
        event.setdefault("ts", datetime.now(timezone.utc).isoformat())
        with open(TRAIL_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=True) + "\n")
    except Exception as e:
        logging.error(f"Error writing trail: {e}")


# ---------------------------------------------------------------------------
# State management (last_processed_time + session mappings)
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    """Load the full state dict from disk."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Error reading state file: {e}")
    return {}


def _save_state(state: dict) -> None:
    """Write the full state dict to disk."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving state file: {e}")


def get_last_processed_time():
    state = _load_state()
    lpt = state.get('last_processed_time')
    if lpt:
        return datetime.fromisoformat(lpt)
    return datetime.now(timezone.utc)


def save_last_processed_time(dt):
    state = _load_state()
    state['last_processed_time'] = dt.isoformat()
    _save_state(state)


def get_session_id(phone: str):
    """Look up stored opencode session ID for a phone number."""
    state = _load_state()
    return state.get('sessions', {}).get(phone)


def save_session_id(phone: str, session_id: str) -> None:
    """Persist an opencode session ID for a phone number."""
    state = _load_state()
    sessions = state.setdefault('sessions', {})
    sessions[phone] = session_id
    _save_state(state)
    logging.info(f"Saved session {session_id} for {phone}")


def clear_session(phone: str) -> None:
    """Delete a user's session mapping so the next message starts fresh."""
    state = _load_state()
    sessions = state.get('sessions', {})
    if phone in sessions:
        old = sessions.pop(phone)
        _save_state(state)
        logging.info(f"Cleared session {old} for {phone}")


def session_exists_on_disk(session_id: str) -> bool:
    """Check whether opencode has a stored session file for this ID."""
    import glob
    pattern = os.path.expanduser(
        f"~/.local/share/opencode/storage/session/*/{session_id}.json"
    )
    return len(glob.glob(pattern)) > 0


# ---------------------------------------------------------------------------
# Aliases — human-readable names for sessions
# ---------------------------------------------------------------------------

def get_alias(name: str):
    """Look up a session ID by its alias. Returns None if not found."""
    state = _load_state()
    return state.get('aliases', {}).get(name.lower())


def set_alias(name: str, session_id: str) -> None:
    """Map a human-readable alias to a session ID."""
    state = _load_state()
    aliases = state.setdefault('aliases', {})
    aliases[name.lower()] = session_id
    _save_state(state)
    logging.info(f"Alias '{name}' -> {session_id}")


def get_alias_for_session(session_id: str):
    """Reverse lookup: find the alias for a session ID, if any."""
    state = _load_state()
    for name, sid in state.get('aliases', {}).items():
        if sid == session_id:
            return name
    return None


def resolve_session_or_alias(value: str):
    """
    Given a string that is either a session ID (ses_...) or an alias,
    return the real session ID. Returns None if not resolvable.
    """
    if value.startswith("ses_"):
        return value
    # Try as alias
    return get_alias(value)


def format_session_display(session_id: str) -> str:
    """Format a session ID for display, including alias if one exists."""
    alias = get_alias_for_session(session_id)
    if alias:
        return f'"{alias}" ({session_id})'
    return session_id


# ---------------------------------------------------------------------------
# opencode wrapper call — now with session + JSON support
# ---------------------------------------------------------------------------

def call_opencode_wrapper(prompt, session_id=None):
    """
    Calls runopencode.py with --format=json (and optionally --session).
    Parses NDJSON output to extract the response text and session ID.
    Returns (response_text, session_id_from_output).
    """
    try:
        logging.info(
            f"Calling wrapper with prompt length: {len(prompt)}"
            f" (session: {session_id or 'new'})"
        )

        cmd = [
            PYTHON_PATH,
            WRAPPER_SCRIPT,
            "--input", prompt,
            "--model", "openai/gpt-5.2",
            "--variant", "medium",
            "--opencode", OPENCODE_PATH,
            "--format", "json",
        ]

        if session_id:
            cmd.extend(["--session", session_id])

        start_t = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=130,
            stdin=subprocess.DEVNULL,
        )
        duration = time.time() - start_t

        if result.returncode != 0:
            logging.error(
                f"Wrapper failed (code {result.returncode}): "
                f"{result.stderr[:300]}"
            )
            return ("I'm here \u2014 can you rephrase that?", None)

        stdout = result.stdout.strip()
        logging.info(
            f"Wrapper returned in {duration:.1f}s. Output len: {len(stdout)}"
        )

        if not stdout:
            logging.warning("Wrapper returned empty response.")
            return ("I'm here \u2014 can you rephrase that?", None)

        # Parse NDJSON lines
        response_parts = []
        output_session_id = None

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)

                # Capture session ID from any event
                if not output_session_id:
                    output_session_id = data.get("sessionID")

                # Collect text parts
                if data.get("type") == "text":
                    part = data.get("part", {})
                    text = part.get("text")
                    if text:
                        response_parts.append(text)

            except json.JSONDecodeError:
                logging.warning(f"Failed to parse JSON line: {line[:100]}...")

        response = "".join(response_parts).strip()

        if not response:
            logging.warning("No text parts found in JSON output.")
            return ("I'm here \u2014 can you rephrase that?", output_session_id)

        return (response, output_session_id)

    except subprocess.TimeoutExpired:
        logging.error("Wrapper timed out.")
        return ("Thinking took too long. Please try again.", None)
    except Exception as e:
        logging.error(f"Error calling wrapper: {e}")
        return ("System error processing request.", None)


def send_whatsapp(to, body):
    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)
        # Split message if too long
        max_len = 1500
        chunks = [body[i:i+max_len] for i in range(0, len(body), max_len)]

        for chunk in chunks:
            message = client.messages.create(
                from_=FROM_WA,
                body=chunk,
                to=to
            )
            logging.info(f"Sent message {message.sid} to {to}")
            time.sleep(1)  # Rate limit

    except Exception as e:
        logging.error(f"Failed to send WhatsApp: {e}")


def main():
    logging.info("Agent v11 (Session Aliases) starting...")
    if not ACCOUNT_SID or not AUTH_TOKEN:
        logging.error("Twilio credentials not found")
        return

    identity_text = load_identity_text()
    if identity_text:
        logging.info(f"Loaded identity from {IDENTITY_FILE} ({len(identity_text)} chars)")
    else:
        logging.warning(f"No identity loaded (missing/empty {IDENTITY_FILE})")

    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    last_processed = get_last_processed_time()
    logging.info(f"Resuming from {last_processed}")

    while True:
        try:
            # Poll for messages
            messages = client.messages.list(
                date_sent_after=last_processed - timedelta(minutes=5),
                to=FROM_WA,
                limit=50
            )

            new_messages = []
            for msg in reversed(messages):
                if msg.direction != 'inbound':
                    continue

                if msg.date_sent:
                    msg_date = msg.date_sent.astimezone(timezone.utc)
                else:
                    continue

                if msg_date <= last_processed:
                    continue

                new_messages.append((msg_date, msg))

            for msg_date, msg in new_messages:
                user_text = (msg.body or "").strip()
                user_lower = user_text.lower()
                logging.info(f"Received message from {msg.from_}: {user_text}")

                # ---- Command: --id ----
                if user_lower == ID_COMMAND:
                    cur = get_session_id(msg.from_)
                    if cur:
                        reply = f"Current session: {format_session_display(cur)}"
                    else:
                        reply = "No active session. Send a message to start one."
                    send_whatsapp(msg.from_, reply)
                    last_processed = msg_date
                    save_last_processed_time(last_processed)
                    continue

                # ---- Command: --rename <alias> ----
                if user_lower.startswith(RENAME_PREFIX):
                    alias = user_text[len(RENAME_PREFIX):].strip()
                    cur = get_session_id(msg.from_)
                    if not cur:
                        send_whatsapp(msg.from_, "No active session to rename.")
                    elif not alias:
                        send_whatsapp(msg.from_, "Usage: --rename <name>")
                    else:
                        set_alias(alias, cur)
                        send_whatsapp(
                            msg.from_,
                            f'Session renamed to "{alias}"\n({cur})'
                        )
                    append_trail({
                        "from": msg.from_,
                        "to": msg.to,
                        "inbound_ts": msg_date.isoformat(),
                        "inbound": user_text,
                        "action": "session_rename",
                        "session_id": cur,
                        "alias": alias or None,
                    })
                    last_processed = msg_date
                    save_last_processed_time(last_processed)
                    continue

                # ---- Command: --new / !reset / !new ----
                if user_lower in RESET_COMMANDS:
                    old_session = get_session_id(msg.from_)
                    clear_session(msg.from_)
                    reply = "Session cleared. Send a message to start fresh."
                    if old_session:
                        reply += f"\n(Previous: {format_session_display(old_session)})"
                    send_whatsapp(msg.from_, reply)
                    append_trail({
                        "from": msg.from_,
                        "to": msg.to,
                        "inbound_ts": msg_date.isoformat(),
                        "inbound": user_text,
                        "action": "session_reset",
                        "old_session": old_session,
                    })
                    last_processed = msg_date
                    save_last_processed_time(last_processed)
                    continue

                # ---- Command: --resume <session_id or alias> ----
                if user_lower.startswith(RESUME_PREFIX):
                    raw = user_text[len(RESUME_PREFIX):].strip()
                    # Strip optional "id:" prefix
                    if raw.lower().startswith("id:"):
                        raw = raw[3:].strip()
                    if not raw:
                        send_whatsapp(msg.from_, "Usage: --resume <session_id or alias>")
                    else:
                        target_id = resolve_session_or_alias(raw)
                        if not target_id:
                            send_whatsapp(msg.from_, f'Alias "{raw}" not found.')
                        elif not session_exists_on_disk(target_id):
                            send_whatsapp(msg.from_, f"Session {target_id} not found on disk.")
                        else:
                            save_session_id(msg.from_, target_id)
                            send_whatsapp(
                                msg.from_,
                                f"Session resumed: {format_session_display(target_id)}\nSend a message to continue."
                            )
                    append_trail({
                        "from": msg.from_,
                        "to": msg.to,
                        "inbound_ts": msg_date.isoformat(),
                        "inbound": user_text,
                        "action": "session_resume",
                        "target_input": raw if raw else None,
                    })
                    last_processed = msg_date
                    save_last_processed_time(last_processed)
                    continue

                # ---- Normal message processing ----
                existing_session = get_session_id(msg.from_)
                is_new_session = not existing_session

                # Build the prompt:
                # - First message (no session yet): include identity
                # - Continuing session: just the user text (identity is in history)
                if existing_session:
                    prompt = user_text
                else:
                    prompt = build_prompt(identity_text, user_text)

                response, output_session_id = call_opencode_wrapper(
                    prompt, session_id=existing_session
                )

                # Save session mapping if this was a new session
                if is_new_session and output_session_id:
                    save_session_id(msg.from_, output_session_id)

                # Prepend session header on first message of a session
                session_id = output_session_id or existing_session
                if is_new_session and session_id:
                    response = f"[New session: {session_id}]\n\n{response}"

                append_trail({
                    "from": msg.from_,
                    "to": msg.to,
                    "inbound_ts": msg_date.isoformat(),
                    "inbound": user_text,
                    "model": "openai/gpt-5.2",
                    "session_id": session_id,
                    "new_session": is_new_session,
                    "prompt_len": len(prompt),
                    "response_len": len(response or ""),
                    "response": response,
                })

                send_whatsapp(msg.from_, response)

                last_processed = msg_date
                save_last_processed_time(last_processed)

        except Exception as e:
            logging.error(f"Error in main loop: {e}")

        time.sleep(5)


if __name__ == "__main__":
    main()
