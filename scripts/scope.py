"""Git scope calculation for codespot.

Emits a JSON {scope, files:[{path,language}]} to stdout or --out.
Tiers: uncommitted | unpushed | ref:<ref> | all ; auto falls back
uncommitted -> unpushed -> all (first non-empty).
"""

import json
import os
import subprocess
import sys

SUPPORTED_LANGS = {
    ".py": "py",
    ".js": "js", ".jsx": "jsx", ".mjs": "js", ".cjs": "js",
    ".ts": "ts", ".mts": "ts", ".cts": "ts", ".tsx": "tsx",
    ".java": "java", ".sql": "sql",
}

EXCLUDED_DIRS = (".git/", ".codespot/", "node_modules/", "vendor/", "dist/", "build/")


def git(root, *args):
    try:
        r = subprocess.run(["git", "-C", root] + list(args),
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise RuntimeError("git failed: %s" % e)
    if r.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout


def detect_language(path):
    return SUPPORTED_LANGS.get(os.path.splitext(path)[1].lower())


def _clean_paths(root, raw):
    out = []
    for line in raw.splitlines():
        path = line.strip()
        if not path:
            continue
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        p = path.replace(os.sep, "/")
        if any(p.startswith(d) or "/" + d in "/" + p for d in EXCLUDED_DIRS):
            continue
        if os.path.isfile(os.path.join(root, path)):
            out.append(path)
    return out


def _uncommitted(root):
    raw = git(root, "status", "--porcelain")
    paths = []
    for line in raw.splitlines():
        if len(line) < 4:
            continue
        status, path = line[:2], line[3:].strip()
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        if status.strip() == "R" and "->" in path:
            path = path.split("->", 1)[1].strip()
        paths.append(path)
    return [p for p in paths
            if not any(p.replace(os.sep, "/").startswith(d) for d in EXCLUDED_DIRS)
            and os.path.isfile(os.path.join(root, p))]


def _default_branch(root):
    for ref in ("main", "master"):
        r = subprocess.run(["git", "-C", root, "rev-parse", "--verify", ref],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return ref
    return None


def _unpushed(root):
    try:
        git(root, "rev-parse", "--verify", "@{u}")
        base = "@{u}"
    except RuntimeError:
        base = _default_branch(root)
        if not base:
            raise RuntimeError("no upstream branch and no main/master to compare")
    names = git(root, "diff", "--name-only", base + "...HEAD")
    return _clean_paths(root, names)


def _ref(root, ref):
    names = git(root, "diff", "--name-only", ref + "...HEAD")
    return _clean_paths(root, names)


def _all(root):
    names = git(root, "ls-files", "-co", "--exclude-standard")
    return _clean_paths(root, names)


def compute(root, scope):
    if scope == "auto":
        for tier in ("uncommitted", "unpushed", "all"):
            try:
                tier_files = compute(root, tier)[0]
            except RuntimeError:
                continue
            if tier_files:
                return tier_files, tier
        return [], "uncommitted"

    if scope == "uncommitted":
        return _uncommitted(root), scope
    if scope == "unpushed":
        pushed = _unpushed(root)
        merged = list(pushed)
        for p in _uncommitted(root):
            if p not in set(pushed):
                merged.append(p)
        return merged, scope
    if scope.startswith("ref:"):
        return _ref(root, scope[4:]), scope
    if scope == "all":
        return _all(root), scope
    raise RuntimeError("unknown scope: %s" % scope)


def main(argv=None):
    argv = argv or sys.argv[1:]
    root = "."
    out = None
    scope = "auto"
    args = list(argv)
    while args:
        a = args.pop(0)
        if a == "--workdir":
            root = args.pop(0)
        elif a == "--out":
            out = args.pop(0)
        elif a == "--scope":
            scope = args.pop(0)
        else:
            sys.stderr.write("unknown arg: %s\n" % a)
            return 2
    try:
        files, effective = compute(os.path.abspath(root), scope)
    except (RuntimeError, subprocess.CalledProcessError) as e:
        sys.stderr.write("codespot-scope error: %s\n" % e)
        return 2
    entries = [{"path": p, "language": detect_language(p)} for p in sorted(set(files))]
    payload = {"scope": effective, "files": entries}
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
