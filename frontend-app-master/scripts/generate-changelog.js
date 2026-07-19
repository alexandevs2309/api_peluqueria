const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Paths
const packageJsonPath = path.join(__dirname, '../package.json');
const changelogJsonPath = path.join(__dirname, '../src/assets/changelog.json');

// 1. Read version from package.json
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
const currentVersion = `v${packageJson.version}`;
const today = new Intl.DateTimeFormat('es-DO', {
  day: 'numeric',
  month: 'long',
  year: 'numeric'
}).format(new Date());

// 2. Fetch Git Commits
// We fetch commits since the last tag. If there's no tag, we fallback to the last 30 commits.
let gitCommits = '';
try {
  // Get last tag name
  const lastTag = execSync('git describe --tags --abbrev=0', { encoding: 'utf8' }).trim();
  gitCommits = execSync(`git log ${lastTag}..HEAD --pretty=format:"%s"`, { encoding: 'utf8' });
} catch (e) {
  // Fallback: get last 30 commits
  gitCommits = execSync('git log -n 30 --pretty=format:"%s"', { encoding: 'utf8' });
}

const commitLines = gitCommits.split('\n').map(c => c.trim()).filter(Boolean);

// 3. Filter and parse commits
const features = [];
const fixes = [];
const securityList = [];
const performanceList = [];

commitLines.forEach(line => {
  if (line.startsWith('feat:')) {
    features.push(line.replace('feat:', '').trim());
  } else if (line.startsWith('fix:')) {
    fixes.push(line.replace('fix:', '').trim());
  } else if (line.startsWith('security:')) {
    securityList.push(line.replace('security:', '').trim());
  } else if (line.startsWith('perf:')) {
    performanceList.push(line.replace('perf:', '').trim());
  }
});

// If no user-facing changes are found, we don't need to generate a new entry
if (features.length === 0 && fixes.length === 0 && securityList.length === 0 && performanceList.length === 0) {
  console.log('No user-facing changes (feat/fix/security/perf) found in git log. Skipping changelog update.');
  process.exit(0);
}

// Prepare the new entry
const newChanges = [];
let mainType = 'feat';
let mainTitle = 'Actualizaciones del sistema';

if (features.length > 0) {
  features.forEach(f => newChanges.push(`Nueva funcionalidad: ${f}`));
  mainType = 'feat';
  mainTitle = features[0]; // Use first feature as main title
}
if (fixes.length > 0) {
  fixes.forEach(f => newChanges.push(`Corrección: ${f}`));
  if (newChanges.length === fixes.length) {
    mainType = 'fix';
    mainTitle = fixes[0];
  }
}
if (securityList.length > 0) {
  securityList.forEach(s => newChanges.push(`Seguridad: ${s}`));
  mainType = 'security';
  mainTitle = securityList[0];
}
if (performanceList.length > 0) {
  performanceList.forEach(p => newChanges.push(`Rendimiento: ${p}`));
  if (features.length === 0 && fixes.length === 0 && securityList.length === 0) {
    mainType = 'perf';
    mainTitle = performanceList[0];
  }
}

const newEntry = {
  version: currentVersion,
  date: today,
  title: mainTitle.charAt(0).toUpperCase() + mainTitle.slice(1),
  description: `Actualizaciones y mejoras automatizadas para la versión ${currentVersion}.`,
  type: mainType,
  changes: newChanges
};

// 4. Read existing changelog.json and merge
let changelogData = [];
if (fs.existsSync(changelogJsonPath)) {
  try {
    changelogData = JSON.parse(fs.readFileSync(changelogJsonPath, 'utf8'));
  } catch (e) {
    console.error('Error parsing existing changelog.json, initializing empty list.');
  }
}

// Remove old entry for the same version if it exists to prevent duplicates
changelogData = changelogData.filter(entry => entry.version !== currentVersion);

// Prepend the new entry to the list
changelogData.unshift(newEntry);

// Save back
fs.writeFileSync(changelogJsonPath, JSON.stringify(changelogData, null, 4), 'utf8');
console.log(`Changelog updated successfully for version ${currentVersion}!`);
