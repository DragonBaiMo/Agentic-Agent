// SPDX-License-Identifier: MIT
// Compile and assemble an image-first deck, finalize, then render the actual PPTX.
// Usage: node scripts/assemble_pptx.mjs --project DIR --build B01 --presentations-skill DIR
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {parseArgs} from 'node:util';
import {execFileSync} from 'node:child_process';
import {addImage,addObject} from './pptx_backend/render_objects.mjs';
import {reserveBuildPaths} from './pptx_backend/build_paths.mjs';

const {values:args} = parseArgs({options:{
  project:{type:'string'}, plan:{type:'string',default:'deck.json'},
  build:{type:'string'}, 'presentations-skill':{type:'string'}, help:{type:'boolean'},
}});
const scripts = path.dirname(fileURLToPath(import.meta.url));
if (args.help) {
  process.stdout.write('node scripts/assemble_pptx.mjs --project DIR --build B01 --presentations-skill DIR [--plan deck.json]\n');
} else {
  await main();
}

/** Require explicit host runtime paths; never install packages or guess private paths. */
async function runtime() {
  const env = process.env;
  for (const key of ['RUNTIME_NODE','RUNTIME_PYTHON','RUNTIME_NODE_MODULES','RUNTIME_BIN_DIR']) {
    if (!path.isAbsolute(env[key] || '')) throw new Error('missing_runtime: ' + key);
    await fs.access(env[key]);
  }
  if (!path.isAbsolute(args['presentations-skill'] || '')) throw new Error('missing_presentations_skill');
  const require = createRequire(path.join(env.RUNTIME_NODE_MODULES,'..','package.json'));
  const api = await import(require.resolve('@oai/artifact-tool'));
  const skill = args['presentations-skill'];
  const utils = await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
  return {...api,...utils,skill,python:env.RUNTIME_PYTHON};
}

/** Record a bounded host operation and export a new, immutable build directory. */
async function main() {
  if (!args.project || !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(args.build || '')) throw new Error('project_and_build_required');
  const root = await fs.realpath(path.resolve(args.project));
  const {build:dir,temporary:tmp} = await reserveBuildPaths(root,args.build);
  const compiled = path.join(dir,'compiled.json');
  execFileSync(process.env.RUNTIME_PYTHON,[path.join(scripts,'pptx_project.py'),
    '--project',root,'--plan',args.plan,'--out',path.relative(root,compiled)],
    {stdio:'inherit',timeout:30000});
  const data = JSON.parse(await fs.readFile(compiled,'utf8'));
  const rt = await runtime();
  // NOTE: This marker is required by the active host presentation authoring workflow.
  execFileSync(process.env.RUNTIME_NODE,[path.join(rt.skill,'container_tools/mark_artifact_operation_started.mjs'),
    '--operation-kind','create','--expected-output-count','1','--output-format','pptx'],
    {stdio:'inherit',timeout:30000});
  const deck = rt.Presentation.create({slideSize:{width:data.canvas[0],height:data.canvas[1]}});
  const master = deck.masters.add(data.name || 'Image-first deck');
  master.background.fill = data.theme.background;
  const layout = deck.layouts.add('Semantic image composition');
  layout.setParentLayoutId(master.id);
  for (const page of data.slides) {
    const slide = deck.slides.add(); slide.setLayout(layout);
    await addImage(slide,{file:data.background,box:[0,0,...data.canvas],alt:data.background_alt},root);
    for (const item of page.elements) await addObject(slide,item,root,rt.applyPresentationChartFont);
    slide.speakerNotes.textFrame.setText(page.notes || '');
  }
  const raw = path.join(tmp,'raw.pptx');
  const candidate = path.join(tmp,'candidate.pptx');
  const semantic = {...data,slides:data.slides.map(s=>({...s,images:s.elements.filter(e=>e.kind==='image')}))};
  const semantics = path.join(tmp,'semantics.json');
  await fs.writeFile(semantics,JSON.stringify(semantic));
  await (await rt.PresentationFile.exportPptx(deck)).save(raw);
  execFileSync(rt.python,[path.join(scripts,'pptx_backend/semantics.py'),'--input',raw,
    '--output',candidate,'--manifest',semantics],{stdio:'inherit',timeout:60000});
  await finalize(root,dir,candidate,data,rt);
}

/** Finalize and inspect the exported bytes, not an in-memory preview of the source deck. */
async function finalize(root,dir,candidate,data,rt) {
  const output = path.join(dir,'final.pptx');
  const checks = path.join(root,'evidence',path.basename(dir));
  const owners = kind => data.slides.flatMap((s,i)=>s.elements.some(e=>e.kind===kind)?[i+1]:[]);
  const tables = owners('table');
  await rt.finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath:output,
    pythonExecutable:rt.python,
    integrityValidatorPath:path.join(rt.skill,'container_tools/inspect_presentation_package_integrity.py'),
    layoutValidatorPath:path.join(rt.skill,'container_tools/inspect_presentation_layout_geometry.py'),
    layoutArgs:['--expected-slide-size-emu',data.canvas.map(v=>Math.round(v*9525)).join(','),
      ...tables.flatMap(n=>['--require-native-table-slide',String(n)])],
    explicitTotalSlideCount:data.slides.length,
    requiredNativeChartOwnerSlides:owners('chart'),requiredNativeTableOwnerSlides:tables,
    materializeLiteralChartWorkbooks:true,fontPolicy:data.font_policy,
    verifyArtifactToolImport:true,receiptPath:path.join(checks,'validation.json')});
  const actual = await rt.PresentationFile.importPptx(await rt.FileBlob.load(output));
  for (let i=0;i<data.slides.length;i++) {
    const png = await actual.export({slide:actual.slides.getItem(i),format:'png',scale:1});
    await fs.writeFile(path.join(dir,`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
  }
  await fs.writeFile(path.join(dir,'inspect.ndjson'),
    (await actual.inspect({kind:'slide,textbox,image,chart,table',maxChars:100000})).ndjson);
  process.stdout.write(JSON.stringify({level:'INFO',event:'pptx_ready',file:output})+'\n');
}
