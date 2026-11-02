// Synthetic display fixture only. Uses an installed renderer, no production dependency.
const fs=require('node:fs'),path=require('node:path');
const sharp=require(process.env.INFRA_SHARP_MODULE||'sharp');
const dest=path.resolve('.project/experiments/EXP-0008.assets');fs.mkdirSync(dest,{recursive:true});
function panel(x,title,values,max,unit){
  const colors=['#75b6e1','#62d9c5'],labels=['Baseline','Candidate'];
  return `<g transform="translate(${x},100)"><text x="190" y="0" text-anchor="middle" font-size="18">${title}</text><path d="M35 35V300H370" fill="none" stroke="#5c7387"/><text x="35" y="25" font-size="12" fill="#91a8ba">${unit}</text>${values.map((v,i)=>{const h=v/max*220,bx=90+i*150;return `<rect x="${bx}" y="${300-h}" width="76" height="${h}" fill="${colors[i]}"/><text x="${bx+38}" y="${287-h}" text-anchor="middle" font-size="17">${v}</text><text x="${bx+38}" y="330" text-anchor="middle" font-size="14">${labels[i]}</text>`;}).join('')}</g>`;
}
const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="520"><rect width="1000" height="520" fill="#0c141e"/><g fill="#dce7ed" font-family="Arial,sans-serif"><text x="500" y="48" text-anchor="middle" font-size="25">One figure / multiple metric comparisons</text>${panel(65,'Accuracy comparison',[0.72,0.81],1,'Score')}${panel(540,'Latency comparison',[58,44],70,'Milliseconds')}<text x="500" y="488" text-anchor="middle" font-size="13" fill="#9cafbd">SYNTHETIC DISPLAY FIXTURE - NOT MEASURED PERFORMANCE</text></g></svg>`;
sharp(Buffer.from(svg)).png().toFile(path.join(dest,'metrics-comparison.png')).then(()=>{
  fs.writeFileSync(path.join(dest,'metrics-fixture.csv'),'method,accuracy,latency_ms\nBaseline,0.72,58\nCandidate,0.81,44\n');
  console.log('Created a single comparison figure and CSV table. Values are synthetic display fixtures.');
}).catch(e=>{console.error(e);process.exitCode=1;});
