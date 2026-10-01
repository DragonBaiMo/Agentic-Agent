// SPDX-License-Identifier: MIT
// Check advance arithmetic and guardrails independently of any font aesthetic.
const test = require('node:test');
const assert = require('node:assert/strict');
const {measureLine} = require('../scripts/measure_text.cjs');
const font = {family:'Diagnostic', postscript:'Diagnostic'};
const item = {name:'line', value:'ABC', size:20, tracking:100, x:10, baseline:40};
const context = {measureText:() => ({width:10})};

test('advance includes only two inter-character gaps', () => {
  const result = measureLine(item, font, context, 40);
  assert.equal(result.advance_width, 34);
  assert.equal(result.suggested_tracking, 250);
});

test('one glyph has no invented tracking recommendation', () => {
  const result = measureLine({...item, value:'A'}, font, context, 40);
  assert.equal(result.advance_width, 10);
  assert.equal(result.suggested_tracking, null);
});

test('omitted target only measures the existing style', () => {
  assert.equal(measureLine(item, font, context).suggested_tracking, null);
});

test('invalid target cannot suggest a destructive layout change', () => {
  assert.throws(() => measureLine(item, font, context, NaN));
  assert.throws(() => measureLine(item, font, context, -1));
});
