import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
launcher=module('sonic_cd_launcher',ROOT/'launcher/SonicCD.py')
package=module('sonic_cd_package',ROOT/'tools/package_release.py')


class ProfileTests(unittest.TestCase):
    def test_file_picker_uses_portable_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'selected.bin';source.write_bytes(b'fixture')
            env={'XDG_DATA_HOME':str(Path(temporary)/'data')}
            with patch.object(launcher.shutil,'which',return_value='/usr/bin/zenity'),patch.object(launcher.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=str(source)+'\n')) as picker:
                self.assertEqual(launcher.select_file('Select BIOS',env),source.resolve())
                self.assertIs(picker.call_args.kwargs['env'],env)

    def test_existing_save_and_settings_survive_update(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);data=root/'userdata';payload=root/'payload'
            data.mkdir();(payload/'seed').mkdir(parents=True)
            (payload/'seed/sonic-cd.brm').write_bytes(bytes(8192))
            (data/'sonic-cd.brm').write_bytes(b'personal save preserved')
            (data/'sonic-cd-settings.ini').write_text('volume=37\nview_mode=0\n')
            settings,backup=launcher.seed_profile(data,payload)
            self.assertEqual(backup.read_bytes(),b'personal save preserved')
            self.assertEqual(settings.read_text(),'volume=37\nview_mode=0\n')

    def test_fresh_profile_has_window_audio_and_adaptive_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);settings,backup=launcher.seed_profile(root/'user',root/'payload')
            self.assertIn('fullscreen=0\n',settings.read_text())
            self.assertIn('audio_enabled=1\nvolume=100\nview_mode=2\n',settings.read_text())
            self.assertFalse(backup.exists())

    def test_bad_config_is_reported_and_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'config.json'
            text=json.dumps({'schema':launcher.SCHEMA,'bios_path':13})
            path.write_text(text)
            with self.assertRaises(ValueError):launcher.load_config(path)
            self.assertEqual(path.read_text(),text)


class DiscCacheTests(unittest.TestCase):
    def test_cache_reused_and_tampered_content_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);cue=root/'owned.cue';cue.write_text('synthetic test fixture')
            identity={'schema':'SGCDCueSourceIdentity1','fixture':'owned-a'}
            def convert(command,**kwargs):Path(command[-1]).write_bytes(b'synthetic converted image')
            with patch.object(launcher,'inspect_cue',return_value=identity),patch.object(launcher.subprocess,'run',side_effect=convert) as conversion:
                first=launcher.prepare_disc(cue,root,root/'converter.py',{})
                second=launcher.prepare_disc(cue,root,root/'converter.py',{})
                self.assertEqual(first,second);self.assertEqual(conversion.call_count,1)
                first.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'changed'):launcher.prepare_disc(cue,root,root/'converter.py',{})
                self.assertEqual(conversion.call_count,1)

    def test_mid_conversion_source_change_is_not_committed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);cue=root/'owned.cue';cue.write_text('synthetic test fixture')
            def convert(command,**kwargs):Path(command[-1]).write_bytes(b'synthetic result')
            with patch.object(launcher,'inspect_cue',side_effect=[{'id':'before'},{'id':'after'}]),patch.object(launcher.subprocess,'run',side_effect=convert):
                with self.assertRaisesRegex(ValueError,'changed during conversion'):
                    launcher.prepare_disc(cue,root,root/'converter.py',{})
            self.assertEqual(list((root/'disc').iterdir()),[])

    def test_orphaned_cache_fails_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);cue=root/'owned.cue';cue.write_text('fixture')
            identity={'schema':'SGCDCueSourceIdentity1','fixture':'a'}
            def convert(command,**kwargs):Path(command[-1]).write_bytes(b'result')
            with patch.object(launcher,'inspect_cue',return_value=identity),patch.object(launcher.subprocess,'run',side_effect=convert):
                output=launcher.prepare_disc(cue,root,root/'converter.py',{})
                output.with_suffix('.json').unlink()
                with self.assertRaisesRegex(ValueError,'Incomplete'):launcher.prepare_disc(cue,root,root/'converter.py',{})
                self.assertEqual(output.read_bytes(),b'result')


class PackageTests(unittest.TestCase):
    def test_terminated_rtf_license_is_valid_but_embedded_binary_is_not(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);license=root/'MSVC-runtime.rtf'
            license.write_bytes(b'{\\rtf1 legal text}\0')
            package.audit_licenses(root)
            license.write_bytes(b'{\\rtf1 legal\0binary}')
            with self.assertRaisesRegex(ValueError,'Binary content'):package.audit_licenses(root)

    def tree(self,root):
        (root/'licenses').mkdir();(root/'licenses/test.txt').write_text('Synthetic license text')
        (root/'userdata').mkdir()
        (root/'userdata/portable-config.json').write_text(json.dumps({'schema':launcher.SCHEMA,'bios_path':None,'disc_path':None}))
        (root/'package-manifest.json').write_text('{}')
        return {'owner_media_copied':False,'files':[package.file_record(root,p) for p in sorted(root.rglob('*')) if p.is_file() and p.name!='package-manifest.json']}

    def test_owned_path_is_rejected_even_if_manifest_hash_matches(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manifest=self.tree(root)
            config=root/'userdata/portable-config.json'
            config.write_text(json.dumps({'bios_path':'/private/owned/bios.bin','disc_path':None}))
            manifest['files']=[package.file_record(root,root/row['path']) for row in manifest['files']]
            with self.assertRaisesRegex(ValueError,'machine-specific'):package.audit_public_tree(root,manifest)

    def test_unrecorded_disc_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manifest=self.tree(root)
            (root/'private.sgcd').write_bytes(b'synthetic image')
            with self.assertRaisesRegex(ValueError,'Unrecorded'):package.audit_public_tree(root,manifest)

    def test_media_cannot_hide_in_license_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manifest=self.tree(root)
            path=root/'licenses/owned.bin';path.write_bytes(b'fixture')
            manifest['files'].append(package.file_record(root,path))
            with self.assertRaisesRegex(ValueError,'license payload'):package.audit_public_tree(root,manifest)

    def test_traversal_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manifest=self.tree(root)
            manifest['files'].append({'path':'../outside.txt','bytes':0,'sha256':'0'*64})
            with self.assertRaisesRegex(ValueError,'Unsafe'):package.audit_public_tree(root,manifest)

    def test_nonblank_save_cannot_be_seeded_into_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            seed=Path(temporary)/'save.brm';seed.write_bytes(bytes(8192))
            with self.assertRaisesRegex(ValueError,'qualified empty'):package.check_seed(seed)


if __name__=='__main__':unittest.main()
