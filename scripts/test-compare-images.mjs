// 合成图仅测试比稿算法，不作为真实页面验收证据。
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { PNG } from 'pngjs';
import { compareImages } from './compare-images.mjs';

function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'fcd-images-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}

function image(root, name, rgba, width = 24, height = 24) {
  const png = new PNG({ width, height });
  for (let i = 0; i < png.data.length; i += 4) png.data.set(rgba, i);
  const file = path.join(root, name);
  fs.writeFileSync(file, PNG.sync.write(png));
  return file;
}

test('相同图片为 100 分，但仍须审阅', (t) => {
  const root = fixture(t), reference = image(root, 'design.png', [30, 80, 160, 255]);
  const result = compareImages({ reference, actual: reference, out: path.join(root, 'round1') });
  assert.equal(result.score, 100);
  assert.equal(result.pixelmatch.mismatched_pixels, 0);
  assert.equal(result.acceptance, 'requires_review');
  assert.ok(fs.existsSync(path.join(root, 'round1/side-by-side.png')));
});

test('明显差异无法通过初筛', (t) => {
  const root = fixture(t);
  const reference = image(root, 'design.png', [255, 255, 255, 255]);
  const actual = image(root, 'actual.png', [0, 0, 0, 255]);
  const result = compareImages({ reference, actual, out: path.join(root, 'round1') });
  assert.equal(result.screening_pass, false);
  assert.equal(result.pixelmatch.mismatch_ratio, 1);
  assert.ok(result.score < 1);
});

test('尺寸不一致拒绝自动拉伸', (t) => {
  const root = fixture(t), reference = image(root, 'design.png', [0, 0, 0, 255]);
  const actual = image(root, 'actual.png', [0, 0, 0, 255], 48, 48);
  assert.throws(() => compareImages({ reference, actual, out: path.join(root, 'round1') }), /尺寸不一致/);
  assert.equal(fs.existsSync(path.join(root, 'round1')), false);
});

test('显式裁剪与缩放后比较，并保留转换参数', (t) => {
  const root = fixture(t), reference = image(root, 'design.png', [100, 50, 20, 255]);
  const actual = image(root, 'actual.png', [100, 50, 20, 255], 60, 60);
  const result = compareImages({ reference, actual, 'actual-crop': '4,4,48,48', 'actual-scale': '0.5', out: path.join(root, 'round1') });
  assert.equal(result.score, 100);
  assert.equal(result.inputs.actual.crop, '4,4,48,48');
  assert.equal(result.inputs.actual.scale, 0.5);
});

test('透明像素与白色背景按可见结果比较', (t) => {
  const root = fixture(t), reference = image(root, 'design.png', [255, 0, 0, 0]);
  const actual = image(root, 'actual.png', [255, 255, 255, 255]);
  assert.equal(compareImages({ reference, actual, out: path.join(root, 'round1') }).score, 100);
});

test('无效裁剪和缩放被拒绝', (t) => {
  const root = fixture(t), reference = image(root, 'design.png', [0, 0, 0, 255]);
  for (const overrides of [{ 'actual-crop': '-1,0,24,24' }, { 'actual-crop': '0,0,80,80' }, { 'actual-scale': '0' }]) {
    assert.throws(() => compareImages({ reference, actual: reference, out: path.join(root, 'round1'), ...overrides }));
  }
});

test('不能覆盖已有轮次证据', (t) => {
  const root = fixture(t), reference = image(root, 'design.png', [0, 0, 0, 255]);
  const options = { reference, actual: reference, out: path.join(root, 'round1') };
  compareImages(options);
  const original = fs.readFileSync(path.join(root, 'round1/comparison.json'));
  assert.throws(() => compareImages(options), /输出目录已存在/);
  assert.deepEqual(fs.readFileSync(path.join(root, 'round1/comparison.json')), original);
});
