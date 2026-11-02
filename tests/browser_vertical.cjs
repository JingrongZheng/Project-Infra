const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8766/');
    await page.locator('[data-node-id="PLAN-0001"]').waitFor();
    const state=await (await page.request.get('http://127.0.0.1:8766/api/state')).json();
    const points=await page.locator('.circuit-node').evaluateAll(es=>Object.fromEntries(es.map(e=>[e.dataset.nodeId,{x:parseFloat(e.style.left),y:parseFloat(e.style.top)}])));
    const mains=state.mainline.map(n=>points['main:'+n.id]);
    assert.ok(mains.every(p=>p.x===mains[0].x));
    for(const n of state.mainline)for(const parent of n.after||[])assert.ok(points['main:'+n.id].y>points['main:'+parent].y);
    for(const o of state.objects.filter(o=>o.kind==='experiment')){
      assert.ok(points[o.meta.id].y>points[o.meta.plan].y);
      for(const parent of o.meta.predecessors||[])assert.ok(points[o.meta.id].y>points[parent].y);
    }
    assert.ok(points['PLAN-0002'].x>points['main:views'].x);
    assert.ok(points['PLAN-0002'].y<points['PLAN-0003'].y);
    assert.equal(await page.locator('.graph-routing-warning').count(),0);
    const dest=path.resolve('.project/experiments/EXP-0010.assets');fs.mkdirSync(dest,{recursive:true});
    await page.screenshot({path:path.join(dest,'after.png')});
    await page.getByRole('button',{name:'适应全图',exact:true}).click();
    await page.screenshot({path:path.join(dest,'overview.png')});
    await page.getByRole('button',{name:'定位进行中',exact:true}).click();
    await page.screenshot({path:path.join(dest,'focused.png')});
    await page.locator('[data-node-id="PLAN-0001"]').click();
    await page.locator('#detail').waitFor({state:'visible'});
    assert.ok((await page.locator('#detail-id').innerText()).includes('PLAN-0001'));
    assert.deepEqual(errors,[]);
    console.log('PASS: one vertical design spine, experiments move downward, parallel lanes branch sideways, Plan bands separated, pan/zoom/details retained; readability still needs user feedback');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
