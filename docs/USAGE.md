# Playing Sonic CD

## Windows

Extract the release ZIP completely, then run `SonicCD.cmd`. Select the supported
BIOS and disc on first launch. CUE conversion needs Python 3 on PATH; choosing
an already converted SGCD avoids that dependency. Don't run from inside a ZIP.

All writable state is under `userdata` by default: `sonic-cd.brm`,
`sonic-cd-settings.ini`, input paths, converted discs, logs and temporary files.
Choose another data directory with:

```powershell
.\SonicCD.cmd -DataRoot 'D:\Games\SonicCD-data'
```

The package must be extracted somewhere writable if using the default profile.
The launcher never overwrites an existing backup RAM file with its empty seed.

## Linux

The x86_64 AppImage targets glibc 2.39+ and bundles the game's SDL2/C++ runtime
dependencies. Python 3 runs the portable launcher. Zenity or KDialog enables
file dialogs; alternatively provide both input paths:

```sh
./SonicCD-0.0.1-linux-x86_64.AppImage \
  --bios '/path/to/segacd-us-1.10.bin' --disc '/path/to/Sonic CD.cue'
```

Writable data is `userdata` beside the AppImage. To choose a different location:

```sh
./SonicCD-0.0.1-linux-x86_64.AppImage --data-root '/path/to/SonicCD-data'
```

If your distribution doesn't enable FUSE for AppImages, use:

```sh
./SonicCD-0.0.1-linux-x86_64.AppImage --appimage-extract-and-run
```

Or extract once with `--appimage-extract`, then run `squashfs-root/AppRun`.
Keep your selected inputs and data directory outside the read-only AppImage.

## Display, audio and controls

Press F1 or Esc (controller Back) for recomp-ui. The game pauses while the
menu is open and resumes with held gameplay inputs released. Display/Graphics
offers original, fixed16:9 and adaptive / Fit to screen; resize the window to
change adaptive framing. Normal stages render extra scenery and entities.
Special stages retain their centered original projection, and cinematics retain
their original framing. The game starts windowed on each launch.

Use arrow keys to move, Z/X/C for A/B/C, and Enter for Start. A controller uses
D-pad/left stick, X/A/B for A/B/C, and Start. P pauses/resumes emulation.
Audio starts enabled at normal volume. Volume and filtering changes persist.

Use the original game's menus to start or Continue. Back up `sonic-cd.brm`
while the game is closed before manually moving saves. Replacing an AppImage
or unpacking a new version doesn't require deleting `userdata`.

## Troubleshooting

- An input-revision error means the selected BIOS/disc does not match
  [the qualified inputs](INPUTS.md). Renaming it will not change its contents.
- A conversion error usually names a missing CUE track or unsupported format.
  Keep all original tracks together; don't select the ZIP/7z archive itself.
- To select different inputs, edit or remove `userdata/portable-config.json`
  with the game closed, then relaunch. Keep `sonic-cd.brm` to preserve your save.
- On Linux, install Python 3 and Zenity/KDialog if first-run dialogs are missing,
  or supply the input paths explicitly. glibc2.39 is the initial release minimum.
- For a bug report, include OS, release version, stage/time period, steps and
  the relevant `userdata/logs/SonicCD.log`. Don't upload BIOS or disc files.
