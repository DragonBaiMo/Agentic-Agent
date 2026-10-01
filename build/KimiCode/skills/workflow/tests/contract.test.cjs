// SPDX-License-Identifier: MIT
// Exercise the public manifest and CLI boundaries before expensive raster work.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {validate,resolveAsset,resolveFont,rectangle} = require('../scripts/contract.cjs');
const {argumentsFor,outputPaths,build} = require('../scripts/assemble.cjs');
const example = require('../examples/future-lab.json');
const tempRoot = path.join(__dirname,'../tmp/tests');
fs.mkdirSync(tempRoot,{recursive:true});

/** Give each mutation test an independent manifest to avoid cross-test state. */
function fixture() { return structuredClone(example); }

test('valid manifest preserves semantic groups',()=>{
  const input=fixture(); const result=validate(input);
  assert.deepEqual(result.groups,input.groups);
});
test('rejects oversized canvas',()=>{
  const input=fixture(); input.width=100000;
  assert.throws(()=>validate(input),/width/);
});
test('rejects path traversal in an asset name',()=>{
  const input=fixture(); input.art[0].file='../escape.png';
  assert.throws(()=>validate(input),/art.file/);
});
test('rejects out-of-bounds crop',()=>{
  const input=fixture(); input.art[0].crop=[0,0,5000,5000];
  assert.throws(()=>validate(input),/crop_out_of_bounds/);
});
test('rejects duplicate layer names',()=>{
  const input=fixture(); input.text[0].name=input.art[0].name;
  assert.throws(()=>validate(input),/duplicate_layer/);
});
test('rejects multiline point text explicitly',()=>{
  const input=fixture(); input.text[0].value='a\nb';
  assert.throws(()=>validate(input),/text.value/);
});
test('rejects malformed text color',()=>{
  const input=fixture(); input.text[0].color='red';
  assert.throws(()=>validate(input),/text.color/);
});
test('accepts off-canvas placement but not non-finite rectangles',()=>{
  assert.equal(rectangle([-100,0,10,10]),true);
  assert.equal(rectangle([0,0,NaN,10]),false);
});
test('requires explicit CLI paths and rejects unknown options',()=>{
  assert.throws(()=>argumentsFor([]));
  assert.throws(()=>argumentsFor(['--unknown']));
  assert.deepEqual(argumentsFor(['--config','a','--out','b','--overwrite']),{config:'a',out:'b',overwrite:true});
});
test('output collision fails unless overwrite is explicit',()=>{
  const root=fs.mkdtempSync(path.join(tempRoot,'collision-'));
  fs.writeFileSync(path.join(root,`${example.name}.psd`),'existing');
  assert.throws(()=>outputPaths(root,example,false));
  assert.ok(outputPaths(root,example,true).psd.endsWith('.psd'));
  fs.rmSync(root,{recursive:true,force:true});
});
test('missing font fails without substitution',()=>{
  assert.throws(()=>resolveFont(process.cwd(),{path:'missing-font.ttf',family:'missing'}));
});
test('asset symlink cannot escape its explicit directory',()=>{
  const root=fs.mkdtempSync(path.join(tempRoot,'symlink-'));
  fs.mkdirSync(path.join(root,'assets'));
  fs.writeFileSync(path.join(root,'external.png'),'outside');
  fs.symlinkSync(path.join(root,'external.png'),path.join(root,'assets','bad.png'));
  assert.throws(()=>resolveAsset(root,{asset_dir:'assets'},'bad.png'));
  fs.rmSync(root,{recursive:true,force:true});
});
test('actual sample build returns native text and semantic pixels',async()=>{
  const root=fs.mkdtempSync(path.join(tempRoot,'build-'));
  const result=await build({config:path.join(__dirname,'../examples/future-lab.json'),out:root,overwrite:false});
  assert.equal(result.report.layers.length,11);
  assert.equal(result.report.layers.filter(layer=>layer.type==='type').length,8);
  assert.ok(fs.statSync(result.psd).size>1_000_000);
  fs.rmSync(root,{recursive:true,force:true});
});
