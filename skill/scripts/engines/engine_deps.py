"""OSV-Scanner adapter — dependency/supply-chain vulnerability scanning.

Finds dependency manifests & lockfiles in the scope, runs
`osv-scanner scan source -L <file> -f json`, maps results to the unified
issue schema. Offline-first: when a local OSV vulnerability DB has been
downloaded (codespot update-db), scans run with --offline-vulnerabilities;
otherwise the live osv.dev API is queried.
Exit codes: 0 = clean, 1 = vulnerabilities found, >=2 = error.
category: dependencies (config.json rules.dependencies.disabled/ignore apply).
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
RULE_URL = "https://osv.dev/vulnerability/{id}"

MANIFEST_PATTERNS = (
    "requirements*.txt",
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock",
    "pom.xml", "go.mod", "go.sum", "Cargo.lock",
    "composer.lock", "Gemfile.lock",
)
# NOTE: pyproject.toml / package.json are NOT in the list — osv-scanner requires
# version-pinning files; loose manifests make it exit 127.
MANIFEST_RE = re.compile(r".*\.csproj$", re.I)
SEV_TEXT = {"CRITICAL": "critical", "HIGH": "major", "MODERATE": "minor",
            "MEDIUM": "minor", "LOW": "minor"}


def find_binary():
    hits = sorted(glob.glob(os.path.join(ENGINES_DIR, "osv-scanner-*", "osv-scanner")))
    return hits[-1] if hits else shutil.which("osv-scanner")


def offline_db_available():
    """True when a previously downloaded OSV local DB exists (osv-scalibr cache)."""
    bases = (os.path.expanduser("~/Library/Caches/osv-scalibr"),
             os.path.expanduser(os.path.join(os.environ.get("XDG_CACHE_HOME", "~/.cache"), "osv-scalibr")))
    return any(glob.glob(os.path.join(b, "*", "*.zip")) for b in bases)


def is_manifest(path):
    name = os.path.basename(path)
    if MANIFEST_RE.match(name):
        return True
    import fnmatch
    return any(fnmatch.fnmatch(name, pat) for pat in MANIFEST_PATTERNS)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    binary = find_binary()
    if not binary:
        fail("osv-scanner not installed; run: codespot setup")
    entries = read_file_list(a.files)
    manifests = []
    for e in entries:
        fp = e["path"] if os.path.isabs(e["path"]) else os.path.join(a.workdir, e["path"])
        if os.path.isfile(fp) and is_manifest(fp) and fp not in manifests:
            manifests.append(fp)
    if not manifests:
        write_result(a.out, [])
        return

    cmd = [binary, "scan", "source", "--allow-no-lockfiles", "-f", "json"]
    if offline_db_available():
        cmd += ["--offline-vulnerabilities"]
    for m in manifests:
        cmd += ["-L", m]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=a.workdir)
    except subprocess.TimeoutExpired:
        fail("osv-scanner timed out after 300s")
    if r.returncode not in (0, 1):
        fail("osv-scanner failed (exit %s): %s" % (r.returncode, r.stderr.strip()[:300]))
    try:
        data = json.loads(r.stdout or "{}")
    except ValueError:
        fail("osv-scanner produced invalid JSON")

    issues = []
    for result in data.get("results", []):
        for pkg in result.get("packages", []):
            pkg_info = pkg.get("package", {}) or {}
            src_path = pkg_info.get("file", "")
            rel = os.path.relpath(src_path, a.workdir) if os.path.isabs(src_path) else src_path
            for v in pkg.get("vulnerabilities", []) or []:
                vuln_id = v.get("id", "unknown")
                fixed = None
                for aff in v.get("affected", []) or []:
                    for rng in aff.get("ranges", []) or []:
                        for ev in rng.get("events", []) or []:
                            if ev.get("fixed"):
                                fixed = ev["fixed"]
                                break
                ds = (v.get("database_specific") or {})
                sev_raw = (ds.get("severity") or ds.get("cvss_score") or "")
                sev = SEV_TEXT.get(str(sev_raw).upper(), "major")
                fix_hint = {"description": "upgrade to %s" % fixed} if fixed else None
                issues.append(make_issue(
                    tool="osv-scanner", language="*",
                    rule=vuln_id, rule_url=RULE_URL.format(id=vuln_id),
                    severity=sev, file=rel or "requirements", line=1, column=1,
                    message="%s: %s" % (pkg_info.get("name", "dependency"),
                                        v.get("summary") or v.get("details", "")[:120]),
                    snippet="%s@%s" % (pkg_info.get("name", "?"), pkg_info.get("version", "?")),
                    fix_hint=fix_hint))
    write_result(a.out, issues)


if __name__ == "__main__":
    main()
