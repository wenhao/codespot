"""Engine download/setup helpers for codespot (idempotent, version-locked).

Install forms (registry.json), all Windows-aware:
  - platform tarball/zip (download.url + os_map/arch_map/ext_map)
  - raw single-file binary (raw_binary; ".exe" suffix on Windows)
  - zip dist with layout wrapper (PMD/SpotBugs: launcher needs its lib tree;
    unix gets an sh wrapper, Windows points at the bundled .bat via a shim)
  - npm project (install: "npm") / python venv (install: "venv"; on Windows
    tools live under Scripts\\ and "python" is preferred over "python3")
"""

import glob
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
IS_WINDOWS = platform.system() == "Windows"


def _exe_variants(base):
    return [base + ".exe", base + ".bat", base] if IS_WINDOWS else [base]


def resolve_engine_cmd(name, inner_paths=("bin/%s", "Scripts/%s")):
    """Locate an installed engine's executable across platform layouts:
    <engines>/<name>-*/<name>[.exe|.bat] plus venv-style inner paths
    (bin/ on unix, Scripts\\ on Windows). Returns the newest match or None."""
    hits = []
    for d in sorted(glob.glob(os.path.join(ENGINES_DIR, name + "-*"))):
        cands = [os.path.join(d, name)]
        for tpl in inner_paths:
            cands.append(os.path.join(d, tpl % name))
        for c in cands:
            hit = next((v for v in _exe_variants(c) if os.path.isfile(v)), None)
            if hit:
                hits.append(hit)
                break
    return hits[-1] if hits else None


def registry_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines", "registry.json")


def load_registry():
    with open(registry_path(), "r", encoding="utf-8") as f:
        return json.load(f)["engines"]


def platform_supported(spec):
    allowed = spec.get("platforms")
    return not allowed or platform.system().lower() in allowed


def engine_bin_dir(name, version):
    return os.path.join(ENGINES_DIR, "%s-%s" % (name, version))


def engine_binary(name, version):
    """Path to the installed binary (or engine dir for npm/venv), or None."""
    d = engine_bin_dir(name, version)
    if not os.path.isfile(os.path.join(d, ".ok")):
        return None
    for v in _exe_variants(os.path.join(d, name)):
        if os.path.isfile(v):
            return v
    for inner in (os.path.join(d, "bin", name), os.path.join(d, "Scripts", name)):
        for v in _exe_variants(inner):
            if os.path.isfile(v):
                return v
    # npm-form engines have no binary; presence of .ok is the contract
    return d if os.path.isdir(os.path.join(d, "node_modules")) else None


def _download(url, dest, label=""):
    req = urllib.request.Request(url, headers={"User-Agent": "codespot-setup"})
    total = None
    got = 0
    last_tick = 0.0
    import time
    with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as f:
        total = int(resp.headers.get("Content-Length") or 0)
        while True:
            chunk = resp.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            now = time.monotonic()
            if now - last_tick > 1.0:
                last_tick = now
                mb = got / 1e6
                if total:
                    sys.stdout.write("\r  %s %.1f/%.1f MB" % (label, mb, total / 1e6))
                else:
                    sys.stdout.write("\r  %s %.1f MB" % (label, mb))
                sys.stdout.flush()
    if total:
        sys.stdout.write("\r  %s %.1f/%.1f MB\n" % (label, got / 1e6, total / 1e6))
    else:
        sys.stdout.write("\n")


def _extract(archive, dest):
    if archive.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
    else:
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(dest)


def _write_wrapper(dest_dir, name, inner):
    """Unix: dest/<name> sh wrapper. Windows: dest/<name>.bat shim calling the
    bundled launcher (CreateProcess also runs .bat directly, the shim just
    keeps a stable top-level path)."""
    if IS_WINDOWS:
        exe = os.path.join(dest_dir, name + ".bat")
        with open(exe, "w") as f:
            f.write('@call "%%~dp0%s" %%*\n' % inner.replace("/", "\\"))
        return exe
    exe = os.path.join(dest_dir, name)
    with open(exe, "w") as f:
        f.write("#!/bin/sh\nexec \"$(dirname \"$0\")/%s\" \"$@\"\n" % inner)
    os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
    return exe


