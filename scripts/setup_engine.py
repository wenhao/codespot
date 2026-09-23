"""Engine download/setup helpers for codespot (idempotent, version-locked).

Supports three install forms (registry.json):
  - platform tarball (download.url + os_map/arch_map/ext_map)
  - zip dist with layout wrapper (e.g. PMD: launcher needs its lib tree,
    so we extract everything and write a wrapper script dest/<name>)
  - npm project (install: "npm", npm_deps locked versions)
"""

import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

ENGINES_DIR = os.path.expanduser("~/.codespot/engines")


def registry_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines", "registry.json")


def load_registry():
    with open(registry_path(), "r", encoding="utf-8") as f:
        return json.load(f)["engines"]


def engine_bin_dir(name, version):
    return os.path.join(ENGINES_DIR, "%s-%s" % (name, version))


def engine_binary(name, version):
    """Path to the installed binary (or engine dir for npm/venv), or None."""
    d = engine_bin_dir(name, version)
    if not os.path.isfile(os.path.join(d, ".ok")):
        return None
    exe = os.path.join(d, name)
    if os.path.isfile(exe):
        return exe
    for inner in (os.path.join(d, "bin", name),):
        if os.path.isfile(inner):
            return inner
    # npm-form engines have no binary; presence of .ok is the contract
    return d if os.path.isdir(os.path.join(d, "node_modules")) else None


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "codespot-setup"})
    with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def _extract(archive, dest):
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
    else:
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(dest)


def _write_wrapper(dest_dir, name, inner):
    """Write dest/<name> shell wrapper exec'ing dest/<inner> (relative layout kept)."""
    exe = os.path.join(dest_dir, name)
    with open(exe, "w") as f:
        f.write("#!/bin/sh\nexec \"$(dirname \"$0\")/%s\" \"$@\"\n" % inner)
    os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
    return exe


def setup_engine(spec):
    """Install one engine. Returns binary path (or engine dir). Raises RuntimeError."""
    name, version = spec["name"], spec["version"]
    exe = engine_binary(name, version)
    if exe:
        print("setup: %s-%s already installed (%s)" % (name, version, exe))
        return exe

    dest_dir = engine_bin_dir(name, version)
    try:
        os.makedirs(dest_dir, exist_ok=True)
        if spec.get("install") == "npm":
            return _setup_npm(spec, dest_dir)
        if spec.get("install") == "venv":
            return _setup_venv(spec, dest_dir)
        return _setup_binary(spec, dest_dir)
    except Exception as e:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise RuntimeError(
            "setup %s failed: %s (retry later, or remove %s to reset)"
            % (name, e, dest_dir))


def _verify(exe, name, flag="--version"):
    r = subprocess.run([exe, flag], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError("%s %s failed: %s" % (name, flag, (r.stderr or r.stdout).strip()[:200]))
    return (r.stdout or r.stderr).strip()


def _setup_binary(spec, dest_dir):
    name, version = spec["name"], spec["version"]
    dl = spec.get("download", {})
    sysname = platform.system().lower()
    os_name = dl.get("os_map", {}).get(sysname)
    arch = dl.get("arch_map", {}).get(platform.machine(), platform.machine().lower())
    ext = dl.get("ext_map", {}).get(sysname, "tar.gz")
    if not os_name and "{os}" in dl.get("url", ""):
        raise RuntimeError("unsupported platform %s/%s for %s" % (platform.system(), platform.machine(), name))
    url = (dl["url"].replace("{version}", version).replace("{os}", os_name or "")
           .replace("{arch}", arch or "").replace("{ext}", ext))

    tmpd = tempfile.mkdtemp(prefix="codespot-dl-")
    try:
        archive = os.path.join(tmpd, "engine." + ext)
        print("setup: downloading %s %s from %s" % (name, version, url))
        _download(url, archive)
        _extract(archive, tmpd)
        layout = spec.get("layout", {})
        archive_dir = layout.get("archive_dir", "").replace("{version}", version)
        src_root = os.path.join(tmpd, archive_dir) if archive_dir and \
            os.path.isdir(os.path.join(tmpd, archive_dir)) else tmpd

        if layout.get("wrapper"):
            inner = layout["binary"]
            if not os.path.isfile(os.path.join(src_root, inner)):
                raise RuntimeError("layout binary %s not found in archive" % inner)
            # keep the extracted tree (launcher needs lib/), wrapper points into it
            tree = os.path.join(dest_dir, os.path.basename(archive_dir) or name)
            if os.path.isdir(tree):
                shutil.rmtree(tree)
            shutil.move(src_root, tree)
            # zip archives don't preserve the exec bit — restore it on the launcher
            real = os.path.join(tree, inner)
            os.chmod(real, os.stat(real).st_mode | stat.S_IEXEC)
            exe = _write_wrapper(dest_dir, name, os.path.join(os.path.basename(tree), inner))
        else:
            exe = os.path.join(dest_dir, name)
            src = os.path.join(src_root, name)
            if not os.path.isfile(src):
                # some archives name the binary per-platform (e.g. oxlint-x86_64-apple-darwin)
                arch_expr = layout.get("archive_binary", "").replace(
                    "{arch}", arch or "").replace("{os}", os_name or "").replace("{version}", version)
                if arch_expr:
                    cand = os.path.join(src_root, arch_expr)
                    if os.path.isfile(cand):
                        src = cand
            if not os.path.isfile(src):
                raise RuntimeError("binary %s not found in archive" % name)
            shutil.copy2(src, exe)
            os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
        ok = _verify(exe, name, spec.get("version_flag", "--version"))
        for extra in spec.get("extra_downloads", []):
            target = os.path.join(tree if layout.get("wrapper") else dest_dir, extra["name"])
            print("setup: downloading %s" % extra["name"])
            _download(extra["url"], target)
        with open(os.path.join(dest_dir, ".ok"), "w") as f:
            f.write(ok or "ok")
        print("setup: %s %s installed (%s)" % (name, version, exe))
        return exe
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)


