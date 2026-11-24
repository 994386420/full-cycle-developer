---
name: full-cycle-developer
description: 将需求、设计稿和现有代码转为可追溯的实现清单，按六阶段完成开发、自验返工和经验沉淀。用于多功能点需求、跨模块改造、设计还原，或用户要求“按文章的工作流”“全流程开发”“自己验收”。单纯咨询、局部文案调整和小修复不必启动完整流程。
---

# 全流程开发

目标是交付可核实的实现、验收证据和未完成事项。依据公开文章独立编写，并非腾讯原版源码；来源与能力边界见 [references/origin.md](references/origin.md)。

## 开始和恢复

1. 读取项目 `AGENTS.md` 和文档入口，检查 Git 状态，寻找已有迭代和相近实现。项目约定优先；技能不扩大任务范围或操作权限。
2. 确定需求、设计来源和任务目录。已有 `plan.json` 就恢复，不再建第二份清单。按项目现有规则确定任务产物的位置。Flutter 项目可读取 [references/flutter.md](references/flutter.md)。
3. 将下文技能目录记作 `SKILL_DIR`，项目目录记作 `PROJECT_ROOT`，任务目录记作 `TASK_DIR`。命令中的变量必须替换为当前实际路径。

```bash
python3 "$SKILL_DIR/scripts/workflow.py" init --root "$PROJECT_ROOT" \
  --task-dir "$TASK_DIR" --title "需求名称" --profile generic \
  --source "用户需求或 PRD 链接" --design "设计稿链接"
```

`--profile` 可选 `flutter`、`web`、`generic`；无设计稿省略 `--design`。生成 `plan.json`、`PLAN.md` 和迭代入口 `README.md`。遵循项目导航规则接入索引。

`plan.json` 是唯一任务账本，`PLAN.md` 是它的可读视图。修改账本后运行 `render`，不要分别维护两份结论。字段约定见 [references/ledger.md](references/ledger.md)。

## 六阶段执行

**只在进入当前阶段时读取该阶段文件。** 可以阅读本页的全局约束，不预读后续阶段的操作提示词，不提前修改业务代码。

| 阶段 | 当前阶段文件 | 进入下一阶段前的检查 |
| --- | --- | --- |
| 1 环境检查 | [references/01-environment.md](references/01-environment.md) | 工具、依赖和本次必需运行条件就绪 |
| 2 制定 Plan、分发规范 | [references/02-plan.md](references/02-plan.md) | 来源读完、逐项可验收、规范明确、冲突有处理 |
| 3 建立验收场景 | [references/03-fixtures.md](references/03-fixtures.md) | 设计状态与任务有明确映射；不适用有原因 |
| 4 逐项实现、自验返工 | [references/04-implement.md](references/04-implement.md) | 每项有有效证据；未通过项有明确交接 |
| 5 沉淀经验 | [references/05-learn.md](references/05-learn.md) | 只沉淀已验证结论，并更新已有知识入口 |
| 6 盘点、清理、交付 | [references/06-close.md](references/06-close.md) | 清单与代码双向核对，完成口径和待办真实 |

每阶段结束执行：

```bash
python3 "$SKILL_DIR/scripts/workflow.py" gate --root "$PROJECT_ROOT" \
  --task-dir "$TASK_DIR" --stage 2
python3 "$SKILL_DIR/scripts/workflow.py" render --root "$PROJECT_ROOT" --task-dir "$TASK_DIR"
```

`gate` 会重新检查此前阶段，失败时返回非零退出码和缺项；修复缺项后复检。程序只核对结构、文件指纹和已登记证据，**不能证明需求理解或验收结论本身正确**，必须逐条审阅证据内容。

## 贯穿全程的约束

- 每项任务写明需求出处、类别、影响范围、规范、可客观判断的验收条件和隐藏态。六类覆盖分别检查 UI、交互、数据、埋点、兼容、性能，不相关的写明理由。
- 截图前先确认实际状态。设计稿值、实测值、差异归因、修复和复检都落盘；父级问题先修父级，不用反向偏移或硬编码掩盖根因。
- 证据必须包括实际结果与上下文。源码或证据文件变化后，相关验收失效，需要重新验证。静态检查、单测、离屏图、构建、真实服务、模拟器和真机分别陈述。
- 先诊断再修复，将同轮差异合并修复后统一复验。涉及初始化、注册、缓存和持久化时，增加冷启动、重开、刷新或重新进入验证。
- 未读来源、冲突或环境缺失只阻塞依赖它的工作；独立范围可拆成另一份明确的任务，不凭猜测跨过当前 Gate。连续两轮同因失败且没有新证据时先诊断或登记阻塞，避免无界重试。
- 单项通过后仍要执行真实入口→数据→渲染→持久化/返回刷新的组合验证。整体形态也要与主设计帧核对。
- 默认在当前会话顺序执行。会话或项目已允许代理协作时，可按阶段 4 的任务包使用子代理；缺少代理工具时照常执行并如实记录验证独立性。不要因文章使用了子代理就要求用户额外配置或授权。
- 不把技能当成发布、推送、提交工时、发送消息、创建线上测试文档或调用付费服务的授权。默认使用本地验收文档；已有明确授权时才用外部系统。
- 有待验项时可以完成代码交付和知识沉淀，但必须汇报“部分完成/待验”，不能说全部验收通过。不要把没有设计稿误写为 UI 验收通过。

## 截图比对

需要视觉验收时，先读 [references/visual-review.md](references/visual-review.md)。提供 PNG 裁剪、显式缩放、pixelmatch 差异图和 SSIM 评分。依赖在技能目录内通过 `npm ci` 安装，不改业务应用依赖。

## 交付口径

说明完成了多少任务、实际验证了哪些层次、哪些被阻塞或待验，并链接 Plan 和证据。记录经验存放位置。无需让用户批准已经授权且可逆的常规实现。
