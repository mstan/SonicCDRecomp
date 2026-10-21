#!/usr/bin/env python3
"""Portable Linux launcher for Sonic CD Recompiled."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SCHEMA='SegaCDWindowsPortablePackage1'


def file_hash(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                                         prefix=path.name+'.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def load_config(path: Path) -> dict:
    if not path.exists():return {'schema':SCHEMA,'bios_path':None,'disc_path':None}
    config=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(config,dict) or config.get('schema')!=SCHEMA:
        raise ValueError(f'Unsupported input configuration: {path}')
    for key in ('bios_path','disc_path'):
        if config.get(key) is not None and not isinstance(config[key],str):
            raise ValueError(f'Invalid {key} in input configuration: {path}')
    return config


def select_file(title: str, env: dict | None = None) -> Path:
    if shutil.which('zenity'):
        command=['zenity','--file-selection','--title',title]
    elif shutil.which('kdialog'):
        command=['kdialog','--title',title,'--getopenfilename',str(Path.home())]
    else:
        raise ValueError('Input selection needs Zenity/KDialog, or pass --bios PATH --disc PATH.')
    selected=subprocess.run(command,capture_output=True,text=True,env=env)
    if selected.returncode or not selected.stdout.strip():raise ValueError('Input selection cancelled.')
    return Path(selected.stdout.rstrip('\r\n')).resolve(strict=True)


def inspect_cue(converter: Path, cue: Path, env: dict) -> dict:
    output=subprocess.check_output([sys.executable,str(converter),'inspect-cue',str(cue)],env=env,text=True)
    value=json.loads(output)
    if value.get('schema')!='SGCDCueSourceIdentity1':raise ValueError('Unexpected CUE inspection format.')
    return value


def prepare_disc(disc: Path, data: Path, converter: Path, env: dict) -> Path:
    disc=disc.resolve(strict=True)
    if disc.suffix.lower()=='.sgcd':return disc
    if disc.suffix.lower()!='.cue':raise ValueError('Select an SGCD image or a CUE/BIN disc set.')
    identity=inspect_cue(converter,disc,env)
    key=hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    directory=data/'disc';directory.mkdir(exist_ok=True)
    output=directory/f'owned-{key}.sgcd';manifest=output.with_suffix('.json')
    if output.exists() or manifest.exists():
        if not output.is_file() or not manifest.is_file():raise ValueError('Incomplete converted-disc cache; move its matching image/manifest aside and retry.')
        saved=json.loads(manifest.read_text())
        if saved.get('schema')!='SonicCDCueCache1' or saved.get('source_identity')!=identity or saved.get('sgcd_sha256')!=file_hash(output):
            raise ValueError('Converted-disc cache content changed; move its matching image/manifest aside and retry.')
        return output
    temporary=output.with_suffix('.partial.sgcd')
    try:
        subprocess.run([sys.executable,str(converter),str(disc),str(temporary)],env=env,check=True)
        if inspect_cue(converter,disc,env)!=identity:raise ValueError('CUE or tracks changed during conversion; result rejected.')
        digest=file_hash(temporary)
        os.replace(temporary,output)
        atomic_json(manifest,{'schema':'SonicCDCueCache1','source_identity':identity,'sgcd_sha256':digest})
    finally:temporary.unlink(missing_ok=True)
    return output


def seed_profile(data: Path, payload: Path) -> tuple[Path,Path]:
    data.mkdir(parents=True,exist_ok=True)
    settings=data/'sonic-cd-settings.ini';backup=data/'sonic-cd.brm'
    if not settings.exists():
        with settings.open('x',encoding='ascii') as stream:
            stream.write('fullscreen=0\nwindow_scale=3\nlinear_filter=0\naudio_enabled=1\nvolume=100\nview_mode=2\n')
    seed=payload/'seed/sonic-cd.brm'
    if not backup.exists() and seed.is_file():
        if seed.stat().st_size!=8192:raise ValueError('Invalid empty backup-RAM seed.')
        with backup.open('xb') as stream:stream.write(seed.read_bytes())
    return settings,backup


def run(args: argparse.Namespace) -> int:
    payload=Path(os.environ.get('SONICCD_PAYLOAD_ROOT',Path(__file__).resolve().parent)).resolve()
    package=Path(os.environ.get('SONICCD_PACKAGE_HOME',payload)).resolve()
    data=(args.data_root or package/'userdata').resolve()
    data.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy()
    for key,relative in {'TEMP':'temp','TMP':'temp','TMPDIR':'temp','APPDATA':'appdata/Roaming',
                         'LOCALAPPDATA':'appdata/Local','XDG_CACHE_HOME':'xdg/cache',
                         'XDG_CONFIG_HOME':'xdg/config','XDG_DATA_HOME':'xdg/data',
                         'XDG_STATE_HOME':'xdg/state','PYTHONPYCACHEPREFIX':'python-cache'}.items():
        directory=data/relative;directory.mkdir(parents=True,exist_ok=True);env[key]=str(directory)
    # Dialogs and the converter use host libraries. Only the game process gets
    # the packaged native-library search path below.
    env.pop('LD_LIBRARY_PATH',None);env.pop('LD_PRELOAD',None)
    config_path=data/'portable-config.json';config=load_config(config_path)
    bios=args.bios or (Path(config['bios_path']) if config.get('bios_path') else None)
    disc=args.disc or (Path(config['disc_path']) if config.get('disc_path') else None)
    if bios is None or not bios.is_file():bios=select_file('Sonic CD - select your Sega CD BIOS',env)
    if disc is None or not disc.is_file():disc=select_file('Sonic CD - select your disc image',env)
    bios=bios.resolve(strict=True);disc=disc.resolve(strict=True)
    if not bios.is_file() or not disc.is_file():raise ValueError('Selected input is not a regular file.')
    converted=prepare_disc(disc,data,payload/'tools/segacd/disc_image.py',env)
    config.update(bios_path=str(bios),disc_path=str(disc));atomic_json(config_path,config)
    settings,backup=seed_profile(data,payload)
    binary=payload/'SonicCD'
    if not binary.is_file():raise ValueError(f'Game executable missing: {binary}')
    native_env=env.copy()
    if native_env.get('SDL_AUDIODRIVER')=='dummy':native_env.pop('SDL_AUDIODRIVER')
    if args.mute:native_env['SDL_AUDIODRIVER']='dummy'
    libraries=payload.parent/'lib'
    if libraries.is_dir():native_env['LD_LIBRARY_PATH']=str(libraries)
    arguments=[str(binary),'--bios',str(bios),'--disc',str(converted),
               '--backup',str(backup),'--settings',str(settings)]
    if args.mute:arguments.append('--mute')
    arguments.extend(args.runner_args[1:] if args.runner_args[:1]==['--'] else args.runner_args)
    logs=data/'logs';logs.mkdir(exist_ok=True)
    with (logs/'SonicCD.log').open('ab') as log:
        return subprocess.run(arguments,cwd=data,env=native_env,stdout=log,stderr=subprocess.STDOUT).returncode


def main() -> int:
    parser=argparse.ArgumentParser(description='Sonic CD Recompiled 0.0.1')
    parser.add_argument('--bios',type=Path)
    parser.add_argument('--disc',type=Path)
    parser.add_argument('--data-root',type=Path)
    parser.add_argument('--mute',action='store_true')
    parser.add_argument('--version',action='version',version='Sonic CD Recompiled 0.0.1')
    parser.add_argument('runner_args',nargs=argparse.REMAINDER)
    try:return run(parser.parse_args())
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        print(f'Sonic CD: {error}',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
