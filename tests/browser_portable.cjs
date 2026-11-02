const assert=require('node:assert/strict');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE);
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.argv[2]);
  await page.locator('[data-node-id="root"]').waitFor();
  assert.equal(await page.locator('#diagnostics').isVisible(),false);
  await page.getByRole('button',{name:'探索看板',exact:true}).click();
  assert.equal(await page.locator('.column').count(),3);
  assert.equal(await page.locator('.card').count(),0);
  await page.screenshot({path:process.argv[3]});
  assert.deepEqual(errors,[]);
  console.log('PASS: frozen portable app renders empty project in browser');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
