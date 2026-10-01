// SPDX-License-Identifier: MIT
// Verify exact edited table cells; inspect previews expose only the first row.

/** @typedef {{kind:string, id:string, slide:number, name?:string, rows:number, cols:number}} TableRow */
/** @typedef {{kind:string, slide:number, name?:string, row:number, column:number, text:string|number, expected_before?:string|number}} Edit */
/** @typedef {{resolve:(id:string)=>{getCell:(row:number,column:number)=>{text:unknown}}}} Deck */
/** @typedef {{row:number,column:number,before:string,target:string}} CellEdit */
/** @typedef {{target:Edit,rows:number,columns:number,values:string[][],edits:CellEdit[]}} Snapshot */

/** Find one inspected table without guessing among multiple tables on a slide.
 * @param {TableRow[]} rows @param {Edit} action */
function findTable(rows, action) {
  const matches = rows.filter(row => row.kind === 'table' && row.slide === action.slide &&
    (!action.name || row.name === action.name));
  if (matches.length !== 1) throw new Error('ambiguous_table_target');
  return matches[0];
}

/** Reject stale/out-of-range coordinates before the authoring call can mutate them.
 * @param {TableRow} row @param {Edit} action */
function checkCell(row, action) {
  if (!Number.isInteger(action.row) || !Number.isInteger(action.column) ||
      action.row < 0 || action.column < 0 || action.row >= row.rows || action.column >= row.cols)
    throw new Error('table_cell_out_of_range');
}

/** Read full cell text through the documented public API, including non-header rows.
 * @param {Deck} deck @param {TableRow} row */
function readTable(deck, row) {
  const table = deck.resolve(row.id);
  return Array.from({length:row.rows}, (_, r) =>
    Array.from({length:row.cols}, (_, c) => String(table.getCell(r, c).text)));
}

/** Snapshot only affected tables; optional expected_before rejects a stale edit request.
 * @param {Deck} deck @param {TableRow[]} rows @param {Edit[]} actions */
export function snapshotTableEdits(deck, rows, actions) {
  /** @type {Map<string, Snapshot>} */
  const snapshots = new Map();
  for (const action of actions.filter(item => item.kind === 'table')) {
    const row = findTable(rows, action);
    checkCell(row, action);
    let snapshot = snapshots.get(row.id);
    if (!snapshot) {
      snapshot = {target:action, rows:row.rows, columns:row.cols,
        values:readTable(deck, row), edits:[]};
      snapshots.set(row.id, snapshot);
    }
    const before = snapshot.values[action.row][action.column];
    if (action.expected_before !== undefined && before !== String(action.expected_before))
      throw new Error('table_source_value_mismatch');
    if (snapshot.edits.some(edit=>edit.row===action.row && edit.column===action.column))
      throw new Error('duplicate_table_cell_target');
    snapshot.edits.push({row:action.row, column:action.column, before, target:String(action.text)});
  }
  return [...snapshots.values()];
}

/** Verify edited values, dimensions and every untouched cell after save/reopen.
 * @param {Deck} deck @param {TableRow[]} rows @param {Snapshot[]} snapshots */
export function verifyTableEdits(deck, rows, snapshots) {
  return snapshots.map(before => {
    const row = findTable(rows, before.target);
    if (row.rows !== before.rows || row.cols !== before.columns)
      throw new Error('table_dimensions_changed');
    const values = readTable(deck, row);
    const expected = before.values.map(cells => [...cells]);
    for (const edit of before.edits) expected[edit.row][edit.column] = edit.target;
    for (const edit of before.edits) {
      if (values[edit.row][edit.column] !== edit.target) throw new Error('table_edit_did_not_survive');
    }
    if (JSON.stringify(values) !== JSON.stringify(expected)) throw new Error('untouched_table_cell_changed');
    return {slide:row.slide, name:row.name, rows:row.rows, columns:row.cols,
      edits:before.edits.map(edit => ({...edit, after:values[edit.row][edit.column]})), values};
  });
}
