# 提交防重复示例

示例使用本地 PRD 和受控请求回调，覆盖连续提交与请求结束后再次提交。 [示例 PRD](PRD.md)

在仓库根目录运行 `python3 examples/no-double-submit/demo.py --output /tmp/fcd-submit-demo`，或省略 `--output` 让程序创建临时目录。该命令会打印生成文件的位置。

生成的 `task/PLAN.md` 对应任务账本。证据目录保留两轮测试输出、首次通过、代码变化后拒绝、复验后通过的阶段检查记录。故意追加的源码注释用于验证文件指纹变化，提交功能的行为保持一致。
