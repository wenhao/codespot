"""gitleaks adapter — secrets scanning (always-on, cross-language).

Strategy: gitleaks dir accepts a single path. <=50 target files -> one call per
file; more -> symlink them into a temp dir and scan once.
Exit code 1 is ambiguous (findings OR error): treat as success iff the report
file exists and parses.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import fail, make_issue, read_file_list, redact, write_result  # noqa: E402

BATCH_SYMLINK_THRESHOLD = 50
AGGREGATE_DIR_NAME = "codespot-scope"


def find_binary():
    import glob
    home = os.path.expanduser("~/.codespot/engines")
    hits = sorted(glob.glob(os.path.join(home, "gitleaks-*", "gitleaks")))
    if hits:
        return hits[-1]
    which = shutil.which("gitleaks")
    return which


def line_for_content(content, start=0):
    return content.count("\n", 0, start) + 1


def run_gitleaks(binary, target, report_path, cwd):
    cmd = [binary, "dir", target,
           "--report-format", "json", "--report-path", report_path,
           "--exit-code", "1", "--redact", "-v", "--no-banner"]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=cwd)


def parse_findings(raw, workdir):
    issues = []
    for f in raw:
        file_rel = f.get("File", "")
        if os.path.isabs(file_rel):
            try:
                file_rel = os.path.relpath(file_rel, workdir)
            except ValueError:
                pass
        snippet = redact(f.get("Secret") or f.get("Match", ""))
        issue = make_issue(
            tool="gitleaks", language="*", rule=f.get("RuleID", "unknown"),
            rule_url="https://github.com/gitleaks/gitleaks/tree/master/config#rules",
            severity="critical", file=file_rel,
            line=f.get("StartLine", 1) or 1, column=1,
            message="Potential secret detected (rule: %s)" % f.get("Description", f.get("RuleID", "")),
            snippet=snippet, cwe="798")
        issue["fingerprint"] = f.get("Fingerprint", "")
        issues.append(issue)
    return issues


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    binary = find_binary()
    if not binary:
        fail("gitleaks binary not found; run: codespot setup")
    entries = read_file_list(a.files)
    paths = [e["path"] if os.path.isabs(e["path"]) else os.path.abspath(os.path.join(a.workdir, e["path"]))
             for e in entries]
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        write_result(a.out, [])
        return

    tmpd = tempfile.mkdtemp(prefix="codespot-gitleaks-")
    report_path = os.path.join(tmpd, "report.json")
    try:
        if len(paths) <= BATCH_SYMLINK_THRESHOLD:
            all_issues = []
            for p in paths:
                r = run_gitleaks(binary, p, report_path, a.workdir)
                if r.returncode not in (0, 1):
                    fail("gitleaks failed on %s: %s" % (p, r.stderr.strip()[:300]))
                if os.path.isfile(report_path):
                    with open(report_path, "r", encoding="utf-8") as f:
                        try:
                            raw = json.load(f)
                        except ValueError:
                            if r.returncode == 1:
                                fail("gitleaks error, unreadable report: %s" % r.stderr.strip()[:300])
                            raw = []
                    all_issues.extend(parse_findings(raw, a.workdir))
                    os.remove(report_path)
                elif r.returncode == 1:
                    fail("gitleaks error, no report produced: %s" % r.stderr.strip()[:300])
            issues = all_issues
        else:
            agg = os.path.join(tmpd, AGGREGATE_DIR_NAME)
            os.makedirs(agg)
            for i, p in enumerate(paths):
                link = os.path.join(agg, "%04d-%s" % (i, os.path.basename(p)))
                try:
                    os.symlink(p, link)
                except OSError:
                    shutil.copy2(p, link)
            r = run_gitleaks(binary, agg, report_path, a.workdir)
            if r.returncode not in (0, 1):
                fail("gitleaks failed: %s" % r.stderr.strip()[:300])
            if os.path.isfile(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    try:
                        raw = json.load(f)
                    except ValueError:
                        fail("gitleaks error, unreadable report")
                issues = parse_findings(raw, a.workdir)
            elif r.returncode == 1:
                fail("gitleaks error, no report produced")
            else:
                issues = []

        gitleaksignore = os.path.join(a.workdir, ".gitleaksignore")
        if os.path.isfile(gitleaksignore):
            with open(gitleaksignore, "r", encoding="utf-8") as f:
                ignored = {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}
            issues = [i for i in issues if i.get("fingerprint") not in ignored]

        for i in issues:
            i.pop("fingerprint", None)
        write_result(a.out, issues)
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)


if __name__ == "__main__":
    main()
