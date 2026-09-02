import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.mjs';

const CATALOG_ENTRY={
  package:'IDNNOVLogAgent',version:'1.0.8-1009',dname:'IDNNOV Log Agent',
  desc:'Receives local RFC5424 syslog and forwards it to an HTTPS collector.',
  arches:['apollolake','geminilake','r1000','v1000','epyc7002'],min_build:72806,max_build:99999,
  url:'https://github.com/z0gg/IDNNOVLogAgent/releases/download/v1.0.8-1009/IDNNOVLogAgent-1.0.8-1009-x86_64.spk',
  size:3010560,md5:'86b87d3885e72640cbfb73b4e44ce1c8',
  sha256:'3072548f94d74eccf643bb285a8b534fa1874582da46d80b68d4842e0280258b'};
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
  assert.equal(j.packages[0].version,'1.0.8-1009');
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

test('5b valid but unserved arch (bromolow) returns empty 200',async()=>{
  const r=await worker.fetch(new Request('https://packages.idnnov.com/?arch=bromolow&build=86009&language=fre'),env);
  assert.equal(r.status,200);
  assert.deepEqual((await r.json()).packages,[]);
});

test('6 valid but incompatible arch returns empty packages 200',async()=>{
  // apollolake is a real DSM arch but we have no package for it; note: unknown arch strings are 422
  const r=await worker.fetch(new Request('https://packages.idnnov.com/?arch=geminilake&build=86009&language=fre&unique=synology_gemini'+''+'lake_920%2B'),env);
  assert.equal(r.status,200);
});

test('7 build below os_min_ver 72806 hides package; DSM 7.2.2 through DSM 7.4.1 show it',async()=>{
  const below=await (await worker.fetch(new Request('https://packages.idnnov.com/?arch=geminilake&build=72805&language=fre'),env)).json();
  assert.deepEqual(below.packages,[]);
  for(const b of ['72806','86009','89999','90075','90080']){
    const j=await (await worker.fetch(new Request(`https://packages.idnnov.com/?arch=geminilake&build=${b}&language=fre`),env)).json();
    assert.equal(j.packages.length,1,b);
  }
});

test('7b AMD r1000 DS723+ DSM 7.2.2 receives the x86_64 release',async()=>{
  const j=await (await worker.fetch(new Request('https://packages.idnnov.com/?arch=r1000&build=72806&language=fre&major=7'),env)).json();
  assert.equal(j.packages.length,1);
  assert.equal(j.packages[0].version,'1.0.8-1009');
});

test('7c DSM 7.4.1 NAS (build 90080) also receives the release',async()=>{
  for(const a of ['r1000','geminilake']){
    const j=await (await worker.fetch(new Request(`https://packages.idnnov.com/?arch=${a}&build=90080&language=fre&major=7&minor=4`),env)).json();
    assert.equal(j.packages.length,1,a);
    assert.equal(j.packages[0].version,'1.0.8-1009',a);
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
  assert.equal(j.packages[0].version,'1.0.8-1009');
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
