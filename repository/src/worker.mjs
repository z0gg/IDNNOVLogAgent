import embeddedCatalog from '../catalog/releases.json' with {type:'json'};

const BOUNDED=/^[A-Za-z0-9_.-]{1,32}$/;
const BUILD_RE=/^[0-9]{1,8}$/;
const KNOWN_ARCH=new Set(['apollolake','avoton','braswell','broadwell','broadwellnk','broadwellnkv2','broadwellntbap','bromolow','cedarview','denverton','epyc7002','geminilake','geminilakenk','grantley','icelaked','kvmx64','purley','r1000','r1000nk','v1000','v1000nk']);
const KNOWN_LANG=new Set(['enu','fre','deu','esn','ita','jpn','krn','ptg','rus','chs','cht','nld','nor','sve','dan','plk','hun','trk','csy','brazil']);
function json(value,status=200){return new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff','content-security-policy':"default-src 'none'"}})}
function semverKey(p){const[v,rev]=p.version.split('-');const nums=v.split('.').map(Number);return ((nums[0]||0)*1e10)+((nums[1]||0)*1e6)+((nums[2]||0)*1e3)+Number(rev||0)}
export default {async fetch(request,env){
  if(!['GET','POST'].includes(request.method))return json({error:'method_not_allowed'},405);
  const u=new URL(request.url);
  if(u.pathname!=='/')return json({error:'not_found'},404);
  const params=request.method==='POST'?new URLSearchParams(await request.text()):u.searchParams;
  const get=k=>params.get(k);
  // Required params: absent -> 400 (spkrepo MissingParameter)
  for(const k of ['arch','build','language']){if(get(k)===null||get(k)==='')return json({error:'missing_required_parameter'},400)}
  const arch=get('arch'),language=get('language'),buildRaw=get('build'),majorRaw=get('major');
  // Present but malformed -> 422 (spkrepo UnprocessableEntity)
  if(!BOUNDED.test(arch))return json({error:'invalid_arch'},422);
  if(!BOUNDED.test(language))return json({error:'invalid_language'},422);
  if(!BUILD_RE.test(buildRaw))return json({error:'invalid_build'},422);
  const build=Number(buildRaw);
  if(!KNOWN_ARCH.has(arch))return json({error:'invalid_arch'},422);
  if(!KNOWN_LANG.has(language))return json({error:'invalid_language'},422);
  // major: explicit (6/7 valid) or inferred from build (DSM 7 builds 40000-99999, DSM 6 below)
  let major;
  if(majorRaw!==null){
    if(!BUILD_RE.test(majorRaw))return json({error:'invalid_major'},422);
    major=Number(majorRaw);
    if(major!==6&&major!==7)return json({error:'invalid_major'},422);
  }else{
    major=build>=40000?7:6;
  }
  if(major!==7)return json({packages:[]}); // we serve nothing to DSM 6
  let manifest;
  try{manifest=env.CATALOG?JSON.parse(env.CATALOG):embeddedCatalog}catch{return json({error:'catalog_unavailable'},503)}
  const httpsRe=/^https:\/\/github\.com\/[^/]+\/[^/]+\/releases\/download\//;
  const compatible=(manifest.packages||[])
    .filter(p=>p&&(Array.isArray(p.arches)?p.arches.includes(arch):p.arch===arch)&&build>=p.min_build&&build<=p.max_build&&httpsRe.test(p.url||'')&&typeof p.size==='number'&&/^[0-9a-f]{32}$/.test(p.md5||''))
    .sort((a,b)=>semverKey(b)-semverKey(a));
  if(compatible.length===0)return json({packages:[]});
  const p=compatible[0];
  return json({packages:[{
    package:p.package,version:p.version,dname:p.dname||p.package,desc:p.desc||'',
    link:p.url,thumbnail:Array.isArray(p.thumbnail)?p.thumbnail:[],
    thumbnail_retina:Array.isArray(p.thumbnail_retina)?p.thumbnail_retina:[],
    qinst:false,qupgrade:false,qstart:false,
    deppkgs:null,conflictpkgs:null,download_count:0,recent_download_count:0,
    snapshot:[],md5:p.md5,size:p.size,startable:'yes',
    changelog:p.changelog||'',distributor:'IDNNOV',distributor_url:'https://idnnov.com',
    maintainer:'IDNNOV',maintainer_url:'https://idnnov.com'
  }]});
}};
