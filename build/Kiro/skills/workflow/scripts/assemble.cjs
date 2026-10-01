// SPDX-License-Identifier: MIT
// CLI: assemble model-generated assets into a true layered RGB PSD and preview.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {writePsdBuffer,readPsd,initializeCanvas} = require('ag-psd');
const {messages,loadManifest} = require('./contract.cjs');
const render = require('./render.cjs');
initializeCanvas(render.createCanvas);

/** Parse a bounded CLI; output replacement must be explicitly requested. */
function argumentsFor(argv) {
  const values = {overwrite:false};
  for (let index = 0; index < argv.length; index++) {
    const token = argv[index];
    if (token === '--overwrite') values.overwrite = true;
    else if (token === '--config' || token === '--out') values[token.slice(2)] = argv[++index];
    else throw new Error(messages.usage);
  }
  assert.ok(values.config && values.out, messages.usage);
  return values;
}

/** Persist a small structured event without embedding images or sensitive data. */
function log(out, message, detail = {}) {
  fs.appendFileSync(path.join(out,'logs','assembly.jsonl'), JSON.stringify({timestamp:new Date().toISOString(),level:'INFO',message,...detail})+'\n');
}

/** Check output collision before any build output is created. */
function outputPaths(out, config, overwrite) {
  const files = {psd:path.join(out,`${config.name}.psd`),preview:path.join(out,`${config.name}-preview.png`)};
  assert.ok(overwrite || !Object.values(files).some(file => fs.existsSync(file)), messages.output_exists);
  return files;
}

/** Verify dimensions, grouping, literal text and raw image buffers by reopening. */
function verify(buffer, config) {
  const psd = readPsd(buffer,{useImageData:true,skipThumbnail:true});
  const leaves = psd.children.flatMap(group => group.children);
  assert.deepEqual([psd.width,psd.height],[config.width,config.height],messages.roundtrip_failed);
  assert.deepEqual(psd.children.map(group => group.name),config.groups,messages.roundtrip_failed);
  assert.equal(leaves.length, config.art.length+config.text.length,messages.roundtrip_failed);
  const byName = new Map(leaves.map(layer => [layer.name,layer]));
  [...config.art,...config.text].forEach(item => {
    const layer = byName.get(item.name);
    assert.ok(layer,messages.roundtrip_failed);
    assert.equal(layer.blendMode,item.blend || 'normal',messages.roundtrip_failed);
    assert.equal(Boolean(layer.hidden),item.hidden || false,messages.roundtrip_failed);
    assert.ok(Math.abs(layer.opacity - (item.opacity ?? 1)) <= 1/255,messages.roundtrip_failed);
    if (item.value !== undefined) assert.equal(layer.text?.text,item.value,messages.roundtrip_failed);
    else assert.ok(!layer.text,messages.roundtrip_failed);
  });
  assert.ok(leaves.every(layer => layer.imageData.data.length > 0),messages.roundtrip_failed);
  return {technical_passed:true,visual_review:'not_performed_by_code',dimensions:[psd.width,psd.height],groups:config.groups,layers:leaves.map(layer=>({name:layer.name,type:layer.text?'type':'pixel',blend:layer.blendMode,opacity:layer.opacity,visible:!layer.hidden}))};
}

/** Run deterministic assembly after manifest and font checks have succeeded. */
async function build(options) {
  const {config,base} = loadManifest(options.config);
  const out = path.resolve(options.out);
  const files = outputPaths(out,config,options.overwrite);
  render.registerFonts(base,config);
  const art = await Promise.all(config.art.map(item=>render.artLayer(item,config,base)));
  const layers = [...art,...config.text.map(item=>render.textLayer(item,config))];
  const {composite,children} = render.compose(layers,config);
  const psd = {width:config.width,height:config.height,children,imageData:render.pixels(composite),
    imageResources:{versionInfo:{hasRealMergedData:true,writerName:'workflow / ag-psd',readerName:'PSD reader',fileVersion:1}}};
  const buffer = writePsdBuffer(psd);
  const report = verify(buffer,config);
  fs.mkdirSync(path.join(out,'qa'),{recursive:true});
  fs.mkdirSync(path.join(out,'logs'),{recursive:true});
  log(out,messages.build_start,{layers:layers.length});
  fs.writeFileSync(files.psd,buffer);
  fs.writeFileSync(files.preview,composite.toBuffer('image/png'));
  fs.writeFileSync(path.join(out,'qa','ag-psd-verification.json'),JSON.stringify(report,null,2));
  log(out,messages.build_done,{bytes:buffer.length});
  return {...files,report};
}

if (require.main === module) {
  Promise.resolve().then(()=>build(argumentsFor(process.argv.slice(2))))
    .then(result=>process.stdout.write(JSON.stringify(result)+'\n'))
    .catch(error=>{process.stderr.write(JSON.stringify({message:messages.build_failed,error:error.message})+'\n');process.exitCode=1;});
}
module.exports = {argumentsFor,outputPaths,verify,build};