def setup_engine(spec):
    """Install one engine. Returns binary path (or engine dir). Raises RuntimeError."""
    name, version = spec["name"], spec["version"]
    if not platform_supported(spec):
        raise RuntimeError("%s does not support this platform (%s)" % (name, platform.system()))
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
    machine = platform.machine().lower()
    arch = dl.get("arch_map", {}).get(platform.machine(), dl.get("arch_map", {}).get(machine, machine))
    ext = dl.get("ext_map", {}).get(sysname, "tar.gz")
    if not os_name and "{os}" in dl.get("url", ""):
        raise RuntimeError("unsupported platform %s/%s for %s" % (platform.system(), platform.machine(), name))
    url = (dl["url"].replace("{version}", version).replace("{os}", os_name or "")
           .replace("{arch}", arch or "").replace("{ext}", ext))

    tmpd = tempfile.mkdtemp(prefix="codespot-dl-")
    try:
        if spec.get("raw_binary"):
            exe = os.path.join(dest_dir, name + (".exe" if IS_WINDOWS else ""))
            print("setup: downloading %s %s from %s" % (name, version, url))
            _download(url, exe, label="download %s" % name)
            if not IS_WINDOWS:
                os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
            ok = _verify(exe, name, spec.get("version_flag", "--version"))
            with open(os.path.join(dest_dir, ".ok"), "w") as f:
                f.write(ok or "ok")
            print("setup: %s %s installed (%s)" % (name, version, exe))
            return exe
        archive = os.path.join(tmpd, "engine." + ext)
        print("setup: downloading %s %s from %s" % (name, version, url))
        _download(url, archive, label="download %s" % name)
        _extract(archive, tmpd)
        layout = spec.get("layout", {})
        archive_dir = layout.get("archive_dir", "").replace("{version}", version)
        src_root = os.path.join(tmpd, archive_dir) if archive_dir and \
            os.path.isdir(os.path.join(tmpd, archive_dir)) else tmpd

        if layout.get("wrapper"):
            inner = layout["windows_binary"] if (IS_WINDOWS and layout.get("windows_binary")) \
                else layout["binary"]
            if not os.path.isfile(os.path.join(src_root, inner)):
                raise RuntimeError("layout binary %s not found in archive" % inner)
            # keep the extracted tree (launcher needs lib/), wrapper points into it
            tree = os.path.join(dest_dir, os.path.basename(archive_dir) or name)
            if os.path.isdir(tree):
                shutil.rmtree(tree)
            shutil.move(src_root, tree)
            real = os.path.join(tree, inner)
            if not IS_WINDOWS:
                # zip archives don't preserve the exec bit — restore it on the launcher
                os.chmod(real, os.stat(real).st_mode | stat.S_IEXEC)
            exe = _write_wrapper(dest_dir, name, os.path.join(os.path.basename(tree), inner))
        else:
            exe = os.path.join(dest_dir, name + (".exe" if IS_WINDOWS else ""))
            src = next((v for v in _exe_variants(os.path.join(src_root, name))
                        if os.path.isfile(v)), None)
            if not src:
                # some archives name the binary per-platform (e.g. oxlint-x86_64-apple-darwin)
                arch_expr = layout.get("archive_binary", "").replace(
                    "{arch}", arch or "").replace("{os}", os_name or "").replace("{version}", version)
                if arch_expr:
                    src = next((v for v in _exe_variants(os.path.join(src_root, arch_expr))
                                if os.path.isfile(v)), None)
            if not src:
                # some archives wrap the binary in a platform-named directory
                # (e.g. ruff-x86_64-unknown-linux-gnu/ruff) — search recursively
                for hit in glob.glob(os.path.join(tmpd, "**", name), recursive=True):
                    src = next((v for v in _exe_variants(hit) if os.path.isfile(v)), None)
                    if src:
                        break
            if not src:
                raise RuntimeError("binary %s not found in archive" % name)
            shutil.copy2(src, exe)
            if not IS_WINDOWS:
                os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC)
        ok = _verify(exe, name, spec.get("version_flag", "--version"))
        for extra in spec.get("extra_downloads", []):
            target = os.path.join(tree if layout.get("wrapper") else dest_dir, extra["name"])
            print("setup: downloading %s" % extra["name"])
            _download(extra["url"], target, label="download %s" % extra["name"])
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
    dep_args = ["%s@%s" % (k, v) for k, v in spec.get("npm_deps", {}).items()]
    pkg = json.dumps({"name": "codespot-eslint-layer", "private": True,
                      "version": "1.0.0", "type": "module"}, indent=1)
    with open(os.path.join(dest_dir, "package.json"), "w") as f:
        f.write(pkg)
    print("setup: npm install for %s %s" % (spec["name"], spec["version"]))
    r = subprocess.run([npm, "install", "--no-audit", "--no-fund"] + dep_args,
                       capture_output=True, text=True, timeout=600, cwd=dest_dir)
    if r.returncode != 0:
        raise RuntimeError("npm install failed: %s" % (r.stderr or r.stdout).strip()[:300])
    with open(os.path.join(dest_dir, ".ok"), "w") as f:
        f.write("npm layer ok")
    print("setup: %s %s installed (%s)" % (spec["name"], spec["version"], dest_dir))
    return dest_dir


