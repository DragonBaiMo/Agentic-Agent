// SPDX-License-Identifier: MIT
// Fault injection for exact-cell proof; real Artifact Tool replay is recorded separately.
const test = require('node:test');
const assert = require('node:assert/strict');
const api = import('../scripts/pptx_backend/verify_table_edits.mjs');

/** Model only the documented getCell().text surface, without emulating authoring. */
function fixture(values, overrides = {}) {
  const row = {kind:'table', id:'tb/test', slide:1, name:'', rows:2, cols:2, ...overrides};
  const deck = {resolve:() => ({getCell:(r, c) => ({text:values[r][c]})})};
  return {deck, rows:[row]};
}

const action = {kind:'table', slide:1, row:1, column:1, text:'2300', expected_before:'2100'};
const original = [['项目', '金额'], ['课程', '2100']];

test('reads non-header cell and records source, target and reopened value', async () => {
  const {snapshotTableEdits, verifyTableEdits} = await api;
  const before = fixture(original);
  const after = fixture([['项目', '金额'], ['课程', '2300']]);
  const snapshots = snapshotTableEdits(before.deck, before.rows, [action]);
  const [result] = verifyTableEdits(after.deck, after.rows, snapshots);
  assert.deepEqual(result.edits, [{row:1, column:1, before:'2100', target:'2300', after:'2300'}]);
});

test('a target string elsewhere cannot hide a failed cell edit', async () => {
  const {snapshotTableEdits, verifyTableEdits} = await api;
  const before = fixture([['2300', '金额'], ['课程', '2100']]);
  const snapshots = snapshotTableEdits(before.deck, before.rows, [action]);
  assert.throws(() => verifyTableEdits(before.deck, before.rows, snapshots), /table_edit_did_not_survive/);
});

test('detects an unintended change to another cell', async () => {
  const {snapshotTableEdits, verifyTableEdits} = await api;
  const before = fixture(original);
  const after = fixture([['项目', '金额'], ['不同课程', '2300']]);
  const snapshots = snapshotTableEdits(before.deck, before.rows, [action]);
  assert.throws(() => verifyTableEdits(after.deck, after.rows, snapshots), /untouched_table_cell_changed/);
});

test('rejects negative row coordinates', async () => {
  const {snapshotTableEdits} = await api;
  const before = fixture(original);
  assert.throws(() => snapshotTableEdits(before.deck, before.rows, [{...action, row:-1}]), /table_cell_out_of_range/);
});

test('rejects a column beyond the existing table', async () => {
  const {snapshotTableEdits} = await api;
  const before = fixture(original);
  assert.throws(() => snapshotTableEdits(before.deck, before.rows, [{...action, column:2}]), /table_cell_out_of_range/);
});

test('rejects fractional coordinates', async () => {
  const {snapshotTableEdits} = await api;
  const before = fixture(original);
  assert.throws(() => snapshotTableEdits(before.deck, before.rows, [{...action, row:0.5}]), /table_cell_out_of_range/);
});

test('rejects a stale expected source value', async () => {
  const {snapshotTableEdits} = await api;
  const before = fixture(original);
  assert.throws(() => snapshotTableEdits(before.deck, before.rows, [{...action, expected_before:'9999'}]), /table_source_value_mismatch/);
});

test('rejects ambiguous multiple tables', async () => {
  const {snapshotTableEdits} = await api;
  const before = fixture(original);
  assert.throws(() => snapshotTableEdits(before.deck, [...before.rows, ...before.rows], [action]), /ambiguous_table_target/);
});

test('detects changed dimensions after reopening', async () => {
  const {snapshotTableEdits, verifyTableEdits} = await api;
  const before = fixture(original);
  const after = fixture([['项目', '金额'], ['课程', '2300'], ['', '']], {rows:3});
  const snapshots = snapshotTableEdits(before.deck, before.rows, [action]);
  assert.throws(() => verifyTableEdits(after.deck, after.rows, snapshots), /table_dimensions_changed/);
});

test('leaves existing image/text/chart-only callers unchanged', async () => {
  const {snapshotTableEdits, verifyTableEdits} = await api;
  const before = fixture(original);
  const snapshots = snapshotTableEdits(before.deck, before.rows, []);
  assert.deepEqual(verifyTableEdits(before.deck, before.rows, snapshots), []);
});

test('matches a named table and permits an explicitly empty string', async () => {
  const {snapshotTableEdits, verifyTableEdits} = await api;
  const before = fixture(original, {name:'quote'});
  const after = fixture([['项目', '金额'], ['课程', '']], {name:'quote'});
  const snapshots = snapshotTableEdits(before.deck, before.rows, [{...action, name:'quote', text:''}]);
  assert.equal(verifyTableEdits(after.deck, after.rows, snapshots)[0].edits[0].after, '');
});

test('rejects repeated cell targets before any authoring mutation', async () => {
  const {snapshotTableEdits} = await api;
  const before = fixture(original);
  assert.throws(() => snapshotTableEdits(before.deck, before.rows,
    [action, {...action, text:'2400'}]), /duplicate_table_cell_target/);
});
