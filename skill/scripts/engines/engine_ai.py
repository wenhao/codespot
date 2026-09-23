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
    files, total = [], 0
    for e in entries:
        fp = e["path"] if os.path.isabs(e["path"]) else os.path.join(a.workdir, e["path"])
        if os.path.isfile(fp):
            n = count_lines(fp)
            files.append({"path": e["path"], "lines": n})
            total += n

    plan = {
        "generatedFor": "codespot AI review (agent-driven)",
        "files": files,
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
                            "分多轮分析，每轮 ≤%d 文件，每轮单独写一次 ai-result.json 并 absorb"
                            % (len(files), total, MAX_FILES, MAX_LINES, MAX_FILES))

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
