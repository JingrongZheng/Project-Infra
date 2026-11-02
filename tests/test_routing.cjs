const {test}=require('node:test');
const assert=require('node:assert/strict');
const {routeConnections,separateNodes,segmentHitsBox,wireCrossings}=require('../project_infra/static/graph-layout.js');
const node=(id,x,y,height=82)=>({id,x,y,box:{left:x-18,right:x+300,top:y-26,bottom:y+height}});
test('crossing decoration never cuts a genuine fork or merge',()=>{
  const a={from:'a',to:'merge',points:[{x:0,y:50},{x:100,y:50}]};
  const b={from:'b',to:'merge',points:[{x:50,y:0},{x:50,y:100}]};
  assert.deepEqual(wireCrossings([a,b]),[]);
  assert.deepEqual(wireCrossings([a,{...b,from:'a',to:'other'}]),[]);
  assert.equal(wireCrossings([a,{...b,to:'other'}]).length,1);
  assert.deepEqual(wireCrossings([a,{...b,to:'other',points:[{x:100,y:0},{x:100,y:100}]}]),[],'A corner is not a perpendicular interior crossing');
});
function safe(nodes,edges){
  const routed=routeConnections(nodes,edges);
  assert.deepEqual(routed.errors,[]);
  assert.equal(routed.paths.length,edges.length);
  for(const edge of routed.paths){
    for(let i=1;i<edge.points.length;i++){
      const a=edge.points[i-1],b=edge.points[i];
      assert.ok(a.x===b.x||a.y===b.y,'Only orthogonal segments are allowed');
      for(const n of nodes)if(n.id!==edge.from&&n.id!==edge.to)
        assert.equal(segmentHitsBox(a,b,n.box),false,`${edge.from}->${edge.to} crossed ${n.id}`);
    }
  }
  return routed;
}
test('regression: direct mainline to Plan never passes the three unrelated experiment nodes',()=>{
  const nodes=[node('design',1180,110),node('A',1200,290),node('B',1200,450),node('C',1200,610),node('plan',1230,830)];
  safe(nodes,[{from:'design',to:'plan'}]);
});
test('label rectangles, not only pads, are obstacles',()=>{
  const nodes=[node('a',200,100),node('long-label',550,300,260),node('b',1000,700)];
  safe(nodes,[{from:'a',to:'b'}]);
});
test('measured long content is separated before wires are routed',()=>{
  const original=[node('a',200,100,240),node('b',200,260,100),node('c',200,380,200)];
  const separated=separateNodes(original);
  assert.equal(original[1].y,260,'The routing module must not mutate source records');
  for(let i=1;i<separated.length;i++)assert.ok(separated[i].box.top>separated[i-1].box.bottom);
  safe(separated,[{from:'a',to:'b'},{from:'b',to:'c'}]);
});
test('forks, multi-input merges and reverse adoption preserve actual endpoints',()=>{
  const nodes=[node('design',100,100),node('p',450,350),node('a',850,350),node('b',850,550),node('merge',1250,450)];
  const edges=[{from:'design',to:'p'},{from:'p',to:'a'},{from:'p',to:'b'},{from:'a',to:'merge'},{from:'b',to:'merge'},{from:'merge',to:'design'}];
  safe(nodes,edges);
});
test('reusable invariants hold for multiple project sizes and arrangements',()=>{
  for(const count of [4,7,11,15]){
    const raw=Array.from({length:count},(_,i)=>node('n'+i,180+(i%4)*395,100+Math.floor(i/4)*170,80+(i%3)*45));
    const nodes=separateNodes(raw);
    const edges=nodes.slice(1).map((n,i)=>({from:nodes[Math.floor(i/2)].id,to:n.id}));
    if(count>7)edges.push({from:nodes.at(-1).id,to:nodes[0].id});
    safe(nodes,edges);
  }
});
test('vertical forward traces are monotonic and join at the top port',()=>{
  const nodes=[node('a',180,100),node('block',180,340),node('b',580,600)];
  const {paths}=safe(nodes,[{from:'a',to:'b',type:'lineage'}]);
  for(let i=1;i<paths[0].points.length;i++)assert.ok(paths[0].points[i].y>=paths[0].points[i-1].y);
  assert.equal(paths[0].points.at(-1).x,580);
  assert.equal(paths[0].points.at(-1).y,588);
});
test('child layers clear tall parent text even when they are in different columns',()=>{
  const nodes=separateNodes([node('a',180,100,400),node('b',580,320)],34,[{from:'a',to:'b',type:'lineage'}]);
  assert.ok(nodes[1].box.top>nodes[0].box.bottom);
  safe(nodes,[{from:'a',to:'b',type:'lineage'}]);
});
