"""验证 Gate 的拒绝条件与部分交付语义；所有产物都在临时项目。"""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

SCRIPT = Path(__file__).with_name("workflow.py")
SPEC = importlib.util.spec_from_file_location("workflow", SCRIPT)
workflow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(workflow)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.task_dir = self.root / "docs/iterations/example"
        args = SimpleNamespace(title="状态控制及组合验收", profile="generic", source=["本轮用户需求"], design=[])
        workflow.initialize(args, self.root, self.task_dir)
        self.plan = workflow.read_json(self.task_dir / "plan.json")
        self.plan["sources"][0].update(status="read", summary="读取全部输入，要求提交中禁止重复提交")
        self.plan["design"].update(status="not_applicable", reason="本次验证 CLI 门禁，无视觉设计")
        self.plan["coverage"] = {key: "T1/T2 覆盖状态验证，其余在本次 CLI 样例不适用" for key in workflow.CATEGORIES}
        (self.root / "feature.py").write_text("def enabled(busy):\n    return not busy\n")
        workflow.write_json(self.task_dir / "evidence/preflight.json", {
            "project_root": str(self.root), "profile": "generic", "config": {},
            "checks": [{"name": "隔离测试项目", "ok": True, "detail": "仅在临时目录测试 Gate"}], "manual_checks": []})
        self.plan["environment"]["report"] = "evidence/preflight.json"
        for task_id, category in [("T1", "interaction"), ("T2", "integration")]:
            self.plan["tasks"].append({
                "id": task_id, "title": "检查提交状态", "type": category,
                "source": {"id": "S1", "location": "本轮第 1 条"},
                "scope": ["feature.py"], "rules": ["不适用：隔离 Gate 测试工程无业务规范"],
                "depends_on": [], "hidden_state": "始终显示，提交中禁用",
                "fixture": {"status": "not_applicable", "reason": "无视觉变更", "path": ""},
                "implementation": {"status": "done", "files": ["feature.py"], "note": "隔离样例"},
                "acceptance": [{"id": "C1", "expected": "提交中禁用，结束后恢复", "method": "unit", "status": "pending", "actual": "", "evidence": []}],
            })
            log = self.task_dir / f"evidence/{task_id}.txt"
            # 真实运行样例断言，获得独立于 Gate 的日志。
            result = subprocess.run([sys.executable, "-c", "from feature import enabled; assert not enabled(True); assert enabled(False); print('2 assertions passed')"], cwd=self.root, capture_output=True, text=True, check=True)
            log.write_text(result.stdout)
            args = SimpleNamespace(task=task_id, criterion="C1", kind="unit", file=f"evidence/{task_id}.txt", result="pass", actual="两条状态断言通过", context="临时工程 Python 断言；非业务系统验收", watch=["feature.py"])
            workflow.record(args, self.root, self.task_dir, self.plan)
        self.plan["learnings"] = [{"kind": "none", "summary": "需求、环境、实现和验证均为既有 Gate 的隔离样例，不形成业务规则"}]
        (self.task_dir / "reconciliation.md").write_text("已核对样例状态函数和两项验收；无其他业务改动。")
        self.plan["reconciliation"] = "reconciliation.md"
        self.plan["cleanup"] = {"reviewed": True, "note": "全部产物限于 TemporaryDirectory，由测试清理"}

    def check(self, stage=6):
        return workflow.gate(self.plan, self.root, self.task_dir, stage)

    def test_complete_evidence_chain(self):
        result = self.check()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["delivery"], "complete")
        self.assertEqual(result["completed_tasks"], 2)

    def test_unread_source_blocks_later_stages(self):
        self.plan["sources"][0]["status"] = "pending"
        self.assertFalse(self.check()["ok"])

    def test_unresolved_blocking_decision(self):
        self.plan["decisions"] = [{"id": "D1", "question": "接口变更？", "blocking": True, "status": "open"}]
        self.assertFalse(self.check()["ok"])

    def test_source_change_invalidates_old_evidence(self):
        (self.root / "feature.py").write_text("def enabled(busy):\n    return True\n")
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertTrue(any("关联源码已变化" in e for e in result["errors"]))
        self.assertIsNone(result["completed_tasks"])

    def test_artifact_change_invalidates_evidence(self):
        (self.task_dir / "evidence/T1.txt").write_text("changed after record")
        self.assertFalse(self.check()["ok"])

    def test_missing_watch_cannot_claim_complete(self):
        self.plan["tasks"][0]["acceptance"][0]["evidence"][0]["code"] = {}
        self.assertFalse(self.check()["ok"])

    def test_changed_acceptance_cannot_reuse_previous_pass(self):
        self.plan["tasks"][0]["acceptance"][0]["expected"] = "新要求：请求失败后显示错误并保持禁用"
        result = self.check()
        self.assertFalse(result["ok"])
        self.assertTrue(any("验收条件已变化" in e for e in result["errors"]))

    def test_unit_evidence_cannot_prove_device_acceptance(self):
        self.plan["tasks"][0]["acceptance"][0]["method"] = "device"
        self.assertFalse(self.check()["ok"])

    def test_device_handoff_is_partial_even_when_gate_passes(self):
        task = self.plan["tasks"][0]
        task["acceptance"].append({"id": "C2", "expected": "实际设备中连续点击只提交一次", "method": "device", "status": "blocked", "actual": "无设备", "evidence": []})
        self.assertFalse(self.check()["ok"])
        self.plan["handoff"] = [{"task": "T1", "criterion": "C2", "owner": "待项目负责人指定", "reason": "隔离环境无设备", "next_step": "在授权设备按真实链路验证"}]
        result = self.check()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["delivery"], "partial")
        self.assertEqual(result["completed_tasks"], 1)

    def test_ui_with_design_requires_fixture(self):
        self.plan["design"].update(status="available", refs=["测试设计帧"])
        self.plan["tasks"][0]["type"] = "ui"
        self.assertFalse(self.check()["ok"])

    def test_dependency_cycle_is_rejected(self):
        self.plan["tasks"][0]["depends_on"] = ["T2"]
        self.plan["tasks"][1]["depends_on"] = ["T1"]
        with self.assertRaisesRegex(ValueError, "依赖存在环"):
            self.check()

    def test_init_never_overwrites_existing_task(self):
        before = (self.task_dir / "plan.json").read_bytes()
        with self.assertRaises(FileExistsError):
            workflow.initialize(SimpleNamespace(title="重复", profile="generic", source=[], design=[]), self.root, self.task_dir)
        self.assertEqual(before, (self.task_dir / "plan.json").read_bytes())

    def test_paths_cannot_escape_project_via_symlink(self):
        outside = self.root.parent / "outside"
        (self.root / "linked").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "超出允许目录"):
            workflow.local(self.root, "linked/evidence.txt")

    def test_environment_config_change_requires_recheck(self):
        config = self.root / ".fvmrc"
        config.write_text('{"flutter":"3.47.9"}')
        report_path = self.task_dir / "evidence/preflight.json"
        report = workflow.read_json(report_path)
        report["config"] = {".fvmrc": workflow.digest(config)}
        workflow.write_json(report_path, report)
        config.write_text('{"flutter":"3.47.8"}')
        self.assertFalse(self.check()["ok"])

    def test_real_preflight_and_cli_on_clean_git_workspace(self):
        workflow.write_json(self.task_dir / "plan.json", self.plan)
        for command in [["git", "init", "-q"], ["git", "add", "."], ["git", "-c", "user.name=Workflow Test", "-c", "user.email=workflow@example.invalid", "commit", "-qm", "isolated fixture"]]:
            subprocess.run(command, cwd=self.root, check=True, capture_output=True)
        completed = subprocess.run([sys.executable, str(SCRIPT), "preflight", "--root", str(self.root), "--task-dir", str(self.task_dir)], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.plan = workflow.read_json(self.task_dir / "plan.json")
        self.assertTrue(self.check()["ok"])

    def test_deferred_implementation_needs_explicit_authority(self):
        self.plan["tasks"][0]["implementation"]["status"] = "deferred"
        self.plan["handoff"] = [{"task": "T1", "criterion": "implementation", "owner": "本次执行者", "reason": "延期", "next_step": "后续实施"}]
        self.assertFalse(self.check()["ok"])
        self.plan["tasks"][0]["implementation"]["authority"] = "本轮测试用户明确决定延期"
        self.assertTrue(self.check()["ok"])

    def test_additional_evidence_and_new_round(self):
        (self.task_dir / "evidence/extra.txt").write_text("补充同轮的实际断言输出")
        args = SimpleNamespace(task="T1", criterion="C1", kind="unit", file="evidence/extra.txt", result="pass", actual="补充状态断言", context="同轮独立测量", watch=["feature.py"], append=True)
        workflow.record(args, self.root, self.task_dir, self.plan)
        self.assertEqual(len(self.plan["tasks"][0]["acceptance"][0]["evidence"]), 2)
        args.append = False
        workflow.record(args, self.root, self.task_dir, self.plan)
        self.assertEqual(len(self.plan["tasks"][0]["acceptance"][0]["evidence"]), 1)
        self.assertTrue((self.task_dir / "evidence/T1.txt").is_file())


if __name__ == "__main__":
    unittest.main()
