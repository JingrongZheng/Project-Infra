// Browser-only fixture: no synthetic records are written into the project.
const assert=require('node:assert/strict');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8766/');
    await page.locator('[data-node-id="PLAN-0001"]').waitFor();
    await page.getByRole('button',{name:'探索看板',exact:true}).click();
    const fixture=await (await page.request.get('http://127.0.0.1:8766/api/state')).json();
    fixture.objects=Array.from({length:48},(_,i)=>({kind:'plan',path:'.project/plans/PLAN-'+i+'.md',revision:'browser-only',
      meta:{id:'PLAN-'+String(i+1).padStart(4,'0'),title:'浏览器夹具 '+(i+1),summary:'引用 PLAN-0001 EXP-0001 不应导致编号误匹配。',status:i<30?'active':i<46?'paused':'closed'},sections:{Synthesis:'这里也引用 PLAN-0001'}}));
    fixture.objects.push(...[1,10,11].map(i=>({kind:'experiment',path:'fixture',revision:'browser-only',meta:{id:'EXP-'+String(i).padStart(4,'0'),title:'实验夹具 '+i,summary:'引用 PLAN-0001',status:'active'},sections:{}})));
    await page.route('**/api/state',route=>route.fulfill({json:fixture}));
    await page.getByRole('button',{name:'↻ 刷新',exact:true}).click();
    await page.waitForFunction(()=>document.querySelectorAll('.board .card').length===48);
    const lists=page.locator('.column-items');
    assert.equal(await lists.count(),3);
    const metrics=await lists.evaluateAll(es=>es.map(e=>({height:e.clientHeight,total:e.scrollHeight})));
    assert.ok(metrics[0].total>metrics[0].height);
    assert.ok(metrics[1].total>metrics[1].height);
    assert.ok(metrics[0].height>100,JSON.stringify(metrics));
    await lists.nth(0).hover();await page.mouse.wheel(0,600);
    await page.waitForFunction(()=>document.querySelector('.column-items').scrollTop>0);
    assert.equal(await lists.nth(1).evaluate(e=>e.scrollTop),0);
    assert.equal(await page.evaluate(()=>window.scrollY),0);
    const first=await lists.nth(0).evaluate(e=>e.scrollTop);
    await lists.nth(1).hover();await page.mouse.wheel(0,350);
    await page.waitForFunction(()=>document.querySelectorAll('.column-items')[1].scrollTop>0);
    assert.equal(await lists.nth(0).evaluate(e=>e.scrollTop),first);
    await page.getByRole('button',{name:'↻ 刷新',exact:true}).click();
    await page.waitForTimeout(150);
    assert.equal(await lists.nth(0).evaluate(e=>e.scrollTop),first);
    const search=page.getByRole('textbox',{name:'搜索',exact:true});
    for(const value of ['1','001','PLAN-0001',' plan-1 ']){
      await search.fill(value);
      assert.deepEqual(await page.locator('.board .node-id').allTextContents(),['PLAN-0001']);
    }
    for(const value of ['EXP-0001','浏览器夹具','引用','999']){
      await search.fill(value);assert.equal(await page.locator('.board .card').count(),0);
    }
    await search.fill('1');
    await page.getByRole('button',{name:'实验记录',exact:true}).click();
    assert.deepEqual(await page.locator('.object-list .node-id').allTextContents(),['EXP-0001']);
    await search.fill('10');
    assert.deepEqual(await page.locator('.object-list .node-id').allTextContents(),['EXP-0010']);
    await search.fill('PLAN-0001');assert.equal(await page.locator('.object-list .card').count(),0);
    await search.fill('');assert.equal(await page.locator('.object-list .card').count(),3);
    assert.deepEqual(errors,[]);
    console.log('PASS: uneven 30/16/2 Plan columns scroll independently, page stays still, scroll survives refresh; exact numeric-ID filtering ignores references, text, other kinds and 10/11 when searching 1');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
