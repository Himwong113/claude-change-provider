"""Execute Claude Code with vendor environment."""

import os
import shutil
import sys

from claudeapikey.env_builder import build_env


def find_claude() -> str | None:
    """Find the claude executable in PATH."""
    return shutil.which("claude")


def run_vendor(vendor_name: str, extra_args: list[str] | None = None) -> None:
    """Run Claude Code with the environment for the given vendor.

    Uses os.execvpe to replace the current process cleanly.
    """
    claude_path = find_claude()
    if claude_path is None:
        print("Error: 'claude' command not found in PATH.", file=sys.stderr)
        print("Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code/setup", file=sys.stderr)
        sys.exit(1)

    env = build_env(vendor_name)
    # Merge with current environment
    new_env = os.environ.copy()
    new_env.update(env)

    args = [claude_path, "--model", new_env["ANTHROPIC_MODEL"]]
    if extra_args:
        args.extend(extra_args)

    os.execvpe(claude_path, args, new_env)
