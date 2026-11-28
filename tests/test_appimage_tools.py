"""Offline acquisition and title packaging-plan checks; no Linux build needed."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
ENGINE=Path(os.environ.get('SEGACD_ENGINE_ROOT',ROOT/'external/segacdrecomp'))
BASH=os.environ.get('RELEASE_TEST_BASH') or (str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Git/bin/bash.exe') if os.name=='nt' else shutil.which('bash'))


@unittest.skipUnless(BASH and Path(BASH).is_file(),'Bash release host required')
class AppImageToolsTests(unittest.TestCase):
    def run_bash(self,script,*arguments):
        # Git Bash resets TEMP/TMP on entry; restore the caller's explicit
        # scratch root before any GNU helper or child tool can create files.
        script='export TEMP="$TMPDIR" TMP="$TMPDIR"\n'+script
        return subprocess.run([BASH,'-c',script,'release-test',*[Path(p).as_posix() for p in arguments]],
                              text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

    def test_cached_tools_and_corrupt_download_rejection(self):
        helper=ENGINE/'external/segagenesisrecomp/tools/release/appimage.sh'
        if not helper.is_file():self.skipTest('Initialize pinned release provider')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);tool=root/'tool';tool.write_text('trusted')
            result=self.run_bash('''set -eu
source "$1"
expected=$(printf trusted | sha256sum | cut -d' ' -f1)
curl() { echo 'Unexpected network request' >&2; return 91; }
genesis_fetch_tool unused "$expected" "$2/tool"
''',helper,root)
            self.assertEqual(result.returncode,0,result.stdout)
            tool.write_text('corrupt')
            result=self.run_bash('''set -eu
source "$1"
expected=$(printf trusted | sha256sum | cut -d' ' -f1)
curl() { printf trusted > "${@: -1}"; }
genesis_fetch_tool unused "$expected" "$2/tool"
''',helper,root)
            self.assertEqual(result.returncode,0,result.stdout)
            self.assertEqual(tool.read_text(),'trusted')
            tool.write_text('preserve rejected cache')
            result=self.run_bash('''set -eu
source "$1"
expected=$(printf trusted | sha256sum | cut -d' ' -f1)
curl() { printf tampered > "${@: -1}"; }
genesis_fetch_tool unused "$expected" "$2/tool"
''',helper,root)
            self.assertNotEqual(result.returncode,0,result.stdout)
            self.assertEqual(tool.read_text(),'preserve rejected cache')

    def test_title_plan_retains_explicit_type2_runtime_and_finalizer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);app=root/'AppDir';(app/'usr/bin').mkdir(parents=True)
            binary=app/'usr/bin/SonicCD';binary.write_text('#!/bin/sh\nexit 0\n');binary.chmod(0o755)
            stub=root/'stubs';stub.mkdir();log=root/'plan.log'
            lib=root/'library.so';lib.write_bytes(b'synthetic library')
            for name,text in {
                'linuxdeploy':'mkdir -p "$APPDIR/usr/lib"\nprintf "deploy %s\\n" "$*" >> "$PLAN_LOG"',
                'appimagetool':'printf "package %s\\n" "$*" >> "$PLAN_LOG"\nprintf fixture > "${@: -1}"',
                'ldd':'printf "libstdc++.so.6 => %s (0)\\nlibgcc_s.so.1 => %s (0)\\n" "$PLAN_LIBRARY" "$PLAN_LIBRARY"',
                'strip':'exit 0',
                'python3':'printf "finalize %s\\n" "$*" >> "$PLAN_LOG"',
            }.items():
                path=stub/name;path.write_text('#!/bin/bash\nset -eu\n'+text+'\n');path.chmod(0o755)
            provider=root/'engine/external/segagenesisrecomp/tools/release';provider.mkdir(parents=True)
            (provider/'appimage.sh').write_text('''genesis_appimage_tools() {
    printf 'tools %s\\n' "$1" >> "$PLAN_LOG"
    LINUXDEPLOY_BIN="$PLAN_STUB/linuxdeploy"
    APPIMAGETOOL_BIN="$PLAN_STUB/appimagetool"
    RUNTIME=embedded-runtime-must-not-be-used
}
genesis_fetch_tool() {
    printf 'fetch %s %s %s\\n' "$1" "$2" "$3" >> "$PLAN_LOG"
    printf fixture > "$3"
}
''')
            script='''set -eu
root=$(cygpath -u "$1" 2>/dev/null || printf '%s' "$1")
export PLAN_STUB="$root/stubs" PLAN_LOG="$root/plan.log" PLAN_LIBRARY="$root/library.so" APPDIR="$root/AppDir"
export PATH="$PLAN_STUB:$PATH" SEGACD_ENGINE_ROOT="$root/engine"
bash "$2" "$APPDIR" "$root/tools" "$root/SonicCD.AppImage"
'''
            result=self.run_bash(script,root,ROOT/'tools/build-appimage.sh')
            self.assertEqual(result.returncode,0,result.stdout)
            plan=log.read_text()
            self.assertIn('617aa77314d57c8b8e4fae9c3f0b35af7b30d5529cb69e98f64f92510ed98a46',plan)
            self.assertIn('aa154fc9070614bbe7921f89db11efd1dba7a1f3a41685958110e2230f9c0ca1',plan)
            self.assertIn('finalize ',plan)
            self.assertIn('--runtime-file ',plan)
            self.assertIn('/tools/runtime-x86_64',plan)
            self.assertNotIn('embedded-runtime-must-not-be-used',plan)
            self.assertEqual((app/'AppRun').read_bytes(),(ROOT/'launcher/AppRun').read_bytes())


if __name__=='__main__':unittest.main()
