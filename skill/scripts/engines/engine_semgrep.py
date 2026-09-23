"""Semgrep CE adapter — cross-language semantic/taint scanning.

LICENSE BOUNDARY: codespot is an INTERNAL tool. Semgrep CE engine and its
registry rules are used under "internal business purposes" only; rules are
fetched from the official registry at runtime and are NOT bundled with or
distributed by codespot. Do not ship codespot (with this engine configured)
externally without re-reviewing the Semgrep Rules License.

Default ruleset: `--config auto` (semgrep picks packs by project language;
the legacy p/<lang> endpoints 404 for programmatic fetch, so auto is the only
stable registry channel — verified 2026-09-23). Override via
.codespot/config.json: "semgrep_config": "<any --config value>".
Semgrep exit codes: 0 = clean, 1 = findings, >=2 = error.
Severity: ERROR->major, WARNING->minor, INFO->info (tunable via overrides).
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

ENGINES_DIR = os.path.expanduser("~/.codespot/engines")
SEV = {"ERROR": "major", "WARNING": "minor", "INFO": "info"}
DEFAULT_RULESET_URL = "https://semgrep.dev/rulehub/"

LANG_RULESETS = {
    "py": ["p/python"],
    "js": ["p/javascript"], "jsx": ["p/javascript"], "mjs": ["p/javascript"], "cjs": ["p/javascript"],
    "ts": ["p/typescript"], "tsx": ["p/typescript"], "mts": ["p/typescript"], "cts": ["p/typescript"],
    "java": ["p/java"],
    "go": ["p/go"],
    "ruby": ["p/ruby"],
    "php": ["p/php"],
    "kotlin": ["p/kotlin"],
    "rust": ["p/rust"],
    "csharp": ["p/csharp"],
    "c": ["p/c"], "cpp": ["p/c"],
    "terraform": ["p/terraform"],
    "yaml": ["p/kubernetes"],
    "scala": ["p/scala"],
    "swift": ["p/swift"],
}


def find_semgrep():
    venv = sorted(glob.glob(os.path.join(ENGINES_DIR, "semgrep-*", "bin", "semgrep")))
    return venv[-1] if venv else shutil.which("semgrep")


def project_ruleset_override(workdir):
    p = os.path.join(workdir, ".codespot", "config.json")
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f).get("semgrep_config")
        except (OSError, ValueError):
            pass
    return None


def rule_url(check_id, metadata):
    refs = (metadata or {}).get("references") or []
    if refs:
        return refs[0]
    return DEFAULT_RULESET_URL


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    semgrep = find_semgrep()
    if not semgrep:
        fail("semgrep not installed; run: codespot setup")
    entries = read_file_list(a.files)
    paths = [e["path"] if os.path.isabs(e["path"]) else os.path.join(a.workdir, e["path"])
             for e in entries]
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        write_result(a.out, [])
        return

    override = project_ruleset_override(a.workdir)
    if override:
        configs = [override]
    else:
        configs = ["auto"]
    if not configs:
        write_result(a.out, [])
        return

    cmd = [semgrep, "scan", "--json", "--quiet", "--timeout-threshold", "3"]
    for c in configs:
        cmd += ["--config", c]
    cmd += paths
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=a.workdir)
    except subprocess.TimeoutExpired:
        fail("semgrep timed out after 600s")
    if r.returncode not in (0, 1):
        fail("semgrep failed (exit %s): %s" % (r.returncode, r.stderr.strip()[:300]))
    try:
        data = json.loads(r.stdout or "{}")
    except ValueError:
        fail("semgrep produced invalid JSON")

    issues = []
    for v in data.get("results", []):
        extra = v.get("extra", {})
        meta = extra.get("metadata", {}) or {}
        path = v.get("path", "")
        rel = os.path.relpath(path, a.workdir) if os.path.isabs(path) else path
        sev = SEV.get(extra.get("severity", "WARNING"), "minor")
        cwe = None
        cwes = meta.get("cwe")
        if isinstance(cwes, str):
            cwe = cwes.split(":")[0].split(",")[0].strip().lstrip("CWE-").strip() or None
        elif isinstance(cwes, list) and cwes:
            cwe = str(cwes[0]).split(":")[0].split(",")[0].strip().lstrip("CWE-").strip() or None
        check_id = v.get("check_id", "unknown")
        issues.append(make_issue(
            tool="semgrep", language=rel.rsplit(".", 1)[-1] if "." in rel else "*",
            rule=check_id, rule_url=rule_url(check_id, meta),
            severity=sev, file=rel.replace(os.sep, "/"),
            line=(v.get("start") or {}).get("line", 1),
            column=(v.get("start") or {}).get("col", 1),
            message=extra.get("message", ""),
            snippet=(extra.get("lines") or "").strip()[:160],
            cwe=cwe))
    write_result(a.out, issues)


if __name__ == "__main__":
    main()
