"""bandit adapter — Python security scanning (venv-installed tool).

bandit exit codes: 0 = clean, 1 = findings, other = error.
Severity map: HIGH->critical MEDIUM->major LOW->minor.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fail, make_issue, read_file_list, write_result  # noqa: E402

SEV = {"HIGH": "critical", "MEDIUM": "major", "LOW": "minor"}
ENGINES_DIR = os.path.expanduser("~/.codespot/engines")


def find_bandit():
    venv = sorted(glob.glob(os.path.join(ENGINES_DIR, "bandit-*", "bin", "bandit")))
    return venv[-1] if venv else shutil.which("bandit")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    bandit = find_bandit()
    if not bandit:
        fail("bandit not installed; run: codespot setup")
    entries = read_file_list(a.files)
    paths = [e["path"] if os.path.isabs(e["path"]) else os.path.join(a.workdir, e["path"])
             for e in entries if (e.get("language") == "py" or e["path"].endswith(".py"))]
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        write_result(a.out, [])
        return

    r = subprocess.run([bandit, "-q", "-f", "json"] + paths,
                       capture_output=True, text=True, timeout=300)
    if r.returncode not in (0, 1):
        fail("bandit failed (exit %s): %s" % (r.returncode, r.stderr.strip()[:300]))
    try:
        data = json.loads(r.stdout or "{}")
    except ValueError:
        fail("bandit produced invalid JSON")

    issues = []
    for v in data.get("results", []):
        fname = v.get("filename", "")
        rel = os.path.relpath(fname, a.workdir) if os.path.isabs(fname) else fname
        code = v.get("test_id", "unknown")
        snippet = (v.get("code") or "").strip().splitlines()
        issues.append(make_issue(
            tool="bandit", language="py", rule=code,
            rule_url="https://bandit.readthedocs.io/en/latest/plugins/index.html",
            severity=SEV.get(v.get("issue_severity", "MEDIUM"), "major"),
            file=rel, line=v.get("line_number", 1), column=1,
            message=v.get("issue_text", ""),
            snippet=snippet[0][:160] if snippet else "",
            cwe=str(v["test_cwe"].split(",")[0].strip(" CWE")) if v.get("test_cwe") else None))
    write_result(a.out, issues)


if __name__ == "__main__":
    main()
