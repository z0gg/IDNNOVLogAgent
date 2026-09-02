const bounded=/^[A-Za-z0-9_.-]{1,32}$/;
function json(value,status=200){return new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':status===200?'public, max-age=300':'no-store','x-content-type-options':'nosniff','content-security-policy':"default-src 'none'"}})}
export default {async fetch(request,env){
  if(!['GET','POST'].includes(request.method))return json({error:'method_not_allowed'},405);
  const u=new URL(request.url),params=request.method==='POST'?new URLSearchParams(await request.text()):u.searchParams;
  const arch=params.get('arch')||'',buildRaw=params.get('build')||params.get('major')||'';
  if(!bounded.test(arch)||!/^[0-9]{1,8}$/.test(buildRaw))return json({error:'invalid_parameters'},400);
  const build=Number(buildRaw);let manifest;
  try{manifest=JSON.parse(env.CATALOG)}catch{return json({error:'catalog_unavailable'},503)}
  const packages=manifest.packages.filter(p=>p.arch===arch&&build>=p.min_build&&build<=p.max_build&&/^https:\/\/github\.com\/[^/]+\/[^/]+\/releases\/download\//.test(p.url)).map(p=>({package:p.package,version:p.version,arch:p.arch,dsmappname:'SYNO.SDS.App.IDNNOVLogAgent.Instance',name:'IDNNOV Log Agent',desc:'Agent Syslog RFC5424 vers HTTPS',link:p.url,size:p.size,checksum:p.sha256,checksum_type:'SHA256'}));
  return json({packages});
}};
