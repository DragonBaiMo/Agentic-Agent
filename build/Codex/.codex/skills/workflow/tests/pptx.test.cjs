// SPDX-License-Identifier: MIT
// Check argument fidelity to the public API; real exports are tested separately.
const test=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs/promises');
const {pathToFileURL}=require('node:url');
const root=path.resolve(__dirname,'..');
const api=import(pathToFileURL(path.join(root,'scripts/pptx_backend/render_objects.mjs')));

test('PPTX image preserves source bytes and explicit frame',async()=>{
  const {addImage}=await api;
  const file='assets/future-lab/reference-preview.png';
  const actual=await addImage({images:{add:value=>value}},
    {file,box:[10,20,30,40],alt:'Reference'},root);
  assert.deepEqual(actual.position,{left:10,top:20,width:30,height:40});
  assert.deepEqual(Buffer.from(actual.blob),await fs.readFile(path.join(root,file)));
});

test('PPTX asset cannot escape project via relative traversal',async()=>{
  const {assetPath}=await api;
  await assert.rejects(assetPath(path.join(root,'scripts'),'../SKILL.md'),/outside_project/);
});

test('PPTX native text uses entire authored style without default typography',async()=>{
  const {addObject}=await api;const textState={};
  const shape={set text(value){textState.value=value;},get text(){return textState;}};
  const style={typeface:'Chosen Font',fontSize:37,italic:true,color:'#182029'};
  const actual=await addObject({shapes:{add:()=>shape}},
    {kind:'text',id:'body',box:[0,0,300,40],text:'Native content',style},root);
  assert.equal(actual.text.value,'Native content');
  assert.deepEqual(actual.text.style,style);
});

test('PPTX native chart receives exact category order and explicit data',async()=>{
  const {addObject}=await api;
  const options={categories:['B','A'],series:[{values:[80,60]}]};let assigned;
  const chart={};
  const actual=await addObject({charts:{add:(kind,value)=>{assigned={kind,value};return chart;}}},
    {kind:'chart',chart_type:'bar',options,font_family:'Chosen Font'},root,(object,font)=>{object.font=font;});
  assert.deepEqual(assigned,{kind:'bar',value:options});
  assert.deepEqual(actual.font,{fontFamily:'Chosen Font'});
});

test('PPTX table applies complete range styles to real declared dimensions',async()=>{
  const {addObject}=await api;let seen;
  const options={rows:2,columns:3,values:[['a','b','c'],['d','e','f']]};
  const range={block:{row:0,column:0,rowCount:2,columnCount:3},style:{fill:'none'}};
  const table={cells:{block:block=>({assign:style=>{seen={block,style};}})}};
  await addObject({tables:{add:value=>{assert.deepEqual(value,options);return table;}}},
    {kind:'table',options,ranges:[range]},root);
  assert.deepEqual(seen,range);
});

test('PPTX structural rule preserves measured coordinates and color',async()=>{
  const {addObject}=await api;
  const shape=await addObject({shapes:{add:value=>value}},
    {kind:'rule',id:'divider',box:[50,20,1,500],fill:'#BAAABD'},root);
  assert.deepEqual(shape.position,{left:50,top:20,width:1,height:500});
  assert.equal(shape.fill,'#BAAABD');
});
