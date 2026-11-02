// Tests the very same pure layout function used by the homepage, no extra dependencies.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {layoutExperiments:layout}=require('../project_infra/static/graph-layout.js');
const exp=(id,predecessors=[])=>({meta:{id,predecessors}});
const plain=x=>JSON.parse(JSON.stringify(x));
test('one or two roots stay parallel; no inferred chronology',()=>{
  const r=layout([exp('A'),exp('B')]);
  assert.equal(r.positions.get('A').y,r.positions.get('B').y);
  assert.notEqual(r.positions.get('A').x,r.positions.get('B').x);
  assert.deepEqual(plain(r.edges),[]);
});
test('serial experiments progress along the same trace',()=>{
  const r=layout([exp('C',['B']),exp('A'),exp('B',['A'])]);
  assert.ok(r.positions.get('C').y>r.positions.get('B').y);
  assert.ok(r.positions.get('B').y>r.positions.get('A').y);
  assert.equal(r.positions.get('A').x,r.positions.get('C').x);
  assert.deepEqual(plain(r.edges),[{from:'B',to:'C'},{from:'A',to:'B'}]);
});
test('a long exploration forks, merges, and continues without a Task',()=>{
  const r=layout([exp('A'),exp('B'),exp('C',['A']),exp('D',['A']),exp('E',['B','C','D']),exp('F',['E'])]);
  assert.equal(r.positions.size,6);
  assert.notEqual(r.positions.get('C').x,r.positions.get('D').x);
  for(const {from,to} of r.edges)assert.ok(r.positions.get(to).y>r.positions.get(from).y);
  assert.deepEqual(plain(r.edges.filter(e=>e.to==='E').map(e=>e.from)),['B','C','D']);
  assert.ok(r.positions.get('F').y>r.positions.get('E').y);
});
test('array reordering changes neither lineage nor node placement',()=>{
  const objects=[exp('A'),exp('B'),exp('C',['A']),exp('D',['A']),exp('E',['B','C','D'])];
  const a=layout(objects),b=layout([...objects].reverse());
  for(const [id,pos] of a.positions)assert.deepEqual(plain(pos),plain(b.positions.get(id)));
});
test('cycles and unknown references fail rather than hanging the canvas',()=>{
  assert.throws(()=>layout([exp('A',['B']),exp('B',['A'])]));
  assert.throws(()=>layout([exp('A',['missing'])]));
  assert.equal(layout([]).positions.size,0);
});
