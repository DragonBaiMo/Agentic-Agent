// SPDX-License-Identifier: MIT
// Real Node subprocesses test loading separately from package metadata discovery.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {createRequire} = require('node:module');
const vm = require('node:vm');

/** Keep all synthetic dependency files inside the project's disposable test directory. */
function fixture(t, options = {}) {
  const base = path.resolve(__dirname, '../tmp/doctor-tests');
  fs.mkdirSync(base, {recursive:true});
  const root = fs.mkdtempSync(path.join(base, 'case-'));
  t.after(() => fs.rmSync(root, {recursive:true, force:true}));
  const project = path.join(root, 'project');
  const modules = path.join(options.local ? project : path.join(root, 'external'), 'node_modules');
  const pkg = path.join(modules, 'doctor-fixture-package');
  fs.mkdirSync(path.join(project, 'scripts'), {recursive:true});
  fs.mkdirSync(path.join(pkg, 'dist'), {recursive:true});
  fs.copyFileSync(path.resolve(__dirname, '../scripts/doctor.cjs'), path.join(project, 'scripts/doctor.cjs'));
  fs.writeFileSync(path.join(project, 'package.json'), JSON.stringify({
    name:'doctor-fixture-project', dependencies:{'doctor-fixture-package':'1.0.0'}}));
  const entry = options.deep ? Array(14).fill('deep').join('/')+'/index.cjs'
    : options.noMetadata ? 'index.js' : 'dist/index.cjs';
  fs.mkdirSync(path.dirname(path.join(pkg, entry)), {recursive:true});
  fs.writeFileSync(path.join(pkg, entry), options.loadError
    ? "throw Object.assign(new Error('fixture'), {code:'FIXTURE_LOAD_FAILED'});"
    : 'module.exports = {ready:true};');
  if (!options.noMetadata) fs.writeFileSync(path.join(pkg, 'package.json'), JSON.stringify({
    name:options.wrongName ? 'unrelated-package' : 'doctor-fixture-package',
    version:options.noVersion ? undefined : options.version || '1.0.0', main:entry,
    ...(options.exportsOnly ? {exports:{'.':'./'+entry}} : {})}));
  if (options.unrelatedParent) fs.writeFileSync(path.join(root, 'external', 'package.json'),
    JSON.stringify({name:'doctor-fixture-package', version:'77.0.0'}));
  return () => {
    const actual = JSON.parse(execFileSync(process.execPath, ['scripts/doctor.cjs'], {
      cwd:project, env:{...process.env, NODE_PATH:options.missing ? '' : modules},
      encoding:'utf8', timeout:10000})).dependencies[0];
    // NOTE: Also execute the exported API for source-file coverage; dependency resolution
    // still uses Node's createRequire, while only the small declaration is fixture input.
    const source = path.resolve(__dirname, '../scripts/doctor.cjs');
    const resolver = createRequire(path.join(options.missing ? project : path.dirname(modules), 'loader.cjs'));
    const declaration = JSON.parse(fs.readFileSync(path.join(project, 'package.json'), 'utf8'));
    const fixtureRequire = Object.assign(name => name === '../package.json' ? declaration : resolver(name),
      {resolve:resolver.resolve});
    const output = {exports:{}};
    vm.runInNewContext(fs.readFileSync(source, 'utf8'),
      {require:fixtureRequire, module:output, process, console}, {filename:source});
    const fromApi = JSON.parse(JSON.stringify(output.exports.inspectDependencies()[0]));
    assert.deepEqual(fromApi, actual);
    return actual;
  };
}

test('a normal local locked installation retains its existing success contract', t => {
  const run = fixture(t, {local:true});
  const result = run();
  assert.equal(result.loadable, true);
  assert.equal(result.installed, '1.0.0');
  assert.equal(result.version_matches, true);
});

test('NODE_PATH loading does not require a duplicate local node_modules', t => {
  const run = fixture(t);
  const result = run();
  assert.equal(result.loadable, true);
  assert.equal(result.installed, '1.0.0');
  assert.equal(result.version_matches, true);
});

test('package exports may hide package.json while the public entry loads', t => {
  const run = fixture(t, {exportsOnly:true});
  const result = run();
  assert.equal(result.loadable, true);
  assert.equal(result.metadata_verified, true);
  assert.equal(result.version_matches, true);
});

test('a wrong installed version stays loadable but fails version matching', t => {
  const run = fixture(t, {version:'2.0.0'});
  const result = run();
  assert.equal(result.loadable, true);
  assert.equal(result.installed, '2.0.0');
  assert.equal(result.version_matches, false);
});

test('missing metadata never turns a successful require into a load failure', t => {
  const run = fixture(t, {noMetadata:true});
  const result = run();
  assert.equal(result.loadable, true);
  assert.equal(result.metadata_verified, false);
  assert.equal(result.version_matches, false);
  assert.equal(result.metadata_error_code, 'PACKAGE_METADATA_NOT_FOUND');
});

test('unrelated ancestor metadata cannot supply an invented installed version', t => {
  const run = fixture(t, {noMetadata:true, unrelatedParent:true});
  const result = run();
  assert.equal(result.loadable, true);
  assert.equal(result.metadata_verified, false);
  assert.equal(result.installed, undefined);
});

test('a mismatched package name is not accepted as version evidence', t => {
  const run = fixture(t, {wrongName:true});
  const result = run();
  assert.equal(result.loadable, true);
  assert.equal(result.metadata_error_code, 'PACKAGE_NAME_MISMATCH');
  assert.equal(result.version_matches, false);
});

test('a truly missing module still reports loadable false', t => {
  const run = fixture(t, {missing:true});
  const result = run();
  assert.equal(result.loadable, false);
  assert.equal(result.error_code, 'MODULE_NOT_FOUND');
});

test('a public entry that throws still reports the actual loader error', t => {
  const run = fixture(t, {loadError:true});
  const result = run();
  assert.equal(result.loadable, false);
  assert.equal(result.error_code, 'FIXTURE_LOAD_FAILED');
});

test('a package without a version loads but cannot verify the lock requirement', t => {
  const run = fixture(t, {noVersion:true});
  const result = run();
  assert.equal(result.loadable, true);
  assert.equal(result.metadata_error_code, 'PACKAGE_VERSION_MISSING');
  assert.equal(result.version_matches, false);
});

test('deep entries stop metadata lookup at the bounded ancestor limit', t => {
  const run = fixture(t, {deep:true});
  const result = run();
  assert.equal(result.loadable, true);
  assert.equal(result.metadata_verified, false);
  assert.equal(result.metadata_error_code, 'PACKAGE_METADATA_NOT_FOUND');
});
