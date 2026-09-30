"""AI review engine — agent-driven, opt-in.

This adapter does not call any model. It writes a review PLAN
(.codespot/ai-plan.json) for the surrounding AI agent to execute:
the agent analyzes the listed files (semantic issues static rules can't
catch), writes .codespot/ai-result.json in the unified schema, then merges
with `codespot ai-scan absorb`. Returns zero issues per the adapter contract.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read_file_list, write_result  # noqa: E402

MAX_FILES = 40
MAX_LINES = 5000

REVIEW_FOCUS = [
    "逻辑正确性：算法/条件/返回值错误，边界条件（空集、零、负数、溢出、最后元素）",
    "并发与竞态：共享状态无保护、检查-使用间隔、死锁风险",
    "错误处理缺口：吞异常、缺回滚/清理、失败路径状态不一致",
    "资源泄漏：文件/连接/锁未关闭的路径",
    "跨文件不一致：接口与实现的契约偏差、调用方传参与签名不符",
    "安全隐患：静态规则难覆盖的注入面、鉴权绕过逻辑",
    "明显与意图不符的实现（注释/命名与行为矛盾）",
    "不要报告静态工具已覆盖的规则类问题（风格、已知模式、依赖 CVE）——那些已由其他引擎产出",
]

SCHEMA_EXAMPLE = {
    "rule": "AI-off-by-one",
    "severity": "major",
    "file": "src/app.py",
    "line": 42,
    "column": 1,
    "message": "range 上界应含最后一个元素，当前少扫一项",
    "snippet": "for i in range(0, len(items) - 1):",
    "confidence": "high",
}


IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)|import\s+([\w\.]+))", re.M)


def _local_module(path):
    """repo-relative dotted module name for import matching (src/a/m.py -> src.a.m / a.m)."""
    p = path.replace(os.sep, "/")
    if p.endswith(".py"):
        p = p[:-3]
    parts = p.split("/")
    return [".".join(parts[i:]) for i in range(len(parts))]  # all suffixes


def _read_imports(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return []
    mods = []
    for m in IMPORT_RE.finditer(text):
        mods.append(m.group(1) or m.group(2))
    return [m for m in mods if m]


class _UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def cluster_bundles(files_with_paths):
    """Group files: same directory OR import relationship (union-find).
    files_with_paths: [(rel_path, abs_path)] -> [[rel_path, ...], ...]
    Bundles sorted by total lines desc; unlinked files become singleton bundles."""
    if not files_with_paths:
        return []
    rels = [r for r, _a in files_with_paths]
    idx = {r: i for i, r in enumerate(rels)}
    uf = _UF(len(rels))
    # same directory -> union
    by_dir = {}
    for r, _a in files_with_paths:
        by_dir.setdefault(os.path.dirname(r) or ".", []).append(idx[r])
    for members in by_dir.values():
        for m in members[1:]:
            uf.union(members[0], m)
    # import edges -> union
    module_to_idx = {}
    for r, a in files_with_paths:
        for mod in _local_module(r):
            module_to_idx.setdefault(mod, idx[r])
    for r, a in files_with_paths:
        for imp in _read_imports(a):
            target = module_to_idx.get(imp)
            if target is not None and target != idx[r]:
                uf.union(idx[r], target)
    groups = {}
    for r in rels:
        groups.setdefault(uf.find(idx[r]), []).append(r)
    def lines_of(r):
        return count_lines(dict(files_with_paths)[r])
    bundles = sorted(groups.values(), key=lambda g: -sum(lines_of(r) for r in g))
    return bundles


def count_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workdir", required=True)
    p.add_argument("--files", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()

    entries = read_file_list(a.files)
    files, total, abs_paths = [], 0, []
    for e in entries:
        fp = e["path"] if os.path.isabs(e["path"]) else os.path.join(a.workdir, e["path"])
        if os.path.isfile(fp):
            n = count_lines(fp)
            files.append({"path": e["path"], "lines": n})
            abs_paths.append((e["path"], fp))
            total += n

    bundles = cluster_bundles(abs_paths)
    lines_by_path = {f["path"]: f["lines"] for f in files}
    bundle_objs = [{"files": b, "totalLines": sum(lines_by_path[r] for r in b)}
                   for b in bundles]

    plan = {
        "generatedFor": "codespot AI review (agent-driven)",
        "files": files,
        "bundles": bundle_objs,
        "totalLines": total,
        "reviewFocus": REVIEW_FOCUS,
        "outputFile": ".codespot/ai-result.json",
        "outputSchema": {
            "type": "array",
            "item": {"rule": "AI-<semantic-slug>", "severity": "critical|major|minor|info",
                     "file": "<repo-relative path>", "line": 0, "column": 1,
                     "message": "<what & why, with evidence>", "snippet": "<offending line>",
                     "confidence": "high|medium|low"},
            "example": SCHEMA_EXAMPLE,
            "notes": ["每条发现必须给精确 file:line 与依据", "规则名用 AI- 前缀的语义化短名",
                      "confidence 必填；不确定用 low", "无发现时写空数组 []"],
        },
    }
    if len(files) > MAX_FILES or total > MAX_LINES:
        plan["batching"] = ("文件数 %d / 总行数 %d 超过单轮上限（%d 文件 / %d 行）："
                            "按 bundle 边界分轮（同 bundle 不拆开，bundle 自身超限时组内再按文件切），"
                            "每轮总行数 ≤%d；每轮单独写一次 ai-result.json 并 absorb"
                            % (len(files), total, MAX_FILES, MAX_LINES, MAX_LINES))

    plan_path = os.path.join(a.workdir, ".codespot", "ai-plan.json")
    os.makedirs(os.path.dirname(plan_path), exist_ok=True)
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)

    sys.stderr.write("codespot-ai: review plan written to .codespot/ai-plan.json "
                     "(%d file(s), %d line(s)) — agent: analyze per plan, write "
                     ".codespot/ai-result.json, then run: codespot ai-scan absorb\n"
                     % (len(files), total))
    write_result(a.out, [])


if __name__ == "__main__":
    main()
