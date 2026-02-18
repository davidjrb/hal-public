#!/usr/bin/env python3
"""
runopencode.py — clean wrapper for `opencode run`

Examples:
  python runopencode.py --input "What is 2+2?"
  echo "Tell me a joke" | python runopencode.py
  python runopencode.py --input "Hello" --model openai/gpt-5.2 --variant medium
  python runopencode.py --input "Hello" --raw
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from typing import Optional

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
BUILD_LINE_RE = re.compile(r"^\s*>\s*build\b", re.IGNORECASE)


def strip_ansi(s: str) -> str:
    return ANSI_RE.sub("", s)


def extract_answer(text: str) -> str:
    """
    Heuristic:
    - Strip ANSI
    - Remove opencode metadata lines (e.g., '> build · ...') wherever they appear
    - Trim leading/trailing blank lines
    """
    txt = strip_ansi(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in txt.split("\n")]

    cleaned_lines: list[str] = []
    for ln in lines:
        if BUILD_LINE_RE.match(ln):
            continue
        cleaned_lines.append(ln)

    # trim leading/trailing empties
    while cleaned_lines and cleaned_lines[0].strip() == "":
        cleaned_lines.pop(0)
    while cleaned_lines and cleaned_lines[-1].strip() == "":
        cleaned_lines.pop()

    return "\n".join(cleaned_lines).strip()


def read_prompt(cli_input: Optional[str]) -> str:
    if cli_input is not None and cli_input.strip():
        return cli_input.strip()

    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            return data

    raise SystemExit("No input provided. Use --input or pipe via stdin.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", help="Prompt text. If omitted, reads from stdin.")
    ap.add_argument("--model", default="openai/gpt-5.2")
    ap.add_argument("--variant", default="medium")
    ap.add_argument("--session", help="Session ID for conversation continuity.")
    ap.add_argument("--format", help="Output format (e.g., 'json' for structured NDJSON).")
    ap.add_argument("--opencode", default="opencode", help="Path to opencode binary.")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument(
        "--raw",
        action="store_true",
        help="Print raw cleaned output (stdout+stderr) for debugging.",
    )
    args = ap.parse_args()

    prompt = read_prompt(args.input)

    cmd = [
        args.opencode,
        "run",
        prompt,
        f"--model={args.model}",
        f"--variant={args.variant}",
    ]

    if args.session:
        cmd.append(f"--session={args.session}")

    if args.format:
        cmd.append(f"--format={args.format}")

    env = os.environ.copy()
    # Encourage non-fancy output (still safe if opencode ignores)
    env.setdefault("TERM", "dumb")
    env.setdefault("NO_COLOR", "1")
    env.setdefault("CLICOLOR", "0")

    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            env=env,
            timeout=args.timeout,
        )
    except FileNotFoundError:
        print(
            f"ERROR: '{args.opencode}' not found in PATH (or provide --opencode).",
            file=sys.stderr,
        )
        return 127
    except subprocess.TimeoutExpired:
        print("ERROR: opencode timed out.", file=sys.stderr)
        return 124

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    if args.raw:
        combined = (stdout + ("\n" + stderr if stderr else "")).strip()
        print(strip_ansi(combined))
        return 0 if proc.returncode == 0 else proc.returncode

    if proc.returncode != 0:
        combined = (stdout + ("\n" + stderr if stderr else "")).strip()
        print(strip_ansi(combined) or f"ERROR: opencode exited {proc.returncode}", file=sys.stderr)
        return proc.returncode

    # JSON mode: print raw stdout (valid NDJSON) for the caller to parse
    if args.format == "json":
        print(stdout.strip())
        return 0

    # Prefer stdout for the answer; opencode often prints status to stderr
    primary = stdout if stdout.strip() else stderr
    answer = extract_answer(primary)

    print(
        answer
        if answer
        else "I ran the request but didn’t get a readable answer. Try --raw to debug."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
