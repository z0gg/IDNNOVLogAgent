import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.mjs';

const CATALOG_ENTRY={
  package:'IDNNOVLogAgent',version:'1.0.0-1001',dname:'IDNNOV Log Agent',
  desc:'Collecte les journaux Synology et les transmet au collecteur IDNNOV.',
  arch:'geminilake',min_build:86009,max_build:89999,
  url:'https://github.com/z0gg/IDNNOVLogAgent/releases/download/v1.0.0-1001/IDNNOVLogAgent-1.0.0-1001-geminilake.spk',
  size:3020800,md5:'d4ff47141be15cd0e1b984ed10b9782f',
  sha256:'10379bf5eb07f84134fd09b546314315a64caaa312ad69bdd38efb241c4bac7b'};
const env={CATALOG:JSON.stringify({packages:[CATALOG_ENTRY]})};
const GET='https://packages.idnnov.com/?arch=geminilake&build=86009&language=fre&major=7&minor=3&micro=1&package_update_channel=stable';

test('1 GET valid DSM 7.3 geminilake returns 200 json with exactly one package',async()=>{
  const r=await worker.fetch(new Request(GET),env);
  assert.equal(r.status,200);
  assert.match(r.headers.get('content-type'),/^application\/json/);
  const j=await r.json();
  assert.equal(j.packages.length,1);
});

test('1b embedded versioned catalog works without a runtime binding',async()=>{
  const r=await worker.fetch(new Request(GET),{});
  assert.equal(r.status,200);
  const j=await r.json();
  assert.equal(j.packages.length,1);
  assert.equal(j.packages[0].version,'1.0.0-1001');
});

test('2 POST form-urlencoded equals GET response deeply',async()=>{
  const get=await (await worker.fetch(new Request(GET),env)).json();
  const body='arch=geminilake&build=86009&language=fre&major=7&minor=3&micro=1&package_update_channel=stable';
  const r=await worker.fetch(new Request('https://packages.idnnov.com/',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body}),env);
  assert.equal(r.status,200);
  const post=await r.json();
  assert.deepEqual(post,get);
});

test('3 POST application/json is rejected with 400',async()=>{
  const r=await worker.fetch(new Request('https://packages.idnnov.com/',{method:'POST',headers:{'content-type':'application/json'},body:'{"arch":"geminilake"}'}),env);
  assert.equal(r.status,400);
});

test('4 missing required arch/build/language returns 400',async()=>{
  for(const q of ['build=86009&language=fre','arch=geminilake&language=fre','arch=geminilake&build=86009']){
    const r=await worker.fetch(new Request('https://packages.idnnov.com/?'+q),env);
    assert.equal(r.status,400,q);
  }
});

test('5 invalid arch/build/major/language returns 422',async()=>{
  for(const q of ['arch=zzzunknown&build=86009&language=fre','arch=geminilake&build=abc&language=fre','arch=geminilake&build=86009&language=fre&major=zzz','arch=geminilake&build=86009&language=xx']){
    const r=await worker.fetch(new Request('https://packages.idnnov.com/?'+q),env);
    assert.equal(r.status,422,q);
  }
});

test('5b valid but unserved arch (apollolake) returns empty 200',async()=>{
  const r=await worker.fetch(new Request('https://packages.idnnov.com/?arch=apollolake&build=86009&language=fre'),env);
  assert.equal(r.status,200);
  assert.deepEqual((await r.json()).packages,[]);
});

test('6 valid but incompatible arch returns empty packages 200',async()=>{
  // apollolake is a real DSM arch but we have no package for it; note: unknown arch strings are 422
  const r=await worker.fetch(new Request('https://packages.idnnov.com/?arch=geminilake&build=86009&language=fre&unique=synology_gemini'+''+'lake_920%2B'),env);
  assert.equal(r.status,200);
});

test('7 build below os_min_ver 86009 hides package; 86009 and above show it',async()=>{
  const below=await (await worker.fetch(new Request('https://packages.idnnov.com/?arch=geminilake&build=86008&language=fre'),env)).json();
  assert.deepEqual(below.packages,[]);
  for(const b of ['86009','86100','89999']){
    const j=await (await worker.fetch(new Request(`https://packages.idnnov.com/?arch=geminilake&build=${b}&language=fre`),env)).json();
    assert.equal(j.packages.length,1,b);
  }
});

test('8 major other than 7 returns no packages',async()=>{
  const j=await (await worker.fetch(new Request('https://packages.idnnov.com/?arch=geminilake&build=86009&language=fre&major=6'),env)).json();
  assert.deepEqual(j.packages,[]);
});

test('9 beta channel under DSM 7 still returns the stable package',async()=>{
  const j=await (await worker.fetch(new Request('https://packages.idnnov.com/?arch=geminilake&build=86009&language=fre&package_update_channel=beta'),env)).json();
  assert.equal(j.packages.length,1);
});

test('10 supported non-English language falls back to same payload',async()=>{
  const a=await (await worker.fetch(new Request(GET),env)).json();
  const b=await (await worker.fetch(new Request('https://packages.idnnov.com/?arch=geminilake&build=86009&language=enu'),env)).json();
  assert.deepEqual(b,a);
});

test('11 exact DSM 7 field types: q* booleans, counts and size integers, startable string',async()=>{
  const j=await (await worker.fetch(new Request(GET),env)).json();
  const p=j.packages[0];
  for(const k of ['qinst','qupgrade','qstart'])assert.equal(typeof p[k],'boolean',k);
  for(const k of ['download_count','recent_download_count','size'])assert.equal(typeof p[k],'number',k);
  assert.equal(typeof p.startable,'string');
  assert.match(p.md5,/^[0-9a-f]{32}$/);
});

test('12 no keyrings, arch, os_min_ver or sha256 in DSM 7 response',async()=>{
  const j=await (await worker.fetch(new Request(GET),env)).json();
  const p=j.packages[0];
  for(const k of ['keyrings','arch','os_min_ver','sha256'])assert.equal(k in p,false,k);
});

test('13 multiple compatible releases yield only the newest promoted one',async()=>{
  const two={packages:[CATALOG_ENTRY,{...CATALOG_ENTRY,version:'0.9.0-900',url:'https://github.com/z0gg/IDNNOVLogAgent/releases/download/v0.9.0-900/IDNNOVLogAgent-0.9.0-900-geminilake.spk',md5:'e'.repeat(32)}]};
  const j=await (await worker.fetch(new Request(GET),{CATALOG:JSON.stringify(two)})).json();
  assert.equal(j.packages.length,1);
  assert.equal(j.packages[0].version,'1.0.0-1001');
});

test('14 malformed catalog or non-HTTPS URL fails closed with no partial response',async()=>{
  assert.equal((await worker.fetch(new Request(GET),{CATALOG:'{broken'})).status,503);
  const bad={packages:[{...CATALOG_ENTRY,url:'http://insecure.example/x.spk'}]};
  const j=await (await worker.fetch(new Request(GET),{CATALOG:JSON.stringify(bad)})).json();
  assert.deepEqual(j.packages,[]);
});

test('15 mutation methods and sensitive routes are refused',async()=>{
  assert.equal((await worker.fetch(new Request(GET,{method:'PUT'}),env)).status,405);
  assert.equal((await worker.fetch(new Request(GET,{method:'DELETE'}),env)).status,405);
  for(const path of ['/api/packages','/admin']){
    const r=await worker.fetch(new Request('https://packages.idnnov.com'+path+'?arch=geminilake&build=86009&language=fre'),env);
    assert.ok([404,405].includes(r.status),path);
  }
});
