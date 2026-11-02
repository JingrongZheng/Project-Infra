// Optional visual and interaction checks against the real, read-only workspace.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:900}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8766/');
    await page.locator('[data-node-id="PLAN-0001"]').waitFor();
    await page.locator('.sidebar-art img').evaluate(img=>img.decode());
    assert.equal(await page.locator('.sidebar-art').getAttribute('aria-hidden'),'true');
    assert.ok(await page.locator('.sidebar-art img').evaluate(img=>img.naturalWidth>0));
    assert.equal(await page.locator('.sidebar-art img').getAttribute('src'),'/facets.svg');
    assert.equal(await page.locator('img[src*="observer"]').count(),0);
    assert.equal(await page.getByText('THE OBSERVER',{exact:true}).count(),0);
    assert.equal(await page.locator('#stats').count(),0);
    assert.equal(await page.locator('.circuit-node .node-summary').count(),0);
    assert.equal(await page.locator('.sidebar-art').evaluate(e=>getComputedStyle(e).pointerEvents),'none');
    const dark=await page.locator('body').evaluate(e=>getComputedStyle(e).backgroundColor);
    assert.equal(dark,'rgb(11, 17, 25)');
    // Reference images inspire faceting only, not human subjects or a new red palette.
    const palette=await page.evaluate(()=>({
      nav:getComputedStyle(document.querySelector('.sidebar')).backgroundColor,
      button:getComputedStyle(document.querySelector('#new')).backgroundColor,
      trunk:getComputedStyle(document.querySelector('.wire.trunk')).stroke,
      experiment:getComputedStyle(document.querySelector('.wire.lineage')).stroke,
      active:getComputedStyle(document.querySelector('.circuit-node.current')).color,
      activeLegend:getComputedStyle(document.querySelector('.legend-current')).color,
      designNode:getComputedStyle(document.querySelector('.circuit-node.mainline')).color
    }));
    assert.deepEqual(palette,{nav:'rgb(13, 21, 30)',button:'rgb(40, 110, 101)',trunk:'rgb(101, 216, 191)',experiment:'rgb(117, 182, 225)',active:'rgb(217, 232, 162)',activeLegend:'rgb(217, 232, 162)',designNode:'rgb(101, 216, 191)'});
    const dest=path.resolve('.work/visual-checks');fs.mkdirSync(dest,{recursive:true});
    await page.screenshot({path:path.join(dest,'after.png')});
    const initial=await page.locator('.graph-canvas').getAttribute('style');
    const viewport=await page.locator('.graph-viewport').boundingBox();
    await page.mouse.move(viewport.x+120,viewport.y+160);
    await page.mouse.down();await page.mouse.move(viewport.x+210,viewport.y+210,{steps:10});await page.mouse.up();
    assert.notEqual(await page.locator('.graph-canvas').getAttribute('style'),initial);
    await page.getByRole('button',{name:'定位进行中',exact:true}).click();
    await page.locator('[data-node-id="PLAN-0001"]').click();
    await page.locator('#detail').waitFor({state:'visible'});
    assert.ok((await page.locator('#detail-content').innerText()).includes('Question'));
    await page.locator('#detail').getByRole('button',{name:'关闭',exact:true}).click();
    // Regression: After evidence must read meta.after, not experiment predecessors.
    await page.getByRole('button',{name:'实验记录',exact:true}).click();
    await page.getByRole('button',{name:/EXP-0003/}).click();
    await page.locator('.evidence-box img').last().evaluate(img=>img.decode());
    assert.equal(await page.locator('.evidence-box img').count(),2);
    assert.equal(await page.locator('.evidence-box .error').count(),0);
    await page.locator('#detail').getByRole('button',{name:'关闭',exact:true}).click();
    await page.getByRole('button',{name:'探索看板',exact:true}).click();
    assert.equal(await page.locator('.column').count(),4);
    await page.getByRole('button',{name:'参考资料',exact:true}).click();
    assert.ok(await page.locator('.ref').count()>0);
    await page.getByRole('button',{name:'项目脉络',exact:true}).click();
    await page.setViewportSize({width:390,height:844});
    await page.reload();await page.locator('[data-node-id="PLAN-0001"]').waitFor();
    const width=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth}));
    assert.ok(width.scroll<=width.client,JSON.stringify(width));
    assert.equal(await page.locator('.sidebar-art').isVisible(),false);
    await page.getByRole('button',{name:'定位进行中',exact:true}).click();
    assert.equal(await page.locator('.zoom-value').innerText(),'100%');
    await page.screenshot({path:path.join(dest,'mobile.png')});
    assert.deepEqual(errors,[]);
    console.log('PASS: abstract facets, no Observer, original navy/teal/blue/violet palette, noninteractive decor, desktop/mobile, pan/focus/details, boards/library, paired evidence, no page errors');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
