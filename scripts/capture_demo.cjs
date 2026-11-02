// Capture real application screens; the project is fictional and marked as such.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const output=path.resolve('docs/media'),frames=path.resolve('.work/demo-frames');
 fs.mkdirSync(output,{recursive:true});fs.mkdirSync(frames,{recursive:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.INFRA_DEMO_URL||'http://127.0.0.1:8768/');
  await page.locator('[data-node-id="EXP-0006"]').waitFor();
  await page.addStyleTag({content:'#root{visibility:hidden}'}); // Redact the machine-specific directory only.
  await page.waitForTimeout(400);
  await page.evaluate(()=>{
   const canvas=document.querySelector('.graph-canvas'),vp=canvas.parentElement;
   const points=[...canvas.querySelectorAll('.circuit-node')].filter(n=>['EXP-0002','EXP-0003','EXP-0004','EXP-0005','EXP-0006'].includes(n.dataset.nodeId)).map(n=>({x:parseFloat(n.style.left),y:parseFloat(n.style.top)}));
   const left=Math.min(...points.map(p=>p.x))-25,top=Math.min(...points.map(p=>p.y))-45;
   const right=Math.max(...points.map(p=>p.x))+310,bottom=Math.max(...points.map(p=>p.y))+100;
   graphCamera.scale=Math.min(.95,(vp.clientWidth-70)/(right-left),(vp.clientHeight-85)/(bottom-top));
   graphCamera.initialized=true;
   graphCamera.x=(vp.clientWidth-(right-left)*graphCamera.scale)/2-left*graphCamera.scale;graphCamera.y=40-top*graphCamera.scale;
   canvas.style.transform=`translate(${graphCamera.x}px,${graphCamera.y}px) scale(${graphCamera.scale})`;
   document.querySelector('.zoom-value').textContent=Math.round(graphCamera.scale*100)+'%';
  });
  await page.waitForTimeout(150);
  let i=0;
  const frame=()=>page.screenshot({path:path.join(frames,String(++i).padStart(2,'0')+'.png')});
  await page.screenshot({path:path.join(output,'project-graph.png')});await frame();
  await page.locator('[data-node-id="EXP-0005"]').hover();
  assert.equal(await page.locator('.wire.related').count(),2);
  await frame();
  await page.locator('[data-node-id="EXP-0006"]').click();
  await page.locator('.result-table').waitFor();
  await page.screenshot({path:path.join(output,'experiment-results.png')});await frame();
  await page.locator('#detail').getByRole('button',{name:'关闭',exact:true}).click();
  await page.getByRole('button',{name:'探索看板',exact:true}).click();
  assert.equal(await page.locator('.column').count(),3);
  await page.screenshot({path:path.join(output,'plan-board.png')});await frame();
  await page.getByRole('textbox',{name:'搜索',exact:true}).fill('1');
  assert.deepEqual(await page.locator('.board .node-id').allTextContents(),['PLAN-0001']);await frame();
  await page.getByRole('textbox',{name:'搜索',exact:true}).fill('');
  await page.getByRole('button',{name:'参考资料',exact:true}).click();
  await page.screenshot({path:path.join(output,'reference-library.png')});
  assert.deepEqual(errors,[]);
  console.log('Captured real graph, incoming highlight, results, board, numeric search and reference library; machine path hidden; fictional demo data only');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
