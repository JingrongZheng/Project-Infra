// Real DOM workflow against an isolated fictional demo; fixture notes are not model reviews.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
const [url,project,output]=process.argv.slice(2);
if(!url||!project||!output)throw Error('Usage: node tests/browser_reviewer.cjs URL PROJECT OUTPUT');
const root=path.resolve(project),dest=path.resolve(output);
fs.mkdirSync(dest,{recursive:true});
function cli(...args){return execFileSync(process.env.INFRA_TEST_PYTHON||'python',['-m','project_infra','--root',root,...args],{encoding:'utf8'}).trim();}
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  cli('reviewer','disable','--reason','UI fixture startup self-check pending');
  const historyDir=path.join(root,'.project/reviews/PLAN-0001');const before=fs.existsSync(historyDir)?fs.readdirSync(historyDir).length:0;
  await page.goto(url);await page.waitForFunction(()=>document.querySelector('#reviewer-capability').textContent.includes('已关闭'));
  await page.addStyleTag({content:'#root{visibility:hidden}'});
  await page.screenshot({path:path.join(dest,'reviewer-disabled.png')});
  await page.evaluate(()=>showObject('PLAN-0001'));
  await page.getByRole('button',{name:'交付检查 · 无独立审查'}).click();
  await page.waitForFunction(()=>document.querySelector('#detail-content').textContent.includes('未执行独立审查'));
  const probe=JSON.parse(cli('reviewer','probe','--label','browser protocol fixture','--timeout','120'));
  const request=JSON.parse(fs.readFileSync(path.join(root,probe.request),'utf8'));
  const response=path.join(root,probe.response);
  fs.writeFileSync(response,JSON.stringify({nonce:request.nonce,independent:true,session:'browser-fixture-not-a-model'}));
  cli('reviewer','accept','--response',response);
  await page.evaluate(()=>refresh());
  await page.waitForFunction(()=>document.querySelector('#reviewer-capability').textContent.includes('质疑者可用'));
  await page.getByRole('button',{name:'发起交付审查'}).click();
  await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('独立会话'));
  assert.equal(fs.existsSync(historyDir)?fs.readdirSync(historyDir).length:0,before,'Pending review must not be completed');
  const active=JSON.parse(fs.readFileSync(path.join(root,'.work/reviewer/active/PLAN-0001.json'),'utf8'));
  const round=path.basename(active.archive,'.md');
  const note=path.join('.work/reviews/PLAN-0001',round,'NOTE.md');
  fs.writeFileSync(path.join(root,note),'Reviewer: browser fixture, not a real model review\n\n## 已核查\nActual UI and protocol fixture only.\n\n## 主要疑点\nNo production method was reviewed.\n');
  cli('review','PLAN-0001','--record',note);
  await page.evaluate(()=>refresh());
  await page.waitForFunction(()=>document.querySelector('#detail-content').textContent.includes('browser fixture'));
  assert(fs.existsSync(path.join(root,active.archive)));
  await page.locator('[data-section="Review"]').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(dest,'reviewer-round.png')});
  assert.deepEqual(errors,[]);
  console.log('PASS: disabled notice, explicit unreviewed delivery, host capability, pending handoff, archived review and actual DOM update');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
