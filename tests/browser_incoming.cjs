const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {chromium}=require(process.env.INFRA_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(process.env.INFRA_ROUTING_URL||'http://127.0.0.1:8766/');
    await page.locator('path.wire').first().waitFor({state:'attached'});
    const report=await page.evaluate(()=>{
      const svg=document.querySelector('.graph-canvas svg'),wires=[...svg.querySelectorAll('path.wire')];
      const key=p=>p.dataset.from+'->'+p.dataset.to,failures=[];
      for(const node of document.querySelectorAll('.circuit-node')){
        node.dispatchEvent(new MouseEvent('mouseenter'));
        const expected=wires.filter(p=>p.dataset.to===node.dataset.nodeId).map(key).sort();
        const actual=[...svg.querySelectorAll('.wire.related')].map(key).sort();
        if(JSON.stringify(expected)!==JSON.stringify(actual))failures.push(node.dataset.nodeId+' input mismatch');
        if(getComputedStyle(svg.querySelector('.wire-crossings')).display!=='none')failures.push('crossing overlays cover hover');
        const order=[...svg.children],chosen=wires.filter(p=>p.classList.contains('related'));
        if(chosen.some(p=>wires.some(q=>!q.classList.contains('related')&&order.indexOf(q)>order.indexOf(p))))failures.push('incoming trace is behind another wire');
        if(wires.some(p=>!p.getAttribute('marker-end')))failures.push('missing arrow');
        node.dispatchEvent(new MouseEvent('mouseleave'));
      }
      if(svg.querySelector(':scope > .wire-halo'))failures.push('full-path erase halo remains');
      return {failures,nodes:document.querySelectorAll('.circuit-node').length};
    });
    assert.deepEqual(report.failures,[]);
    const target=page.locator('[data-node-id="EXP-0007"]');
    if(await target.count()){
      await target.evaluate(node=>{
        const canvas=node.closest('.graph-canvas'),vp=canvas.parentElement;
        canvas.style.transform=`translate(${vp.clientWidth/2-parseFloat(node.style.left)}px,${vp.clientHeight*.65-parseFloat(node.style.top)}px) scale(1)`;
        node.dispatchEvent(new MouseEvent('mouseenter'));
      });
      const dest=path.resolve('.work/incoming-checks');fs.mkdirSync(dest,{recursive:true});
      await page.screenshot({path:path.join(dest,'incoming.png')});
    }
    assert.deepEqual(errors,[]);
    console.log(`PASS: all ${report.nodes} nodes highlight exactly incoming edges; outgoing edges stay dim; complete inputs paint above background; no full-path erase halos; arrows retained`);
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
