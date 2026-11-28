"""Release integration checks use synthetic binaries, never retail inputs."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('release_runtime_package', ROOT/'tools/package_release.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


def pe(path, imports=(), machine=0x8664):
    data=bytearray(2048);data[:2]=b'MZ'
    struct.pack_into('<I',data,0x3c,0x80);data[0x80:0x84]=b'PE\0\0'
    struct.pack_into('<HH',data,0x84,machine,1)
    struct.pack_into('<H',data,0x94,0xf0);struct.pack_into('<H',data,0x98,0x20b)
    struct.pack_into('<II',data,0x98+56,0x2000,0x200)
    struct.pack_into('<I',data,0x98+108,16)
    struct.pack_into('<I',data,0x98+120,0x1000 if imports else 0)
    struct.pack_into('<I',data,0x98+124,20*(len(imports)+1) if imports else 0)
    struct.pack_into('<IIII',data,0x188+8,1024,0x1000,1024,0x200)
    offset=0x300
    for index,name in enumerate(imports):
        struct.pack_into('<I',data,0x200+20*index+12,0x1000+offset-0x200)
        raw=name.encode('ascii')+b'\0';data[offset:offset+len(raw)]=raw;offset+=len(raw)
    path.write_bytes(data)


@unittest.skipUnless(os.name=='nt','Windows dependency assembly')
class RuntimePackageTests(unittest.TestCase):
    def fixture(self,root):
        source=root/'source';source.mkdir()
        licenses=root/'licenses';licenses.mkdir();(licenses/'test.txt').write_text('Synthetic license')
        crt=root/'crt';crt.mkdir()
        pe(source/'SonicCD.exe',['SDL2.dll','vcruntime140.dll'])
        pe(source/'SDL2.dll',['msvcp140.dll'])
        pe(crt/'vcruntime140.dll',['msvcp140_1.dll'])
        pe(crt/'msvcp140.dll');pe(crt/'msvcp140_1.dll')
        license=root/'crt.txt';license.write_text('Synthetic redistributable license')
        return SimpleNamespace(destination=root/'stage',exe=source/'SonicCD.exe',
            sdl2_dll=source/'SDL2.dll',licenses_dir=licenses,crt_dir=crt,
            crt_license=license,blank_seed=None,archive=root/'SonicCD.zip')

    def stage(self,args):
        # The unchanged title payload stager is outside this dependency seam.
        # Exercise the real provider, title policy, manifest and archive below.
        real_run=subprocess.run
        def run(command,**kwargs):
            if command[1].endswith('package_windows.py'):
                root=args.destination;(root/'licenses').mkdir(parents=True)
                package.shutil.copyfile(args.exe,root/'SonicCD.exe')
                package.shutil.copyfile(args.sdl2_dll,root/'SDL2.dll')
                package.shutil.copyfile(args.licenses_dir/'test.txt',root/'licenses/test.txt')
                (root/'userdata').mkdir()
                (root/'userdata/portable-config.json').write_text(json.dumps({'bios_path':None,'disc_path':None}))
                (root/'package-manifest.json').write_text(json.dumps({'owner_media_copied':False}))
                return SimpleNamespace(returncode=0)
            return real_run(command,**kwargs)
        with patch.object(package.subprocess,'run',side_effect=run),patch.object(package,'source_info',return_value={'project':'synthetic'}):
            return package.stage_windows(args)

    def test_transitive_exe_and_sdl_imports_reach_exact_title_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            args=self.fixture(Path(temporary));result=self.stage(args)
            self.assertEqual(result['runner_sha256'],package.digest(args.exe))
            manifest=json.loads((args.destination/'package-manifest.json').read_text())
            package.audit_public_tree(args.destination,manifest)
            with zipfile.ZipFile(args.archive) as archive:
                self.assertEqual(set(archive.namelist()),{'SonicCD/'+p.relative_to(args.destination).as_posix() for p in args.destination.rglob('*') if p.is_file()})
                for name in archive.namelist():
                    self.assertEqual(archive.read(name),(args.destination/name.removeprefix('SonicCD/')).read_bytes())
            self.assertTrue((args.destination/'msvcp140_1.dll').is_file())
            self.assertTrue((args.destination/'licenses/MSVC-runtime.txt').is_file())
            before=args.archive.read_bytes()
            with self.assertRaisesRegex(ValueError,'existing archive'):
                # A fresh stage is required independently of the archive guard.
                args.destination=Path(temporary)/'second-stage';self.stage(args)
            self.assertEqual(args.archive.read_bytes(),before)

    def test_missing_or_wrong_architecture_transitive_runtime_is_rejected(self):
        for bad in ('missing','x86','optional-header','import-rva'):
            with self.subTest(bad=bad),tempfile.TemporaryDirectory() as temporary:
                args=self.fixture(Path(temporary));path=args.crt_dir/'msvcp140_1.dll'
                if bad=='missing':path.unlink()
                elif bad=='x86':pe(path,machine=0x14c)
                else:
                    data=bytearray(path.read_bytes())
                    if bad=='optional-header':struct.pack_into('<H',data,0x98,0x10b)
                    else:struct.pack_into('<I',data,0x98+120,0xf0000000)
                    path.write_bytes(data)
                with self.assertRaisesRegex(ValueError,'dependency verification failed'):self.stage(args)
                self.assertFalse(args.archive.exists())

    def test_runtime_license_and_title_allowlist_are_still_required(self):
        for bad in ('license','private-import'):
            with self.subTest(bad=bad),tempfile.TemporaryDirectory() as temporary:
                args=self.fixture(Path(temporary))
                if bad=='license':args.crt_license=None
                else:
                    pe(args.crt_dir/'msvcp140_1.dll',['unexpected.dll']);pe(args.crt_dir/'unexpected.dll')
                with self.assertRaisesRegex(ValueError,'crt-license|Unexpected public'):self.stage(args)
                self.assertFalse(args.archive.exists())


if __name__=='__main__':unittest.main()
