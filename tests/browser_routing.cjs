const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    const url=process.env.INFRA_ROUTING_URL||'http://127.0.0.1:8766/';
    await page.goto(url);
    // A straight vertical SVG path has zero bounding-box width in Playwright.
    await page.locator('path.wire').first().waitFor({state:'attached'});
    assert.equal(await page.locator('.graph-routing-warning').count(),0);
    const failures=await page.evaluate(()=>{
      const canvas=document.querySelector('.graph-canvas'),rect=canvas.getBoundingClientRect();
      const scale=new DOMMatrix(getComputedStyle(canvas).transform).a;
      const nodes=[...canvas.querySelectorAll('.circuit-node')].map(e=>{
        const a=e.querySelector('.circuit-pad').getBoundingClientRect(),b=e.querySelector('.circuit-label').getBoundingClientRect();
        return {id:e.dataset.nodeId,left:Math.min(a.left,b.left),right:Math.max(a.right,b.right),top:Math.min(a.top,b.top),bottom:Math.max(a.bottom,b.bottom)};
      });
      const issues=[];
      for(const edge of canvas.querySelectorAll('path.wire')){
        const points=JSON.parse(edge.dataset.route).map(p=>({x:rect.left+p.x*scale,y:rect.top+p.y*scale}));
        for(const n of nodes)if(n.id!==edge.dataset.from&&n.id!==edge.dataset.to){
          for(let i=1;i<points.length;i++){
            const a=points[i-1],b=points[i];
            const hit=Math.abs(a.x-b.x)<.1?a.x>n.left+.1&&a.x<n.right-.1&&Math.max(a.y,b.y)>n.top+.1&&Math.min(a.y,b.y)<n.bottom-.1:
              a.y>n.top+.1&&a.y<n.bottom-.1&&Math.max(a.x,b.x)>n.left+.1&&Math.min(a.x,b.x)<n.right-.1;
            if(hit)issues.push(edge.dataset.from+'->'+edge.dataset.to+' crosses '+n.id);
          }
        }
      }
      return issues;
    });
    assert.deepEqual(failures,[]);
    await page.getByRole('button',{name:'适应全图',exact:true}).click();
    if(!process.env.INFRA_ROUTING_URL)for(let i=0;i<2;i++)await page.getByRole('button',{name:'＋',exact:true}).click();
    const plan=await page.locator('.circuit-node.plan').all();
    const selected=await (plan.length>1?plan[1]:plan[0]).getAttribute('data-node-id');
    await (plan.length>1?plan[1]:plan[0]).hover();
    const related=await page.locator('path.wire.related').evaluateAll(es=>es.map(e=>({from:e.dataset.from,to:e.dataset.to})));
    assert.ok(related.some(e=>e.to===selected));
    assert.ok(related.every(e=>e.to===selected));
    const dest=path.resolve(process.env.INFRA_ROUTING_URL?'.work/routing-fixture':'.work/routing-checks');fs.mkdirSync(dest,{recursive:true});
    await page.screenshot({path:path.join(dest,'after.png')});
    assert.deepEqual(errors,[]);
    console.log('PASS: measured real DOM labels and nodes never crossed by unrelated wires; direct design->Plan edge, directional arrows, true-neighbor hover, no routing warnings');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
