from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DOTENV_LOADED = False


def _load_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
    _DOTENV_LOADED = True


def _timeout(backend: str) -> float:
    for key in (f"{backend.upper()}_CLI_TIMEOUT", "CLI_SUBPROCESS_TIMEOUT", "CLI_TIMEOUT"):
        raw = os.environ.get(key, "").strip()
        if raw:
            try:
                return float(raw)
            except ValueError:
                break
    return 600.0


def _run(
    cmd: list[str],
    *,
    label: str,
    timeout: float,
    stdin: Optional[str] = None,
) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(
            cmd,
            input=stdin,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Cannot find {label} CLI: {cmd[0]}. Install it and log in first.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"{label} CLI timed out after {timeout}s.") from exc

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"{label} CLI failed with exit {proc.returncode}: {detail[:500]}")
    return proc


def _run_claude(text: str, model: str, effort: str) -> str:
    cmd = [os.environ.get("CLAUDE_CLI_BIN", "claude"), "-p", "--output-format", "text"]
    if effort:
        cmd += ["--effort", effort]
    if model:
        cmd += ["--model", model]
    proc = _run(cmd, label="Claude", timeout=_timeout("claude"), stdin=text)
    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError("Claude CLI returned empty output.")
    return out


def _run_codex(text: str, model: str, effort: str) -> str:
    fd, temp_name = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    output_path = Path(temp_name)
    try:
        cmd = [
            os.environ.get("CODEX_CLI_BIN", "codex"),
            "exec",
            "--skip-git-repo-check",
            "-o",
            str(output_path),
        ]
        if effort:
            cmd[3:3] = ["-c", f'model_reasoning_effort="{effort}"']
        if model:
            cmd += ["-m", model]
        cmd.append(text)
        _run(cmd, label="Codex", timeout=_timeout("codex"))
        out = output_path.read_text(encoding="utf-8").strip()
        if not out:
            raise RuntimeError("Codex CLI returned empty output.")
        return out
    finally:
        try:
            output_path.unlink()
        except OSError:
            pass


def run_cli(
    backend: str,
    text: str,
    model: str = "",
    effort: str = "",
    *,
    env_override: Optional[dict[str, str]] = None,
) -> str:
    _load_dotenv()
    if env_override:
        os.environ.update(env_override)

    normalized = (backend or "").strip().lower()
    if normalized == "claude":
        return _run_claude(text, model, effort)
    if normalized == "codex":
        return _run_codex(text, model, effort)
    raise RuntimeError(f"Local CLI transport only supports claude/codex, got {backend!r}.")
