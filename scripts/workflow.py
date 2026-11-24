#!/usr/bin/env python3
"""全流程任务账本、环境检查与证据 Gate。Python 3.9+，仅使用标准库。"""
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
CATEGORIES = ("ui", "interaction", "data", "tracking", "compatibility", "performance")
METHODS = ("static", "unit", "widget", "golden", "ui", "build", "service", "simulator", "device", "manual")
IMPLEMENTATION_STATES = ("pending", "in_progress", "done", "blocked", "deferred", "dropped")
ACCEPTANCE_STATES = ("pending", "pass", "fail", "blocked", "not_applicable")


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract_digest(plan, task, criterion):
    """验收条件或需求边界变化时，不能沿用旧条件下的通过结论。"""
    contract = {"task": {key: task.get(key) for key in ("title", "type", "source", "scope", "rules", "hidden_state", "depends_on")},
                "criterion": {key: criterion.get(key) for key in ("id", "expected", "method")},
                "design": plan.get("design"),
                "source": next((s for s in plan["sources"] if s["id"] == task["source"]["id"]), None)}
    return hashlib.sha256(json.dumps(contract, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and bool(value) and all(text(v) for v in value)


def local(base, name):
    if not text(name):
        raise ValueError("缺少本地路径")
    path = (base / name.split("#", 1)[0]).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f"路径超出允许目录：{name}")
    return path


def run(command, root):
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=25)
        return {"name": " ".join(command), "ok": result.returncode == 0,
                "exit_code": result.returncode, "detail": (result.stdout + result.stderr).strip() or "命令成功，无输出"}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"name": " ".join(command), "ok": False, "detail": str(error)}


def locations(args):
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise ValueError("项目目录不存在")
    task_dir = local(root, args.task_dir)
    return root, task_dir


