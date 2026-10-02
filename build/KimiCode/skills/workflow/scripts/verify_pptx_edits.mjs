// SPDX-License-Identifier: MIT
// Edit a diagnostic copy of actual PPTX bytes, save/reopen, then render evidence.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';
import {execFileSync} from 'node:child_process';
import {fileURLToPath,URL} from 'node:url';
import {assetPath} from './pptx_backend/render_objects.mjs';
import {snapshotTableEdits,verifyTableEdits} from './pptx_backend/verify_table_edits.mjs';

const {values:args} = parseArgs({options:{project:{type:'string'},input:{type:'string'},
  actions:{type:'string'},out:{type:'string'}}});
const root = await fs.realpath(path.resolve(args.project));
const out = path.resolve(root,args.out);
if (!out.startsWith(root+path.sep)) throw new Error('outside_project');
const source = await assetPath(root,args.input);
const actionFile = await assetPath(root,args.actions);
const config = JSON.parse(await fs.readFile(actionFile,'utf8'));
const mediaPreflight = inspectMedia(source);
const tableEligibility = inspectPlainTables(source);
const require = createRequire(path.join(process.env.RUNTIME_NODE_MODULES,'..','package.json'));
const {PresentationFile,FileBlob} = await import(require.resolve('@oai/artifact-tool'));
await fs.mkdir(path.dirname(out),{recursive:true});
await fs.mkdir(out,{recursive:false});
const deck = await PresentationFile.importPptx(await FileBlob.load(source));
const rows = (await deck.inspect({kind:'image,textbox,table,chart',maxChars:100000}))
  .ndjson.trim().split('\n').map(JSON.parse);
const tableSnapshots = snapshotTableEdits(deck,rows,config.actions);

/** Resolve the exact inspected object, refusing ambiguous or stale names. */
function find(action) {
  const matches = rows.filter(r=>r.kind===action.kind && r.slide===action.slide &&
    (!action.name || r.name===action.name));
  if (matches.length!==1) throw new Error('ambiguous_edit_target: '+JSON.stringify(action));
  return deck.resolve(matches[0].id);
}

for (const action of config.actions) {
  const object = find(action);
  if (action.kind==='image') object.frame={...object.frame,left:action.left};
  else if (action.kind==='textbox') object.text=action.text;
  else if (action.kind==='chart') object.series.getItemAt(action.series).values=action.values;
  else if (action.kind==='table') object.cells.set(action.row,action.column,action.text);
  else throw new Error('unsupported_edit_kind');
}
const diagnostic = path.join(out,'diagnostic.pptx');
await (await PresentationFile.exportPptx(deck)).save(diagnostic);
inspectPlainTables(diagnostic);
const reopened = await PresentationFile.importPptx(await FileBlob.load(diagnostic));
const snapshot = (await reopened.inspect({kind:'image,textbox,table,chart',maxChars:100000})).ndjson;
const reopenedRows = snapshot.trim().split('\n').map(JSON.parse);
const tableChecks = verifyTableEdits(reopened,reopenedRows,tableSnapshots);
// NOTE: Table inspect preview contains headers only; verified full cells supply the rest.
const actualText = [snapshot,...tableChecks.flatMap(table=>table.values.flat())].join('\n');
if (config.expected_text.some(text=>!actualText.includes(text))) throw new Error('native_edit_did_not_survive');
for (const action of config.actions.filter(item=>['image','chart'].includes(item.kind))) {
  const matches = reopenedRows.filter(r=>r.kind===action.kind && r.slide===action.slide &&
    (!action.name || r.name===action.name));
  if (matches.length!==1) throw new Error('ambiguous_reopened_target');
  if (action.kind==='image' && Math.abs(matches[0].bbox[0]-action.left)>0.05)
    throw new Error('image_position_did_not_survive');
  if (action.kind==='chart') {
    const values = reopened.resolve(matches[0].id).series.getItemAt(action.series).values;
    if (JSON.stringify(values)!==JSON.stringify(action.values)) throw new Error('chart_data_did_not_survive');
  }
}
for (const index of config.render_indices) {
  const png = await reopened.export({slide:reopened.slides.getItem(index),format:'png',scale:1});
  await fs.writeFile(path.join(out,`edited-slide-${index+1}.png`),new Uint8Array(await png.arrayBuffer()));
}
await fs.writeFile(path.join(out,'inspect.ndjson'),snapshot);
await fs.writeFile(path.join(out,'result.json'),JSON.stringify({passed:true,input:args.input,
  actions:config.actions,targetApplicationTest:false,workbookPreservationVerified:false,
  diagnosticOnly:true,tableChecks,tableEligibility,mediaPreflight},null,2));
process.stdout.write(JSON.stringify({level:'INFO',event:'edit_copy_reopened',output:args.out})+'\n');

/** Covered merged cells can store changed text without displaying it; reject that route. */
function inspectPlainTables(file) {
  if (!config.actions.some(action=>action.kind==='table')) return [];
  const python = process.env.RUNTIME_PYTHON || process.env.CODEX_PRIMARY_RUNTIME_PYTHON;
  if (!path.isAbsolute(python || '')) throw new Error('missing_runtime_python');
  const script = fileURLToPath(new URL('./pptx_backend/inspect_plain_tables.py',import.meta.url));
  return JSON.parse(execFileSync(python,[script,file,actionFile],{encoding:'utf8',timeout:30000}));
}

/** Stop before importing or creating output when this route would risk dropping media. */
function inspectMedia(file) {
  const python = process.env.RUNTIME_PYTHON || process.env.CODEX_PRIMARY_RUNTIME_PYTHON;
  if (!path.isAbsolute(python || '')) throw new Error('missing_runtime_python');
  const script = fileURLToPath(new URL('./inspect_pptx_media.py',import.meta.url));
  return JSON.parse(execFileSync(python,[script,file],
    {encoding:'utf8',timeout:30000,maxBuffer:2*1024*1024}));
}
