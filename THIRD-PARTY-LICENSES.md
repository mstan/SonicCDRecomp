# Third-party notices

The standalone Sonic CD release links the pinned segagenesisrecomp Sega CD
runtime and generated Main/Sub68000/Z80 code. The project and shared cores
use PolyForm Noncommercial1.0.0; see `LICENSE` and component texts under
`licenses/` in the release package.

| Component | Use | License / included text |
|---|---|---|
| SDL2 | Window, input and audio | zlib; `licenses/SDL2.txt` |
| ymfm, Aaron Giles and contributors | YM2612 FM synthesis | BSD3-Clause; `licenses/ymfm.txt` |
| ares team / Near and contributors | Attributed Sega CD hardware algorithms | ISC; `licenses/ares.txt` |
| m68k-recomp-core | Shared68000 native ABI/semantics | PolyForm Noncommercial1.0.0; `licenses/m68k-recomp-core.txt` |
| z80-recomp-core | Shared Z80 native ABI/semantics | PolyForm Noncommercial1.0.0; `licenses/z80-recomp-core.txt` |
| recomp-ui | Runtime settings menu | MIT; `licenses/recomp-ui.txt` |
| Microsoft Visual C++ runtime (Windows) | App-local runtime DLLs | Microsoft redistributable terms; `licenses/MSVC-runtime.rtf` |

The source generation frontend from smsggrecomp is a build tool and is not
bundled in the game download. Its own source terms continue to apply.

Linux AppImages also bundle selected system runtime libraries. Their package
copyright/license texts are included under `licenses/system/`, with applicable
common license texts and an inventory identifying their source packages.
AppImage tooling/runtime source and pinned identities are documented in
`tools/build-appimage.sh` and the release build metadata.

The runtime game package includes no independent emulator reference/oracle.
No original BIOS, disc image or extracted game-code catalog is redistributed.
Screenshots illustrate the original game, whose rights remain with SEGA.
