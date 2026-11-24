#!/usr/bin/env python3
"""复跑本地 PRD、六阶段检查、实际测试与证据失效。"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

EXAMPLE = Path(__file__).resolve().parent
CLI = EXAMPLE.parents[1] / "scripts/workflow.py"

CASES = [
    ("T1", "interaction", "提交期间忽略重复操作", "§1", "连续提交只发出一次请求", "test_duplicate_submit"),
    ("T2", "integration", "完成回调后可再次提交", "§2", "真实示例入口经完成回调后可以发出下一次请求", "test_submit_again_after_completion"),
]


def run(root, *command, expected=0):
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    if result.returncode != expected:
        raise RuntimeError(f"{command} 返回 {result.returncode}\n{result.stdout}{result.stderr}")
    return result.stdout + result.stderr


def workflow(root, command, *options, expected=0):
    result = run(root, sys.executable, str(CLI), command, "--root", ".", "--task-dir", "task",
                 *options, expected=expected)
    return json.loads(result)


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def example_task(case):
    task_id, task_type, title, section, check, _ = case
    return {
        "id": task_id, "title": title, "type": task_type,
        "source": {"id": "S1", "location": section},
        "scope": ["submit.py", "test_submit.py"],
        "rules": ["PRD.md 要求在完成回调前忽略重复提交"],
        "depends_on": ["T1"] if task_type == "integration" else [],
        "hidden_state": "本例只验提交状态，未定义可见性",
        "fixture": {"status": "not_applicable", "reason": "提交入口通过内存请求回调验收"},
        "implementation": {"status": "pending", "files": [], "note": "等待实现"},
        "acceptance": [{"id": "C1", "expected": check, "method": "unit", "status": "pending",
                        "actual": "", "evidence": []}],
    }


def check_and_record(root, round_number):
    for task_id, _, _, _, check, test in CASES:
        command = [sys.executable, "-B", "-m", "unittest", "-v", f"test_submit.SubmitTests.{test}"]
        output = run(root, *command)
        relative_log = f"evidence/{task_id}-round-{round_number}.txt"
        (root / "task" / relative_log).write_text(output, encoding="utf-8")
        workflow(root, "record", "--task", task_id, "--criterion", "C1", "--kind", "unit",
                 "--file", relative_log, "--result", "pass", "--actual", check,
                 "--context", f"python3 -B -m unittest -v test_submit.SubmitTests.{test}",
                 "--watch", "submit.py", "--watch", "test_submit.py")


def demo(root):
    shutil.copy2(EXAMPLE / "PRD.md", root / "PRD.md")
    run(root, "git", "init", "-q")
    run(root, "git", "add", "PRD.md")
    run(root, "git", "-c", "user.name=FCD Example", "-c", "user.email=example@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "core.hooksPath=.git/no-hooks",
        "commit", "-qm", "feat：添加示例需求")
    workflow(root, "init", "--title", "提交防重复", "--source", "PRD.md")
    workflow(root, "preflight")
    workflow(root, "gate", "--stage", "1")

    ledger = root / "task/plan.json"
    plan = json.loads(ledger.read_text(encoding="utf-8"))
    plan["sources"][0].update(status="read", summary="已读取本地 PRD 的 §1 和 §2")
    plan["design"].update(status="not_applicable", reason="本例验证提交入口行为")
    plan["coverage"].update(ui="无视觉稿", interaction="T1 与 T2",
                            data="使用内存请求列表", tracking="PRD 无埋点要求",
                            compatibility="仅运行 Python 受控样例", performance="PRD 无耗时要求")
    plan["tasks"] = [example_task(case) for case in CASES]
    save_json(ledger, plan)
    workflow(root, "gate", "--stage", "2")
    workflow(root, "gate", "--stage", "3")

    for name in ("submit.py", "test_submit.py"):
        shutil.copy2(EXAMPLE / name, root / name)
    for task in plan["tasks"]:
        task["implementation"].update(status="done", files=["submit.py", "test_submit.py"],
                                      note="独立示例已实现提交与回调")
    save_json(ledger, plan)
    check_and_record(root, 1)
    before = workflow(root, "gate", "--stage", "4")
    assert before["delivery"] == "complete", before

    with (root / "submit.py").open("a", encoding="utf-8") as source:
        source.write("\n# 演示文件变化后需要重新验证。\n")
    stale = workflow(root, "gate", "--stage", "4", expected=1)
    assert any("关联源码已变化" in error for error in stale["errors"]), stale
    check_and_record(root, 2)
    workflow(root, "gate", "--stage", "4")

    plan = json.loads(ledger.read_text(encoding="utf-8"))
    (root / "NOTES.md").write_text("覆盖重复提交时，应检查底层请求调用次数。\n", encoding="utf-8")
    plan["learnings"] = [{"kind": "iteration", "summary": "请求次数的断言覆盖重复调用风险",
                         "path": "NOTES.md", "evidence": ["evidence/T1-round-2.txt"]}]
    save_json(ledger, plan)
    workflow(root, "gate", "--stage", "5")

    (root / "task/evidence/reconciliation.md").write_text(
        "已核对 PRD §1、§2、提交入口、回调和两条实际测试。\n", encoding="utf-8")
    plan["reconciliation"] = "evidence/reconciliation.md"
    plan["cleanup"] = {"reviewed": True, "note": "保留示例输出供查看，运行期间未启动服务"}
    save_json(ledger, plan)
    workflow(root, "render")
    after = workflow(root, "gate", "--stage", "6")
    assert after["delivery"] == "complete", after
    save_json(root / "task/evidence/gate-results.json", {"first_pass": before, "stale": stale,
                                                        "revalidated": after})
    print(f"首次验证通过，修改后旧证据被拒绝，复验后 2/2 项完成。\n计划文件 {root / 'task/PLAN.md'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="尚不存在的示例输出目录")
    args = parser.parse_args()
    root = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix="fcd-demo-"))
    if args.output:
        root.mkdir()
    demo(root)


if __name__ == "__main__":
    main()
