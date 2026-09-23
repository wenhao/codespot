"""Java engine — PMD 7 source-level scanning (no compilation needed).

JRE missing -> empty result, one-line reason on stderr, exit 0 (engine is
optional; orchestration surfaces the note without failing the scan).
PMD exit codes: 0 = clean, 4 = violations found, other = error.
Severity: PMD priority 1->critical 2->major 3->minor 4/5->info.
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

RULESET = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                       "assets", "pmd-ruleset.xml")
RULE_URL = "https://docs.pmd-code.org/latest/pmd_rules_java_{category}.html#{rule_lowercase}"
PRIORITY_SEV = {1: "critical", 2: "major", 3: "minor", 4: "info", 5: "info"}
# SpotBugs rank 1-20 ("scariest" .. "of concern") -> codespot severity
RANK_SEV = lambda rank: ("critical" if rank <= 4 else "major" if rank <= 9
                         else "minor" if rank <= 14 else "info")
SEV_ORDER = ("info", "minor", "major", "critical")
SPOTBUGS_TIMEOUT = 600
ENGINES_DIR = os.path.expanduser("~/.codespot/engines")


def find_pmd():
    hits = sorted(glob.glob(os.path.join(ENGINES_DIR, "pmd-*", "pmd")))
    return hits[-1] if hits else shutil.which("pmd")


def java_available():
    try:
        r = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=30)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def rule_url(rule_ref):
    # SARIF rule id like "category/java/errorprone.xml/EmptyCatchBlock"
    parts = rule_ref.split("/")
    if len(parts) >= 4:
        _, _, category, rule = parts[-4], parts[-3], parts[-2], parts[-1]
        return RULE_URL.format(category=category, rule_lowercase=rule.lower())
    return "https://docs.pmd-code.org/latest/pmd_rules_java.html"


def _uri_to_path(uri):
    if uri.startswith("file://"):
        from urllib.parse import unquote, urlparse
        return unquote(urlparse(uri).path)
    return uri


def parse_sarif(path, workdir):
    with open(path, "r", encoding="utf-8") as f:
        sarif = json.load(f)
    rules_by_index = {}
    issues = []
    for run in sarif.get("runs", []):
        for i, rule in enumerate(run.get("tool", {}).get("driver", {}).get("rules", [])):
            rules_by_index[i] = rule
        for result in run.get("results", []):
            rule = rules_by_index.get(result.get("ruleIndex"), {})
            ref = rule.get("id", result.get("ruleId", "unknown"))
            prio = rule.get("properties", {}).get("priority")
            loc = (result.get("locations") or [{}])[0].get("physicalLocation", {})
            region = loc.get("region", {})
            art = _uri_to_path(loc.get("artifactLocation", {}).get("uri", ""))
            rel = os.path.relpath(art, workdir) if os.path.isabs(art) else art
            snippet = ""
            sc = region.get("snippet")
            if isinstance(sc, dict):
                snippet = (sc.get("text") or "").strip()
            issues.append(make_issue(
                tool="pmd", language="java", rule=parts_last(ref),
                rule_url=rule_url(ref),
                severity=PRIORITY_SEV.get(int(prio), "major") if prio else "major",
                file=rel.replace(os.sep, "/"),
                line=region.get("startLine", 1), column=region.get("startColumn", 1),
                message=result.get("message", {}).get("text", ""), snippet=snippet))
    return issues


def parts_last(ref):
    return ref.split("/")[-1]


# ---------------- SpotBugs + FindSecBugs deep layer (optional) ----------------

def find_spotbugs():
    hits = sorted(glob.glob(os.path.join(ENGINES_DIR, "spotbugs-*", "spotbugs")))
    return hits[-1] if hits else shutil.which("spotbugs")


def find_findsecbugs(spotbugs_dir):
    d = os.path.dirname(spotbugs_dir)
    for base in (d, os.path.join(d, "spotbugs-4.10.4")):
        hits = sorted(glob.glob(os.path.join(base, "findsecbugs-plugin-*.jar")))
        if hits:
            return hits[-1]
    return None


def detect_and_compile(workdir):
    """Returns (classes_dir, None) or (None, skip_reason)."""
    if os.path.isfile(os.path.join(workdir, "pom.xml")) and shutil.which("mvn"):
        r = subprocess.run(["mvn", "-q", "compile", "-DskipTests"], cwd=workdir,
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return None, "mvn compile failed — SpotBugs layer skipped: %s" % r.stderr.strip()[-200:]
        classes = os.path.join(workdir, "target", "classes")
    elif any(os.path.isfile(os.path.join(workdir, b)) for b in ("build.gradle", "build.gradle.kts")) \
            and shutil.which("gradle"):
        r = subprocess.run(["gradle", "compileJava", "-q"], cwd=workdir,
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return None, "gradle compileJava failed — SpotBugs layer skipped: %s" % r.stderr.strip()[-200:]
        classes = os.path.join(workdir, "build", "classes", "java", "main")
    else:
        return None, "no pom.xml/build.gradle — SpotBugs layer skipped (source-level PMD only)"
    if not os.path.isdir(classes) or not glob.glob(os.path.join(classes, "**", "*.class"), recursive=True):
        return None, "no compiled classes found — SpotBugs layer skipped"
    return classes, None


def run_spotbugs(spotbugs, fsb, classes, report_path):
    cmd = [spotbugs, "-textui", "-effort:min", "-pluginList", fsb,
           "-sarif=" + report_path, classes]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=SPOTBUGS_TIMEOUT)
    # spotbugs: 0/1/2/3 exit with report are fine; >2 without report = error
    if not os.path.isfile(report_path):
        return "spotbugs failed (exit %s): %s" % (r.returncode, r.stderr.strip()[:300])
    return None


def spotbugs_issues(report_path, workdir):
    with open(report_path, "r", encoding="utf-8") as f:
        sarif = json.load(f)
    issues = []
    for run in sarif.get("runs", []):
        rules_by_index = {}
        for i, rule in enumerate(run.get("tool", {}).get("driver", {}).get("rules", [])):
            rules_by_index[i] = rule
        for result in run.get("results", []):
            rule = rules_by_index.get(result.get("ruleIndex"), {})
            props = rule.get("properties", {})
            ref = rule.get("id", result.get("ruleId", "unknown"))
            pattern = ref.split(".")[-1]
            rank = props.get("rank")
            sev = RANK_SEV(int(rank)) if isinstance(rank, int) else "major"
            is_security = "SECURITY" in (props.get("tags") or []) or pattern.startswith("SEC")
            if is_security:
                sev = SEV_ORDER[min(SEV_ORDER.index(sev) + 1, len(SEV_ORDER) - 1)]
            loc = (result.get("locations") or [{}])[0].get("physicalLocation", {})
            region = loc.get("region", {})
            art = _uri_to_path(loc.get("artifactLocation", {}).get("uri", ""))
            rel = os.path.relpath(art, workdir) if os.path.isabs(art) else art
            cwe = props.get("cweid")
            if not cwe:
                for rel_item in rule.get("relationships", []):
                    target = rel_item.get("target", {})
                    if target.get("toolComponent", {}).get("name") == "CWE":
                        cwe = target.get("id")
                        break
            issues.append(make_issue(
                tool="spotbugs", language="java", rule=pattern,
                rule_url="https://spotbugs.readthedocs.io/en/latest/bugDescriptions.html",
                severity=sev, file=rel.replace(os.sep, "/"),
                line=region.get("startLine", 1), column=1,
                message=result.get("message", {}).get("text", ""), snippet="",
                cwe=cwe))
    return issues


def deep_layer(workdir):
    """Returns list of issues (possibly empty); skip reasons go to stderr."""
    spotbugs = find_spotbugs()
    if not spotbugs:
        return []
    classes, reason = detect_and_compile(workdir)
    if not classes:
        if reason:
            sys.stderr.write("codespot-java: %s\n" % reason)
        return []
    fsb = find_findsecbugs(spotbugs)
    if not fsb:
        sys.stderr.write("codespot-java: findsecbugs plugin missing — SpotBugs layer skipped\n")
        return []
    import tempfile
    with tempfile.TemporaryDirectory(prefix="codespot-sb-") as tmpd:
        report = os.path.join(tmpd, "sb.sarif")
        err = run_spotbugs(spotbugs, fsb, classes, report)
        if err:
            sys.stderr.write("codespot-java: %s\n" % err)
            return []
        return spotbugs_issues(report, workdir)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    pmd = find_pmd()
    if not pmd:
        fail("pmd not installed; run: codespot setup")
    if not java_available():
        sys.stderr.write("codespot-java skipped: java (JRE 8+) not found on PATH "
                         "— install a JRE to enable Java scanning\n")
        write_result(a.out, [])
        return

    entries = read_file_list(a.files)
    paths = [e["path"] if os.path.isabs(e["path"]) else os.path.join(a.workdir, e["path"])
             for e in entries if (e.get("language") == "java" or e["path"].endswith(".java"))]
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        write_result(a.out, [])
        return

    import tempfile
    with tempfile.TemporaryDirectory(prefix="codespot-pmd-") as tmpd:
        report = os.path.join(tmpd, "out.sarif")
        cmd = [pmd, "check", "--no-progress", "--no-cache",
               "-d", ",".join(paths), "-R", RULESET,
               "-f", "sarif", "-r", report]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode not in (0, 4):
            fail("pmd failed (exit %s): %s" % (r.returncode, r.stderr.strip()[:300]))
        if not os.path.isfile(report):
            write_result(a.out, [])
            return
        try:
            issues = parse_sarif(report, a.workdir)
        except ValueError as e:
            fail("pmd produced invalid SARIF: %s" % e)
    issues.extend(deep_layer(a.workdir))
    write_result(a.out, issues)


if __name__ == "__main__":
    main()
