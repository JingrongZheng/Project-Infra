/* Shared by every project and by tests. Coordinates never encode relationships. */
(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;else root.ProjectGraph=api;
})(globalThis,function(){
  function layoutExperiments(experiments){
    const objects=new Map(experiments.map(o=>[o.meta.id,o])),positions=new Map(),pending=new Set(objects.keys());
    while(pending.size){
      const ready=[...pending].filter(id=>(objects.get(id).meta.predecessors||[]).every(p=>positions.has(p)));
      if(!ready.length)throw Error('实验脉络存在循环或无效前序，请检查项目文件');
      const depth=id=>Math.max(-1,...(objects.get(id).meta.predecessors||[]).map(p=>positions.get(p).depth))+1;
      const nextDepth=Math.min(...ready.map(depth)),layer=ready.filter(id=>depth(id)===nextDepth);
      const target=id=>{const ps=objects.get(id).meta.predecessors||[];return ps.length?ps.reduce((sum,p)=>sum+positions.get(p).x,0)/ps.length:0;};
      layer.sort((a,b)=>target(a)-target(b)||a.localeCompare(b));
      let lastX=-360;
      for(const id of layer){const x=Math.max(lastX+360,target(id));positions.set(id,{depth:nextDepth,x,y:(nextDepth+1)*220});lastX=x;pending.delete(id);}
    }
    return {positions,edges:experiments.flatMap(o=>(o.meta.predecessors||[]).map(from=>({from,to:o.meta.id}))),
      width:Math.max(0,...[...positions.values()].map(p=>p.x))+300,
      height:Math.max(0,...[...positions.values()].map(p=>p.y))+120};
  }
  const overlaps=(a,b,gap=0)=>a.left<b.right+gap&&a.right>b.left-gap&&a.top<b.bottom+gap&&a.bottom>b.top-gap;
  // Bounds are measured from real rendered nodes AND labels, not guessed from title length.
  function separateNodes(nodes,gap=34,edges=[]){
    const placed=[];
    const originals=new Map(nodes.map(n=>[n.id,n]));
    for(const node of [...nodes].sort((a,b)=>a.y-b.y||a.x-b.x||a.id.localeCompare(b.id))){
      const n={...node,box:{...node.box}};
      const parents=edges.filter(e=>e.to===n.id&&['trunk','branch','lineage','review'].includes(e.type)&&originals.get(e.from)?.y<n.y).map(e=>placed.find(p=>p.id===e.from)).filter(Boolean);
      const parentShift=Math.max(0,...parents.map(p=>p.box.bottom+gap-n.box.top));
      n.y+=parentShift;n.box.top+=parentShift;n.box.bottom+=parentShift;
      for(let pass=0;pass<=placed.length;pass++){
        const collisions=placed.filter(p=>overlaps(n.box,p.box,gap));
        if(!collisions.length)break;
        const shift=Math.max(...collisions.map(p=>p.box.bottom+gap-n.box.top));
        n.y+=shift;n.box.top+=shift;n.box.bottom+=shift;
      }
      placed.push(n);
    }
    return placed;
  }
  function segmentHitsBox(a,b,box){
    if(a.x===b.x)return a.x>box.left&&a.x<box.right&&Math.max(a.y,b.y)>box.top&&Math.min(a.y,b.y)<box.bottom;
    if(a.y===b.y)return a.y>box.top&&a.y<box.bottom&&Math.max(a.x,b.x)>box.left&&Math.min(a.x,b.x)<box.right;
    return true; // Non-orthogonal paths are not accepted as an untested shortcut.
  }
  class MinHeap{
    constructor(){this.items=[];}
    push(value){const a=this.items;a.push(value);let i=a.length-1;while(i){const p=(i-1)>>1;if(a[p].score<=value.score)break;a[i]=a[p];i=p;}a[i]=value;}
    pop(){const a=this.items,first=a[0],last=a.pop();if(a.length){let i=0;while(i*2+1<a.length){let c=i*2+1;if(c+1<a.length&&a[c+1].score<a[c].score)c++;if(a[c].score>=last.score)break;a[i]=a[c];i=c;}a[i]=last;}return first;}
    get size(){return this.items.length;}
  }
  function routeConnections(nodes,edges){
    if(!nodes.length)return {paths:[],errors:[]};
    const byId=new Map(nodes.map(n=>[n.id,n]));
    const boxes=nodes.map(n=>({id:n.id,left:n.box.left-8,right:n.box.right+8,top:n.box.top-8,bottom:n.box.bottom+8}));
    const ports=edges.map(e=>{
      const a=byId.get(e.from),b=byId.get(e.to);if(!a||!b)return null;
      const down=b.y>=a.y;
      return {a,b,start:{x:a.x,y:down?a.box.bottom+16:a.box.top-16},end:{x:b.x,y:down?b.box.top-16:b.box.bottom+16},down};
    });
    const xs=new Set(),ys=new Set();
    for(const b of boxes){xs.add(b.left);xs.add(b.right);ys.add(b.top);ys.add(b.bottom);}
    for(const p of ports)if(p){xs.add(p.start.x);xs.add(p.end.x);ys.add(p.start.y);ys.add(p.end.y);}
    const left=Math.min(...boxes.map(b=>b.left)),right=Math.max(...boxes.map(b=>b.right));
    const top=Math.min(...boxes.map(b=>b.top)),bottom=Math.max(...boxes.map(b=>b.bottom));
    // Reusable exterior lanes; more edges get more lanes, not hard-coded project spacing.
    for(let i=0;i<=edges.length;i++){xs.add(left-24-i*18);xs.add(right+24+i*18);ys.add(top-24-i*18);ys.add(bottom+24+i*18);}
    const xx=[...xs].sort((a,b)=>a-b),yy=[...ys].sort((a,b)=>a-b),nx=xx.length;
    const points=yy.flatMap(y=>xx.map(x=>({x,y}))),adj=Array.from({length:points.length},()=>[]);
    const inside=p=>boxes.some(b=>p.x>b.left&&p.x<b.right&&p.y>b.top&&p.y<b.bottom);
    const valid=points.map(p=>!inside(p));
    function connect(i,j,dir){
      if(!valid[i]||!valid[j]||boxes.some(b=>segmentHitsBox(points[i],points[j],b)))return;
      const cost=Math.abs(points[i].x-points[j].x)+Math.abs(points[i].y-points[j].y);
      adj[i].push({to:j,dir,cost});adj[j].push({to:i,dir,cost});
    }
    for(let yi=0;yi<yy.length;yi++)for(let xi=0;xi<nx;xi++){
      const i=yi*nx+xi;if(xi+1<nx)connect(i,i+1,1);if(yi+1<yy.length)connect(i,i+nx,2);
    }
    const pointIndex=p=>yy.indexOf(p.y)*nx+xx.indexOf(p.x),usage=new Map(),paths=[],errors=[];
    const segmentKey=(a,b)=>a<b?a+':'+b:b+':'+a;
    for(let ei=0;ei<edges.length;ei++){
      const e=edges[ei],p=ports[ei];if(!p){errors.push({edge:e,reason:'Missing endpoint'});continue;}
      const start=pointIndex(p.start),end=pointIndex(p.end),heap=new MinHeap(),distance=new Map(),previous=new Map();
      const forward=p.down&&p.start.y<=p.end.y&&['trunk','branch','lineage','review'].includes(e.type);
      const initial=start*3;distance.set(initial,0);heap.push({key:initial,score:0,cost:0});let found=null;
      while(heap.size){
        const current=heap.pop();if(current.cost!==distance.get(current.key))continue;
        const at=Math.floor(current.key/3),direction=current.key%3;
        if(at===end){found=current.key;break;}
        for(const step of adj[at]){
          if(forward&&points[step.to].y<points[at].y)continue;
          const occupied=usage.get(segmentKey(at,step.to))||[];
          const unrelated=occupied.some(old=>old.from!==e.from&&old.to!==e.to);
          const cost=current.cost+step.cost+(direction&&direction!==step.dir?26:0)+(unrelated?step.cost*8+80:0);
          const key=step.to*3+step.dir;
          if(cost>=(distance.get(key)??Infinity))continue;
          distance.set(key,cost);previous.set(key,current.key);
          const q=points[step.to],estimate=Math.abs(q.x-p.end.x)+Math.abs(q.y-p.end.y);
          heap.push({key,cost,score:cost+estimate});
        }
      }
      if(found===null){errors.push({edge:e,reason:'No safe route'});continue;}
      const indices=[];for(let key=found;key!==undefined;key=previous.get(key))indices.push(Math.floor(key/3));indices.reverse();
      for(let i=1;i<indices.length;i++){const key=segmentKey(indices[i-1],indices[i]);if(!usage.has(key))usage.set(key,[]);usage.get(key).push(e);}
      const raw=[{x:p.a.x,y:p.a.y+(p.down?12:-12)},...indices.map(i=>points[i]),{x:p.b.x,y:p.b.y+(p.down?-12:12)}];
      const simplified=[];
      for(const q of raw){
        if(simplified.length&&simplified.at(-1).x===q.x&&simplified.at(-1).y===q.y)continue;
        while(simplified.length>1){const a=simplified.at(-2),b=simplified.at(-1);if((a.x===b.x&&b.x===q.x)||(a.y===b.y&&b.y===q.y))simplified.pop();else break;}
        simplified.push(q);
      }
      // Fail closed: never draw a convenient line through unrelated content.
      const unsafe=nodes.some(n=>n.id!==e.from&&n.id!==e.to&&simplified.slice(1).some((q,i)=>segmentHitsBox(simplified[i],q,n.box)));
      if(unsafe){errors.push({edge:e,reason:'Route intersects unrelated content'});continue;}
      paths.push({...e,points:simplified});
    }
    return {paths,errors};
  }
  // Only unrelated perpendicular crossings need a bridge. Shared-source forks
  // and shared-target merges must remain joined, regardless of paint order.
  function wireCrossings(paths){
    const crossings=[];
    for(let over=1;over<paths.length;over++)for(let under=0;under<over;under++){
      const a=paths[over],b=paths[under];
      if(a.from===b.from||a.to===b.to)continue;
      for(let i=1;i<a.points.length;i++)for(let j=1;j<b.points.length;j++){
        const p=a.points[i-1],q=a.points[i],r=b.points[j-1],s=b.points[j];
        const horizontal=p.y===q.y;
        if(horizontal===(r.y===s.y))continue;
        const x=horizontal?r.x:p.x,y=horizontal?p.y:r.y;
        const interior=(v,a,b)=>v>Math.min(a,b)+5&&v<Math.max(a,b)-5;
        if((horizontal?interior(x,p.x,q.x)&&interior(y,r.y,s.y):interior(y,p.y,q.y)&&interior(x,r.x,s.x)))
          crossings.push({over,under,x,y,horizontal});
      }
    }
    return crossings;
  }
  return {layoutExperiments,separateNodes,routeConnections,segmentHitsBox,wireCrossings};
});
