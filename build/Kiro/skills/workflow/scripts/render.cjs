// SPDX-License-Identifier: MIT
// Render registered generated assets and matching native-type bitmap previews.
const assert = require('node:assert/strict');
const {createCanvas, loadImage, GlobalFonts} = require('@napi-rs/canvas');
const {messages, resolveAsset, resolveFont} = require('./contract.cjs');

/** Register exact fonts; failing is safer than silently substituting glyphs. */
function registerFonts(base, config) {
  config.fonts.forEach(font => {
    assert.ok(typeof font.family === 'string' && typeof font.postscript === 'string', messages.font_missing);
    assert.ok(GlobalFonts.registerFromPath(resolveFont(base, font), font.family), messages.font_missing);
  });
}

/** Return the layer's raw RGBA pixels, preserving the generated alpha channel. */
function pixels(surface) {
  return surface.getContext('2d').getImageData(0, 0, surface.width, surface.height);
}

/** Preserve semitransparent materials; alpha facts are not an aesthetic score. */
function alphaStats(data) {
  let min = 255;
  let max = 0;
  for (let index = 3; index < data.length; index += 4) {
    min = Math.min(min, data[index]);
    max = Math.max(max, data[index]);
  }
  return {min, max};
}

/** Apply the same declared layer settings to the PSD and its composite preview. */
function settings(item) {
  return {blendMode:item.blend || 'normal', opacity:item.opacity ?? 1, hidden:item.hidden ?? false};
}

/** Create a document-sized raster layer using only crop, scale and placement. */
async function artLayer(item, config, base) {
  const source = await loadImage(resolveAsset(base, config, item.file));
  assert.deepEqual([source.width, source.height], item.source_size, messages.size_mismatch);
  if (item.expect_alpha) {
    // NOTE: A transparent destination margin cannot turn an opaque source into a cutout.
    const raw = createCanvas(source.width, source.height);
    raw.getContext('2d').drawImage(source,0,0);
    assert.ok(alphaStats(pixels(raw).data).min < 255, messages.alpha_missing);
  }
  const surface = createCanvas(config.width, config.height);
  surface.getContext('2d').drawImage(source, ...item.crop, ...item.destination);
  const imageData = pixels(surface);
  const alpha = alphaStats(imageData.data);
  assert.ok(alpha.max > 0, messages.empty_layer);
  // NOTE: No weak-alpha deletion or exact bbox comparison. Visual review owns edges.
  return {name:item.name, group:item.group, z:item.z, imageData, surface, ...settings(item)};
}

/** Convert a validated #RRGGBB string to PSD color metadata. */
function color(hex) {
  return {r:parseInt(hex.slice(1,3),16),g:parseInt(hex.slice(3,5),16),b:parseInt(hex.slice(5,7),16)};
}

/** Pair real point-type metadata with an explicitly rendered bitmap preview. */
function textLayer(item, config) {
  const font = config.fonts[item.font];
  const surface = createCanvas(config.width, config.height);
  const context = surface.getContext('2d');
  context.font = `${font.weight || 'normal'} ${item.size}px "${font.family}"`;
  context.fillStyle = item.color;
  let x = item.x;
  // NOTE: Tracking units match Photoshop: thousandths of an em.
  for (const character of item.value) {
    context.fillText(character, x, item.baseline);
    x += context.measureText(character).width + (item.tracking || 0) * item.size / 1000;
  }
  const text = {text:item.value, transform:[1,0,0,1,item.x,item.baseline],
    shapeType:'point',orientation:'horizontal',antiAlias:'smooth',
    style:{font:{name:font.postscript},fontSize:item.size,fillColor:color(item.color),
      tracking:item.tracking || 0,autoKerning:false},paragraphStyle:{justification:'left'}};
  const imageData = pixels(surface);
  assert.ok(alphaStats(imageData.data).max > 0, messages.empty_layer);
  return {name:item.name,group:item.group,z:item.z,imageData,text,surface,...settings(item)};
}

/** Form bottom-to-top group records and composite them in the same order. */
function compose(layers, config) {
  const composite = createCanvas(config.width, config.height);
  const context = composite.getContext('2d');
  const children = config.groups.map(name => {
    const members = layers.map((layer,index) => ({...layer,z:layer.z ?? index}))
      .filter(layer => layer.group === name).sort((first,second) => first.z - second.z);
    members.forEach(layer => {
      if (layer.hidden) return;
      context.globalCompositeOperation = layer.blendMode === 'normal' ? 'source-over' : layer.blendMode;
      context.globalAlpha = Math.round(layer.opacity * 255) / 255;
      context.drawImage(layer.surface,0,0);
    });
    // NOTE: Pass-through groups let a shadow blend with the background below its folder.
    return {name,opened:true,blendMode:'pass through',children:members.map(({surface,group,z,...rest})=>rest)};
  });
  return {composite, children};
}

module.exports = {createCanvas, registerFonts, pixels, artLayer, textLayer, compose, alphaStats};