def render(plan, task_dir):
    def safe(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = [f"# {plan['title']}", "", "由 plan.json 生成；修改账本后运行 render，勿单独维护此文件。", "",
             f"技术栈：`{plan['profile']}`；创建时间：{plan['created_at']}", "", "## 来源", ""]
    for source in plan["sources"]:
        lines.append(f"- {source['id']} [{source['status']}] {source['ref']}：{source.get('summary', '')}")
    lines += ["", "## 设计与覆盖", "", f"设计：{plan['design']}", ""]
    lines += [f"- {k}：{v}" for k, v in plan["coverage"].items()]
    lines += ["", "## 任务", "", "| ID | 类型 | 任务 | 实现 | 验收 |", "| --- | --- | --- | --- | --- |"]
    for task in plan["tasks"]:
        statuses = ", ".join(f"{c['id']}={c['status']}" for c in task["acceptance"])
        row = [task["id"], task["type"], task["title"], task["implementation"]["status"], statuses]
        lines.append("| " + " | ".join(safe(v) for v in row) + " |")
    for task in plan["tasks"]:
        lines += ["", f"### {task['id']} {task['title']}", "",
                  f"- 来源：{task['source']}", f"- 范围：{', '.join(task['scope'])}",
                  f"- 规范：{'; '.join(task['rules'])}", f"- 依赖：{task.get('depends_on', [])}",
                  f"- 隐藏态：{task['hidden_state']}", f"- 验收场景：{task['fixture']}",
                  f"- 实现：{task['implementation']}", ""]
        for criterion in task["acceptance"]:
            lines += [f"- {criterion['id']} [{criterion['status']}] {criterion['expected']}",
                      f"  - 方法：{criterion['method']}；实际：{criterion.get('actual', '')}；理由：{criterion.get('reason', '')}"]
            for evidence in criterion.get("evidence", []):
                lines.append(f"  - 证据：[{evidence['path']}]({evidence['path']})；上下文：{evidence.get('context', '')}")
    for title, key in [("决策", "decisions"), ("待办与交接", "handoff"), ("经验沉淀", "learnings")]:
        lines += ["", f"## {title}", "", "```json", json.dumps(plan[key], ensure_ascii=False, indent=2), "```"]
    lines += ["", "## 盘点与清理", "", f"盘点：{plan['reconciliation']}", f"清理：{plan['cleanup']}", ""]
    (task_dir / "PLAN.md").write_text("\n".join(lines), encoding="utf-8")


def initialize(args, root, task_dir):
    plan = read_json(SKILL / "assets/plan.json")
    plan.update(title=args.title, profile=args.profile, created_at=now())
    plan["sources"] = [{"id": f"S{i}", "ref": ref, "status": "pending", "summary": ""}
                       for i, ref in enumerate(args.source, 1)]
    plan["design"]["refs"] = args.design
    task_dir.mkdir(parents=True, exist_ok=False)
    (task_dir / "evidence").mkdir()
    write_json(task_dir / "plan.json", plan)
    render(plan, task_dir)
    (task_dir / "README.md").write_text(
        f"# {args.title}\n\n状态：已建立任务账本，尚未完成需求分析或实施。\n\n"
        "- [任务与验收计划](PLAN.md)\n- [唯一任务账本](plan.json)\n\n"
        "实施、验证、联调与设备验收结论须按实际证据补充，并同步项目文档导航。\n", encoding="utf-8")
    return {"task_dir": str(task_dir.relative_to(root)), "status": "initialized"}


def preflight(args, root, task_dir, plan):
    checks = [run(["git", "--version"], root), run(["git", "status", "--short"], root),
              run(["git", "rev-parse", "HEAD"], root), run(["git", "branch", "--show-current"], root)]
    config = {}
    for name in ("pubspec.yaml", "pubspec.lock", ".fvmrc", "package.json", "package-lock.json"):
        if (root / name).is_file():
            config[name] = digest(root / name)
    if plan["profile"] == "flutter":
        flutter = run(["flutter", "--version", "--machine"], root)
        checks += [flutter, run(["dart", "--version"], root)]
        for name in ("pubspec.yaml", ".dart_tool/package_config.json"):
            checks.append({"name": name, "ok": (root / name).is_file(), "detail": "检查工程文件与依赖解析产物"})
        if (root / ".fvmrc").is_file():
            pinned = read_json(root / ".fvmrc").get("flutter")
            try:
                actual = json.loads(flutter["detail"]).get("frameworkVersion")
            except (ValueError, TypeError):
                actual = None
            checks.append({"name": "FVM SDK 一致性", "ok": bool(pinned and pinned == actual),
                           "detail": f".fvmrc={pinned}; 当前 flutter={actual}"})
        if args.device:
            devices = run(["flutter", "devices", "--machine"], root)
            try:
                found = any(d.get("id") == args.device for d in json.loads(devices["detail"]))
            except (ValueError, TypeError):
                found = False
            devices.update(name=f"设备 {args.device}", ok=devices["ok"] and found)
            checks.append(devices)
    elif args.device:
        raise ValueError("--device 仅适用于 Flutter profile")
    if plan["profile"] == "web":
        checks += [run(["node", "--version"], root), run(["npm", "--version"], root)]
    for address in args.port:
        host, port = address.rsplit(":", 1)
        try:
            with socket.create_connection((host, int(port)), timeout=3):
                ok, detail = True, "TCP 可连接；仍须核实代理规则/本地代码实际生效"
        except (OSError, ValueError) as error:
            ok, detail = False, str(error)
        checks.append({"name": f"端口 {address}", "ok": ok, "detail": detail})
    report = {"created_at": now(), "project_root": str(root), "profile": plan["profile"],
              "checks": checks, "manual_checks": [], "config": config}
    write_json(task_dir / "evidence/preflight.json", report)
    plan["environment"]["report"] = "evidence/preflight.json"
    write_json(task_dir / "plan.json", plan)
    return {"ok": all(c["ok"] for c in checks), "report": "evidence/preflight.json",
            "failed": [c for c in checks if not c["ok"]]}


def record(args, root, task_dir, plan):
    task = next((t for t in plan["tasks"] if t["id"] == args.task), None)
    if task is None:
        raise ValueError(f"任务不存在：{args.task}")
    criterion = next((c for c in task["acceptance"] if c["id"] == args.criterion), None)
    if criterion is None or criterion["method"] != args.kind:
        raise ValueError("验收条件不存在，或证据类型与验收方法不一致")
    artifact = local(task_dir, args.file)
    if not artifact.is_file() or artifact.stat().st_size == 0:
        raise ValueError("证据文件不存在或为空；请先实际执行验证并保存产物")
    watched = {}
    for name in args.watch:
        path = local(root, name)
        watched[str(path.relative_to(root))] = digest(path)
    evidence = {"path": str(artifact.relative_to(task_dir)), "sha256": digest(artifact),
                "kind": args.kind, "context": args.context, "recorded_at": now(), "code": watched,
                "contract_sha256": contract_digest(plan, task, criterion)}
    # 新轮次默认替换旧证据；同轮的额外截图/测量可显式追加。
    prior = criterion.get("evidence", []) if getattr(args, "append", False) else []
    prior = [item for item in prior if item.get("path") != evidence["path"]]
    criterion.update(status=args.result, actual=args.actual, evidence=[*prior, evidence], reason="")
    write_json(task_dir / "plan.json", plan)
    render(plan, task_dir)
    return {"task": args.task, "criterion": args.criterion, "status": args.result, "evidence": evidence}


def gate(plan, root, task_dir, stage):
    errors = []

    def require(ok, message):
        if not ok:
            errors.append(message)

    def file_at(base, name, label):
        try:
            path = local(base, name)
            require(path.is_file() and path.stat().st_size > 0, f"{label}：文件不存在或为空 {name}")
            return path if path.is_file() else None
        except (ValueError, OSError) as error:
            errors.append(f"{label}：{error}")
            return None

    require(plan.get("schema_version") == 1, "不支持的 schema_version")
    require(text(plan.get("title")), "缺少需求标题")
    require(plan.get("profile") in ("generic", "flutter", "web"), "未知技术栈 profile")
    report_path = file_at(task_dir, plan.get("environment", {}).get("report"), "阶段1环境报告")
    if report_path:
        report = read_json(report_path)
        require(report.get("project_root") == str(root), "阶段1环境报告来自另一项目")
        require(report.get("profile") == plan["profile"], "阶段1环境报告技术栈不匹配")
        checks = report.get("checks", []) + report.get("manual_checks", [])
        require(bool(checks), "阶段1环境检查为空")
        for check in checks:
            require(check.get("ok") is True and text(check.get("detail")), f"阶段1检查未通过：{check.get('name')}")
        for name, sha in report.get("config", {}).items():
            path = file_at(root, name, "阶段1配置")
            if path:
                require(digest(path) == sha, f"阶段1配置已变化，需重新检查：{name}")
    if stage < 2:
        return result(plan, stage, errors)
    sources = plan.get("sources", [])
    source_ids = [s.get("id") for s in sources]
    require(bool(sources) and all(text(i) for i in source_ids) and len(source_ids) == len(set(source_ids)), "阶段2来源为空或 ID 重复/缺失")
    for source in sources:
        require(source.get("status") == "read" and text(source.get("ref")) and text(source.get("summary")), f"阶段2来源未读完：{source.get('id')}")
    design = plan.get("design", {})
    require(design.get("status") in ("available", "not_applicable"), "阶段2设计状态未确认")
    require(strings(design.get("refs")) if design.get("status") == "available" else text(design.get("reason")), "阶段2缺少设计引用或不适用理由")
    for category in CATEGORIES:
        require(text(plan.get("coverage", {}).get(category)), f"阶段2覆盖未说明：{category}")
    for decision in plan.get("decisions", []):
        require(text(decision.get("id")) and text(decision.get("question")), "阶段2决策缺少 ID/问题")
        require(decision.get("status") in ("open", "resolved"), "阶段2决策状态无效")
        require(not decision.get("blocking", True) or decision.get("status") == "resolved", f"阶段2有未决阻塞：{decision.get('id')}")
        if decision.get("status") == "resolved":
            require(text(decision.get("resolution")) and text(decision.get("authority")), "阶段2决策缺少结论或依据")
    tasks = plan.get("tasks", [])
    task_ids = [t.get("id") for t in tasks]
    require(bool(tasks) and all(text(i) for i in task_ids) and len(task_ids) == len(set(task_ids)), "阶段2任务为空或 ID 重复/缺失")
    require(any(t.get("type") == "integration" for t in tasks), "阶段2缺少独立组合验收任务")
    for task in tasks:
        label = f"阶段2任务 {task.get('id')}"
        require(text(task.get("title")) and text(task.get("hidden_state")), f"{label} 缺少标题/隐藏态说明")
        require(task.get("type") in (*CATEGORIES, "integration", "documentation"), f"{label} 类别无效")
        require(task.get("source", {}).get("id") in source_ids and text(task.get("source", {}).get("location")), f"{label} 缺少有效出处")
        require(strings(task.get("scope")) and strings(task.get("rules")), f"{label} 范围/规范为空")
        dependencies = task.get("depends_on", [])
        require(isinstance(dependencies, list) and all(d in task_ids and d != task.get("id") for d in dependencies), f"{label} 依赖无效")
        criteria = task.get("acceptance", [])
        ids = [c.get("id") for c in criteria]
        require(bool(criteria) and all(text(i) for i in ids) and len(ids) == len(set(ids)), f"{label} 验收为空或 ID 重复/缺失")
        for criterion in criteria:
            require(text(criterion.get("expected")) and criterion.get("method") in METHODS, f"{label}/{criterion.get('id')} 缺少预期/方法")
            require(criterion.get("status") in ACCEPTANCE_STATES, f"{label} 验收状态无效")
    graph = {t.get("id"): t.get("depends_on", []) for t in tasks}
    active, visited = set(), set()

    def visit(key):
        if key in active:
            raise ValueError("阶段2任务依赖存在环")
        if key in visited:
            return
        active.add(key)
        for dependency in graph.get(key, []):
            visit(dependency)
        active.remove(key)
        visited.add(key)

    for key in graph:
        visit(key)
    if stage < 3:
        return result(plan, stage, errors)
    for task in tasks:
        fixture = task.get("fixture", {})
        if fixture.get("status") == "ready":
            file_at(task_dir, fixture.get("path"), f"阶段3 {task['id']} 场景")
        elif fixture.get("status") == "not_applicable":
            require(text(fixture.get("reason")), f"阶段3 {task['id']} 缺少不适用理由")
            require(not (task["type"] == "ui" and design.get("status") == "available"), f"阶段3 {task['id']} 有设计的 UI 任务不能跳过场景")
        else:
            require(False, f"阶段3 {task['id']} 验收场景未就绪")
    if stage < 4:
        return result(plan, stage, errors)
    handoffs = plan.get("handoff", [])
    for handoff in handoffs:
        require(all(text(handoff.get(k)) for k in ("task", "criterion", "owner", "reason", "next_step")), "阶段4交接记录字段不完整")
        target = next((t for t in tasks if t["id"] == handoff.get("task")), None)
        require(target is not None and handoff.get("criterion") in ["implementation", *[c["id"] for c in target["acceptance"]]] if target else False, "阶段4交接引用不存在的任务/条件")

    def handed(task_id, criterion_id):
        return any(h.get("task") == task_id and h.get("criterion") == criterion_id for h in handoffs)

    for task in tasks:
        implementation = task.get("implementation", {})
        require(implementation.get("status") in IMPLEMENTATION_STATES, f"阶段4 {task['id']} 实现状态无效")
        if implementation.get("status") != "done":
            require(handed(task["id"], "implementation"), f"阶段4 {task['id']} 未实现且没有交接")
        if implementation.get("status") in ("deferred", "dropped"):
            require(text(implementation.get("authority")) and text(implementation.get("note")), f"阶段4 {task['id']} 延期/放弃缺少明确依据")
        files = implementation.get("files", [])
        require(isinstance(files, list), f"阶段4 {task['id']} files 必须为数组")
        if not files:
            require(text(implementation.get("note")), f"阶段4 {task['id']} 无文件改动须说明原因")
        watched = set()
        for name in files:
            file_at(root, name, f"阶段4 {task['id']} 实现")
        for criterion in task["acceptance"]:
            label = f"阶段4 {task['id']}/{criterion['id']}"
            status = criterion.get("status")
            if status == "not_applicable":
                require(text(criterion.get("reason")), f"{label} 缺少不适用理由")
            elif status != "pass":
                require(handed(task["id"], criterion["id"]), f"{label} 未通过且没有交接")
            else:
                require(text(criterion.get("actual")) and bool(criterion.get("evidence")), f"{label} 没有实际结果/证据")
                for evidence in criterion.get("evidence", []):
                    require(evidence.get("contract_sha256") == contract_digest(plan, task, criterion), f"{label} 需求边界或验收条件已变化，需复验")
                    path = file_at(task_dir, evidence.get("path"), label)
                    if path:
                        require(digest(path) == evidence.get("sha256"), f"{label} 证据已变化，需复验")
                    require(evidence.get("kind") == criterion["method"] and text(evidence.get("context")), f"{label} 证据方法不匹配或缺少上下文")
                    for name, sha in evidence.get("code", {}).items():
                        source_path = file_at(root, name, label)
                        if source_path:
                            require(digest(source_path) == sha, f"{label} 关联源码已变化，需复验：{name}")
                        watched.add(name)
        if implementation.get("status") == "done" and all(c["status"] in ("pass", "not_applicable") for c in task["acceptance"]):
            require(set(files) <= watched, f"阶段4 {task['id']} 证据未覆盖全部实现文件的指纹")
    if stage < 5:
        return result(plan, stage, errors)
    require(bool(plan.get("learnings")), "阶段5缺少经验沉淀判断")
    for learning in plan.get("learnings", []):
        require(learning.get("kind") in ("rule", "skill", "iteration", "none") and text(learning.get("summary")), "阶段5沉淀类别/结论不完整")
        if learning.get("kind") != "none":
            file_at(root, learning.get("path"), "阶段5知识文件")
            require(strings(learning.get("evidence")), "阶段5沉淀缺少依据")
            for name in learning.get("evidence", []):
                file_at(task_dir, name, "阶段5依据")
    if stage >= 6:
        file_at(task_dir, plan.get("reconciliation"), "阶段6双向盘点")
        require(plan.get("cleanup", {}).get("reviewed") is True and text(plan.get("cleanup", {}).get("note")), "阶段6清理尚未盘点/缺少说明")
    return result(plan, stage, errors)


def result(plan, stage, errors):
    tasks = plan.get("tasks", [])
    completed = sum(t.get("implementation", {}).get("status") == "done" and bool(t.get("acceptance"))
                    and all(c.get("status") in ("pass", "not_applicable") for c in t["acceptance"]) for t in tasks)
    return {"ok": not errors, "stage": stage, "delivery": "complete" if stage >= 4 and tasks and completed == len(tasks) and not errors else "partial",
            "completed_tasks": completed if stage >= 4 and not errors else None,
            "declared_completed_tasks": completed, "total_tasks": len(tasks), "errors": errors,
            "note": "Gate 仅核对登记、指纹和产物；须审阅证据，不能由脚本结果推断实际业务/设备验收。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "preflight", "render", "record", "gate"):
        sub = commands.add_parser(command)
        sub.add_argument("--root", default=".")
        sub.add_argument("--task-dir", required=True)
        if command == "init":
            sub.add_argument("--title", required=True)
            sub.add_argument("--profile", choices=("generic", "flutter", "web"), default="generic")
            sub.add_argument("--source", action="append", default=[])
            sub.add_argument("--design", action="append", default=[])
        elif command == "preflight":
            sub.add_argument("--device")
            sub.add_argument("--port", action="append", default=[])
        elif command == "gate":
            sub.add_argument("--stage", type=int, choices=range(1, 7), required=True)
        elif command == "record":
            for field in ("task", "criterion", "file", "actual", "context"):
                sub.add_argument(f"--{field}", required=True)
            sub.add_argument("--kind", choices=METHODS, required=True)
            sub.add_argument("--result", choices=("pass", "fail", "blocked"), required=True)
            sub.add_argument("--watch", action="append", default=[])
            sub.add_argument("--append", action="store_true", help="追加同轮其他证据；新一轮复验不要使用")
    args = parser.parse_args()
    try:
        root, task_dir = locations(args)
        if args.command == "init":
            output = initialize(args, root, task_dir)
        else:
            plan = read_json(task_dir / "plan.json")
            if args.command == "preflight":
                output = preflight(args, root, task_dir, plan)
            elif args.command == "record":
                output = record(args, root, task_dir, plan)
            elif args.command == "render":
                render(plan, task_dir)
                output = {"status": "rendered", "path": str((task_dir / "PLAN.md").relative_to(root))}
            else:
                output = gate(plan, root, task_dir, args.stage)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0 if output.get("ok", True) else 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
