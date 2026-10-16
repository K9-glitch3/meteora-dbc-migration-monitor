const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const lock=JSON.parse(fs.readFileSync('package-lock.json','utf8'));
const packages=Object.entries(lock.packages).filter(([p])=>p).map(([p,meta])=>{
  const pkg=JSON.parse(fs.readFileSync(path.join(p,'package.json'),'utf8'));
  const notices=fs.readdirSync(p).filter(n=>/^(licen[sc]e|notice|copying)(\.|$)/i.test(n));
  return {name:pkg.name,version:pkg.version,declared_license:pkg.license||'NOT_DECLARED',integrity:meta.integrity,
    notices:notices.filter(n=>fs.statSync(path.join(p,n)).isFile()).map(n=>({file:n,sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(p,n))).digest('hex')}))};
});
packages.sort((a,b)=>a.name.localeCompare(b.name));
fs.writeFileSync('docs/dependency-inventory.json',JSON.stringify({purpose:'Development-only SDK reference dependencies; declared licenses, not a legal clearance',packages},null,2)+'\n');
console.log(JSON.stringify({packages:packages.length,licenses:[...new Set(packages.map(p=>p.declared_license))]}));
