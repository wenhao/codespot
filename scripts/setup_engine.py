"""Engine download/setup helpers for codespot (idempotent, version-locked)."""

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

ENGINES_DIR = os.path.expanduser("~/.codespot/engines")


def registry_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "engines", "registry.json")


def load_registry():
    with open(registry_path(), "r", encoding="utf-8") as f:
        return json.load(f)["engines"]


def engine_bin_dir(name, version):
    return os.path.join(ENGINES_DIR, "%s-%s" % (name, version))


def engine_binary(name, version):
    """Path to the installed binary, or None if not installed/verified."""
    d = engine_bin_dir(name, version)
    marker = os.path.join(d, ".ok")
    if not os.path.isfile(marker):
        return None
    exe = os.path.join(d, name)
    return exe if os.path.isfile(exe) else None


def _download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "codespot-setup"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def setup_engine(spec):
    name, version = spec["name"], spec["version"]
    exe = engine_binary(name, version)
    if exe:
        print("setup: %s %s already installed (%s)" % (name, version, exe))
        return exe

    dl = spec.get("download", {})
    os_name = dl.get("os_map", {}).get(platform.system().lower())
    arch = dl.get("arch_map", {}).get(platform.machine())
    ext = dl.get("ext_map", {}).get(platform.system().lower(), "tar.gz")
    if not os_name or not arch:
        raise RuntimeError("unsupported platform %s/%s for %s" % (platform.system(), platform.machine(), name))
    url = dl["url"].replace("{version}", version).replace("{os}", os_name).replace("{arch}", arch).replace("{ext}", ext)

    dest_dir = engine_bin_dir(name, version)
    os.makedirs(dest_dir, exist_ok=True)
    tmpd = tempfile.mkdtemp(prefix="codespot-dl-")
    try:
        archive = os.path.join(tmpd, "engine." + ext)
        print("setup: downloading %s %s from %s" % (name, version, url))
        _download(url, archive)
        with tarfile.open(archive, "r:gz") as tf:
            for member in tf.getmembers():
                if member.isfile() and os.path.basename(member.name) in (name, "gitleaks", "ruff"):
                    member.name = os.path.basename(member.name)
                    tf.extract(member, tmpd)
        src = None
        for cand in (os.path.join(tmpd, name), os.path.join(tmpd, "ruff-" + arch + "-" + os_name, name)):
            if os.path.isfile(cand):
                src = cand
                break
        if not src:
            raise RuntimeError("binary %s not found in archive" % name)
        target = os.path.join(dest_dir, name)
        shutil.move(src, target)
        os.chmod(target, os.stat(target).st_mode | stat.S_IEXEC)
        r = subprocess.run([target, "--version"], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise RuntimeError("%s --version failed: %s" % (name, r.stderr.strip()))
        with open(os.path.join(dest_dir, ".ok"), "w") as f:
            f.write(r.stdout.strip() or "ok")
        print("setup: %s %s installed (%s)" % (name, version, target))
        return target
    except Exception as e:
        shutil.rmtree(dest_dir, ignore_errors=True)
        raise RuntimeError("setup %s failed: %s (retry later, or place the binary manually at %s/<name>)"
                           % (name, e, dest_dir))
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)


def setup_all(only=None):
    specs = load_registry()
    results = {}
    for key, spec in specs.items():
        if only and key not in only:
            continue
        results[key] = setup_engine(spec)
    return results
