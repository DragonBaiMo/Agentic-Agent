// SPDX-License-Identifier: MIT
// Small synthetic fixtures test packaging math, not generated artwork quality.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {readPsd} = require('ag-psd');
const {createCanvas,artLayer,compose,alphaStats} = require('../scripts/render.cjs');
const {validate} = require('../scripts/contract.cjs');
const {build} = require('../scripts/assemble.cjs');
const example = require('../examples/future-lab.json');
const root = path.join(__dirname,'../tmp/render-tests');
fs.mkdirSync(root,{recursive:true});

/** Make a tiny uniform source; fixtures never enter production assets. */
function surface(color) {
  const canvas = createCanvas(16,16);
  const context = canvas.getContext('2d');
  context.fillStyle = color;
  context.fillRect(0,0,16,16);
  return canvas;
}

/** Create an image-only manifest with zero fonts and two real raster leaves. */
function fixture(directory,blend='normal') {
  fs.writeFileSync(path.join(directory,'back.png'),surface('#64a0c8').toBuffer('image/png'));
  fs.writeFileSync(path.join(directory,'front.png'),surface('#dc3250').toBuffer('image/png'));
  const item = (name,file,group) => ({name,file,group,source_size:[16,16],crop:[0,0,16,16],destination:[0,0,16,16]});
  return {name:'fixture',width:16,height:16,asset_dir:'.',groups:['back','front'],fonts:[],text:[],
    art:[item('back','back.png','back'),{...item('front','front.png','front'),blend,opacity:0.5,kind:'typography',copy_ids:['test']}]};
}

test('unknown features fail rather than silently discarding masks',()=>{
  const input=structuredClone(example); input.art[0].mask='mask.png';
  assert.throws(()=>validate(input),/unsupported_field/);
});
test('complex native shaping fails explicitly',()=>{
  const input=structuredClone(example); input.text[0].value='مرحبا';
  assert.throws(()=>validate(input),/requires_shaping/);
});
test('invalid opacity and unsupported blend fail',()=>{
  const first=structuredClone(example); first.art[0].opacity=2;
  const second=structuredClone(example); second.art[0].blend='dissolve';
  assert.throws(()=>validate(first),/opacity/);
  assert.throws(()=>validate(second),/blend/);
});
test('source alpha cannot be faked by placing opaque art on a larger canvas',async()=>{
  const directory=fs.mkdtempSync(path.join(root,'alpha-'));
  try {
    const config=fixture(directory); config.width=32;
    await assert.rejects(()=>artLayer({...config.art[0],expect_alpha:true},config,directory),/透明/);
  } finally { fs.rmSync(directory,{recursive:true,force:true}); }
});
test('source mismatch and completely off-canvas content fail',async()=>{
  const directory=fs.mkdtempSync(path.join(root,'bounds-'));
  try {
    const config=fixture(directory);
    await assert.rejects(()=>artLayer({...config.art[0],source_size:[32,32]},config,directory),/尺寸/);
    await assert.rejects(()=>artLayer({...config.art[0],destination:[99,99,16,16]},config,directory),/可见/);
  } finally { fs.rmSync(directory,{recursive:true,force:true}); }
});
test('z permits image above text and hidden pixels stay out of composite',()=>{
  const config={width:16,height:16,groups:['mixed']};
  const layers=[{name:'image',group:'mixed',z:3,surface:surface('#ff0000'),opacity:1,blendMode:'normal'},
    {name:'type',group:'mixed',z:1,surface:surface('#0000ff'),opacity:1,blendMode:'normal'},
    {name:'hidden',group:'mixed',z:9,surface:surface('#00ff00'),opacity:1,blendMode:'normal',hidden:true}];
  const result=compose(layers,config);
  assert.deepEqual(result.children[0].children.map(item=>item.name),['type','image','hidden']);
  assert.deepEqual([...result.composite.getContext('2d').getImageData(0,0,1,1).data],[255,0,0,255]);
  assert.deepEqual(alphaStats(new Uint8ClampedArray([1,2,3,40,4,5,6,200])),{min:40,max:200});
});

// NOTE: Parameterized cases independently exercise all supported blend encodings.
['normal','multiply','screen','overlay'].forEach(blend=>test(`roundtrip image-only ${blend} opacity across groups`,async()=>{
  const directory=fs.mkdtempSync(path.join(root,`${blend}-`));
  try {
    const config=fixture(directory,blend);
    const file=path.join(directory,'config.json'); fs.writeFileSync(file,JSON.stringify(config));
    const result=await build({config:file,out:path.join(directory,'out'),overwrite:false});
    const parsed=readPsd(fs.readFileSync(result.psd),{useImageData:true});
    assert.equal(result.report.layers.length,2);
    assert.equal(result.report.layers[1].type,'pixel');
    assert.equal(parsed.children[1].children[0].blendMode,blend);
    assert.ok(Math.abs(parsed.children[1].children[0].opacity-0.5)<=1/255);
    assert.equal(parsed.children[1].blendMode,'pass through');
  } finally { fs.rmSync(directory,{recursive:true,force:true}); }
}));

module.exports = {fixture};
