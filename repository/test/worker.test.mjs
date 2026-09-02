import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.mjs';

const env={CATALOG:JSON.stringify({packages:[{package:'IDNNOVLogAgent',version:'1.0.0-1001',arch:'geminilake',min_build:86009,max_build:89999,url:'https://github.com/idnnov/idnnov-log-agent/releases/download/v1.0.0-1001/IDNNOVLogAgent-1.0.0-1001-geminilake.spk',size:123,sha256:'a'.repeat(64)}]})};
test('returns one compatible immutable GitHub Release asset',async()=>{const r=await worker.fetch(new Request('https://packages.idnnov.com/?arch=geminilake&build=86009&language=fre'),env);assert.equal(r.status,200);const j=await r.json();assert.equal(j.packages.length,1);assert.match(j.packages[0].link,/github\.com\/idnnov\/idnnov-log-agent\/releases\/download\/v1\.0\.0-1001/)});
test('filters incompatible architecture and build',async()=>{for(const query of ['arch=apollolake&build=86009','arch=geminilake&build=72806']){const r=await worker.fetch(new Request('https://packages.idnnov.com/?'+query),env);assert.deepEqual((await r.json()).packages,[])}});
test('rejects malformed parameters and mutations',async()=>{assert.equal((await worker.fetch(new Request('https://packages.idnnov.com/?arch=x%0a&build=abc'),env)).status,400);assert.equal((await worker.fetch(new Request('https://packages.idnnov.com/',{method:'PUT'}),env)).status,405)});
