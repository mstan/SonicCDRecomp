#!/usr/bin/env python3
"""Record Linux runtime source packages, licenses and final AppDir identities."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    appdir,tools=(Path(x).resolve(strict=True) for x in sys.argv[1:])
    payload=appdir/'usr/bin';licenses=payload/'licenses/system';licenses.mkdir(parents=True)
    cache=subprocess.check_output(['ldconfig','-p'],text=True)
    lookup={}
    for line in cache.splitlines():
        if 'x86-64' not in line:continue
        match=re.search(r'^\s*(\S+) .* => (/.+)$',line)
        if match:
            path=Path(match[2]);lookup[match[1]]=path
            if path.exists():lookup[path.resolve().name]=path
    libraries=[];packages={}
    for library in sorted((appdir/'usr/lib').glob('*')):
        if not library.is_file():continue
        source=lookup.get(library.name)
        if source is None:raise ValueError(f'Cannot identify source package for {library.name}')
        candidates=[str(source),str(source.resolve())]
        if str(source).startswith('/lib/'):candidates.append('/usr'+str(source))
        if str(source).startswith('/usr/lib/'):candidates.append(str(source)[4:])
        package=None
        for candidate in candidates:
            result=subprocess.run(['dpkg-query','-S',candidate],capture_output=True,text=True)
            if result.returncode==0:
                package=result.stdout.splitlines()[0].split(': ',1)[0];break
        if not package:raise ValueError(f'Cannot identify Debian source package for {library.name}')
        if package not in packages:
            version=subprocess.check_output(['dpkg-query','-W','-f=${Version}',package],text=True)
            copyright_file=Path('/usr/share/doc')/package.split(':')[0]/'copyright'
            target=licenses/(package.replace(':','-')+'-copyright.txt')
            shutil.copyfile(copyright_file,target)
            packages[package]={'version':version,'copyright_file':target.relative_to(appdir).as_posix()}
        libraries.append({'path':library.relative_to(appdir).as_posix(),'package':package,'sha256':digest(library)})
    common=licenses/'common';common.mkdir()
    for path in Path('/usr/share/common-licenses').iterdir():
        if path.is_file():shutil.copyfile(path,common/(path.name+'.txt'))
    shutil.copyfile(tools/'AppImage-runtime-LICENSE.txt',payload/'licenses/AppImage-runtime.txt')
    inventory={'libraries':libraries,'packages':packages,
               'appimage_runtime':{'source':'https://github.com/AppImage/type2-runtime/tree/fedfad51acc2860b2916a1eef32ba4a500ff31ef',
                   'sha256':digest(tools/'runtime-x86_64'),'license':'usr/bin/licenses/AppImage-runtime.txt'}}
    info_path=payload/'BUILD-INFO.json';info=json.loads(info_path.read_text())
    info['runner_sha256_before_packaging']=info['runner_sha256']
    info['runner_sha256']=digest(payload/'SonicCD')
    info['linux_runtime']=inventory
    info_path.write_text(json.dumps(info,indent=2)+'\n')
    files=[]
    for path in sorted(appdir.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(appdir).as_posix()
        if not path.resolve().is_relative_to(appdir):raise ValueError(f'AppDir link escapes staging: {relative}')
        if relative=='package-manifest.json':continue
        if path.suffix.lower() in ('.sgcd','.cue','.bin','.iso','.wav','.log','.exe'):
            raise ValueError(f'Unexpected media/diagnostic artifact: {relative}')
        if 'userdata' in path.relative_to(appdir).parts:raise ValueError('AppDir contains a personal profile.')
        files.append({'path':relative,'bytes':path.stat().st_size,'sha256':digest(path)})
    manifest={'schema':'SonicCDLinuxAppDir1','version':'0.0.1','platform':'linux-x86_64',
              'owner_media_copied':False,'source':info,'files':files}
    (appdir/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':len(files),'system_libraries':len(libraries),'source_packages':len(packages),
                      'runner_sha256':info['runner_sha256']},indent=2))


if __name__=='__main__':main()
