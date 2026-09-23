"""ruff adapter — Python quality scanning with fix hints.

Runs `ruff check --output-format json` on the scope files (batched to stay
under ARG_MAX). Severity: explicit map in rules-severity.json (S-family highs
-> critical), everything else defaults to major.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fail, make_issue, read_file_list, write_result  # noqa: E402

BATCH = 100
# secret-bearing rules: the flagged line itself contains a credential,
# so the snippet must not be quoted into reports at all.
NO_SNIPPET_RULES = {"S102", "S103", "S104", "S105", "S106", "S107", "S108"}
CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      "assets", "ruff-defaults.toml")
RULE_URL = "https://docs.astral.sh/ruff/rules/{rule}/"


def find_binary():
    import glob
    home = os.path.expanduser("~/.codespot/engines")
    hits = sorted(glob.glob(os.path.join(home, "ruff-*", "ruff")))
    if hits:
        return hits[-1]
    return shutil.which("ruff")


def _pyproject_has_ruff(workdir):
    p = os.path.join(workdir, "pyproject.toml")
    if not os.path.isfile(p):
        return False
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return "[tool.ruff" in f.read()
    except OSError:
        return False


def to_issues(raw, workdir):
    issues = []
    for v in raw:
        rel = os.path.relpath(v["filename"], workdir) if os.path.isabs(v["filename"]) \
            else v["filename"]
        message = v.get("message", "")
        fix = v.get("fix") or None
        fix_hint = None
        if fix and fix.get("edits"):
            first = fix["edits"][0]
            fix_hint = {"description": fix.get("message", "auto-fixable"),
                        "content": first.get("content", ""),
                        "line": first.get("location", {}).get("row")}
        snippet = ""
        if v["code"] not in NO_SNIPPET_RULES:
            try:
                with open(v["filename"], "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                row = v["location"]["row"]
                if 1 <= row <= len(lines):
                    snippet = lines[row - 1].strip()
            except OSError:
                pass
        issues.append(make_issue(
            tool="ruff", language="py", rule=v["code"],
            rule_url=RULE_URL.format(rule=v["code"].lower()),
            severity="",  # resolved by mapping in make_issue
            file=rel, line=v["location"]["row"], column=v["location"]["column"],
            message=message, snippet=snippet, fix_hint=fix_hint))
    return issues


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    binary = find_binary()
    if not binary:
        fail("ruff binary not found; run: codespot setup")
    entries = read_file_list(a.files)
    paths = [e["path"] if os.path.isabs(e["path"]) else os.path.join(a.workdir, e["path"])
             for e in entries if (e.get("language") == "py" or e["path"].endswith(".py"))]
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        write_result(a.out, [])
        return

    raw = []
    native = any(os.path.isfile(os.path.join(a.workdir, f))
                 for f in (".ruff.toml", "ruff.toml")) or \
        _pyproject_has_ruff(a.workdir)
    for i in range(0, len(paths), BATCH):
        chunk = paths[i:i + BATCH]
        cmd = [binary, "check", "--output-format", "json"]
        if not native:
            cmd += ["--config", CONFIG]
        cmd += chunk
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode not in (0, 1):
            fail("ruff failed (exit %s): %s" % (r.returncode, r.stderr.strip()[:300]))
        try:
            raw.extend(json.loads(r.stdout or "[]"))
        except ValueError:
            fail("ruff produced invalid JSON output")

    write_result(a.out, to_issues(raw, a.workdir))


if __name__ == "__main__":
    main()
