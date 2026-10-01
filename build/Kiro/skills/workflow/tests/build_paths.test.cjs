// SPDX-License-Identifier: MIT
// Reject an occupied build namespace before invoking compilation or any host runtime.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '..');

/** Give every scenario a project-local disposable directory and guaranteed cleanup. */
async function fixture(t) {
  const base = path.join(root, 'tmp/build-path-tests');
  await fs.mkdir(base, {recursive: true});
  const project = await fs.mkdtemp(path.join(base, 'case-'));
  t.after(() => fs.rm(project, {recursive: true, force: true}));
  return project;
}

/** Use a real CLI with no runtime variables; occupied paths must fail before that matters. */
async function rejectsOccupied(t, directory) {
  const project = await fixture(t);
  const occupied = path.join(project, directory, 'B01');
  await fs.mkdir(occupied, {recursive: true});
  await fs.writeFile(path.join(occupied, 'original.txt'), 'unchanged source');
  const before = await fs.readdir(project, {recursive: true});
  const result = spawnSync(process.execPath, [path.join(root, 'scripts/assemble_pptx.mjs'),
    '--project', project, '--build', 'B01'], {encoding: 'utf8', env: {PATH: process.env.PATH}});
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, new RegExp('build_namespace_exists: ' + directory + '/B01'));
  assert.deepEqual(await fs.readdir(project, {recursive: true}), before);
  assert.equal(await fs.readFile(path.join(occupied, 'original.txt'), 'utf8'), 'unchanged source');
}

test('old evidence rejects before any compilation or new write', t => rejectsOccupied(t, 'evidence'));
test('old temporary build rejects before any compilation or new write', t => rejectsOccupied(t, 'tmp'));
test('old final build rejects before any compilation or new write', t => rejectsOccupied(t, 'builds'));

test('new name reserves exactly three empty output directories', async t => {
  const project = await fixture(t);
  const {reserveBuildPaths} = await import(pathToFileURL(path.join(root, 'scripts/pptx_backend/build_paths.mjs')));
  const result = await reserveBuildPaths(project, 'B02');
  assert.deepEqual(result, {build: path.join(project, 'builds/B02'),
    temporary: path.join(project, 'tmp/B02'), evidence: path.join(project, 'evidence/B02')});
  assert.deepEqual(await fs.readdir(result.build), []);
  assert.deepEqual(await fs.readdir(result.temporary), []);
  assert.deepEqual(await fs.readdir(result.evidence), []);
});

test('invalid name is rejected without writes', async t => {
  const project = await fixture(t);
  const {reserveBuildPaths} = await import(pathToFileURL(path.join(root, 'scripts/pptx_backend/build_paths.mjs')));
  await assert.rejects(reserveBuildPaths(project, '../escape'), /project_and_build_required/);
  assert.deepEqual(await fs.readdir(project), []);
});

test('ordinary file occupying a build name is preserved', async t => {
  const project = await fixture(t);
  await fs.mkdir(path.join(project, 'tmp'));
  const file = path.join(project, 'tmp/B01');
  await fs.writeFile(file, 'preserve this file');
  const {reserveBuildPaths} = await import(pathToFileURL(path.join(root, 'scripts/pptx_backend/build_paths.mjs')));
  await assert.rejects(reserveBuildPaths(project, 'B01'), /build_namespace_exists: tmp\/B01/);
  assert.equal(await fs.readFile(file, 'utf8'), 'preserve this file');
  assert.deepEqual(await fs.readdir(project), ['tmp']);
});

test('dangling child link is occupied and must not be replaced', async t => {
  const project = await fixture(t);
  await fs.mkdir(path.join(project, 'evidence'));
  await fs.symlink('missing-target', path.join(project, 'evidence/B01'));
  const {reserveBuildPaths} = await import(pathToFileURL(path.join(root, 'scripts/pptx_backend/build_paths.mjs')));
  await assert.rejects(reserveBuildPaths(project, 'B01'), /build_namespace_exists: evidence\/B01/);
  assert.equal(await fs.readlink(path.join(project, 'evidence/B01')), 'missing-target');
  assert.deepEqual(await fs.readdir(project), ['evidence']);
});

for (const parent of ['builds', 'tmp', 'evidence']) {
  test('external parent link is rejected before writes: ' + parent, async t => {
    const project = await fixture(t);
    const outside = await fixture(t);
    await fs.symlink(outside, path.join(project, parent));
    const {reserveBuildPaths} = await import(pathToFileURL(path.join(root, 'scripts/pptx_backend/build_paths.mjs')));
    await assert.rejects(reserveBuildPaths(project, 'B01'), /build_parent_not_directory/);
    assert.deepEqual(await fs.readdir(outside), []);
    assert.deepEqual(await fs.readdir(project), [parent]);
  });
}
