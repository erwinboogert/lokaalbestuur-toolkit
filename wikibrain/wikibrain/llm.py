"""LLM interface via Claude Code CLI — geen API key nodig."""

import subprocess
import json
import re


def ask_claude(prompt: str, system: str = "", max_tokens: int = 2000) -> str:
    """Stuur een prompt naar Claude via de claude CLI."""
    cmd = ["claude", "--print"]

    if system:
        cmd.extend(["--system-prompt", system])

    cmd.append(prompt)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI fout: {result.stderr.strip()}")

    return result.stdout.strip()


def ask_claude_json(prompt: str, system: str = "", max_tokens: int = 2000) -> dict:
    """Stuur een prompt naar Claude en parse het antwoord als JSON."""
    raw = ask_claude(prompt, system=system, max_tokens=max_tokens)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"Geen JSON gevonden in Claude-antwoord:\n{raw[:200]}")
