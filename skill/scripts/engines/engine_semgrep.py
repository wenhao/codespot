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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import setup_engine as _se  # noqa: E402
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
    return _se.resolve_engine_cmd("semgrep") or shutil.which("semgrep")


LANG_RULE_DIRS = {  # target language -> subdir of the semgrep-rules repo
    "py": "python", "go": "go", "java": "java", "ruby": "ruby", "php": "php",
    "kotlin": "kotlin", "csharp": "csharp", "rust": "rust", "c": "c", "cpp": "c",
    "swift": "swift", "scala": "scala", "terraform": "terraform",
    "js": "javascript", "jsx": "javascript", "mjs": "javascript", "cjs": "javascript",
    "ts": "typescript", "tsx": "typescript", "mts": "typescript", "cts": "typescript",
}


def offline_db_available():
    """True when a local OSV vulnerability DB exists (osv-scalibr cache)."""
    bases = (os.path.expanduser("~/Library/Caches/osv-scalibr"),
             os.path.expanduser(os.path.join(os.environ.get("XDG_CACHE_HOME", "~/.cache"), "osv-scalibr")))
    return any(glob.glob(os.path.join(b, "*", "*.zip")) for b in bases)


def offline_rules_for(langs):
    """Offline rules dirs (under ~/.codespot/semgrep-rules, shipped by the
    offline bundle) for the requested languages. The repo root contains
    non-rule yamls (template etc.), so only language subdirs are used."""
    base = os.environ.get("CODESPOT_SEMGREP_RULES") or os.path.expanduser(
        "~/.codespot/semgrep-rules")
    if not os.path.isdir(base):
        return []
    dirs = []
    for lang in langs:
        sub = LANG_RULE_DIRS.get(lang)
        if not sub:
            continue  # no offline rules for this language
        d = os.path.join(base, sub)
        if os.path.isdir(d) and d not in dirs:
            dirs.append(d)
    return dirs


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


def to_issues(workdir, data):
    """Merge already-parsed semgrep JSON dicts -> unified issues."""
    issues = []
    for v in data.get("results", []):
        extra = v.get("extra", {})
        meta = extra.get("metadata", {}) or {}
        path = v.get("path", "")
        rel = os.path.relpath(path, workdir) if os.path.isabs(path) else path
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
    return issues


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
        # offline rules (bundle): run one semgrep per language dir — a single
        # bad/unsupported rule file then only knocks out its own language
        langs = sorted({e.get("language") for e in entries if e.get("language")})
        dirs = offline_rules_for(langs)
        if dirs:
            runs = [(os.path.basename(d), d) for d in dirs]
            sys.stderr.write("codespot-semgrep: using offline rules from %s\n" % ", ".join(dirs))
        else:
            runs = [("auto", "auto")]
    if not runs:
        write_result(a.out, [])
        return

    results, errors = [], []
    for label, config in runs:
        cmd = [semgrep, "scan", "--json", "--quiet", "--timeout-threshold", "3",
               "--config", config]
        cmd += paths
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, cwd=a.workdir)
        except subprocess.TimeoutExpired:
            errors.append("%s: timed out" % label)
            continue
        if r.returncode not in (0, 1):
            errors.append("%s: exit %s — %s" % (label, r.returncode, r.stderr.strip()[:200]))
            continue
        try:
            results.append(json.loads(r.stdout or "{}"))
        except ValueError:
            errors.append("%s: invalid JSON" % label)
    for e in errors:
        sys.stderr.write("codespot-semgrep: %s\n" % e)
    data = {"results": [v for d in results for v in d.get("results", [])]}
    try:
        write_result(a.out, to_issues(a.workdir, data))
    except Exception as ex:  # one malformed rule result must not kill the adapter
        sys.stderr.write("codespot-semgrep: result parse error: %s\n" % ex)
    return

def parse_output(stdout, workdir):
    """semgrep JSON -> unified issues (single-object or merged multi-run dict)."""
    data = json.loads(stdout or "{}")
    issues = []
    for v in data.get("results", []):
        extra = v.get("extra", {})
        meta = extra.get("metadata", {}) or {}
        path = v.get("path", "")
        rel = os.path.relpath(path, workdir) if os.path.isabs(path) else path
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
    return issues


if __name__ == "__main__":
    main()
