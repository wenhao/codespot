"""Shared utilities for codespot engine adapters.

Contract (stable interface — later engine batches depend on this):
  invoked as: engine_<name>.py --workdir <root> --files <list.json> --out <result.json>
  exit 0: result.json written (list of issues); exit 2: engine failure, reason on stderr.
"""

import hashlib
import json
import os
import sys

SEVERITIES = ("critical", "major", "minor", "info")

REQUIRED_FIELDS = (
    "tool", "language", "rule", "ruleUrl", "severity",
    "file", "line", "column", "message", "snippet",
)


def cs_id(tool, rule):
    """Stable user-facing rule code derived from tool|rule (no state)."""
    return "CS-" + hashlib.sha1(("%s|%s" % (tool, rule)).encode("utf-8")).hexdigest()[:5]


def load_project_config():
    """Read .codespot/config.json (dialect, semgrep_config, rules{...})."""
    p = os.path.join(_repo_root(), ".codespot", "config.json")
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except ValueError:
            pass
    return {}


def category_of(tool):
    """Map real engine name -> user-facing category alias (via registry)."""
    try:
        registry = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registry.json")
        with open(registry, "r", encoding="utf-8") as f:
            return json.load(f)["engines"].get(tool, {}).get("category", tool)
    except (OSError, ValueError, KeyError):
        return tool


def rule_ignore_list(tool):
    """Rules ignored for this tool's category via config.json rules.<cat>.ignore."""
    conf = load_project_config().get("rules", {}) or {}
    entry = conf.get(category_of(tool)) or {}
    return entry.get("ignore") or []


def fail(msg):
    sys.stderr.write("codespot-engine error: %s\n" % msg)
    sys.exit(2)


def read_file_list(path):
    """Read the scope file list JSON -> list of dicts with at least 'path'."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        fail("cannot read file list %s: %s" % (path, e))
    if isinstance(data, dict):
        data = data.get("files", [])
    if not isinstance(data, list):
        fail("file list must be a JSON array or {files: [...]}")
    return data


def write_result(path, issues):
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(issues, f, ensure_ascii=False, indent=1)
    except OSError as e:
        fail("cannot write result %s: %s" % (path, e))


def make_issue(tool, language, rule, rule_url, severity,
               file, line, column, message, snippet,
               cwe=None, fix_hint=None):
    issue = {
        "tool": tool,
        "language": language,
        "rule": str(rule),
        "ruleUrl": rule_url,
        "severity": normalize_severity(tool, rule, severity),
        "csId": cs_id(tool, str(rule)),
        "file": file.replace(os.sep, "/"),
        "line": int(line),
        "column": int(column),
        "message": message,
        "snippet": snippet or "",
    }
    if cwe:
        issue["cwe"] = str(cwe)
    if fix_hint:
        issue["fixHint"] = fix_hint
    return issue


def redact(text, keep=4):
    """Keep first/last `keep` chars of a secret hit, mask the middle."""
    text = text or ""
    if len(text) <= keep * 2:
        return "…"
    return text[:keep] + "…" + text[-keep:]


def _repo_root():
    return os.environ.get("CODESPOT_WORKDIR") or os.getcwd()


def _load_mapping(filename):
    for base in (
        os.path.join(_repo_root(), ".codespot"),
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ):
        p = os.path.join(base, filename)
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except ValueError:
                pass
    return {}


def normalize_severity(tool, rule, raw):
    """raw -> (critical|major|minor|info) via rules-severity.json + user overrides."""
    overrides = _load_mapping("severity-overrides.json")
    defaults = _load_mapping("rules-severity.json")
    for table in (overrides, defaults):
        conf = table.get(tool, {})
        if not isinstance(conf, dict):
            continue
        hit = conf.get("rules", {}).get(str(rule))
        if hit in SEVERITIES:
            return hit
        if isinstance(raw, str) and raw.lower() in SEVERITIES:
            return raw.lower()
        mapped = _map_known_value(raw, conf.get("mapping", {}))
        if mapped:
            return mapped
        if conf.get("default") in SEVERITIES:
            return conf["default"]
    if raw in SEVERITIES:
        return raw
    return "major"


def _map_known_value(raw, mapping):
    if not mapping:
        return None
    key = str(raw).strip().upper()
    for value, sev in mapping.items():
        if str(value).upper() == key and sev in SEVERITIES:
            return sev
    return None


def read_project_ignores(tool):
    """Read .codespot/ignore -> list of {tool,file,rule} filter entries."""
    entries = _load_mapping("ignore")
    if isinstance(entries, list):
        return [e for e in entries if isinstance(e, dict) and e.get("tool") == tool]
    return []
