const assert=require('node:assert/strict');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(process.argv[2]);
    await page.locator('[data-node-id="PLAN-0001"]').waitFor();
    assert.equal(await page.locator('#diagnostics').isVisible(),false);
    await page.getByRole('button',{name:'探索看板',exact:true}).click();
    assert.equal(await page.locator('.column').count(),3);
    assert.equal(await page.locator('.card').count(),1);
    await page.locator('.card').click();
    await page.locator('#detail').waitFor({state:'visible'});
    assert.ok((await page.locator('#detail-content').innerText()).includes('空项目安装验证'));
    await page.locator('#detail').getByRole('button',{name:'关闭',exact:true}).click();
    await page.screenshot({path:process.argv[3]});
    assert.deepEqual(errors,[]);
    console.log('PASS: installed graph, state columns and record dialog render without page errors');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
