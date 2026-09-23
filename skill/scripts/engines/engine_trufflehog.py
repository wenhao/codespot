"""TruffleHog adapter — opt-in deep secrets scanning (800+ detectors).

LICENSE BOUNDARY: AGPL-3.0. Internal use only; binary is downloaded at runtime
and is not distributed with codespot.

Runs `trufflehog filesystem <workdir> --no-verification --json`:
- --no-verification keeps the scan fully local (no network calls to vendors).
- Output is NDJSON; finding lines carry SourceMetadata, log lines do not and
  are skipped.
Exit codes: 0 normally (findings do not change the exit code).
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SEVERITIES, fail, make_issue, read_file_list, redact, write_result  # noqa: E402

ENGINES_DIR = os.path.expanduser("~/.codespot/engines")


def find_trufflehog():
    hits = sorted(glob.glob(os.path.join(ENGINES_DIR, "trufflehog-*", "trufflehog")))
    return hits[-1] if hits else shutil.which("trufflehog")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    binary = find_trufflehog()
    if not binary:
        fail("trufflehog not installed; run: codespot setup")
    entries = read_file_list(a.files)
    if not entries:
        write_result(a.out, [])
        return

    try:
        r = subprocess.run([binary, "filesystem", a.workdir, "--no-verification", "--json"],
                           capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        fail("trufflehog timed out after 600s")
    if r.returncode != 0:
        fail("trufflehog failed (exit %s): %s" % (r.returncode, r.stderr.strip()[:300]))

    issues = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue  # log line
        if "SourceMetadata" not in d:
            continue
        fs = ((d.get("SourceMetadata") or {}).get("Data") or {}).get("Filesystem") or {}
        fp = fs.get("file", "")
        # skip VCS/vendor/build internals — never user-authored secrets
        norm = fp.replace(os.sep, "/")
        if any(seg in norm for seg in ("/.git/", "/.venv/", "/venv/", "/node_modules/",
                                       "/.tox/", "/dist/", "/build/", "site-packages/")):
            continue
        rel = os.path.relpath(fp, a.workdir) if os.path.isabs(fp) else fp
        raw = d.get("Redacted") or d.get("Raw") or ""
        snippet = d.get("Redacted") or redact((d.get("Raw") or "").splitlines()[0] if (d.get("Raw") or "").strip() else "")
        snippet = (snippet or "").splitlines()[0][:160] if (snippet or "").strip() else ""
        issues.append(make_issue(
            tool="trufflehog", language="*", rule=d.get("DetectorName", "unknown"),
            rule_url="https://github.com/trufflesecurity/trufflehog/tree/main/pkg/detectors",
            severity="critical", file=rel.replace(os.sep, "/"),
            line=fs.get("line", 1) or 1, column=1,
            message=d.get("DetectorDescription", "Potential secret detected"),
            snippet=snippet, cwe="798"))
        issues[-1]["verified"] = bool(d.get("Verified"))
    write_result(a.out, issues)


if __name__ == "__main__":
    main()
