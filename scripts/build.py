#!/usr/bin/env python3
"""Create a byte-reproducible DSM SPK from reviewed source inputs."""
import argparse, gzip, hashlib, json, os, shutil, stat, struct, tarfile, tempfile, zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; EPOCH=int(os.environ.get("SOURCE_DATE_EPOCH","1788230400")); NAME="IDNNOVLogAgent-1.0.3-1004-x86_64.spk"
def png(path,size):
    raw=b''.join(b'\0'+bytes((18,115,222,255))*size for _ in range(size))
    def chunk(kind,data): return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b''))
def normalize(root):
    for p in sorted(root.rglob('*')):
        os.utime(p,(EPOCH,EPOCH),follow_symlinks=False)
        if p.is_dir(): p.chmod(0o755)
        elif p.name.endswith('.cgi') or p.parent.name=='scripts' or p.parent.name=='bin': p.chmod(0o755)
        else: p.chmod(0o644)
def add_tree(tf,root):
    for p in sorted(root.rglob('*'),key=lambda x:x.as_posix()):
        arc=p.relative_to(root).as_posix(); info=tf.gettarinfo(str(p),arc); info.uid=info.gid=0; info.uname=info.gname='root'; info.mtime=EPOCH
        if p.is_file():
            with p.open('rb') as f: tf.addfile(info,f)
        else: tf.addfile(info)
def build(binary):
    if not binary.is_file(): raise SystemExit(f"verified cross-build input missing: {binary}")
    artifact=ROOT/'artifacts'/NAME; artifact.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='idnnov-spk-') as td:
        stage=Path(td); payload=stage/'payload'; outer=stage/'outer'; shutil.copytree(ROOT/'pkgroot',payload); shutil.copytree(ROOT/'spk',outer)
        shutil.rmtree(payload/'lib/idnnov_agent/__pycache__',ignore_errors=True)
        shutil.copytree(ROOT/'src/idnnov_agent',payload/'lib/idnnov_agent',ignore=shutil.ignore_patterns('__pycache__')); shutil.copy2(binary,payload/'bin/fluent-bit'); (payload/'scripts').mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/'spk/scripts/service-setup',payload/'scripts/service-setup')
        shutil.copy2(payload/'bin/api.cgi',payload/'ui/api.cgi'); png(payload/'ui/images/icon-64.png',64); png(payload/'ui/images/icon-256.png',256)
        png(outer/'PACKAGE_ICON.PNG',64); png(outer/'PACKAGE_ICON_256.PNG',256)
        normalize(payload); normalize(outer)
        package=outer/'package.tgz'
        with package.open('wb') as raw, gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=EPOCH,compresslevel=9) as gz, tarfile.open(fileobj=gz,mode='w',format=tarfile.GNU_FORMAT) as tf: add_tree(tf,payload)
        os.utime(package,(EPOCH,EPOCH)); package.chmod(0o644)
        info=(outer/'INFO').read_text()
        if 'support_conf_folder=' not in info: info+=f'support_conf_folder="yes"\n'
        pkg_md5=hashlib.md5(package.read_bytes()).hexdigest()
        import re as _re
        info=_re.sub(r'checksum="[^"]*"\n?', '', info)+f'checksum="{pkg_md5}"\n'
        (outer/'INFO').write_text(info); os.utime(outer/'INFO',(EPOCH,EPOCH)); (outer/'INFO').chmod(0o644)
        with artifact.open('wb') as raw, tarfile.open(fileobj=raw,mode='w',format=tarfile.GNU_FORMAT) as tf: add_tree(tf,outer)
    digest=hashlib.sha256(artifact.read_bytes()).hexdigest(); (ROOT/'artifacts/SHA256SUMS').write_text(f"{digest}  {NAME}\n")
    with tarfile.open(artifact) as tf, tarfile.open(fileobj=tf.extractfile('package.tgz'),mode='r:gz') as pt:
        manifest=[{"path":m.name,"size":m.size,"mode":oct(m.mode)} for m in pt.getmembers() if m.isfile()]
    (ROOT/'artifacts/manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n'); return artifact
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--fluent-bit',type=Path,required=True); print(build(p.parse_args().fluent_bit))
