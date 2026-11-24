# Full Cycle Developer

把 PRD 变成可追溯的实施清单，让 Codex 逐项实现、自验、返工，并留下可复核的交付证据。

- 从需求、设计和代码建立任务账本，按阶段检查来源、计划、验收场景与交付。
- 保存测试输出、截图和关联文件指纹。源码或验收条件变更时，阶段检查会提示复验。
- 记录无法完成的验收及下一步。存在未闭环事项时，交付结果保留为部分完成。
- 可选 PNG 比稿工具生成差异图、并排图和评分报告，支持显式裁剪与缩放。

## 在 Codex 中使用

工作流脚本需要 Git 和 Python 3.9 或更高版本。使用 PNG 比稿时还需要 Node.js 18 或更高版本。

安装到当前项目，在项目根目录执行以下命令。将目标目录换成 `~/.agents/skills/full-cycle-developer` 可按用户安装。

```bash
git clone --branch v0.1.0 https://github.com/994386420/full-cycle-developer.git .agents/skills/full-cycle-developer
```

在 Codex 中提供完整 PRD 的位置和本次实施范围。

```text
请用 $full-cycle-developer 实现这份 PRD 中的 App 端需求，并逐项自验。
PRD：<链接或本地路径>
范围：<整份 PRD，或指定章节>
设计稿：<可选链接或本地路径>
```

工作流依次检查环境、制定计划、准备验收场景、实现和自验、记录经验、核对交付。可读的 `PLAN.md` 由 `plan.json` 生成。后续会话可以提供已有账本路径，继续验证和实施。 [技能说明](SKILL.md) · [账本字段](references/ledger.md)

## 运行示例

从本仓库根目录运行。请使用尚不存在的输出目录。

```bash
python3 examples/no-double-submit/demo.py --output /tmp/fcd-submit-demo
```

示例读取本地 PRD，执行真实 Python 断言，再把输出登记为证据。随后改动实现文件并检查原有结论是否被拒绝，最后重跑测试、登记新证据并恢复通过。结果写入输出目录的 `task/PLAN.md` 和 `task/evidence/`。 [示例详情](examples/no-double-submit/README.md)

## 可选的截图比稿

```bash
npm ci --ignore-scripts --no-audit --no-fund
node scripts/compare-images.mjs --reference design.png --actual screenshot.png --out comparison-round-1
```

分数用于筛查差异。验收仍需核对页面状态、布局数值和差异原因。 [比稿参数与产物](references/visual-review.md)

## 验证范围

```bash
python3 -m unittest discover -s scripts -p 'test_workflow.py'
node --test scripts/test-compare-images.mjs
```

`v0.1.0` 是预览版。阶段检查核对记录、文件和指纹，Codex 仍需读取来源、实际执行验证并审阅证据。首版覆盖脚本测试和独立示例，真实业务的端到端效果待实测。

工作流灵感来自侯国春发表的《半年用AI写需求，我终于不用给AI当测试了》，本仓库采用独立实现。 [原文](https://mp.weixin.qq.com/s/oSeeRQikg_J6xA0hSiy8hA) · [实现说明](references/origin.md) · [MIT 许可证](LICENSE)
