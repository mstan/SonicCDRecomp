Sonic CD Recompiled 0.0.1 - initial public release
https://github.com/mstan/SonicCDRecomp

Bring your own Sonic CD US disc and US Sega CD Model1v1.10 BIOS.
No BIOS/disc image or personal save is included.
Supported input identities: https://github.com/mstan/SonicCDRecomp/blob/main/docs/INPUTS.md

Windows: extract the whole ZIP into a writable folder and run SonicCD.cmd.
Choose your BIOS and disc image. SGCD runs without Python; CUE/BIN conversion
requires Python3. Keep all tracks beside their CUE.

Linux: chmod +x the AppImage, then run it. Requires x86_64, glibc2.39+,
Python3 and Zenity/KDialog for file selection. Alternatively pass
--bios /path/to/bios.bin --disc /path/to/disc.cue.
If FUSE is unavailable, add --appimage-extract-and-run.

The game opens windowed, with normal audio and adaptive/Fit to screen enabled.
Arrow keys move; Z/X/C are A/B/C; Enter is Start. F1/Esc opens recomp-ui.
Settings and backup-RAM saves live under userdata beside the Windows package
or AppImage. Keep that folder when updating. Existing saves are never reset.
Special stages and cinematics retain their original presentation.

Known limits and validation:
https://github.com/mstan/SonicCDRecomp/blob/main/docs/VALIDATION.md

Project code: PolyForm Noncommercial1.0.0, included as LICENSE.
Component terms: THIRD-PARTY-LICENSES.md and licenses/.
Engine source: https://github.com/mstan/segagenesisrecomp/tree/feature/segacd-backend
Generated code does not grant rights to the original game. SonicCD and its
characters belong to SEGA. This is an unofficial fan project.
