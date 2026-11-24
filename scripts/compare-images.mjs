#!/usr/bin/env node
// PNG 比稿：显式裁剪/缩放、pixelmatch 差异图、SSIM 和 70/30 加权初筛。
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { PNG } from 'pngjs';
import pixelmatch from 'pixelmatch';
import ssimModule from 'ssim.js';

const { ssim } = ssimModule;
const sha256 = (data) => crypto.createHash('sha256').update(data).digest('hex');

function cropImage(image, region) {
  if (!region) return image;
  const values = region.split(',').map(Number);
  if (values.length !== 4 || values.some((v) => !Number.isInteger(v))) {
    throw new Error('裁剪格式为 x,y,width,height，且均为整数');
  }
  const [x, y, width, height] = values;
  if (x < 0 || y < 0 || width <= 0 || height <= 0 || x + width > image.width || y + height > image.height) {
    throw new Error('裁剪区域超出图片或为空');
  }
  const result = new PNG({ width, height });
  PNG.bitblt(image, result, x, y, width, height, 0, 0);
  return result;
}

function scaleImage(image, scale) {
  if (scale === 1) return image;
  if (!Number.isFinite(scale) || scale <= 0) throw new Error('实际图缩放必须是正数');
  const width = Math.round(image.width * scale);
  const height = Math.round(image.height * scale);
  if (width < 1 || height < 1) throw new Error('缩放后图片为空');
  const result = new PNG({ width, height });
  // 双线性插值；不自动推断缩放比例，不改变原始图片。
  for (let y = 0; y < height; y++) {
    const sy = Math.max(0, Math.min(image.height - 1, (y + 0.5) / scale - 0.5));
    const y0 = Math.floor(sy), y1 = Math.min(y0 + 1, image.height - 1), fy = sy - y0;
    for (let x = 0; x < width; x++) {
      const sx = Math.max(0, Math.min(image.width - 1, (x + 0.5) / scale - 0.5));
      const x0 = Math.floor(sx), x1 = Math.min(x0 + 1, image.width - 1), fx = sx - x0;
      for (let c = 0; c < 4; c++) {
        const a = image.data[(y0 * image.width + x0) * 4 + c];
        const b = image.data[(y0 * image.width + x1) * 4 + c];
        const d = image.data[(y1 * image.width + x0) * 4 + c];
        const e = image.data[(y1 * image.width + x1) * 4 + c];
        result.data[(y * width + x) * 4 + c] = Math.round((1 - fy) * ((1 - fx) * a + fx * b) + fy * ((1 - fx) * d + fx * e));
      }
    }
  }
  return result;
}

function flattenWhite(image) {
  const result = new PNG({ width: image.width, height: image.height });
  for (let i = 0; i < image.data.length; i += 4) {
    const alpha = image.data[i + 3] / 255;
    for (let c = 0; c < 3; c++) result.data[i + c] = Math.round(image.data[i + c] * alpha + 255 * (1 - alpha));
    result.data[i + 3] = 255;
  }
  return result;
}

export function compareImages(options) {
  const minScore = Number(options['min-score'] ?? 98);
  if (!Number.isFinite(minScore) || minScore < 0 || minScore > 100) throw new Error('min-score 必须在 0 到 100 之间');
  for (const key of ['reference', 'actual', 'out']) {
    if (!options[key]) throw new Error(`缺少 --${key}`);
  }
  const originalReference = fs.readFileSync(options.reference);
  const originalActual = fs.readFileSync(options.actual);
  const reference = flattenWhite(cropImage(PNG.sync.read(originalReference), options['reference-crop']));
  const scale = Number(options['actual-scale'] ?? 1);
  const actual = flattenWhite(scaleImage(cropImage(PNG.sync.read(originalActual), options['actual-crop']), scale));
  if (reference.width !== actual.width || reference.height !== actual.height) {
    throw new Error(`尺寸不一致：设计 ${reference.width}x${reference.height}，实际 ${actual.width}x${actual.height}；请明确裁剪或缩放，禁止自动拉伸`);
  }
  if (reference.width < 11 || reference.height < 11) throw new Error('SSIM 比较区域至少为 11x11 像素');
  const out = path.resolve(options.out);
  if (fs.existsSync(out)) throw new Error('输出目录已存在；请用新的轮次目录，保留已有证据');
  const diff = new PNG({ width: reference.width, height: reference.height });
  const pixelOptions = { threshold: 0.1, includeAA: false };
  const mismatch = pixelmatch(reference.data, actual.data, diff.data, reference.width, reference.height, pixelOptions);
  const structural = ssim(reference, actual).mssim;
  if (!Number.isFinite(structural)) throw new Error('SSIM 未生成有效结果');
  const mismatchRatio = mismatch / (reference.width * reference.height);
  const score = Math.max(0, Math.min(100, 100 * (0.7 * (1 - mismatchRatio) + 0.3 * structural)));
  const report = {
    created_at: new Date().toISOString(),
    inputs: {
      reference: { file: path.basename(options.reference), sha256: sha256(originalReference), crop: options['reference-crop'] ?? null },
      actual: { file: path.basename(options.actual), sha256: sha256(originalActual), crop: options['actual-crop'] ?? null, scale },
    },
    width: reference.width, height: reference.height,
    normalization: '显式裁剪和实际图双线性缩放；透明背景合成至白色',
    pixelmatch: { ...pixelOptions, mismatched_pixels: mismatch, mismatch_ratio: mismatchRatio },
    ssim: structural,
    score, min_score: minScore, screening_pass: score >= minScore,
    acceptance: 'requires_review',
    artifacts: { reference: 'reference.png', actual: 'actual.png', diff: 'diff.png', side_by_side: 'side-by-side.png' },
    note: '分数仅用于初筛；须另验状态、数值、隐藏态和差异归因，不等同业务或真机验收。',
  };
  const pair = new PNG({ width: reference.width * 2, height: reference.height });
  PNG.bitblt(reference, pair, 0, 0, reference.width, reference.height, 0, 0);
  PNG.bitblt(actual, pair, 0, 0, actual.width, actual.height, reference.width, 0);
  fs.mkdirSync(out, { recursive: true });
  for (const [name, data] of [['reference.png', reference], ['actual.png', actual], ['diff.png', diff], ['side-by-side.png', pair]]) {
    fs.writeFileSync(path.join(out, name), PNG.sync.write(data));
  }
  fs.writeFileSync(path.join(out, 'comparison.json'), JSON.stringify(report, null, 2) + '\n');
  return report;
}

function main() {
  const args = process.argv.slice(2);
  if (args.includes('--help')) {
    console.log('node compare-images.mjs --reference design.png --actual actual.png --out round1 [--reference-crop x,y,w,h] [--actual-crop x,y,w,h] [--actual-scale 0.5] [--min-score 98]');
    return;
  }
  const allowed = new Set(['reference', 'actual', 'out', 'reference-crop', 'actual-crop', 'actual-scale', 'min-score']);
  const options = {};
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace(/^--/, '');
    if (!args[i].startsWith('--') || !allowed.has(key) || args[i + 1] === undefined) throw new Error(`参数无效：${args[i]}`);
    options[key] = args[i + 1];
  }
  const report = compareImages(options);
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = report.screening_pass ? 0 : 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); } catch (error) {
    console.error(JSON.stringify({ ok: false, error: error.message }));
    process.exitCode = 2;
  }
}
