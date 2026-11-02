const assert=require('node:assert/strict');
const path=require('node:path');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8766/');
    await page.getByRole('button',{name:'实验记录',exact:true}).click();
    await page.getByRole('button',{name:/EXP-0008 验证结果/}).click();
    await page.locator('.result-gallery img').evaluate(img=>img.decode());
    assert.equal(await page.locator('.result-gallery img').count(),1);
    assert.equal(await page.locator('.results-showcase .evidence-grid').count(),0);
    assert.equal(await page.locator('.result-table tr').count(),3);
    assert.ok((await page.locator('.results-showcase').innerText()).includes('非真实实验指标'));
    assert.equal(await page.getByRole('button',{name:'查看结果',exact:true}).count(),1);
    await page.locator('.results-showcase').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.resolve('.project/experiments/EXP-0008.assets/results-ui.png')});
    await page.getByRole('button',{name:'编辑内容',exact:true}).click();
    assert.equal(await page.getByLabel('修改前证据路径',{exact:true}).count(),0);
    assert.equal(await page.getByLabel('修改后证据路径',{exact:true}).count(),0);
    assert.ok((await page.getByLabel('结果文件或链接',{exact:true}).inputValue()).includes('metrics-comparison.png'));
    assert.equal(await page.locator('.optional-comparison').getAttribute('open'),null);
    await page.locator('#detail').getByRole('button',{name:'关闭',exact:true}).click();
    await page.getByRole('button',{name:'探索看板',exact:true}).click();
    await page.getByRole('button',{name:/PLAN-0001 验证文件驱动/}).click();
    await page.getByRole('button',{name:/⇄ EXP-0008/}).click();
    await page.locator('.result-gallery img').waitFor({state:'visible'});
    await page.getByRole('button',{name:'审查上下文',exact:true}).click();
    assert.ok((await page.locator('.context-text').inputValue()).includes('metrics-comparison.png'));
    assert.deepEqual(errors,[]);
    console.log('PASS: one image contains multiple comparisons; CSV table renders; no forced before/after fields; editor, Plan index and context work; no script errors');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
