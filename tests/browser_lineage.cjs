// Optional real-browser smoke test. Only writes into the isolated fixture on port 8767.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:900}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8767/');
    await page.locator('[data-node-id="EXP-0006"]').waitFor();
    const incoming=await page.locator('path.wire.lineage[data-to="EXP-0005"]').count();
    assert.equal(incoming,3);
    assert.equal(await page.locator('path.wire.lineage[data-from="EXP-0001"]').count(),2);
    assert.equal(await page.locator('.circuit-node.task').count(),0);
    const a=await page.locator('[data-node-id="EXP-0001"]').evaluate(e=>e.style.top);
    const c=await page.locator('[data-node-id="EXP-0003"]').evaluate(e=>e.style.top);
    assert.ok(parseFloat(c)>parseFloat(a));
    await page.getByRole('button',{name:'适应全图',exact:true}).click();
    const dest=path.resolve('.work/lineage-checks');fs.mkdirSync(dest,{recursive:true});
    await page.screenshot({path:path.join(dest,'lineage-fixture.png')});
    // Clicking an experiment exposes only the relevant predecessor/successor links.
    await page.locator('[data-node-id="EXP-0003"]').click();
    await page.getByRole('button',{name:'从这里继续实验',exact:true}).click();
    const form=page.locator('#create-form');
    assert.equal(await form.locator('.predecessor-picker input:checked').inputValue(),'EXP-0003');
    await form.locator('[name="title"]').fill('测试：从 C 接续并汇合 B');
    await form.locator('.predecessor-picker input[value="EXP-0002"]').check();
    await form.getByRole('button',{name:'创建并打开',exact:true}).click();
    await page.locator('#detail-id').filter({hasText:'EXP-0007 / 编辑'}).waitFor();
    assert.equal(await page.locator('#detail .predecessor-picker input:checked').count(),2);
    await page.getByRole('button',{name:'保存到项目文件',exact:true}).click();
    await page.locator('#detail-id').filter({hasText:/^EXP-0007$/}).waitFor();
    assert.equal(await page.locator('#detail .relation-link').count(),2);
    await page.locator('#detail').getByRole('button',{name:'关闭',exact:true}).click();
    assert.equal(await page.locator('path.wire.lineage[data-to="EXP-0007"]').count(),2);
    // Edit to a single predecessor and confirm projection uses the saved relation.
    await page.getByRole('button',{name:'定位进行中',exact:true}).click();
    await page.locator('[data-node-id="EXP-0006"]').click();
    await page.getByRole('button',{name:'编辑内容',exact:true}).click();
    const options=await page.locator('#detail .predecessor-picker input').evaluateAll(es=>es.map(e=>e.value));
    assert.ok(!options.includes('EXP-0006'));
    await page.locator('#detail .predecessor-picker input[value="EXP-0005"]').uncheck();
    await page.locator('#detail .predecessor-picker input[value="EXP-0004"]').check();
    await page.getByRole('button',{name:'保存到项目文件',exact:true}).click();
    await page.locator('#detail-id').filter({hasText:/^EXP-0006$/}).waitFor();
    await page.locator('#detail').getByRole('button',{name:'关闭',exact:true}).click();
    assert.equal(await page.locator('path.wire.lineage[data-from="EXP-0004"][data-to="EXP-0006"]').count(),1);
    assert.equal(await page.locator('path.wire.lineage[data-from="EXP-0005"][data-to="EXP-0006"]').count(),0);
    assert.deepEqual(errors,[]);
    // The user's real project is read-only during this test.
    await page.goto('http://127.0.0.1:8766/');
    await page.locator('[data-node-id="PLAN-0001"]').waitFor();
    await page.getByRole('button',{name:'适应全图',exact:true}).click();
    await page.screenshot({path:path.join(dest,'after.png')});
    assert.deepEqual(errors,[]);
    console.log('PASS: actual rendered fork/merge edges, continuation defaults, multi-source create, relation editing, no forced Task, real homepage, no page errors');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
