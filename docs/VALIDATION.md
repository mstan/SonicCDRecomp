# 0.0.1 validation and limits

The initial release uses the original US game programs on the strict native
Main/Sub 68000 and Z80 path. A missing generated instruction stops visibly;
there is no silent interpreter fallback in the game. The separate diagnostic
floor probe is used during catalog generation only.

| Coverage | Result |
|---|---|
| Standard stage/time variants | 70/70 brief entry/movement checks |
| Bosses | 7/7 original death/completion paths |
| Special stages | 8/8 original UFO completion paths |
| Secret stage8 | Original secret credits and real exit to title |
| Original ending | Bad-ending film, full credits and automatic title return |
| Save boundary | Actual stage clear, durable backup RAM, restart and Continue |
| Time travel | Past, future and reverse travel through original triggers |
| Representative mechanics | Flipper, moving bounce platform, generator, forced-hit projector, drowning/death/retry, lift/passive carry, layer and size changes |
| Presentation | Windowed controls/audio, recomp-ui pause/input isolation, adaptive resizing and real margin scenery |
| Independent visuals | PPZ, TTZ, SS1, SS8, ending framing and credits compared with the original |

Coverage uses stage selection, teleports, protection and source-qualified forced
hits to bypass route/combat prerequisites. The original game executes the
completion, result, save and next-scene transitions under test; those outcome
flags aren't supplied by the test. This is representative coverage, not an
exhaustive playthrough of every object interaction.

The complete owned-input recipe generates 333 catalogs / 11,290 C/header files.
All 2,019,176 required original M68K guards are preserved; two-stage native Z80
generation retains all qualified historical code-region guards. Both input
identities and generated source hashes are checked before compilation.

The accepted Windows executable has SHA-256
`80c14de9c887afd5d52d25360beeb1a8ce3d5da21544fc77c23a09c0798ca74d`.
Its final focused run reaches 2,923 frames with native Main/Sub floor counters 0/0,
zero audio faults and nonzero stereo audio. Independent final visual retakes also
have floors 0/0 and zero audio faults. Release manifests identify platform binaries.

The complete content matrix above was recorded on Windows. Linux 0.0.1 rebuilds
the identical owned-generated catalogs with GCC 13.3 on Ubuntu 24.04. Its packaged
runtime passed a source-qualified 2,791-frame Palmtree Panic movement, expanded
scenery and stereo-audio check, with native floors 0/0, zero audio faults and no
audio event underflow/overflow/backwards counters. The captured RGB frame matches
the Windows frame exactly; final visual review passed.

Two actual AppImage launches passed with the clean `Sonic CD` window caption,
normal window defaults, volume 100 default settings, remembered input paths and
preserved existing settings/backup RAM. Automated speaker output was muted;
emulated audio remained active and its nonzero stereo capture was measured.
The complete content matrix was reused rather than repeated for Linux. Other
Linux distributions and physical Linux audio/controller devices remain unverified.

## Known limits

- Only the listed US disc/BIOS combination is supported.
- Special stages retain the original 256px projection. Widescreen expansion is
  available for supported normal stages; it is not claimed for every scene.
- Physical projector contact, air-bubble refill, physical gamepad and the
  alternate all-time-stones good-ending prerequisite route were not independently
  validated in this pass. The projector's original destruction sequence was
  validated using a forced hit.
- Exact reference animation phase and pixel equality are not claimed.
- Netplay, rewind/save-state UI and the separate S3K campaign/Shadow work are
  outside this standalone release.

The hardware-accuracy defer list is limited to instruction-boundary bus/T-state
precision, exact analog DAC/display color conversion, and marginal-media/drive
error behavior beyond the qualified disc. These do not substitute for the
completion checks above.
