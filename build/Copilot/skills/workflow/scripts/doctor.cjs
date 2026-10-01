// SPDX-License-Identifier: MIT
// Read-only Node dependency diagnostics; no installation or network access.
const fs = require('node:fs');
const path = require('node:path');
/** @type {Record<string, string>} */
const declared = require('../package.json').dependencies;
// NOTE: Inspect only the resolved entry's ancestor chain; never scan other installs.
const MAX_METADATA_ASCENTS = 12;

/** Return an error code without confusing loader failures with metadata failures.
 * @param {unknown} error @param {string} fallback */
function errorCode(error, fallback) {
  return error && typeof error === 'object' && 'code' in error && typeof error.code === 'string'
    ? error.code : fallback;
}

/** Locate metadata belonging to the public entry that Node actually resolved.
 * @param {string} name @param {string} entry @returns {{version:string}} */
function packageMetadata(name, entry) {
  if (!path.isAbsolute(entry)) throw Object.assign(new Error('PACKAGE_ENTRY_NOT_FILE'), {code:'PACKAGE_ENTRY_NOT_FILE'});
  let directory = path.dirname(entry);
  for (let depth = 0; depth < MAX_METADATA_ASCENTS; depth++) {
    if (path.basename(directory) === 'node_modules') break;
    let metadata;
    try {
      metadata = JSON.parse(fs.readFileSync(path.join(directory, 'package.json'), 'utf8'));
    } catch (error) {
      if (errorCode(error, '') !== 'ENOENT') throw error;
    }
    if (metadata && metadata.name) {
      if (metadata.name !== name) throw Object.assign(new Error('PACKAGE_NAME_MISMATCH'), {code:'PACKAGE_NAME_MISMATCH'});
      if (typeof metadata.version !== 'string' || !metadata.version)
        throw Object.assign(new Error('PACKAGE_VERSION_MISSING'), {code:'PACKAGE_VERSION_MISSING'});
      return metadata;
    }
    const parent = path.dirname(directory);
    if (parent === directory) break;
    directory = parent;
  }
  throw Object.assign(new Error('PACKAGE_METADATA_NOT_FOUND'), {code:'PACKAGE_METADATA_NOT_FOUND'});
}

/** Public loading decides loadable; verified same-package metadata decides version_matches.
 * @param {string} name @param {string} expected */
function inspectDependency(name, expected) {
  try {
    require(name);
  } catch (error) {
    return {name, expected, loadable:false, error_code:errorCode(error, 'dependency_load_failed')};
  }
  try {
    const metadata = packageMetadata(name, require.resolve(name));
    return {name, expected, installed:metadata.version, loadable:true,
      metadata_verified:true, version_matches:metadata.version === expected};
  } catch (error) {
    return {name, expected, loadable:true, metadata_verified:false, version_matches:false,
      metadata_error_code:errorCode(error, 'PACKAGE_METADATA_INVALID')};
  }
}

/** Load the actual modules so a package file alone cannot imply runtime readiness. */
function inspectDependencies() {
  return Object.entries(declared).map(([name, expected]) => inspectDependency(name, expected));
}

if (require.main === module) {
  console.log(JSON.stringify({version:process.versions.node, minimum_major:20,
    supported:Number(process.versions.node.split('.')[0]) >= 20, dependencies:inspectDependencies()}));
}

module.exports = {inspectDependencies};
