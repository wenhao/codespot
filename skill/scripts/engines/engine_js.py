"""JS/TS engine — two layers.

Fast layer:   oxlint (platform binary, JSON output, --format json with "files" array).
Deep layer:   ESLint + eslint-plugin-sonarjs from the npm eslint-layer install;
              plugin-oxlint disables overlapping rules so layers never duplicate.
Degradation:  no npm / layer missing -> oxlint only, reason on stderr, exit 0.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SEVERITIES, fail, make_issue, read_file_list, write_result  # noqa: E402

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      "assets")
OXLINT_URL = "https://oxc.rs/docs/guide/usage/linter/rules/"
ENGINES_DIR = os.path.expanduser("~/.codespot/engines")


def find_oxlint():
    import glob
    hits = sorted(glob.glob(os.path.join(ENGINES_DIR, "oxlint-*", "oxlint")))
    return hits[-1] if hits else shutil.which("oxlint")


def find_eslint_layer():
    d = os.path.join(ENGINES_DIR, "eslint-layer-1")
    if os.path.isfile(os.path.join(d, ".ok")) and os.path.isdir(os.path.join(d, "node_modules", "eslint")):
        return d
    return None


def run_oxlint(binary, paths, workdir):
    cmd = [binary, "--format", "json"]
    # project-native .oxlintrc.json wins over the codespot default
    if not os.path.isfile(os.path.join(workdir, ".oxlintrc.json")):
        cmd += ["-c", os.path.join(ASSETS, ".oxlintrc.json")]
    cmd += paths
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode not in (0, 1):
        return None, "oxlint failed (exit %s): %s" % (r.returncode, r.stderr.strip()[:300])
    try:
        data = json.loads(r.stdout or "{}")
        return data.get("diagnostics", []), None
    except ValueError:
        return None, "oxlint produced invalid JSON"


def oxlint_issues(diags, workdir):
    issues = []
    for d in diags:
        span = {}
        labels = d.get("labels") or []
        if labels:
            span = labels[0].get("span", {})
        if not span:
            span = d.get("location", {}).get("start", {})
        rule = (d.get("code") or "unknown").replace("()", "")
        fix = d.get("fixes") or []
        fix_hint = None
        if fix:
            fix_hint = {"description": "oxlint autofix", "content": fix[0].get("content", "")}
        fname = d.get("filename", "")
        rel = os.path.relpath(fname, workdir) if os.path.isabs(fname) else fname
        issues.append(make_issue(
            tool="oxlint", language=rel.rsplit(".", 1)[-1] or "js",
            rule=rule, rule_url=d.get("url") or OXLINT_URL,
            severity=d.get("severity") if d.get("severity") in SEVERITIES else "",
            file=rel, line=span.get("line", 1), column=span.get("column", 1),
            message=d.get("message", ""), snippet="",
            fix_hint=fix_hint))
    return issues


def run_eslint(layer, paths):
    eslint = os.path.join(layer, "node_modules", "eslint", "bin", "eslint.js")
    node = shutil.which("node")
    if not node:
        return None, "node not found for eslint deep layer"
    # ESM resolves plugin imports relative to the config file, so the config
    # must live inside the layer dir next to node_modules.
    cfg = os.path.join(layer, "eslint.config.mjs")
    shutil.copy2(os.path.join(ASSETS, "eslint.config.mjs"), cfg)
    cmd = [node, eslint, "--no-config-lookup", "--no-error-on-unmatched-pattern",
           "-c", cfg, "--format", "json"] + paths
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode not in (0, 1):
        return None, "eslint failed (exit %s): %s" % (r.returncode, r.stderr.strip()[:300])
    try:
        return json.loads(r.stdout or "[]"), None
    except ValueError:
        return None, "eslint produced invalid JSON"


def eslint_issues(raw, workdir):
    issues = []
    for f in raw:
        path = f.get("filePath", "")
        rel = os.path.relpath(path, workdir) if os.path.isabs(path) else path
        for m in f.get("messages", []):
            rule = m.get("ruleId") or "parse-error"
            if rule == "parse-error":
                continue  # unparseable TS without tsconfig etc. — not a fixable finding
            if rule.startswith("sonarjs/"):
                sonar_id = m.get("ruleId").split("/")[-1]
                # plugin rule ids like 'sonarjs/no-unused-vars' map to S#### only in docs;
                # use the plugin id as rule key
                url = "https://github.com/SonarSource/SonarJS/blob/master/packages/analysis/src/jsts/rules/README.md"
                tool, sev_key = "eslint-sonarjs", rule
            else:
                url = "https://eslint.org/docs/latest/rules/%s" % rule.replace("/", "-")
                tool, sev_key = "eslint-core", rule
            issues.append(make_issue(
                tool=tool, language=rel.rsplit(".", 1)[-1], rule=rule, rule_url=url,
                severity="major" if m.get("severity") == 2 else "minor",
                file=rel, line=m.get("line", 1), column=m.get("column", 1),
                message=m.get("message", ""), snippet="",
                fix_hint={"description": "eslint --fix"} if m.get("fix") else None))
    return issues


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    entries = read_file_list(a.files)
    paths = []
    for e in entries:
        fp = e["path"] if os.path.isabs(e["path"]) else os.path.join(a.workdir, e["path"])
        if os.path.isfile(fp):
            paths.append(fp)
    if not paths:
        write_result(a.out, [])
        return

    ox = find_oxlint()
    if not ox:
        fail("oxlint not installed; run: codespot setup")
    raw, err = run_oxlint(ox, paths, a.workdir)
    if err:
        fail(err)
    issues = oxlint_issues(raw or [], a.workdir)

    layer = find_eslint_layer()
    if not layer:
        sys.stderr.write("codespot-js degraded: eslint deep layer not installed "
                         "(no npm?) — oxlint layer results only\n")
    else:
        raw, err = run_eslint(layer, paths)
        if err:
            sys.stderr.write("codespot-js degraded: %s — oxlint layer results only\n" % err)
        else:
            issues.extend(eslint_issues(raw or [], a.workdir))

    write_result(a.out, issues)


if __name__ == "__main__":
    main()
