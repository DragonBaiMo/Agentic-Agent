// SPDX-License-Identifier: MIT
// Reserve a fresh build namespace before compilation can consume time or change files.
import fs from 'node:fs/promises';
import path from 'node:path';

/** Reject every occupied output first, including files and dangling symlinks. */
async function requireMissing(directory, relative) {
  try {
    await fs.lstat(directory);
  } catch (error) {
    if (error.code === 'ENOENT') return;
    throw error;
  }
  throw new Error('build_namespace_exists: ' + relative);
}

/** Reject pre-existing non-directory parents before a child lookup can follow a symlink. */
async function requirePlainParent(directory, relative) {
  let stat;
  try {
    stat = await fs.lstat(directory);
  } catch (error) {
    if (error.code === 'ENOENT') return;
    throw error;
  }
  if (!stat.isDirectory() || stat.isSymbolicLink()) {
    throw new Error('build_parent_not_directory: ' + relative);
  }
}

/** Require an absolute project root and safe name; exclusively create three new directories.
 * Existing namespaces are never cleared. I/O failures can leave new empty reservations.
 * This assumes a single writer; it does not prevent malicious parent replacement races.
 */
export async function reserveBuildPaths(root, build) {
  if (!path.isAbsolute(root) || !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(build || '')) {
    throw new Error('project_and_build_required');
  }
  const directories = {build: 'builds', temporary: 'tmp', evidence: 'evidence'};
  const result = {};
  for (const [role, parent] of Object.entries(directories)) {
    await requirePlainParent(path.join(root, parent), parent);
    result[role] = path.join(root, parent, build);
    await requireMissing(result[role], parent + '/' + build);
  }
  // NOTE: Preflight all roles before the first write; mkdir still rejects a racing writer.
  for (const directory of Object.values(result)) {
    await fs.mkdir(path.dirname(directory), {recursive: true});
    await fs.mkdir(directory, {recursive: false});
  }
  return result;
}
