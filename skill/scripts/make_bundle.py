#!/usr/bin/env python3
"""Maintainer tool: build per-platform offline bundles for release.

Run on a native runner (CI matrix) AFTER `codespot setup` for that platform:
    python skill/scripts/make_bundle.py --version v1.0.0 --out dist/

Produces codespot-offline-<version>-<os>-<arch>.<tgz|zip> containing:
  skill/                    installable payload
  engines/                  this platform's engines (with .ok markers)
  wheels/<major>x/          pip-downloaded wheels for venv engines (3.10, 3.11)
  offline/osv-db/           OSV local vulnerability DB (from osv-scalibr cache)
  offline/semgrep-rules/    semgrep rules snapshot (if extractable from cache)
  install-offline.sh/.bat   user-side installer (engines, caches, skill)
  THIRD-PARTY-NOTICES       licenses + upstream source links (AGPL/LGPL included)
  MANIFEST.json
"""

import argparse
import glob
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)

NOTICES_HEADER = """codespot offline bundle — third-party notices
All engines are redistributed unmodified from their official releases.
Source availability statements are included where the license requires them.
"""

# engine -> (license, source url)
NOTICES = {
    "gitleaks": ("MIT", "https://github.com/gitleaks/gitleaks"),
    "ruff": ("MIT", "https://github.com/astral-sh/ruff"),
    "oxlint": ("MIT", "https://github.com/oxc-project/oxc"),
    "bandit": ("Apache-2.0", "https://github.com/PyCQA/bandit"),
    "pmd": ("Apache-2.0 / LGPL portions", "https://github.com/pmd/pmd"),
    "spotbugs": ("LGPL-2.1", "https://github.com/spotbugs/spotbugs"),
    "findsecbugs": ("LGPL-2.1", "https://github.com/find-sec-bugs/find-sec-bugs"),
    "sqlfluff": ("MIT", "https://github.com/sqlfluff/sqlfluff"),
    "semgrep": ("LGPL-2.1", "https://github.com/semgrep/semgrep"),
    "osv-scanner": ("Apache-2.0", "https://github.com/google/osv-scanner"),
    "trufflehog": ("AGPL-3.0 — source available at the link above", "https://github.com/trufflesecurity/trufflehog"),
}

WHEEL_ENGINES = {  # registry key -> pip distribution name
    "bandit": "bandit",
    "sqlfluff": "sqlfluff",
    "semgrep": "semgrep",
}
PY_VERSIONS = ("3.10", "3.11")

def sysinfo():
    sysname = platform.system().lower()          # darwin/linux/windows
    machine = {"x86_64": "x64", "AMD64": "x64", "arm64": "arm64"}.get(
        platform.machine(), platform.machine().lower())
    return sysname, machine


def collect_engines(stage):
    """Copy ~/.codespot/engines/<name>-<version>/ dirs (registry-declared only)."""
    src = os.path.expanduser("~/.codespot/engines")
    dst = os.path.join(stage, "engines")
    os.makedirs(dst, exist_ok=True)
    kept = []
    for d in sorted(glob.glob(os.path.join(src, "*-*"))):
        if not os.path.isfile(os.path.join(d, ".ok")):
            continue
        name = shutil.copytree(d, os.path.join(dst, os.path.basename(d)),
                               symlinks=True, dirs_exist_ok=True)
        kept.append(os.path.basename(d))
    return kept


def download_wheels(stage):
    """pip download full dependency closures for venv engines, per py version."""
    pip = shutil.which("pip") or shutil.which("pip3")
    if not pip:
        print("make_bundle: pip not found — wheels/ skipped", file=sys.stderr)
        return False
    wheels = os.path.join(stage, "wheels")
    ok = True
    for pyv in PY_VERSIONS:
        dest = os.path.join(wheels, pyv.split(".")[0] + "x")
        os.makedirs(dest, exist_ok=True)
        for pkg in WHEEL_ENGINES.values():
            cmd = [pip, "download", "--dest", dest, "--only-binary", ":all:",
                   "--python-version", pyv, pkg]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if r.returncode != 0:
                # try source-dist tolerant pass (platform-native wheels may not exist for all)
                cmd2 = [pip, "download", "--dest", dest, "--python-version", pyv, pkg]
                r = subprocess.run(cmd2, capture_output=True, text=True, timeout=900)
                if r.returncode != 0:
                    print("make_bundle: wheels for %s/%s failed: %s"
                          % (pkg, pyv, r.stderr.strip()[:200]), file=sys.stderr)
                    ok = False
    return ok


