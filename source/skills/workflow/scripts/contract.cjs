// SPDX-License-Identifier: MIT
// Validate the poster manifest before decoding assets or writing any output.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const messages = require('../resources/messages.zh-CN.json');
const blends = ['normal', 'multiply', 'screen', 'overlay'];

/** Throw a stable diagnostic when a manifest invariant is violated. */
function ensure(condition, detail) {
  assert.ok(condition, `${messages.config_invalid}: ${detail}`);
}

/** Require a finite numeric tuple, allowing zero and negative drawing origins. */
function rectangle(value) {
  return Array.isArray(value) && value.length === 4 &&
    value.every(Number.isFinite) && value[2] > 0 && value[3] > 0;
}

/** Reject unsupported options rather than silently flattening their intent. */
function keys(value, allowed) {
  ensure(value && typeof value === 'object' && !Array.isArray(value), 'object');
  ensure(Object.keys(value).every(key => allowed.includes(key)), 'unsupported_field');
}

/** Check packaging metadata only; none of these tests scores visual quality. */
function common(item, config) {
  ensure(typeof item.name === 'string' && item.name.length > 0, 'layer.name');
  ensure(config.groups.includes(item.group), 'layer.group');
  ensure(item.z === undefined || Number.isFinite(item.z), 'layer.z');
  ensure(item.blend === undefined || blends.includes(item.blend), 'layer.blend');
  ensure(item.opacity === undefined || Number.isFinite(item.opacity) && item.opacity >= 0 && item.opacity <= 1, 'layer.opacity');
  ensure(item.hidden === undefined || typeof item.hidden === 'boolean', 'layer.hidden');
}

/** Validate dimensions, names, ordering, text style and registration rectangles. */
function validate(config) {
  keys(config, ['name','width','height','groups','art','text','fonts','asset_dir','notes']);
  ensure(Number.isInteger(config.width) && config.width >= 16 && config.width <= 8192, 'width');
  ensure(Number.isInteger(config.height) && config.height >= 16 && config.height <= 8192, 'height');
  ensure(config.width * config.height <= 32_000_000, 'canvas_pixel_limit');
  ensure(typeof config.name === 'string' && /^[a-z0-9][a-z0-9-]{0,63}$/.test(config.name), 'name');
  ensure(Array.isArray(config.groups) && config.groups.length > 0, 'groups');
  ensure(new Set(config.groups).size === config.groups.length, 'duplicate_group');
  ensure(config.groups.every(value => typeof value === 'string' && value.length > 0), 'group_name');
  ensure(Array.isArray(config.art) && config.art.length > 0, 'art');
  ensure(Array.isArray(config.text), 'text');
  ensure(Array.isArray(config.fonts) && (config.text.length === 0 || config.fonts.length > 0), 'fonts');
  ensure(typeof config.asset_dir === 'string', 'asset_dir');
  // SAFETY(1.0): Bound decoded layer memory, not the model's artistic complexity.
  const count = config.art.length + config.text.length;
  ensure(count >= 2 && count <= 128 && config.width * config.height * (count + 1) <= 200_000_000, 'layer_memory_limit');
  config.art.forEach(item => validateArt(item, config));
  config.text.forEach(item => validateText(item, config));
  const names = [...config.art, ...config.text].map(item => item.name);
  ensure(new Set(names).size === names.length, 'duplicate_layer');
  config.fonts.forEach(font => {
    keys(font, ['path','env','family','postscript','weight']);
    ensure(typeof font.family === 'string' && font.family.length > 0 && typeof font.postscript === 'string' && font.postscript.length > 0, 'font_identity');
  });
  return config;
}

/** Validate one image item; allow intentional off-canvas placement. */
function validateArt(item, config) {
  keys(item, ['name','group','file','crop','destination','source_size','expect_alpha','z','blend','opacity','hidden','kind','copy_ids']);
  common(item, config);
  ensure(typeof item.file === 'string' && path.basename(item.file) === item.file, 'art.file');
  ensure(rectangle(item.crop) && item.crop[0] >= 0 && item.crop[1] >= 0, 'art.crop');
  ensure(rectangle(item.destination), 'art.destination');
  ensure(Array.isArray(item.source_size) && item.source_size.length === 2 && item.source_size.every(value => Number.isInteger(value) && value > 0 && value <= 8192) && item.source_size[0] * item.source_size[1] <= 32_000_000, 'art.source_size');
  ensure(item.crop[0] + item.crop[2] <= item.source_size[0] && item.crop[1] + item.crop[3] <= item.source_size[1], 'crop_out_of_bounds');
  ensure(item.expect_alpha === undefined || typeof item.expect_alpha === 'boolean', 'art.expect_alpha');
  ensure(item.kind === undefined || ['background','object','effects','glass','shadow','typography','decoration'].includes(item.kind), 'art.kind');
  ensure(item.copy_ids === undefined || Array.isArray(item.copy_ids) && item.copy_ids.every(value => typeof value === 'string'), 'art.copy_ids');
}

/** Validate a horizontal single-line native type layer and its font reference. */
function validateText(item, config) {
  keys(item, ['name','group','value','x','baseline','size','font','color','tracking','z','blend','opacity','hidden','copy_id']);
  common(item, config);
  ensure(typeof item.value === 'string' && item.value.length > 0 && !/[\r\n]/.test(item.value), 'text.value');
  ensure(Number.isFinite(item.size) && item.size > 0, 'text.size');
  ensure(Number.isFinite(item.x) && Number.isFinite(item.baseline), 'text.position');
  ensure(Number.isInteger(item.font) && config.fonts[item.font], 'text.font');
  ensure(typeof item.color === 'string' && /^#[0-9a-fA-F]{6}$/.test(item.color), 'text.color');
  ensure(item.tracking === undefined || Number.isFinite(item.tracking), 'text.tracking');
  // NOTE: This backend uses simple per-character metrics, not complex-script shaping.
  ensure(!/[\p{Mark}\u0590-\u08ff\u0900-\u109f\u1780-\u17ff\u200c\u200d]/u.test(item.value), 'text.requires_shaping');
  ensure(item.copy_id === undefined || typeof item.copy_id === 'string', 'text.copy_id');
}

/** Load a trusted local manifest; all relative paths are relative to that file. */
function loadManifest(file) {
  const absolute = path.resolve(file);
  const config = validate(JSON.parse(fs.readFileSync(absolute, 'utf8')));
  return {config, base:path.dirname(absolute)};
}

/** Resolve only an ordinary file inside the explicitly configured asset root. */
function resolveAsset(base, config, file) {
  const root = fs.realpathSync(path.resolve(base, config.asset_dir));
  const resolved = fs.realpathSync(path.join(root, file));
  assert.ok(resolved.startsWith(root + path.sep) && fs.statSync(resolved).isFile(), messages.asset_invalid);
  return resolved;
}

/** Resolve a requested font from an environment override or configured path. */
function resolveFont(base, font) {
  const candidate = font.env && process.env[font.env] || font.path;
  assert.ok(typeof candidate === 'string', messages.font_missing);
  const resolved = path.resolve(base, candidate);
  assert.ok(fs.existsSync(resolved) && fs.statSync(resolved).isFile(), `${messages.font_missing}: ${font.env || font.family}`);
  return resolved;
}

module.exports = {messages, rectangle, validate, loadManifest, resolveAsset, resolveFont};
