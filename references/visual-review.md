# 截图比对与归因

技能的比图工具是初筛工具，不自动证明 UI 正确。必须保留原始图，确认选中/展开/禁用/隐藏等实际状态，再比较同一区域。

## 安装和运行

技能目录独立维护 Node 依赖，不写业务项目 `pubspec.yaml`。依赖缺失时：

```bash
npm ci --prefix "$SKILL_DIR" --ignore-scripts --no-audit --no-fund
node "$SKILL_DIR/scripts/compare-images.mjs" \
  --reference "$TASK_DIR/evidence/design.png" \
  --actual "$TASK_DIR/evidence/actual.png" \
  --out "$TASK_DIR/evidence/T1-round1"
```

只接受 PNG。可显式添加 `--reference-crop x,y,width,height`、`--actual-crop x,y,width,height` 和 `--actual-scale 0.5`。裁剪是原图像素坐标，先裁剪、再对实际图缩放；两图最终尺寸必须一致，禁止自动拉伸到同尺寸。

输出标准化的两图、并排图、差异图和 `comparison.json`。报告包括原图 SHA-256、裁剪/缩放、pixelmatch 参数、像素差异比例、SSIM 和加权分。

加权分 `100 × [0.7 × (1 - 差异像素数 / 总像素数) + 0.3 × SSIM]`；默认 pixelmatch 阈值为 0.1、排除其判定的抗锯齿差异，初筛线 98，可显式用 `--min-score` 修改。使用各库公开实现，不保证与文章内部参数一致。低于初筛线返回 1；参数/解码错误返回 2。即使高于初筛线，`acceptance` 仍为 `requires_review`。

## 逐项核对

在同轮检查日志中记录：状态断言、设计值、实测值、误差、根因、处理和复验结果。至少核对宽高、相对偏移、间距、颜色、字体/字号/行高、边框/圆角、资源、可见性和中间容器。

大面积背景会掩盖小控件错误，整页图通过后仍检查关键局部。父级底色/布局引起子级差异时先修父级。分数下降超过 2 分时复核是否回归；不能靠更改裁剪框、阈值或屏蔽真实差异来提分。

需求与旧设计稿冲突、字体平台差异、抗锯齿噪声等可以归因，但须有可核实依据；保留原始分数并逐项解释。处理后的已知差异与“零未解释差异”不是同一概念，不能伪造零差异图。
