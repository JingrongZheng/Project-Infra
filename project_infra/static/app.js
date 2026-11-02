/* Project files -> live views. All human edits go back through validated commands. */
const $ = s => document.querySelector(s);
const el = (tag, cls, text) => {const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
const names={draft:'草案',active:'进行中',paused:'暂停',closed:'已结束',ready:'待执行'};
const kinds={plan:'Plan',experiment:'Experiment',proposal:'Proposal'};
let state, view='graph', query='', dirty=false, editing=false, detailRender=0;
const dialog=$('#detail');
function toast(text){const t=$('#toast');t.textContent=text;t.hidden=false;setTimeout(()=>t.hidden=true,4500);}
async function api(path, body){const response=await fetch(path,body?{method:'POST',headers:{'Content-Type':'application/json','X-Infra-Token':state.token},body:JSON.stringify(body)}:{});const result=await response.json();if(!response.ok)throw Error(result.error||'请求失败');return result;}
const byId=id=>state.objects.find(o=>o.meta.id===id);
// Numeric identity search: 1, 001 and PLAN-0001 refer to the same number.
function matchesId(id){
  const input=query.trim();if(!input)return true;
  const wanted=/^(?:(PLAN|EXP|PROP|REF)-)?(\d+)$/i.exec(input);
  const actual=/^(PLAN|EXP|PROP|REF)-(\d+)$/i.exec(id||'');
  return !!wanted&&!!actual&&(!wanted[1]||wanted[1].toUpperCase()===actual[1].toUpperCase())&&Number(wanted[2])===Number(actual[2]);
}
const filtered=o=>matchesId(o.meta.id);
const boardScroll=new Map();
const statusBadge=status=>el('span','badge '+status,names[status]||status||'—');
function reviewText(o){return o.sections.Review||'';}
async function refresh(){try{state=await api('/api/state');$('#root').textContent=state.root;$('#connection').textContent='● 已连接 · 文件自动同步';const d=$('#diagnostics');d.hidden=!state.errors.length;d.textContent=(state.stale?'当前文件存在错误，暂显示上次有效视图。\n':'')+state.errors.join('\n');render();if(dialog.open&&!editing){const id=$('#detail-id').textContent;if(byId(id)&&dialog.dataset.objectRevision!==byId(id).revision)await showObject(id);}}catch(e){$('#connection').textContent='● 连接中断';toast(e.message);}}
function render(){
  if(!state)return;
  const titles={graph:['项目脉络','从设计主干出发，沿分支查看探索、验证与采用的设计。'],plans:['探索看板','围绕问题推进探索，保留每次尝试的理由。'],experiments:['实验记录','具体尝试、数据指标、结果图表与验证结论。'],proposals:['方向收件箱','先留下值得考虑的方向，再决定是否探索。'],library:['参考资料','论文、手册与链接；按需要深入阅读。']};
  document.body.classList.toggle('graph-view',view==='graph');
  document.body.classList.toggle('plans-view',view==='plans');
  $('#heading').textContent=titles[view][0];$('#subtitle').textContent=titles[view][1];
  $('#breadcrumb').textContent=view.toUpperCase();
  document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('selected',b.dataset.view===view));
  const content=$('#content');content.replaceChildren();
  $('#view-note').textContent=view==='graph'?'拖动画布 · 滚轮缩放 · 点击节点展开':view==='library'?'资料索引 · 支持本地文档与外部链接':'点击工作项编辑 · 拖动变更状态';
  if(view==='graph')renderGraph(content);else if(view==='plans')renderBoard(content,'plan');else if(view==='experiments'||view==='proposals')renderList(content,view==='experiments'?'experiment':'proposal');else renderLibrary(content);
}
function card(o){const c=el('button','card');c.append(el('div','node-id',o.meta.id),el('div','card-title',o.meta.title),el('div','card-summary',o.meta.summary||'尚未填写摘要 · 点击展开'));if(reviewText(o)){c.append(el('div','card-foot','◇ 已有审查记录'));}c.onclick=()=>showObject(o.meta.id);return c;}
function renderBoard(host,kind){
  const board=el('div','board'),scrolls=[];
  board.style.setProperty('--board-columns',state.states[kind].length);
  for(const status of state.states[kind]){
    const col=el('div','column'),items=el('div','column-items');
    const key=kind+':'+status,objects=state.objects.filter(o=>o.kind===kind&&o.meta.status===status&&filtered(o));
    const title=el('div','column-title',names[status]);title.append(el('span','',objects.length));
    items.tabIndex=0;items.setAttribute('aria-label',names[status]+'列表');
    items.onscroll=()=>boardScroll.set(key,items.scrollTop);scrolls.push([items,key]);
    for(const o of objects){const c=card(o);c.draggable=true;c.ondragstart=e=>e.dataTransfer.setData('text/plain',o.meta.id);items.append(c);}
    col.append(title,items);
    col.ondragover=e=>{e.preventDefault();col.classList.add('dragover');};
    col.ondragleave=()=>col.classList.remove('dragover');
    col.ondrop=async e=>{
      e.preventDefault();col.classList.remove('dragover');
      const obj=byId(e.dataTransfer.getData('text/plain'));
      if(!obj||obj.kind!==kind||obj.meta.status===status)return;
      if(status==='closed'){showObject(obj.meta.id,true);toast('请填写结论与验收记录，再保存为已结束。');return;}
      try{const fields={status};if(kind==='plan')fields.resolution=null;await api('/api/update',{path:obj.path,revision:obj.revision,fields});await refresh();}catch(err){toast(err.message);}
    };
    board.append(col);
  }
  host.append(board);for(const [items,key]of scrolls)items.scrollTop=boardScroll.get(key)||0;
}
function renderList(host,kind='proposal'){const list=el('div','object-list');state.objects.filter(o=>o.kind===kind&&filtered(o)).forEach(o=>list.append(card(o)));if(!list.children.length)list.append(el('div','empty','没有匹配的记录。'));host.append(list);}
function safeURL(url){return /^https?:\/\//i.test(url);}
function artifactURL(path){return '/api/artifact?path='+encodeURIComponent(path);}
function renderLibrary(host){const list=el('div','object-list');for(const ref of state.library.filter(r=>matchesId(r.id))){const c=el('div','ref');c.append(el('small','',ref.id+' / '+(ref.kind||'参考')),el('h3','',ref.title),el('p','',(ref.tags||[]).join(' · ')));const a=el('a','',ref.location);a.href=safeURL(ref.location)?ref.location:artifactURL('library/'+ref.location);a.target='_blank';a.rel='noopener noreferrer';c.append(a);list.append(c);}if(!list.children.length)list.append(el('div','empty','还没有参考资料。'));host.append(list);const edit=el('button','quiet','编辑资料索引');edit.onclick=()=>editRaw('library/index.toml');host.append(edit);}

const {layoutExperiments,separateNodes,routeConnections,wireCrossings}=ProjectGraph;
const graphCamera={x:0,y:0,scale:1,initialized:false};
function renderGraph(host){
  const shell=el('div','graph-shell'), viewport=el('div','graph-viewport');
  viewport.tabIndex=0;viewport.setAttribute('aria-label','项目脉络画布，可拖动、缩放；方向键移动，0适应全图');
  const canvas=el('div','graph-canvas');
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  canvas.append(svg);viewport.append(canvas);shell.append(viewport);host.append(shell);
  const positions=new Map(), edges=[], placed=new Set(), main=state.mainline;
  const types={plan:'探索',experiment:'实验',proposal:'方向'};
  const nodes=[], depthMemo=new Map();
  function depth(n){if(depthMemo.has(n.id))return depthMemo.get(n.id);depthMemo.set(n.id,0);const d=Math.max(0,...(n.after||[]).map(id=>{const p=main.find(x=>x.id===id);return p?depth(p)+1:0;}));depthMemo.set(n.id,d);return d;}
  const rootTitle=((state.project?.body||'').match(/^# (.+)$/m)||[])[1]||'当前项目';
  function add(id,x,y,title,type,open,status='',meta=''){
    positions.set(id,{x,y});nodes.push({id,x,y,title,type,open,status,meta});placed.add(id);
  }
  add('root',110,80,rootTitle,'root',()=>editRaw('PROJECT.md'),'','项目');
  function link(from,to,type='branch'){if(from&&from!==to)edges.push({from,to,type});}
  function object(o,x,y,label){
    add(o.meta.id,x,y,o.meta.title,o.kind,()=>showObject(o.meta.id),o.meta.status,label||types[o.kind]);
    if(reviewText(o)){
      const rid='review:'+o.meta.id;
      add(rid,x+320,y+100,'审查记录','review',()=>showObject(o.meta.id,false,'Review'),'','按需审查');
      link(o.meta.id,rid,'review');
    }
  }
  // Vertical stages: the next design starts only after this stage's exploration bands.
  const levels=new Map();
  for(const n of main){const d=depth(n);if(!levels.has(d))levels.set(d,[]);levels.get(d).push(n);}
  const mainColumns=Math.max(1,...[...levels.values()].map(group=>group.length));
  const branchX=110+(mainColumns-1)*380+400;
  const plans=state.objects.filter(o=>o.kind==='plan');
  let stageY=260;
  function planBand(p,source,y,anchored){
    const begin=nodes.length;object(p,branchX,y,anchored?'探索':'未关联设计 · 探索');link(source,p.meta.id,anchored?'branch':'unlinked');
    const experiments=(p.meta.experiments||[]).map(byId).filter(Boolean),layout=layoutExperiments(experiments);
    for(const e of experiments){const point=layout.positions.get(e.meta.id);object(e,branchX+point.x,y+point.y);if(!(e.meta.predecessors||[]).length)link(p.meta.id,e.meta.id);}
    for(const edge of layout.edges)link(edge.from,edge.to,'lineage');
    return Math.max(y+layout.height+100,...nodes.slice(begin).map(n=>n.y+180));
  }
  for(const [d,group]of [...levels].sort((a,b)=>a[0]-b[0])){
    group.sort((a,b)=>a.id.localeCompare(b.id));
    group.forEach((n,lane)=>add('main:'+n.id,110+lane*380,stageY,n.title,'mainline',()=>showDesign(n),'','设计'));
    let branchY=stageY+160;
    for(const n of group){
      for(const pred of n.after?.length?n.after:['root'])link(pred==='root'?'root':'main:'+pred,'main:'+n.id,'trunk');
      for(const p of plans.filter(p=>p.meta.design_anchor==='PROJECT.md#'+n.section))branchY=planBand(p,'main:'+n.id,branchY,true);
    }
    stageY=Math.max(stageY+240,branchY+80);
  }
  for(const p of plans.filter(p=>!placed.has(p.meta.id))){stageY=planBand(p,'root',stageY+80,false)+80;}
  let inboxY=stageY+100;
  for(const o of state.objects.filter(o=>!placed.has(o.meta.id))){
    object(o,110,inboxY,'未关联设计 · '+types[o.kind]);link('root',o.meta.id,'unlinked');inboxY+=180;
  }
  for(const n of main)for(const id of n.sources||[])if(positions.has(id))link(id,'main:'+n.id,'adopted');
  // Proposal links express origin only; they do not imply adoption into the design trunk.
  for(const p of state.objects.filter(o=>o.kind==='proposal'))
    for(const id of p.meta.plans||[])if(positions.has(id))link(p.meta.id,id,'unlinked');
  let width=Math.max(900,...nodes.map(n=>n.x+340)),height=Math.max(450,...nodes.map(n=>n.y+110));
  canvas.style.width=width+'px';canvas.style.height=height+'px';
  function highlightRelations(id){
    svg.classList.toggle('highlighting',!!id);
    for(const path of [...svg.querySelectorAll('path.wire')]){
      const incoming=!!id&&path.dataset.to===id;
      path.classList.toggle('related',incoming);
      // Paint complete incoming traces above every background trace.
      if(incoming)svg.append(path);
    }
    if(!id){const bridges=svg.querySelector('.wire-crossings');if(bridges)svg.append(bridges);}
  }
  let ignoreClick=false;
  for(const n of nodes){
    const button=el('button','circuit-node '+n.type+(n.status==='active'?' current':''));
    button.style.left=n.x+'px';button.style.top=n.y+'px';button.dataset.nodeId=n.id;
    const pad=el('span','circuit-pad'),label=el('span','circuit-label');
    const caption=el('span','circuit-caption',n.meta+(n.status?' · '+(names[n.status]||n.status):''));
    label.append(caption,el('span','circuit-title',n.title));button.append(pad,label);
    if(query&&!matchesId(n.id))button.classList.add('dimmed');
    button.onclick=()=>{if(!ignoreClick)n.open();};button.onmouseenter=()=>highlightRelations(n.id);button.onmouseleave=()=>highlightRelations(null);button.onfocus=()=>highlightRelations(n.id);button.onblur=()=>highlightRelations(null);canvas.append(button);
  }
  // Measure real labels before routing. This applies to every loaded project.
  const canvasRect=canvas.getBoundingClientRect(),buttons=[...canvas.querySelectorAll('.circuit-node')];
  const measured=nodes.map((n,i)=>{
    const rect=buttons[i].querySelector('.circuit-pad').getBoundingClientRect(),label=buttons[i].querySelector('.circuit-label').getBoundingClientRect();
    return {...n,box:{left:Math.min(rect.left,label.left)-canvasRect.left-5,right:Math.max(rect.right,label.right)-canvasRect.left+5,
      top:Math.min(rect.top,label.top)-canvasRect.top-5,bottom:Math.max(rect.bottom,label.bottom)-canvasRect.top+5}};
  });
  const separated=separateNodes(measured,34,edges);
  for(const n of separated){
    const original=nodes.find(o=>o.id===n.id);original.y=n.y;original.box=n.box;
    positions.set(n.id,{x:n.x,y:n.y});buttons.find(b=>b.dataset.nodeId===n.id).style.top=n.y+'px';
  }
  const routed=routeConnections(separated,edges),allPoints=routed.paths.flatMap(e=>e.points);
  const shiftX=Math.max(0,35-Math.min(...separated.map(n=>n.box.left),...allPoints.map(p=>p.x)));
  const shiftY=Math.max(0,60-Math.min(...separated.map(n=>n.box.top),...allPoints.map(p=>p.y)));
  width=Math.max(900,Math.max(...separated.map(n=>n.box.right),...allPoints.map(p=>p.x))+shiftX+50);
  height=Math.max(450,Math.max(...separated.map(n=>n.box.bottom),...allPoints.map(p=>p.y))+shiftY+70);
  for(const n of nodes){n.x+=shiftX;n.y+=shiftY;const button=buttons.find(b=>b.dataset.nodeId===n.id);button.style.left=n.x+'px';button.style.top=n.y+'px';}
  canvas.style.width=width+'px';canvas.style.height=height+'px';svg.setAttribute('width',width);svg.setAttribute('height',height);
  const defs=document.createElementNS(svg.namespaceURI,'defs'),marker=document.createElementNS(svg.namespaceURI,'marker');
  marker.id='graph-direction';marker.setAttribute('viewBox','0 0 10 10');marker.setAttribute('refX','9');marker.setAttribute('refY','5');marker.setAttribute('markerWidth','5');marker.setAttribute('markerHeight','5');marker.setAttribute('orient','auto');
  const arrow=document.createElementNS(svg.namespaceURI,'path');arrow.setAttribute('d','M 1 1 L 9 5 L 1 9');arrow.setAttribute('fill','none');arrow.setAttribute('stroke','#9fb7c2');arrow.setAttribute('stroke-width','1.5');marker.append(arrow);defs.append(marker);svg.append(defs);
  for(const edge of routed.paths){
    const points=edge.points.map(p=>({x:p.x+shiftX,y:p.y+shiftY}));
    const d=points.map((p,i)=>(i?'L ':'M ')+p.x+' '+p.y).join(' ');
    const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',d);path.setAttribute('class','wire '+edge.type);path.setAttribute('marker-end','url(#graph-direction)');
    path.dataset.from=edge.from;path.dataset.to=edge.to;path.dataset.route=JSON.stringify(points);
    const title=document.createElementNS(svg.namespaceURI,'title');title.textContent=edge.from+' → '+edge.to;path.append(title);svg.append(path);
  }
  // Full-path halos used to erase genuine merges and highlighted input paths.
  // Add small bridges only at actual unrelated crossings, after all base wires.
  const bridges=document.createElementNS(svg.namespaceURI,'g');bridges.setAttribute('class','wire-crossings');
  for(const cross of wireCrossings(routed.paths)){
    const x=cross.x+shiftX,y=cross.y+shiftY;
    const d=cross.horizontal?`M ${x-4} ${y} Q ${x} ${y-7} ${x+4} ${y}`:`M ${x} ${y-4} Q ${x+7} ${y} ${x} ${y+4}`;
    const halo=document.createElementNS(svg.namespaceURI,'path');halo.setAttribute('d',d);halo.setAttribute('class','wire-halo');bridges.append(halo);
    const line=document.createElementNS(svg.namespaceURI,'path');line.setAttribute('d',d);line.setAttribute('class','wire-bridge '+routed.paths[cross.over].type);bridges.append(line);
  }
  svg.append(bridges);
  if(routed.errors.length)shell.append(el('div','graph-routing-warning','部分连线未能安全布局，已隐藏以免误导。请查看项目关系或报告布局问题。'));
  const hud=el('div','graph-hud');
  hud.append(el('span','legend-trunk','━ 设计主干'),el('span','legend-branch','─ 实验脉络'),el('span','legend-current','● 进行中'),el('span','legend-unlinked','┄ 来源关联'));
  const controls=el('div','graph-controls'),percent=el('span','zoom-value');
  function apply(){canvas.style.transform=`translate(${graphCamera.x}px,${graphCamera.y}px) scale(${graphCamera.scale})`;percent.textContent=Math.round(graphCamera.scale*100)+'%';}
  function setZoom(scale,cx=viewport.clientWidth/2,cy=viewport.clientHeight/2){const next=Math.max(.12,Math.min(2.5,scale)),ratio=next/graphCamera.scale;graphCamera.x=cx-(cx-graphCamera.x)*ratio;graphCamera.y=cy-(cy-graphCamera.y)*ratio;graphCamera.scale=next;apply();}
  function fit(){const w=viewport.clientWidth,h=viewport.clientHeight;graphCamera.scale=Math.max(.12,Math.min(1,(w-110)/width,(h-120)/height));graphCamera.x=(w-width*graphCamera.scale)/2;graphCamera.y=(h-height*graphCamera.scale)/2+20;graphCamera.initialized=true;apply();}
  const active=nodes.filter(n=>n.status==='active');let activeIndex=0;
  function focusCurrent(){if(!active.length){toast('当前没有进行中的探索或实验');return;}const n=active[activeIndex++%active.length];graphCamera.scale=1;graphCamera.x=viewport.clientWidth/2-n.x-100;graphCamera.y=viewport.clientHeight/2-n.y;apply();canvas.querySelectorAll('.focused').forEach(e=>e.classList.remove('focused'));canvas.querySelectorAll('[data-node-id]').forEach(e=>{if(e.dataset.nodeId===n.id)e.classList.add('focused');});toast('正在推进：'+n.title);}
  for(const [label,action]of [['−',()=>setZoom(graphCamera.scale/1.2)],['＋',()=>setZoom(graphCamera.scale*1.2)],['适应全图',fit],['定位进行中',focusCurrent]]){const b=el('button','quiet',label);b.onclick=action;controls.append(b);}
  controls.insertBefore(percent,controls.children[1]);shell.append(hud,controls);
  const hint=el('div','canvas-hint','节点仅展示名称与状态 · 点击查看过程、结论和证据');shell.append(hint);
  viewport.addEventListener('wheel',e=>{e.preventDefault();const rect=viewport.getBoundingClientRect();const delta=Math.max(-120,Math.min(120,e.deltaY));setZoom(graphCamera.scale*Math.exp(-delta*.0015),e.clientX-rect.left,e.clientY-rect.top);},{passive:false});
  let drag=null;
  viewport.onpointerdown=e=>{if(e.button!==0)return;drag={id:e.pointerId,x:e.clientX,y:e.clientY,cx:graphCamera.x,cy:graphCamera.y,moved:false};ignoreClick=false;};
  viewport.onpointermove=e=>{if(!drag||e.pointerId!==drag.id)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.hypot(dx,dy)>4){drag.moved=true;ignoreClick=true;viewport.setPointerCapture(e.pointerId);viewport.classList.add('panning');}if(drag.moved){graphCamera.x=drag.cx+dx;graphCamera.y=drag.cy+dy;apply();}};
  function stop(){drag=null;viewport.classList.remove('panning');setTimeout(()=>ignoreClick=false,0);}
  viewport.onpointerup=stop;viewport.onpointercancel=stop;
  viewport.onkeydown=e=>{if(e.target!==viewport)return;const k=e.key;if(k==='0')fit();else if(k==='+'||k==='=')setZoom(graphCamera.scale*1.2);else if(k==='-')setZoom(graphCamera.scale/1.2);else if(k.startsWith('Arrow')){graphCamera.x+=k==='ArrowLeft'?60:k==='ArrowRight'?-60:0;graphCamera.y+=k==='ArrowUp'?60:k==='ArrowDown'?-60:0;apply();}else return;e.preventDefault();};
  requestAnimationFrame(()=>{if(!graphCamera.initialized){
    // Start legible. A long project may extend beyond the viewport; overview is explicit.
    graphCamera.scale=Math.max(.7,Math.min(1,(viewport.clientWidth-100)/width));
    graphCamera.x=35;graphCamera.y=70;graphCamera.initialized=true;
  }apply();});
}

function escapeHTML(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function markdown(text){const box=el('div','markdown');const lines=(text||'').split('\n');let code=false,buf=[];const inline=s=>escapeHTML(s).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');for(let i=0;i<lines.length;i++){const line=lines[i];if(/^```/.test(line)){if(code){box.append(el('pre','',buf.join('\n')));buf=[];}code=!code;continue;}if(code){buf.push(line);continue;}if(/^<a id=/.test(line))continue;if(line.includes('|')&&i+1<lines.length&&/^\s*\|?\s*:?-{3}/.test(lines[i+1])){const table=el('table');const rows=[line];i++;while(i+1<lines.length&&lines[i+1].includes('|'))rows.push(lines[++i]);rows.forEach((r,j)=>{const tr=el('tr');r.trim().replace(/^\||\|$/g,'').split('|').forEach(cell=>{const td=el(j?'td':'th');td.innerHTML=inline(cell.trim());tr.append(td);});table.append(tr);});box.append(table);continue;}if(!line.trim())continue;const heading=line.match(/^(#{1,6}) (.+)/);const p=el(heading?'h'+Math.min(heading[1].length+1,6):'p');p.innerHTML=inline(heading?heading[2]:line);box.append(p);}if(code)box.append(el('pre','',buf.join('\n')));return box;}
function openDialog(id){detailRender++;delete dialog.dataset.objectRevision;$('#detail-id').textContent=id;$('#detail-content').replaceChildren();dirty=false;editing=false;if(!dialog.open)dialog.showModal();}
function section(host,name,text){const part=el('section','detail-section');part.dataset.section=name;part.append(el('h3','',name));if(name==='Acceptance criteria'&&byId($('#detail-id').textContent)){const obj=byId($('#detail-id').textContent);text.split('\n').forEach((line,index)=>{const match=line.match(/^\s*- \[([ xX])\]\s+(.+)/);if(!match){if(line.trim())part.append(markdown(line));return;}const label=el('label','ac'),check=el('input');check.type='checkbox';check.checked=match[1].toLowerCase()==='x';label.append(check,document.createTextNode(match[2]));check.onchange=async()=>{check.disabled=true;try{const lines=text.split('\n');lines[index]=line.replace(/\[[ xX]\]/,check.checked?'[x]':'[ ]');await api('/api/update',{path:obj.path,revision:obj.revision,sections:{'Acceptance criteria':lines.join('\n')}});await refresh();await showObject(obj.meta.id);}catch(e){check.checked=!check.checked;toast(e.message);}finally{check.disabled=false;}};part.append(label);});}else part.append(markdown(text));host.append(part);return part;}
function hasResults(o){return !!((o.meta.evidence||[]).length||(o.meta.before||[]).length||(o.sections.Results||'').trim());}
function csvTable(text){
  const rows=[];let row=[],cell='',quoted=false;
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
    else if(!quoted&&(c===','||c==='\n'||c==='\r')){
      if(c===',' ){row.push(cell);cell='';}
      else{row.push(cell);if(row.some(v=>v.length))rows.push(row);row=[];cell='';if(c==='\r'&&text[i+1]==='\n')i++;}
    }else cell+=c;
  }
  row.push(cell);if(row.some(v=>v.length))rows.push(row);
  const table=el('table','result-table');
  rows.forEach((cells,index)=>{const tr=el('tr');cells.forEach(value=>tr.append(el(index?'td':'th','',value)));table.append(tr);});
  return table;
}
async function renderResultAsset(box,path,label){
  const url=safeURL(path)?path:artifactURL(path);
  if(!safeURL(path)&&/\.(png|jpe?g|webp|gif)$/i.test(path)){
    const img=el('img');img.src=url;img.alt=label||'实验结果';box.append(img);
  }else if(!safeURL(path)&&/\.(mp4|webm)$/i.test(path)){
    const video=el('video');video.src=url;video.controls=true;box.append(video);
  }else if(!safeURL(path)&&/\.(md|txt|csv|json)$/i.test(path)){
    try{
      const response=await fetch(url);if(!response.ok)throw Error('无法读取结果文件');
      const text=await response.text();
      box.append(/\.md$/i.test(path)?markdown(text):/\.csv$/i.test(path)?csvTable(text):el('pre','',text));
    }catch(e){box.append(el('p','error',e.message));}
  }
  const link=el('a','result-source',path);link.href=url;link.target='_blank';link.rel='noopener noreferrer';box.append(link);
}
async function evidence(host,o,ticket){
  if(!hasResults(o))return;
  const part=el('section','detail-section results-showcase demonstration');part.id='demonstration';
  part.append(el('h3','','结果展示'),el('p','hint','结果形式由实验决定：一张图可以包含多组指标对比，也可以展示表格、样例、文本或视频。'));
  if((o.sections.Results||'').trim())part.append(markdown(o.sections.Results));
  const gallery=el('div','result-gallery');
  for(const path of o.meta.evidence||[]){const box=el('div','result-asset');await renderResultAsset(box,path,'实验结果');gallery.append(box);}
  if(gallery.children.length)part.append(gallery);
  const before=o.meta.before||[],after=o.meta.after||[];
  if(before.length)part.append(el('h4','optional-comparison-title','并排对照'));
  for(let i=0;i<before.length;i++){
    const grid=el('div','evidence-grid');
    for(const [label,path]of [['修改前',before[i]],['修改后',after[i]]]){
      const box=el('div','evidence-box');box.append(el('h4','',label));
      if(path)await renderResultAsset(box,path,label);else box.append(el('p','error','缺少对照'));
      grid.append(box);
    }part.append(grid);
  }
  if($('#detail-id').textContent===o.meta.id&&ticket===detailRender)host.append(part);
}
function demonstrationIndex(host,plan){
  const experiments=(plan.meta.experiments||[]).map(byId).filter(e=>e&&hasResults(e));
  if(!experiments.length)return;
  const part=section(host,'结果展示','图表、指标、样例与其他结果跟随实验保存，点击查看；不要求拆成前后两份。');
  for(const e of experiments){const b=el('button','relation-link','⇄ '+e.meta.id+' · '+e.meta.title);b.onclick=()=>showObject(e.meta.id,false,'Results');part.append(b);}
}
function evidenceEditor(host,o){
  const group=el('fieldset','predecessor-picker result-editor');group.append(el('legend','','结果展示 · 可选，不限定前后对照'));
  group.append(el('p','hint','每行填写一个已有文件或链接。一张多组指标对比图、结果表或视频可直接展示，无需拆成修改前后。结果解读可写在 Results 中。'));
  const paths=el('textarea');paths.setAttribute('aria-label','结果文件或链接');paths.placeholder='例如：experiments/metrics-comparison.png';paths.value=(o.meta.evidence||[]).join('\n');paths.rows=3;group.append(paths);
  const optional=el('details','optional-comparison'),summary=el('summary','','可选：需要左右并排时，添加修改前 / 修改后');optional.append(summary);
  const rows=el('div'),inputs=[];
  function add(before='',after=''){
    const row=el('div','evidence-reference-row'),a=el('input'),b=el('input');
    a.value=before;b.value=after;a.placeholder='修改前：文件路径或链接';b.placeholder='修改后：文件路径或链接';
    a.setAttribute('aria-label','修改前证据路径');b.setAttribute('aria-label','修改后证据路径');row.append(a,b);rows.append(row);inputs.push([a,b]);
  }
  for(let i=0;i<(o.meta.before||[]).length;i++)add(o.meta.before[i],o.meta.after?.[i]);
  optional.open=inputs.length>0;
  const more=el('button','quiet','＋ 添加一组并排对照');more.type='button';more.onclick=()=>{add();optional.open=true;};
  optional.append(rows,more);group.append(optional);host.append(group);
  return ()=>{
    const pairs=inputs.map(([a,b])=>[a.value.trim(),b.value.trim()]).filter(([a,b])=>a||b);
    if(pairs.some(([a,b])=>!a||!b))throw Error('选择并排对照时，两边路径必须成对填写');
    const result={evidence:paths.value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean)};
    if(pairs.length||'before' in o.meta||'after' in o.meta){result.before=pairs.map(p=>p[0]);result.after=pairs.map(p=>p[1]);}
    return result;
  };
}
function predecessorPicker(host,plan,id,selected=[]){
  const group=el('fieldset','predecessor-picker');group.append(el('legend','','基于哪些实验继续 · 可多选汇合，不选则从 Plan 出发'));
  const descendants=new Set(id?[id]:[]);let changed=true;
  while(changed){changed=false;for(const e of state.objects.filter(o=>o.kind==='experiment'&&o.meta.plan===plan)){
    if(!descendants.has(e.meta.id)&&(e.meta.predecessors||[]).some(p=>descendants.has(p))){descendants.add(e.meta.id);changed=true;}
  }}
  const inputs=[];
  for(const e of state.objects.filter(o=>o.kind==='experiment'&&o.meta.plan===plan&&!descendants.has(o.meta.id))){
    const label=el('label','ac'),input=el('input');input.type='checkbox';input.value=e.meta.id;input.checked=selected.includes(e.meta.id);
    label.append(input,document.createTextNode(e.meta.id+' · '+e.meta.title));group.append(label);inputs.push(input);
  }
  if(!inputs.length)group.append(el('p','hint','暂无可选前序实验，将从 Plan 开始。'));
  host.append(group);return ()=>inputs.filter(i=>i.checked).map(i=>i.value);
}
function experimentRelations(host,o){
  const previous=(o.meta.predecessors||[]).map(byId).filter(Boolean);
  const following=state.objects.filter(e=>e.kind==='experiment'&&(e.meta.predecessors||[]).includes(o.meta.id));
  const part=section(host,'探索脉络','');
  const plan=byId(o.meta.plan), origin=el('button','quiet','所属 Plan · '+(plan?.meta.title||o.meta.plan));origin.onclick=()=>showObject(o.meta.plan);part.append(origin);
  for(const [label,items]of [['基于前序结果',previous],['后续尝试',following]]){
    part.append(el('p','hint',label+(items.length?'':' · '+(label==='后续尝试'?'暂无后续，不表示 Plan 自动完成':'从 Plan 出发'))));
    for(const e of items){const b=el('button','relation-link',e.meta.id+' · '+e.meta.title);b.onclick=()=>showObject(e.meta.id);part.append(b);}
  }
}

async function showObject(id,edit=false,focus=null){const o=byId(id);if(!o)return;openDialog(id);const ticket=detailRender;dialog.dataset.objectRevision=o.revision;const host=$('#detail-content');host.append(el('h2','detail-title',o.meta.title),statusBadge(o.meta.status),el('div','detail-path',o.path),markdown(o.meta.summary));const buttons=el('div','detail-buttons');for(const [label,action]of [['编辑内容',()=>editObject(id)],['编辑源文件',()=>editRaw(o.path)],['审查上下文',()=>showContext(id)]]){const b=el('button','quiet',label);b.onclick=action;buttons.append(b);}if(o.kind==='experiment'&&hasResults(o)){const b=el('button','primary','查看结果');b.onclick=()=>host.querySelector('.demonstration')?.scrollIntoView({block:'start'});buttons.append(b);}if(o.kind==='plan'){const b=el('button','primary','＋ 实验');b.onclick=()=>openCreate('experiment',id);buttons.append(b);}if(o.kind==='experiment'){const b=el('button','primary','从这里继续实验');b.onclick=()=>openCreate('experiment',o.meta.plan,null,[id]);buttons.append(b);}host.append(buttons);await evidence(host,o,ticket);if(ticket!==detailRender)return;if(o.kind==='experiment')experimentRelations(host,o);if(o.kind==='plan')demonstrationIndex(host,o);if($('#detail-id').textContent!==id)return;for(const [name,text]of Object.entries(o.sections)){if(name==='Results')continue;if(text||name==='Review'||name==='Conclusion')section(host,name,text||'尚未记录');}const links=[...(o.meta.experiments||[]),...(o.meta.follow_up_plans||[])];if(links.length){const part=section(host,'关联工作','');for(const link of links){const target=byId(link);if(target)part.append(card(target));}}if(edit)editObject(id);if(focus==='Before / After'||focus==='Results')host.querySelector('.demonstration')?.scrollIntoView();else if(focus)Array.from(host.querySelectorAll('[data-section]')).find(x=>x.dataset.section===focus)?.scrollIntoView();}
async function editObject(id){const o=byId(id);openDialog(id+' / 编辑');editing=true;const host=$('#detail-content');const form=el('form');const title=el('label','','标题'),titleInput=el('input');titleInput.value=o.meta.title;title.append(titleInput);const summary=el('label','','脉络摘要 · 用普通语言说明动作和结果'),summaryInput=el('textarea');summaryInput.value=o.meta.summary||'';summary.append(summaryInput);form.append(title,summary);let statusInput,resInput;if(o.kind!=='proposal'){const label=el('label','','状态');statusInput=el('select');for(const value of state.states[o.kind]){const option=el('option','',names[value]);option.value=value;statusInput.append(option);}statusInput.value=o.meta.status;label.append(statusInput);form.append(label);}if(o.kind==='plan'){const label=el('label','','关闭结果 · 仅在已结束时使用');resInput=el('select');for(const value of ['', 'supported','refuted','inconclusive','abandoned']){const option=el('option','',value||'请选择');option.value=value;resInput.append(option);}resInput.value=o.meta.resolution||'';label.append(resInput);form.append(label);}let readPredecessors,readEvidence;if(o.kind==='experiment'){readPredecessors=predecessorPicker(form,o.meta.plan,id,o.meta.predecessors||[]);readEvidence=evidenceEditor(form,o);}const fields={};for(const [name,text]of Object.entries(o.sections)){const l=el('label','',name),t=el('textarea');t.value=text;t.rows=name==='Review'||name==='Verification'?5:3;l.append(t);form.append(l);fields[name]=t;}const hint=el('p','hint','关系、命令和证据引用可在“编辑源文件”中修改。关闭前请先保存记录，再从终端运行 verify。');form.append(hint);const error=el('p','error');const actions=el('div','form-actions'),save=el('button','primary','保存到项目文件');save.type='submit';actions.append(save);form.append(error,actions);form.oninput=()=>dirty=true;form.onsubmit=async e=>{e.preventDefault();save.disabled=true;try{const meta={title:titleInput.value,summary:summaryInput.value};if(statusInput)meta.status=statusInput.value;if(readPredecessors)meta.predecessors=readPredecessors();if(readEvidence)Object.assign(meta,readEvidence());if(o.kind==='plan')meta.resolution=meta.status==='closed'?resInput.value:null;const sections={};for(const [key,input]of Object.entries(fields))if(input.value!==o.sections[key])sections[key]=input.value;await api('/api/update',{path:o.path,revision:o.revision,fields:meta,sections});dirty=false;await refresh();await showObject(id);toast('已写回 '+o.path);}catch(e){error.textContent=e.message;}finally{save.disabled=false;}};host.append(form);}
async function editRaw(path){try{const file=await api('/api/file?path='+encodeURIComponent(path));openDialog(path);editing=true;const host=$('#detail-content');host.append(el('p','hint','修改直接写回源文件。保存前校验格式、引用和状态；冲突时保留你的编辑。'));const form=el('form'),input=el('textarea','raw-editor');input.value=file.raw;const error=el('p','error'),actions=el('div','form-actions'),save=el('button','primary','校验并保存');save.type='submit';actions.append(save);form.append(input,error,actions);form.oninput=()=>dirty=true;form.onsubmit=async e=>{e.preventDefault();save.disabled=true;try{await api('/api/update',{path,revision:file.revision,raw:input.value});dirty=false;dialog.close();await refresh();toast('已保存 '+path);}catch(e){error.textContent=e.message;}finally{save.disabled=false;}};host.append(form);}catch(e){toast(e.message);}}
function showDesign(n){openDialog('DESIGN / '+n.id);const host=$('#detail-content');host.append(el('h2','detail-title',n.title),markdown(n.content));const edit=el('button','quiet','编辑项目主干');edit.onclick=()=>editRaw('PROJECT.md');host.append(edit);const create=el('button','primary','从这里开始探索');create.onclick=()=>openCreate('plan',null,'PROJECT.md#'+n.section);host.append(create);const links=[...(n.sources||[]),...state.objects.filter(o=>o.kind==='plan'&&o.meta.design_anchor==='PROJECT.md#'+n.section).map(o=>o.meta.id)];for(const id of links){const o=byId(id);if(o)host.append(card(o));}}
async function showContext(id){try{const result=await api('/api/context?id='+encodeURIComponent(id)+'&reviewer=1');openDialog(id+' / 审查者入口');const host=$('#detail-content');host.append(el('p','hint','供低频调用的 subagent 阅读；此按钮不调用模型，也不自动声称已经审查。'));const text=el('textarea','context-text');text.value=result.text;text.readOnly=true;const copy=el('button','primary','复制审查上下文');copy.onclick=async()=>{try{await navigator.clipboard.writeText(result.text);toast('已复制');}catch(e){text.select();toast('请复制选中文本');}};host.append(text,copy);}catch(e){toast(e.message);}}
function openCreate(kind='plan',parent=null,anchor=null,after=[]){
  const form=$('#create-form');form.reset();form.elements.kind.value=kind;
  let pickerHost=form.querySelector('.create-predecessors');
  if(!pickerHost){pickerHost=el('div','create-predecessors');form.elements.parent.closest('label').after(pickerHost);}
  function updatePredecessors(){
    pickerHost.replaceChildren();form.readPredecessors=null;
    if(form.elements.kind.value==='experiment')form.readPredecessors=predecessorPicker(pickerHost,form.elements.parent.value,null,after);
  }
  function updateParents(){
    const kind=form.elements.kind.value,parentSelect=form.elements.parent;
    parentSelect.replaceChildren(el('option','','无'));parentSelect.firstChild.value='';
    const candidates=state.objects.filter(o=>kind==='experiment'?o.kind==='plan':kind==='plan'?['proposal','plan'].includes(o.kind):false);
    for(const o of candidates){const option=el('option','',o.meta.id+' · '+o.meta.title);option.value=o.meta.id;parentSelect.append(option);}
    if(parent&&candidates.some(o=>o.meta.id===parent))parentSelect.value=parent;
    parentSelect.required=kind==='experiment';updatePredecessors();
  }
  form.elements.kind.onchange=updateParents;form.elements.parent.onchange=updatePredecessors;updateParents();
  const anchorSelect=form.elements.anchor;anchorSelect.replaceChildren(el('option','','暂未关联'));anchorSelect.firstChild.value='';
  for(const n of state.mainline){const option=el('option','',n.title);option.value='PROJECT.md#'+n.section;anchorSelect.append(option);}
  if(anchor)anchorSelect.value=anchor;$('#create-error').textContent='';$('#create').showModal();
}
$('#create-form').onsubmit=async e=>{e.preventDefault();const f=e.target;const button=f.querySelector('button[type=submit]');button.disabled=true;try{const result=await api('/api/create',{kind:f.elements.kind.value,title:f.elements.title.value,parent:f.elements.parent.value||null,anchor:f.elements.anchor.value||null,predecessors:f.readPredecessors?f.readPredecessors():null});$('#create').close();await refresh();showObject(result.id,true);}catch(e){$('#create-error').textContent=e.message;}finally{button.disabled=false;}};
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{view=b.dataset.view;render();});$('#new').onclick=()=>openCreate(view==='proposals'?'proposal':'plan');$('#project-edit').onclick=()=>editRaw('PROJECT.md');$('#refresh').onclick=refresh;$('#search').oninput=e=>{query=e.target.value;boardScroll.clear();render();};document.querySelectorAll('dialog .close').forEach(b=>b.onclick=()=>{const d=b.closest('dialog');if(d===dialog&&dirty&&!confirm('尚未保存，确定关闭？'))return;dirty=false;d.close();});dialog.addEventListener('cancel',e=>{if(dirty&&!confirm('尚未保存，确定关闭？'))e.preventDefault();});
refresh().then(()=>{const stream=new EventSource('/api/events');stream.onmessage=()=>refresh();stream.onerror=()=>{$('#connection').textContent='● 正在重新连接';};});