def _setup_venv(spec, dest_dir):
    py = shutil.which("python") if IS_WINDOWS else None
    py = py or shutil.which("python3") or shutil.which("python")
    if not py:
        raise RuntimeError("python not found; %s (venv form) skipped" % spec["name"])
    scripts = "Scripts" if IS_WINDOWS else "bin"
    vpy_ext = ".exe" if IS_WINDOWS else ""
    if not os.path.isdir(os.path.join(dest_dir, scripts)):
        r = subprocess.run([py, "-m", "venv", dest_dir], capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            raise RuntimeError("venv creation failed: %s" % r.stderr.strip()[:300])
    vpy = os.path.join(dest_dir, scripts, "python" + vpy_ext)
    deps = spec.get("pip_deps", {})
    if spec.get("min_python"):
        r = subprocess.run([vpy, "-c", "import sys;print('%d.%d'%sys.version_info[:2])"],
                           capture_output=True, text=True)
        venv_ver = r.stdout.strip()
        need = tuple(int(x) for x in spec["min_python"].split("."))
        have = tuple(int(x) for x in venv_ver.split(".")[:2]) if venv_ver else (0, 0)
        if have < need:
            deps = spec.get("pip_deps_fallback", deps)
            print("setup: python %s < %s, using fallback pins for %s"
                  % (venv_ver, spec["min_python"], spec["name"]))
    pip = os.path.join(dest_dir, scripts, "pip" + vpy_ext)
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
    """Install engines in parallel; per-engine failure isolation; skips
    agent-driven engines and platforms not in the registry whitelist."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    specs = load_registry()
    targets = {}
    for key, spec in specs.items():
        if only and key not in only:
            continue
        if spec.get("agent_driven"):
            print("setup: SKIP %s (agent-driven, nothing to install)" % key)
            continue
        if not platform_supported(spec):
            print("setup: SKIP %s (not supported on %s)" % (key, platform.system()))
            continue
        targets[key] = spec
    if not targets:
        return {}
    total = len(targets)
    results, failures = {}, []
    done = 0
    with ThreadPoolExecutor(max_workers=min(4, total)) as pool:
        futs = {pool.submit(setup_engine, spec): key for key, spec in targets.items()}
        for fut in as_completed(futs):
            key = futs[fut]
            done += 1
            try:
                results[key] = fut.result()
                print("setup: [%d/%d] %s ✓" % (done, total, key))
            except RuntimeError as e:
                failures.append((key, str(e)))
                print("setup: [%d/%d] %s ✗ %s" % (done, total, key, str(e)[:120]),
                      file=sys.stderr)
    if failures:
        raise RuntimeError("setup finished with %d failure(s): %s"
                           % (len(failures), ", ".join(k for k, _ in failures)))
    return results
