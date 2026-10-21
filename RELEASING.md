# Release process

Release only the qualified native game. Original BIOS/disc files, extracted
programs, generated source catalogs, memory dumps, diagnostics and personal
saves are private build/test inputs and must not enter a release archive.
The optional empty BIOS-formatted seed has a fixed identity checked by the
package tool; an arbitrary8192-byte save is rejected.

1. Check out the intended source/core pins and build using owned inputs.
2. Run launcher/package contracts and the upstream synthetic suite. Validate
   platform startup, actual gameplay, native miss counters, audio and display.
   Reuse existing gameplay evidence for unchanged code; don't rerun full routes.
3. Review public README/screenshots, supported inputs, known limits and changelog.
4. Commit the source. Stage into a new directory with `tools/package_release.py`.
   This records source revisions and rejects owned paths, unrecorded files and
   nonblank saves. Never zip a build folder or an owner's playtest profile.
5. Validate the Windows staged package with `SonicCD.cmd -ValidateOnly` and the
   pinned engine's `package_windows.py validate`. Validate the Linux AppImage
   through its actual AppRun, including input selection/cache/save boundaries.
6. Produce `SHA256SUMS.txt`, inspect archive contents and publish tag `vVERSION`
   with both platform assets and release notes. Download the public assets and
   compare their hashes before calling the release delivered.

Windows staging example:

```powershell
python tools/package_release.py windows --exe G:/Builds/SonicCD/SonicCD.exe `
  --sdl2-dll G:/Builds/SonicCD/SDL2.dll --licenses-dir G:/Builds/SonicCD/licenses `
  --destination G:/Releases/SonicCD-stage `
  --archive G:/Releases/SonicCD-0.0.1-windows-x64.zip
```

For an MSVC dynamic-CRT build, also pass `--crt-dir` with the approved x64
redistributable DLL directory and `--crt-license` with its license text/RTF.
The package tool checks PE imports and stages the required app-local runtimes.

Linux staging and bundling:

```sh
python3 tools/package_release.py linux-appdir --exe build-native/game/runtime/SonicCD \
  --licenses-dir build-native/game/runtime/licenses --destination build-release/SonicCD.AppDir
bash tools/build-appimage.sh build-release/SonicCD.AppDir build-release/tools \
  build-release/SonicCD-0.0.1-linux-x86_64.AppImage
```

Both staging commands accept `--blank-seed PATH`. Component license texts must
be supplied from the compiled runtime. The Linux bundler checks its tools,
bundles runtime libraries and their copyright/license notices, and keeps the
host Python/dialog environment separate from the game's library search path.

Keep the engine's Sega CD implementation on `feature/segacd-backend` until its
separate upstream merge is requested. Publishing this game does not authorize
merging unrelated campaign/Shadow or framework work into main/master.
