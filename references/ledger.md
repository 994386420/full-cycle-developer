# 任务账本

`assets/plan.json` 是初始化结构。允许编辑 JSON，但不要同时手改生成的 `PLAN.md`。所有状态使用下列值，所有说明用具体中文事实，不填“同上”“其余正常”。

## 顶层字段

- `sources`：`id`、`ref`、`status`（`pending/read/blocked`）、`summary`。用户本轮文本也可作来源，引用具体段落。`read` 必须有读取结论。
- `design`：`status`（`pending/available/not_applicable`）、`refs`、`reason`。无设计必须说明原因。
- `coverage`：六类 `ui/interaction/data/tracking/compatibility/performance` 各写涉及任务 ID，或具体不适用理由。
- `decisions`：`id/question/blocking/status/resolution/authority`，`status` 为 `open/resolved`。阻塞决策必须解决；已解决项有决定和依据。
- `environment.report`：环境检查报告路径，由 `preflight` 写入。
- `tasks`：实现和组合验收的任务清单，至少一项 `integration`。
- `handoff`：未完成项的交接；每项 `task/criterion/owner/reason/next_step`，其中 `criterion` 可为验收 ID 或 `implementation`。负责人未知如实写“待项目负责人指定”，不能虚构他人已接受。
- `learnings`：`kind`（`rule/skill/iteration/none`）、`summary`、`path`、`evidence`。非 `none` 路径相对项目根，依据路径相对任务目录。
- `reconciliation`：清单与代码双向盘点文件，相对任务目录。
- `cleanup`：`reviewed` 布尔值和具体 `note`。

## 单项任务示例

以下仅示范字段，不代表已确认需求或已完成工作：

```json
{
  "id": "T1",
  "title": "提交中禁用确认按钮",
  "type": "interaction",
  "source": {"id": "S1", "location": "交互说明 §2"},
  "scope": ["lib/feature/page.dart"],
  "rules": ["docs/rules/example.md#重复提交"],
  "depends_on": [],
  "hidden_state": "按钮保持可见；请求进行中禁用，结束后恢复",
  "fixture": {"status": "not_applicable", "path": "", "reason": "本项为已有控件状态，场景由验收步骤说明"},
  "implementation": {"status": "pending", "files": [], "note": ""},
  "acceptance": [{
    "id": "C1",
    "expected": "请求未完成时连续点击只发出一次提交；成功与失败后均恢复可操作",
    "method": "widget",
    "status": "pending",
    "actual": "",
    "reason": "",
    "evidence": []
  }]
}
```

`type` 为六类之一、`integration` 或 `documentation`。`depends_on` 必须引用其他有效任务且无环。所有任务都有 `hidden_state`；不相关时写具体原因。规范不适用时可填 `不适用：本次只更新……`。

`implementation.status` 使用 `pending/in_progress/done/blocked/deferred/dropped`。`files` 登记实际实现、测试、配置等文件，路径相对项目根；没有文件改动（例如只验已有页面）在 `note` 说明。延期/放弃还需 `authority` 记录明确决定依据。

`acceptance.method` 为 `static/unit/widget/golden/ui/build/service/simulator/device/manual`。`status` 为 `pending/pass/fail/blocked/not_applicable`；通过须有实际结果和证据，不适用须有理由。`record` 支持登记 `pass/fail/blocked`。

`record` 为每份证据登记文件 SHA-256、方法、观察上下文及 `--watch` 源码指纹。路径相对任务目录；`--watch` 路径相对项目根，可重复。新轮次默认替换该条件的旧证据；同轮补充其他截图/测量使用 `--append`。Gate 检查证据方法匹配、文件内容未变、关联源码未变，并检查通过证据的 watch 并集覆盖该任务 `implementation.files`。需要复验时，应更新真实证据和判断。

通过项不能只附无状态说明的截图或无断言范围的日志。脚本不能判别捏造内容，主执行者仍负责核实实际观察。

证据还绑定登记时的来源、设计状态、任务边界和当前验收条件。上述内容变化时，旧结论需要复验，不能仅修改 `expected` 后沿用原来的通过状态。

## 部分交付

阶段 4 以后，每个未实现任务和每个未通过条件都需要独立 `handoff`。`not_applicable` 只用于确实不适用，不用于掩盖失败。延期/放弃需要在实现说明中附已有授权；脚本不会自动替人批准。

`gate` 退出码 0 只表示该阶段登记要求满足。`delivery` 为 `partial` 时有未闭环项，即便 `ok` 为 true 也必须按部分交付汇报。`delivery` 为 `complete` 还需主执行者确认所有内容与证据真实对应。
