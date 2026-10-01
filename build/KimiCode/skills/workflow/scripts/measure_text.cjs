// SPDX-License-Identifier: MIT
// Measure the same per-character advances as render.cjs without changing a plan.
const assert = require('node:assert/strict');
const {parseArgs} = require('node:util');
const {loadManifest, messages} = require('./contract.cjs');
const {createCanvas, registerFonts} = require('./render.cjs');

/** Report advance width and optional tracking, excluding a nonexistent trailing gap. */
function measureLine(item, font, context, targetWidth) {
  if (targetWidth !== undefined) assert.ok(Number.isFinite(targetWidth) && targetWidth > 0, messages.config_invalid);
  context.font = `${font.weight || 'normal'} ${item.size}px "${font.family}"`;
  const characters = [...item.value];
  const glyphAdvance = characters.reduce((sum, character) => sum + context.measureText(character).width, 0);
  const gaps = Math.max(0, characters.length - 1);
  const tracking = item.tracking || 0;
  // NOTE: This is the cached renderer's advance, not Photoshop reflow or ink bbox.
  return {layer:item.name, family:font.family, postscript:font.postscript, size:item.size,
    characters:characters.length, baseline:item.baseline, x:item.x, glyph_advance:glyphAdvance,
    tracking, advance_width:glyphAdvance + gaps * tracking * item.size / 1000,
    target_width:targetWidth ?? null,
    suggested_tracking:targetWidth !== undefined && gaps > 0 ? (targetWidth - glyphAdvance) * 1000 / (gaps * item.size) : null,
    scope:'renderer_advance_not_ink_bbox_or_photoshop_reflow'};
}

/** Load a valid manifest and emit JSON; the caller decides whether to change style. */
function main() {
  const {values} = parseArgs({options:{config:{type:'string'}, layer:{type:'string'}, 'target-width':{type:'string'}}});
  assert.ok(values.config && values.layer, messages.config_invalid);
  const {config, base} = loadManifest(values.config);
  const item = config.text.find(layer => layer.name === values.layer);
  assert.ok(item, messages.config_invalid);
  registerFonts(base, config);
  const target = values['target-width'] === undefined ? undefined : Number(values['target-width']);
  console.log(JSON.stringify(measureLine(item, config.fonts[item.font], createCanvas(1, 1).getContext('2d'), target)));
}

if (require.main === module) main();
module.exports = {measureLine};
