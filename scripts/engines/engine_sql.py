"""SQLFluff adapter — SQL convention/structure scanning (venv-installed tool).

Dialect chain: in-file `sqlfluff:dialect:<x>` comment > project
.codespot/config.json "dialect" > content heuristics > ansi fallback (+hint).
Pure-style groups (layout.*, capitalisation.*) are dropped client-side —
version-proof across sqlfluff 3.x/4.x rule-code changes.
PRS (parse) violations get unparsable: true and are not fix targets.
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fail, make_issue, read_file_list, write_result  # noqa: E402

ENGINES_DIR = os.path.expanduser("~/.codespot/engines")
RULES_URL = "https://docs.sqlfluff.com/en/stable/reference/rules.html"
DIALECT_COMMENT = re.compile(r"sqlfluff:dialect[:=]\s*(\w+)", re.I)
DIALECT_HINTS = [
    (re.compile(r"AUTO_INCREMENT|ENGINE\s*=\s*InnoDB|`", re.I), "mysql"),
    (re.compile(r"::\s*\w+|\bSERIAL\b|\bRETURNING\b", re.I), "postgres"),
    (re.compile(r"\bGO\b\s*$", re.M), "tsql"),
]
STYLE_PREFIXES = ("layout.", "capitalisation.")


def find_sqlfluff():
    hits = sorted(glob.glob(os.path.join(ENGINES_DIR, "sqlfluff-*", "bin", "sqlfluff")))
    return hits[-1] if hits else shutil.which("sqlfluff")


def read_dialect_config(workdir):
    p = os.path.join(workdir, ".codespot", "config.json")
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f).get("dialect")
            if d:
                return d
        except (OSError, ValueError):
            pass
    return None


def detect_dialect(paths, workdir):
    for fp in paths:
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                head = f.read(4096)
        except OSError:
            continue
        m = DIALECT_COMMENT.search(head)
        if m:
            return m.group(1).lower(), None
    cfg = read_dialect_config(workdir)
    if cfg:
        return cfg.lower(), None
    for rx, dialect in DIALECT_HINTS:
        for fp in paths:
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    if rx.search(f.read()):
                        return dialect, None
            except OSError:
                continue
    return "ansi", "no dialect detected — defaulting to ansi; set \"dialect\" in .codespot/config.json for accurate linting"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    sqlfluff = find_sqlfluff()
    if not sqlfluff:
        fail("sqlfluff not installed; run: codespot setup")
    entries = read_file_list(a.files)
    paths = [e["path"] if os.path.isabs(e["path"]) else os.path.join(a.workdir, e["path"])
             for e in entries if (e.get("language") == "sql" or e["path"].endswith(".sql"))]
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        write_result(a.out, [])
        return

    dialect, hint = detect_dialect(paths, a.workdir)
    if hint:
        sys.stderr.write("codespot-sql: %s\n" % hint)

    cmd = [sqlfluff, "lint", "--dialect", dialect, "--format", "json",
           "--disable-progress-bar"]
    # project-native .sqlfluff config wins over codespot's client-side filtering basis
    native_cfg = os.path.join(a.workdir, ".sqlfluff")
    if os.path.isfile(native_cfg):
        cmd += ["--config", native_cfg]
    cmd += paths
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode not in (0, 1):
        fail("sqlfluff failed (exit %s): %s" % (r.returncode, (r.stderr or r.stdout).strip()[:300]))
    try:
        data = json.loads(r.stdout or "[]")
    except ValueError:
        fail("sqlfluff produced invalid JSON")

    issues = []
    for f in data:
        fname = f.get("filepath", f.get("filename", ""))
        rel = os.path.relpath(fname, a.workdir) if os.path.isabs(fname) else fname
        for v in f.get("violations", []):
            code = v.get("code", "unknown")
            name = v.get("name", "")
            if name.startswith(STYLE_PREFIXES):
                continue  # pure style: out of codespot scope (fix via sqlfluff format)
            line = v.get("start_line_no", v.get("line_no", 1))
            col = v.get("start_line_pos", v.get("line_pos", 1))
            issues.append(make_issue(
                tool="sqlfluff", language="sql", rule=code, rule_url=RULES_URL,
                severity="",  # mapped via rules-severity.json
                file=rel, line=line, column=col,
                message=v.get("description", ""), snippet="",
                fix_hint={"description": "sqlfluff fix"} if not code.startswith("PRS") else None))
            if code.startswith("PRS"):
                issues[-1]["unparsable"] = True
                issues[-1]["severity"] = "minor"
    write_result(a.out, issues)


if __name__ == "__main__":
    main()