def _setup_npm(spec, dest_dir):
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm not found; ESLint deep layer skipped (oxlint layer still covers JS/TS)")
    deps = " ".join('"%s@%s"' % (k, v) for k, v in spec.get("npm_deps", {}).items())
    pkg = json.dumps({"name": "codespot-eslint-layer", "private": True,
                      "version": "1.0.0", "type": "module"}, indent=1)
    with open(os.path.join(dest_dir, "package.json"), "w") as f:
        f.write(pkg)
    print("setup: npm install for %s %s" % (spec["name"], spec["version"]))
    r = subprocess.run("%s install --no-audit --no-fund %s" % (npm, deps),
                       shell=True, capture_output=True, text=True, timeout=600, cwd=dest_dir)
    if r.returncode != 0:
        raise RuntimeError("npm install failed: %s" % (r.stderr or r.stdout).strip()[:300])
    with open(os.path.join(dest_dir, ".ok"), "w") as f:
        f.write("npm layer ok")
    print("setup: %s %s installed (%s)" % (spec["name"], spec["version"], dest_dir))
    return dest_dir


def _setup_venv(spec, dest_dir):
    py = shutil.which("python3")
    if not py:
        raise RuntimeError("python3 not found; %s (venv form) skipped" % spec["name"])
    if not os.path.isdir(os.path.join(dest_dir, "bin")):
        r = subprocess.run([py, "-m", "venv", dest_dir], capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError("venv creation failed: %s" % r.stderr.strip()[:300])
    vpy = os.path.join(dest_dir, "bin", "python")
    deps = spec.get("pip_deps", {})
    if spec.get("min_python"):
        r = subprocess.run([vpy, "-c", "import sys;print('%d.%d'%sys.version_info[:2])"],
                           capture_output=True, text=True)
        venv_ver = r.stdout.strip()
        need = tuple(int(x) for x in spec["min_python"].split("."))
        have = tuple(int(x) for x in venv_ver.split("."))
        if have < need:
            deps = spec.get("pip_deps_fallback", deps)
            print("setup: python %s < %s, using fallback pins for %s"
                  % (venv_ver, spec["min_python"], spec["name"]))
    pip = os.path.join(dest_dir, "bin", "pip")
    pkgs = " ".join("%s==%s" % (k, v) for k, v in deps.items())
    print("setup: pip install for %s %s" % (spec["name"], spec["version"]))
    r = subprocess.run([pip, "install", "--no-input", "--quiet"] + pkgs.split(),
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError("pip install failed: %s" % (r.stderr or r.stdout).strip()[:300])
    with open(os.path.join(dest_dir, ".ok"), "w") as f:
        f.write("venv ok")
    print("setup: %s %s installed (%s)" % (spec["name"], spec["version"], dest_dir))
    return dest_dir


def setup_all(only=None):
    """Per-engine isolation: collect failures, install the rest, report at the end."""
    specs = load_registry()
    results, failures = {}, []
    for key, spec in specs.items():
        if only and key not in only:
            continue
        try:
            results[key] = setup_engine(spec)
        except RuntimeError as e:
            failures.append((key, str(e)))
            print("setup: %s" % e, file=sys.stderr)
    if failures:
        raise RuntimeError("setup finished with %d failure(s): %s"
                           % (len(failures), ", ".join(k for k, _ in failures)))
    return results
