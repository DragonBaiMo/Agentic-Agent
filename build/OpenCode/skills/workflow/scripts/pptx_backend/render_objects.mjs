// SPDX-License-Identifier: MIT
// Faithfully place semantic images and native information from measured page data.
import fs from 'node:fs/promises';
import path from 'node:path';

/** Resolve only existing project assets, including a symlink-escape check. */
export async function assetPath(root, relative) {
  const base = await fs.realpath(root);
  const file = await fs.realpath(path.resolve(base, relative));
  if (!file.startsWith(base + path.sep)) throw new Error('outside_project: ' + relative);
  return file;
}

/** Add original PNG bytes at explicit xywh coordinates; no decorative drawing. */
export async function addImage(slide, item, root) {
  const [left, top, width, height] = item.box;
  const file = await assetPath(root, item.file);
  return slide.images.add({blob:new Uint8Array(await fs.readFile(file)),
    contentType:'image/png', alt:item.alt, fit:'contain', position:{left,top,width,height}});
}

/** Supply only missing paragraph line spacing without mutating authored runs or local spacing. */
function withDefaultLineSpacing(text, lineSpacing) {
  if (lineSpacing === undefined) return text;
  const isParagraph = part => Array.isArray(part) ||
    (part !== null && typeof part === 'object' && !('run' in part));
  const paragraphs = Array.isArray(text) && text.some(isParagraph) ? text : [text];
  return paragraphs.map(part => {
    const paragraph = Array.isArray(part) ? {runs:part} : part;
    const local = paragraph.paragraphStyle || {};
    // NOTE: These mutually exclusive fields use 1/1000 percent and 1/100 point, respectively.
    if (local.lineSpacingPercent !== undefined || local.lineSpacingPoints !== undefined) {
      return paragraph;
    }
    return {...paragraph, paragraphStyle:{...local,
      lineSpacingPercent:Math.round(lineSpacing * 100000)}};
  });
}

/** Preserve explicit run overrides; string and string-paragraph inputs keep their old order. */
function applyNativeText(shape, item) {
  const structured = item.text !== null && typeof item.text === 'object' &&
    (!Array.isArray(item.text) || item.text.some(part => typeof part !== 'string'));
  if (structured) {
    // NOTE: The whole-shape setter overwrites existing run font/size/fill. Apply defaults first.
    shape.text.style = item.style;
    // NOTE: Structured text replaces paragraph records. Inherit spacing before assignment so
    // explicit local percent/point values survive without a later whole-shape overwrite.
    shape.text = withDefaultLineSpacing(item.text, item.style?.lineSpacing);
    return;
  }
  shape.text = item.text;
  // NOTE: Set the complete style in one call; the getter is not a mutable style object.
  shape.text.style = item.style;
}

/** Add one object without substituting the author's typography or chart styling. */
export async function addObject(slide, item, root, fontHelper) {
  if (item.kind === 'image') return addImage(slide, item, root);
  if (item.kind === 'chart') {
    const chart = slide.charts.add(item.chart_type, item.options);
    if (item.font_family) fontHelper(chart, {fontFamily:item.font_family});
    return chart;
  }
  if (item.kind === 'table') {
    const table = slide.tables.add(item.options);
    for (const range of item.ranges || []) table.cells.block(range.block).assign(range.style);
    return table;
  }
  const [left, top, width, height] = item.box;
  const shape = slide.shapes.add({name:item.id,
    geometry:item.kind === 'text' ? 'textbox' : 'rect',
    position:{left,top,width,height}, fill:item.kind === 'text' ? 'none' : item.fill,
    line:{fill:'none',width:0}});
  if (item.kind === 'text') {
    applyNativeText(shape, item);
  }
  return shape;
}
