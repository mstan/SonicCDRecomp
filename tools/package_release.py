#!/usr/bin/env python3
"""Allowlisted public Sonic CD Windows package and Linux AppDir staging."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ENGINE=Path(os.environ.get('GENESIS_RECOMP_ROOT',ROOT/'external/segagenesisrecomp')).resolve()
VERSION='0.0.2'
EMPTY_BRAM_SHA='4390aad972163d9bbc8a8cd7d32e86b216e5a17a0d795c7d230942155e6a895b'
CRT_DLLS={'vcruntime140.dll','vcruntime140_1.dll','vcruntime140_threads.dll',
          'msvcp140.dll','msvcp140_1.dll','msvcp140_2.dll','msvcp140_atomic_wait.dll',
          'msvcp140_codecvt_ids.dll','concrt140.dll'}
PUBLIC_FILES={'LICENSE','THIRD-PARTY-LICENSES.md','README-portable-windows.md','README.txt',
              'SonicCD.exe','SDL2.dll','SonicCD.ps1','SonicCD.cmd','SonicCD','SonicCD.py',
              'BUILD-INFO.json','tools/segacd/disc_image.py','seed/sonic-cd.brm',
              'userdata/portable-config.json'}|CRT_DLLS


def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def git_head(path: Path) -> str:
    return subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd=path,text=True).strip()


def source_info() -> dict:
    return {'project':'SonicCDRecomp','version':VERSION,
            'source_url':'https://github.com/mstan/SonicCDRecomp',
            'game_revision':git_head(ROOT),'engine_revision':git_head(ENGINE),
            'm68k_core_revision':git_head(ENGINE/'external/m68k-recomp-core'),
            'z80_core_revision':git_head(ENGINE/'external/z80-recomp-core'),
            'z80_frontend_revision':git_head(ROOT/'external/z80-frontend')}


def check_seed(seed: Path | None) -> None:
    if seed is not None and (seed.stat().st_size!=8192 or digest(seed)!=EMPTY_BRAM_SHA):
        raise ValueError('Only the qualified empty BIOS-formatted BRAM seed may be packaged.')


def pe_imports(path: Path) -> set[str]:
    data=path.read_bytes()
    if data[:2]!=b'MZ':raise ValueError(f'Not a Windows executable: {path.name}')
    pe=struct.unpack_from('<I',data,0x3c)[0]
    if data[pe:pe+4]!=b'PE\0\0':raise ValueError('Invalid PE signature.')
    machine,count=struct.unpack_from('<HH',data,pe+4)
    if machine!=0x8664:raise ValueError('The initial Windows release requires x64 binaries.')
    optional=pe+24;size=struct.unpack_from('<H',data,pe+20)[0]
    if struct.unpack_from('<H',data,optional)[0]!=0x20b:raise ValueError('Expected PE32+ executable.')
    sections=[]
    for index in range(count):
        vs,va,raw,offset=struct.unpack_from('<IIII',data,optional+size+40*index+8)
        sections.append((va,max(vs,raw),offset))
    def file_offset(rva):
        for va,length,offset in sections:
            if va<=rva<va+length:return offset+rva-va
        raise ValueError('PE import points outside section data.')
    import_rva=struct.unpack_from('<I',data,optional+120)[0]
    if not import_rva:return set()
    cursor=file_offset(import_rva);names=set()
    while True:
        descriptor=struct.unpack_from('<IIIII',data,cursor)
        if not any(descriptor):break
        start=file_offset(descriptor[3]);end=data.index(b'\0',start)
        names.add(data[start:end].decode('ascii').lower());cursor+=20
    return names


def file_record(root: Path,path: Path) -> dict:
    return {'path':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)}


def audit_licenses(root: Path) -> None:
    if not root.is_dir():raise ValueError(f'License directory missing: {root}')
    for path in root.rglob('*'):
        if path.is_symlink():raise ValueError(f'License symlink is not permitted: {path.name}')
        if not path.is_file():continue
        if path.suffix.lower() not in ('.txt','.md','.rtf') or path.stat().st_size>2*1024*1024:
            raise ValueError(f'Unexpected license payload: {path.name}')
        text=path.read_text(encoding='latin-1' if path.suffix.lower()=='.rtf' else 'utf-8-sig')
        if path.suffix.lower()=='.rtf' and not text.startswith('{\\rtf'):
            raise ValueError(f'Invalid RTF license document: {path.name}')
        if path.suffix.lower()=='.rtf':text=text.rstrip('\0')
        if '\0' in text:raise ValueError(f'Binary content in license file: {path.name}')


def audit_public_tree(root: Path, manifest: dict) -> None:
    audit_licenses(root/'licenses')
    recorded=set()
    for row in manifest['files']:
        name=row['path'];relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name or name in recorded:
            raise ValueError(f'Unsafe/duplicate manifest path: {name}')
        recorded.add(name)
        path=root/name
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f'Package file missing or outside package: {name}')
        if path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:
            raise ValueError(f'Package file content changed: {name}')
        if name not in PUBLIC_FILES and not name.startswith('licenses/'):
            raise ValueError(f'Unexpected public package member: {name}')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual!=recorded|{'package-manifest.json'}:
        raise ValueError(f'Unrecorded package content: {sorted(actual-(recorded|{"package-manifest.json"}))}')
    config=root/'userdata/portable-config.json'
    if config.exists():
        c=json.loads(config.read_text())
        if c.get('bios_path') is not None or c.get('disc_path') is not None:
            raise ValueError('Public package contains machine-specific owned-input paths.')
    seed=root/'seed/sonic-cd.brm'
    if seed.exists():check_seed(seed)
    if manifest.get('owner_media_copied') is not False:raise ValueError('Missing no-owned-media declaration.')


def stage_windows(args: argparse.Namespace) -> dict:
    destination=args.destination.resolve()
    check_seed(args.blank_seed)
    audit_licenses(args.licenses_dir)
    command=[sys.executable,str(ENGINE/'tools/segacd/package_windows.py'),'create',
             '--exe',str(args.exe),'--sdl2-dll',str(args.sdl2_dll),
             '--destination',str(destination),'--licenses-dir',str(args.licenses_dir)]
    if args.blank_seed:command+=['--blank-backup-seed',str(args.blank_seed)]
    subprocess.run(command,check=True)
    shutil.copyfile(ROOT/'launcher/SonicCD.ps1',destination/'SonicCD.ps1')
    shutil.copyfile(ROOT/'launcher/SonicCD.cmd',destination/'SonicCD.cmd')
    shutil.copyfile(ROOT/'release/README.txt',destination/'README-portable-windows.md')
    shutil.copyfile(ROOT/'THIRD-PARTY-LICENSES.md',destination/'THIRD-PARTY-LICENSES.md')
    required={name for name in pe_imports(destination/'SonicCD.exe') if name.startswith(('vcruntime','msvcp','concrt'))}
    if required:
        if not args.crt_dir or not args.crt_license:raise ValueError('This executable needs --crt-dir and --crt-license for app-local Microsoft runtimes.')
        if not required<=CRT_DLLS:raise ValueError(f'Unrecognized Microsoft runtime imports: {sorted(required-CRT_DLLS)}')
        for name in sorted(required):
            source=args.crt_dir/name
            pe_imports(source)
            shutil.copyfile(source,destination/name)
        suffix=args.crt_license.suffix.lower()
        if suffix not in ('.txt','.rtf','.md'):raise ValueError('Supply Microsoft runtime license as text or RTF.')
        shutil.copyfile(args.crt_license,destination/('licenses/MSVC-runtime'+suffix))
    info=source_info();info.update(platform='windows-x64',runner_sha256=digest(destination/'SonicCD.exe'))
    (destination/'BUILD-INFO.json').write_text(json.dumps(info,indent=2)+'\n')
    manifest=json.loads((destination/'package-manifest.json').read_text())
    manifest.update(version=VERSION,platform='windows-x64',source=info)
    manifest['files']=[file_record(destination,path) for path in sorted(destination.rglob('*'))
                       if path.is_file() and path.name!='package-manifest.json']
    (destination/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    audit_public_tree(destination,manifest)
    archive=args.archive.resolve()
    if archive.exists():raise ValueError(f'Refusing to replace an existing archive: {archive}')
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in sorted([r['path'] for r in manifest['files']]+['package-manifest.json']):
            z.write(destination/name,'SonicCD/'+name)
    return {'archive':str(archive),'sha256':digest(archive),'runner_sha256':info['runner_sha256'],'files':len(manifest['files'])+1}


def stage_linux(args: argparse.Namespace) -> dict:
    destination=args.destination.resolve()
    if destination.exists():raise ValueError(f'AppDir already exists: {destination}')
    with args.exe.open('rb') as stream:
        if stream.read(4)!=b'\x7fELF':raise ValueError('Linux executable is not ELF.')
    check_seed(args.blank_seed)
    audit_licenses(args.licenses_dir)
    payload=destination/'usr/bin';payload.mkdir(parents=True)
    shutil.copyfile(args.exe,payload/'SonicCD');(payload/'SonicCD').chmod(0o755)
    shutil.copyfile(ROOT/'launcher/SonicCD.py',payload/'SonicCD.py')
    shutil.copyfile(ROOT/'launcher/AppRun',destination/'AppRun');(destination/'AppRun').chmod(0o755)
    for source,target in [(ROOT/'LICENSE',payload/'LICENSE'),
                          (ROOT/'THIRD-PARTY-LICENSES.md',payload/'THIRD-PARTY-LICENSES.md'),
                          (ROOT/'release/README.txt',payload/'README.txt')]:shutil.copyfile(source,target)
    licenses=payload/'licenses';shutil.copytree(args.licenses_dir,licenses)
    notices={'SDL2.txt':'runner/external/SDL2/SDL2-2.28.5/COPYING.txt',
             'ymfm.txt':'runner/external/ymfm/LICENSE','ares.txt':'runner/cd/ARES-LICENSE.txt',
             'm68k-recomp-core.txt':'external/m68k-recomp-core/LICENSE','z80-recomp-core.txt':'external/z80-recomp-core/LICENSE'}
    for name,relative in notices.items():shutil.copyfile(ENGINE/relative,licenses/name)
    converter=payload/'tools/segacd';converter.mkdir(parents=True)
    shutil.copyfile(ENGINE/'tools/segacd/disc_image.py',converter/'disc_image.py')
    if args.blank_seed:
        (payload/'seed').mkdir();shutil.copyfile(args.blank_seed,payload/'seed/sonic-cd.brm')
    shutil.copyfile(ROOT/'release/sonic-cd.svg',destination/'sonic-cd.svg')
    (destination/'.DirIcon').symlink_to('sonic-cd.svg')
    (destination/'sonic-cd.desktop').write_text('[Desktop Entry]\nType=Application\nName=Sonic CD\nExec=SonicCD\nIcon=sonic-cd\nCategories=Game;\nTerminal=false\n')
    info=source_info();info.update(platform='linux-x86_64',minimum_glibc='2.39',runner_sha256=digest(payload/'SonicCD'))
    (payload/'BUILD-INFO.json').write_text(json.dumps(info,indent=2)+'\n')
    return {'appdir':str(destination),'runner_sha256':info['runner_sha256']}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='command',required=True)
    windows=subs.add_parser('windows')
    linux=subs.add_parser('linux-appdir')
    for command in (windows,linux):
        command.add_argument('--exe',required=True,type=Path)
        command.add_argument('--licenses-dir',required=True,type=Path)
        command.add_argument('--destination',required=True,type=Path)
        command.add_argument('--blank-seed',type=Path)
    windows.add_argument('--sdl2-dll',required=True,type=Path)
    windows.add_argument('--archive',required=True,type=Path)
    windows.add_argument('--crt-dir',type=Path,help='Approved x64 Microsoft redistributable DLL directory')
    windows.add_argument('--crt-license',type=Path)
    args=parser.parse_args()
    try:print(json.dumps(stage_windows(args) if args.command=='windows' else stage_linux(args),indent=2))
    except (OSError,ValueError,struct.error,subprocess.CalledProcessError) as error:
        print(f'Packaging failed: {error}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
