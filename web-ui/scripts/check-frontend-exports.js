const fs = require('fs');
const path = require('path');

const publicDir = path.join(__dirname, '..', 'public');

function getJsFiles(dir) {
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith('.js'))
    .map((entry) => path.join(dir, entry.name));
}

function findRecursiveWindowExports(content) {
  const findings = [];
  const re = /window\.(\w+)\s*=\s*function\s*\([^)]*\)\s*\{([\s\S]*?)\};/g;
  let match;

  while ((match = re.exec(content)) !== null) {
    const exportedName = match[1];
    const body = match[2];
    const selfCall = new RegExp(`\\b${exportedName}\\s*\\(`);
    if (selfCall.test(body)) {
      findings.push(exportedName);
    }
  }

  return findings;
}

const files = getJsFiles(publicDir);
const errors = [];

for (const file of files) {
  const content = fs.readFileSync(file, 'utf8');
  const recursiveExports = findRecursiveWindowExports(content);
  if (recursiveExports.length > 0) {
    errors.push({
      file: path.relative(path.join(__dirname, '..'), file),
      exports: recursiveExports
    });
  }
}

if (errors.length > 0) {
  console.error('Found potentially recursive window exports:');
  for (const err of errors) {
    console.error(`- ${err.file}: ${err.exports.join(', ')}`);
  }
  process.exit(1);
}

console.log('Frontend export recursion check passed.');
