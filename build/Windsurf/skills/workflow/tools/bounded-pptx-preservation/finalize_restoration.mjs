// SPDX-License-Identifier: MIT
// Restore validated source dependencies, then use the active Presentations finalizer.
// Usage: node finalize_restoration.mjs --source SRC --authored DRAFT --out-dir NEW --requirements JSON
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {parseArgs} from 'node:util';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {createHash} from 'node:crypto';

const run = promisify(execFile);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const {values: args} = parseArgs({options: {
  source: {type:'string'}, authored: {type:'string'}, 'out-dir': {type:'string'},
  requirements: {type:'string'},
}});
const root = path.dirname(fileURLToPath(import.meta.url));

/** Require explicit runtime paths and invoke the authoritative Python precheck. */
async function restore() {
  const env = process.env;
  for (const key of ['RUNTIME_PYTHON', 'PRESENTATIONS_SKILL_DIR', 'RUNTIME_NODE_MODULES']) {
    if (!path.isAbsolute(env[key] ?? '')) throw new Error(`missing_runtime:${key}`);
    await fs.access(env[key]);
  }
  for (const key of ['source','authored','out-dir','requirements']) {
    if (!args[key]) throw new Error(`missing_argument:${key}`);
    args[key] = path.resolve(args[key]);
  }
  const child = await run(env.RUNTIME_PYTHON, [path.join(root,'restore_chart_dependencies.py'),
    '--source',args.source,'--authored',args.authored,'--out-dir',args['out-dir']],
    {timeout:30000,maxBuffer:1024*1024});
  process.stderr.write(child.stderr);
  return JSON.parse(await fs.readFile(path.join(args['out-dir'],'proof.json'),'utf8'));
}

/** Keep the original workbook mandatory; a literal snapshot cannot hide a loss. */
async function finalize(proof) {
  const config = JSON.parse(await fs.readFile(args.requirements,'utf8'));
  if (!Number.isInteger(config.slideCount) || config.slideCount < 1 ||
      !/^[1-9]\d*,[1-9]\d*$/.test(config.slideSizeEmu) ||
      !Array.isArray(config.fonts) || !config.fonts.length) throw new Error('invalid_requirements');
  const skill = process.env.PRESENTATIONS_SKILL_DIR;
  const {finalizePresentation} = await import(pathToFileURL(path.join(skill,
    'container_tools/artifact_tool_utils.mjs')).href);
  const staged = path.join(args['out-dir'],'verified','validated.pptx');
  await fs.mkdir(path.dirname(staged));
  await finalizePresentation({workspaceDir:args['out-dir'],
    candidatePath:path.join(args['out-dir'],'candidate.pptx'),finalPath:staged,
    pythonExecutable:process.env.RUNTIME_PYTHON,
    integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
    layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
    layoutArgs:['--expected-slide-size-emu',config.slideSizeEmu,'--validate-heading-fit'],
    explicitTotalSlideCount:config.slideCount,
    requiredNativeChartOwnerSlides:[proof.chart_owner_slide],
    requiredEmbeddedWorkbookChartOwnerSlides:[proof.chart_owner_slide],
    materializeLiteralChartWorkbooks:false,
    fontPolicy:{basis:'reference',families:config.fonts,referencePath:args.source,
      referenceSha256:proof.source_sha256},
    verifyArtifactToolImport:true,
    receiptPath:path.join(args['out-dir'],'validation.json')});
  if (sha(await fs.readFile(args.source)) !== proof.source_sha256 ||
      sha(await fs.readFile(args.authored)) !== proof.authored_sha256 ||
      sha(await fs.readFile(staged)) !== proof.restored_sha256) throw new Error('identity_changed');
  const final = path.join(args['out-dir'],'output','final.pptx');
  await fs.mkdir(path.dirname(final));
  // NOTE: Publish only after all checks. An exclusive same-filesystem link is atomic;
  // finalizer or post-check failure cannot leave a partially written deliverable.
  await fs.link(staged,final);
  process.stdout.write(JSON.stringify({level:'INFO',event:'preserved_pptx_ready',file:final,
    sha256:proof.restored_sha256})+'\n');
}

try {
  await finalize(await restore());
} catch (error) {
  process.stderr.write(JSON.stringify({level:'ERROR',event:'preservation_not_delivered',
    reason:error.message,childStderr:error.stderr ?? null})+'\n');
  process.exitCode = 1;
}
