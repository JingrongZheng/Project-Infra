// Real UI prerequisite failure and completion; content explicitly remains a protocol fixture.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
const [url,output]=process.argv.slice(2);
if(!url||!output)throw Error('Usage: node tests/browser_execution.cjs FRESH_DEMO_URL OUTPUT');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 fs.mkdirSync(output,{recursive:true});
 try{
  await page.goto(url);await page.waitForFunction(()=>typeof state!=='undefined'&&state?.objects?.length);
  const initial=await page.evaluate(()=>state.objects.find(o=>o.meta.id==='PLAN-0001'));
  assert(initial.sections['Execution plan'].includes('- [ ] **共享实现整理**'));
  await page.evaluate(()=>showObject('PLAN-0001'));
  await page.getByRole('button',{name:'交付检查 · 无独立审查'}).click();
  await page.waitForFunction(()=>document.querySelector('#toast').textContent.includes('先执行'));
  assert.equal(await page.evaluate(()=>state.objects.find(o=>o.meta.id==='PLAN-0001').revision),initial.revision);
  await page.screenshot({path:path.join(output,'blocked-delivery.png')});
  await page.getByRole('button',{name:'编辑内容',exact:true}).click();
  const field=page.locator('#detail-content label').filter({hasText:/^Execution plan/}).locator('textarea');
  const steps=await field.inputValue();
  await field.fill(steps.replace(/^\s*- \[ \] \*\*共享实现整理\*\*.*$/m,
   '- [x] **共享实现整理**：结果：这是 UI 协议测试，无业务代码修改，不代表实际项目整理完成。'));
  await page.getByRole('button',{name:'保存到项目文件',exact:true}).click();
  await page.getByRole('button',{name:'交付检查 · 无独立审查'}).waitFor();
  await page.getByRole('button',{name:'交付检查 · 无独立审查'}).click();
  await page.waitForFunction(()=>document.querySelector('#detail-content').textContent.includes('未执行独立审查'));
  await page.locator('[data-section="Execution plan"]').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(output,'recorded-step.png')});
  assert.deepEqual(errors,[]);
  console.log('PASS: actual UI rejects incomplete shared step without writing, edits the step/result, then permits delivery with explicit reviewer-unavailable disclosure');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
