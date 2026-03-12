const fs = require('fs');
const path = require('path');

// Fix agents.py - remove trailing Unicode curly quotes
const agentsPath = path.join(__dirname, 'agents.py');
let content = fs.readFileSync(agentsPath, 'utf8');
const before = content.length;
// Remove Unicode LEFT/RIGHT double quotation marks (U+201C, U+201D)
content = content.replace(/\u201c/g, '').replace(/\u201d/g, '');
const after = content.length;
console.log(`agents.py: removed ${before - after} Unicode curly quote chars`);
fs.writeFileSync(agentsPath, content, 'utf8');

// Verify by checking for syntax (basic check: no standalone "" lines)
const lines = content.split('\n');
let issues = 0;
lines.forEach((line, i) => {
  if (/^\s*[\u201c\u201d]+\s*$/.test(line)) {
    console.log(`  Still found issue at line ${i+1}: ${JSON.stringify(line)}`);
    issues++;
  }
});
if (issues === 0) console.log('✓ agents.py clean');

console.log('Done!');