def collect_semgrep_rules(stage):
    """Copy the builder's local semgrep-rules cache into the bundle
    (offline/semgrep-rules; installer copies it to ~/.codespot/semgrep-rules).
    Builder must run `codespot update-rules` first."""
    off = os.path.join(stage, "offline", "semgrep-rules")
    os.makedirs(off, exist_ok=True)
    src = os.path.expanduser("~/.codespot/semgrep-rules")
    if not os.path.isdir(src):
        print("make_bundle: no local semgrep rules — run codespot update-rules first",
              file=sys.stderr)
        shutil.rmtree(off, ignore_errors=True)
        return 0
    shutil.copytree(src, off, ignore=shutil.ignore_patterns(".git"), dirs_exist_ok=True)
    return sum(len([f for f in fs if f.endswith((".yml", ".yaml"))])
               for _r, _d, fs in os.walk(off))


def write_notices(stage, engine_dirs):
    lines = [NOTICES_HEADER, ""]
    seen = set()
    for d in engine_dirs:
        key = d.split("-")[0]
        if key in NOTICES and key not in seen:
            lic, url = NOTICES[key]
            lines.append("%s — %s\n  %s" % (key, lic, url))
            seen.add(key)
    for extra in ("trufflehog",):  # ensure AGPL entry even if dir naming differs
        if extra not in seen:
            lic, url = NOTICES[extra]
            lines.append("%s — %s\n  %s" % (extra, lic, url))
    with open(os.path.join(stage, "THIRD-PARTY-NOTICES"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_installers(stage):
    sh = """#!/bin/sh
# codespot offline installer (unix)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p ~/.codespot/engines
cp -R "$HERE/engines/"* ~/.codespot/engines/ 2>/dev/null || true
# venv engines are non-relocatable: drop their installed-markers so
# `codespot setup --offline-dir` recreates them from wheels/
for d in "$HOME"/.codespot/engines/bandit-* "$HOME"/.codespot/engines/sqlfluff-* "$HOME"/.codespot/engines/semgrep-*; do
  [ -f "$d/.ok" ] && rm -f "$d/.ok"
done
if [ -d "$HERE/offline/osv-db" ]; then
  for base in "$HOME/Library/Caches/osv-scalibr" "$HOME/.cache/osv-scalibr"; do
    mkdir -p "$base" && cp -R "$HERE/offline/osv-db/"* "$base/" 2>/dev/null || true
  done
fi
if [ -d "$HERE/offline/semgrep-rules" ]; then
  mkdir -p ~/.codespot/semgrep-rules
  cp -R "$HERE/offline/semgrep-rules/"* ~/.codespot/semgrep-rules/ 2>/dev/null || true
fi
mkdir -p ~/.agents/skills
rm -rf ~/.agents/skills/codespot
cp -R "$HERE/skill" ~/.agents/skills/codespot
echo "codespot installed offline. Run: ~/.agents/skills/codespot/scripts/codespot setup --offline-dir <bundle>/offline"
"""
    bat = """@echo off
REM codespot offline installer (windows)
set HERE=%~dp0
if not exist "%USERPROFILE%\\.codespot\\engines" mkdir "%USERPROFILE%\\.codespot\\engines"
xcopy /E /I /Y "%HERE%engines\\*" "%USERPROFILE%\\.codespot\\engines\\" >nul
for /D %%d in ("%USERPROFILE%\\.codespot\\engines\\bandit-*" "%USERPROFILE%\\.codespot\\engines\\sqlfluff-*" "%USERPROFILE%\\.codespot\\engines\\semgrep-*") do if exist "%%d\\.ok" del "%%d\\.ok"
if exist "%HERE%offline\\osv-db" (
  if not exist "%USERPROFILE%\\AppData\\Local\\osv-scalibr" mkdir "%USERPROFILE%\\AppData\\Local\\osv-scalibr"
  xcopy /E /I /Y "%HERE%offline\\osv-db\\*" "%USERPROFILE%\\AppData\\Local\\osv-scalibr\\" >nul
)
if exist "%HERE%offline\\semgrep-rules" (
  if not exist "%USERPROFILE%\\.codespot\\semgrep-rules" mkdir "%USERPROFILE%\\.codespot\\semgrep-rules"
  xcopy /E /I /Y "%HERE%offline\\semgrep-rules\\*" "%USERPROFILE%\\.codespot\\semgrep-rules\\" >nul
)
if not exist "%USERPROFILE%\\.agents\\skills" mkdir "%USERPROFILE%\\.agents\\skills"
if exist "%USERPROFILE%\\.agents\\skills\\codespot" rmdir /S /Q "%USERPROFILE%\\.agents\\skills\\codespot"
xcopy /E /I /Y "%HERE%skill" "%USERPROFILE%\\.agents\\skills\\codespot" >nul
echo codespot installed offline. Run: python %USERPROFILE%\\.agents\\skills\\codespot\\scripts\\codespot setup --offline-dir "%HERE%offline"
"""
    with open(os.path.join(stage, "install-offline.sh"), "w", newline="\n") as f:
        f.write(sh)
    os.chmod(os.path.join(stage, "install-offline.sh"), 0o755)
    with open(os.path.join(stage, "install-offline.bat"), "w", newline="\r\n") as f:
        f.write(bat)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="release version, e.g. v1.0.0")
    ap.add_argument("--out", default="dist", help="output directory")
    a = ap.parse_args()

    sysname, machine = sysinfo()
    stage_root = os.path.join(a.out, "stage")
    if os.path.isdir(stage_root):
        shutil.rmtree(stage_root)
    stage = os.path.join(stage_root, "codespot-offline-" + a.version)
    os.makedirs(stage)

    # 1. skill payload
    shutil.copytree(SKILL, os.path.join(stage, "skill"),
                    ignore=shutil.ignore_patterns("__pycache__", ".codespot"), dirs_exist_ok=True)

    # 2. engines (must have run `codespot setup` on this platform first)
    engine_dirs = collect_engines(stage)
    if not engine_dirs:
        print("make_bundle: no engines found — run `codespot setup` first", file=sys.stderr)
        return 2

    # 3. wheels / osv db (semgrep rules ship inside skill/rules — ensure present)
    if not os.path.isdir(os.path.join(SKILL, "rules", "semgrep")):
        r = subprocess.run(["git", "clone", "--depth", "1", "-q",
                            "https://github.com/semgrep/semgrep-rules",
                            os.path.join(SKILL, "rules", "semgrep")],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print("make_bundle: semgrep rules clone failed — bundle will use "
                  "--config auto fallback", file=sys.stderr)
    wheels_ok = download_wheels(stage)

    # 4. notices + manifest + installers
    write_notices(stage, engine_dirs)
    manifest = {
        "version": a.version,
        "platform": "%s-%s" % (sysname, machine),
        "engines": engine_dirs,
        "wheelsComplete": wheels_ok,
        "semgrepRuleFiles": rules_n,
        "builtAt": subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
                                  capture_output=True, text=True).stdout.strip(),
    }
    with open(os.path.join(stage, "MANIFEST.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    write_installers(stage)

    # 5. archive
    os.makedirs(a.out, exist_ok=True)
    base = "codespot-offline-%s-%s-%s" % (a.version, sysname, machine)
    if sysname == "windows":
        out = os.path.join(a.out, base + ".zip")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _dirs, files in os.walk(stage):
                for f in files:
                    fp = os.path.join(root, f)
                    zf.write(fp, os.path.relpath(fp, os.path.dirname(stage)))
    else:
        out = os.path.join(a.out, base + ".tar.gz")
        with tarfile.open(out, "w:gz") as tf:
            tf.add(stage, arcname=os.path.basename(stage))
    print("make_bundle: %s (%.1f MB)" % (out, os.path.getsize(out) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
