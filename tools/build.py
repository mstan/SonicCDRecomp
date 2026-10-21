#!/usr/bin/env python3
"""Generate owned-input native catalogs and build Sonic CD from pinned sources."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'external/segagenesisrecomp'


def invoke(command: list[str], env: dict[str, str]) -> None:
    print('+', subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def executable(directory: Path, name: str) -> Path:
    suffix = '.exe' if os.name == 'nt' else ''
    for relative in (f'Release/{name}{suffix}', f'{name}{suffix}', f'bin/{name}{suffix}',
                     f'runtime/Release/{name}{suffix}', f'runtime/{name}{suffix}'):
        candidate = directory / relative
        if candidate.is_file():
            return candidate
    raise ValueError(f'{name} was not produced under {directory}')


def build(args: argparse.Namespace) -> dict:
    work = args.work_dir.resolve()
    if os.name == 'nt' and work.drive.casefold() == 'c:':
        raise ValueError('The upstream generation tools require a build directory off C:.')
    work.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    state = work / 'host-state'
    for key, relative in {'TEMP':'tmp','TMP':'tmp','TMPDIR':'tmp',
                          'APPDATA':'appdata/Roaming','LOCALAPPDATA':'appdata/Local',
                          'XDG_CACHE_HOME':'cache','XDG_CONFIG_HOME':'config',
                          'XDG_DATA_HOME':'data','XDG_STATE_HOME':'state',
                          'PYTHONPYCACHEPREFIX':'python-cache','CCACHE_DIR':'ccache'}.items():
        directory = state / relative
        directory.mkdir(parents=True, exist_ok=True)
        env[key] = str(directory)
    env['SDL_AUDIODRIVER'] = 'dummy'
    cmake = args.cmake or shutil.which('cmake')
    if not cmake:
        raise ValueError('CMake is not available; pass --cmake PATH.')
    bios, disc = args.bios.resolve(strict=True), args.disc.resolve(strict=True)
    if disc.suffix.lower() == '.cue':
        source=ROOT/'launcher/SonicCD.py'
        spec=importlib.util.spec_from_file_location('sonic_cd_launcher',source)
        if spec is None or spec.loader is None:raise ValueError('Cannot load the disc-cache helper.')
        launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
        owned_inputs=work/'owned-inputs';owned_inputs.mkdir(exist_ok=True)
        disc=launcher.prepare_disc(disc,owned_inputs,ENGINE/'tools/segacd/disc_image.py',env)
    if disc.suffix.lower() != '.sgcd':
        raise ValueError('Select an SGCD image or CUE/BIN disc set.')
    configure = ['-G', args.generator] if args.generator else []
    catalogs = args.catalogs.resolve(strict=True) if args.catalogs else work/'catalogs'
    if not args.catalogs:
        tool_build, z80_build = work/'tools', work/'z80-frontend'
        invoke([cmake, '-S', str(ENGINE/'tests/segacd'), '-B', str(tool_build),
                '-DCMAKE_BUILD_TYPE=Release', *configure], env)
        invoke([cmake, '--build', str(tool_build), '--config', 'Release', '--parallel', str(args.jobs),
                '--target', 'segacd_module_recompiler', 'segacd_bios_floor_probe'], env)
        invoke([cmake, '-S', str(ROOT/'external/z80-frontend/recompiler'), '-B', str(z80_build),
                '-DCMAKE_BUILD_TYPE=Release', *configure], env)
        invoke([cmake, '--build', str(z80_build), '--config', 'Release', '--parallel', str(args.jobs),
                '--target', 'SmsRecomp'], env)
        command = [sys.executable, str(ENGINE/'tools/segacd/owned_native_generate.py'),
                   '--recipe', str(ENGINE/'tools/segacd/sonic_cd_us_recipe.json.gz'),
                   '--source-root', str(ENGINE), '--bios', str(bios), '--disc', str(disc),
                   '--generator', str(executable(tool_build, 'segacd_module_recompiler')),
                   '--probe', str(executable(tool_build, 'segacd_bios_floor_probe')),
                   '--z80-generator', str(executable(z80_build, 'SmsRecomp')),
                   '--output-dir', str(catalogs), '--cmake', cmake, '--parallel', str(args.jobs)]
        if args.resume:
            command.append('--resume')
        invoke(command, env)
    sdl_dir = args.sdl2_dir
    if sdl_dir is None:
        if os.name == 'nt':
            sdl_dir = ENGINE/'runner/external/SDL2/SDL2-2.28.5/cmake'
        else:
            libdir = subprocess.check_output(['pkg-config','--variable=libdir','sdl2'],
                                             env=env, text=True).strip()
            sdl_dir = Path(libdir)/'cmake/SDL2'
    output = work/'game'
    invoke([sys.executable, str(ENGINE/'tools/segacd/native_catalog_build.py'),
            '--source-root', str(ENGINE), '--bios', str(bios), '--disc', str(disc),
            '--catalog-manifest', str(catalogs/'catalog-manifest.json'),
            '--base-catalogs', str(catalogs/'base-catalogs.txt'),
            '--append-overlays', str(catalogs/'append-overlays.txt'),
            '--build-dir', str(output), '--sdl2-dir', str(sdl_dir)], env)
    invoke([cmake, '-S', str(ROOT), '-B', str(output),
            '-C', str(output/'segacd-native-initial-cache.cmake'),
            '-DCMAKE_BUILD_TYPE=Release', *configure], env)
    invoke([cmake, '--build', str(output), '--config', 'Release',
            '--target', 'SonicCD', '--parallel', str(args.jobs)], env)
    result = {'version':'0.0.1', 'executable':str(executable(output,'SonicCD')),
              'catalogs':str(catalogs), 'build_directory':str(output),
              'engine_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ENGINE,text=True).strip(),
              'configured':True,'built':True}
    (work/'build-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bios',required=True,type=Path)
    p.add_argument('--disc',required=True,type=Path)
    p.add_argument('--work-dir',required=True,type=Path)
    p.add_argument('--catalogs',type=Path,help='Reuse an existing hash-verified native catalog bundle')
    p.add_argument('--resume',action='store_true',help='Verify and reuse completed generation steps')
    p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--cmake')
    p.add_argument('--generator',help='CMake generator, e.g. Ninja')
    p.add_argument('--sdl2-dir',type=Path)
    args=p.parse_args()
    if args.jobs<1:p.error('--jobs must be positive')
    try:print(json.dumps(build(args),indent=2))
    except (ValueError,OSError,subprocess.CalledProcessError) as error:
        print(f'Build failed: {error}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
