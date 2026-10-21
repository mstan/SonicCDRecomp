# Build from owned inputs

The source pins the engine's Sega CD feature branch and a Z80 generation
frontend. The engine pins the shared M68K/Z80 cores. No generated game-code
catalogs or original BIOS/disc images are checked in.

```sh
git clone https://github.com/mstan/SonicCDRecomp.git
cd SonicCDRecomp
git submodule update --init external/segagenesisrecomp external/z80-frontend
git -C external/segagenesisrecomp submodule update --init \
  external/m68k-recomp-core external/z80-recomp-core
```

Only these submodules are required for this game. The engine's unrelated
Genesis games/netplay/disassembly submodules aren't needed by the CD target.

Requirements: Python3.10+, CMake3.21+, Git and a C11/C++17 compiler. Windows
uses MSVC and the pinned SDL2 SDK. Linux needs GCC/Clang, SDL2 development files
and pkg-config (`build-essential cmake ninja-build libsdl2-dev pkg-config` on
Ubuntu). Use [the qualified owned inputs](INPUTS.md).

## Generate and compile

On Windows, use a VS developer shell:

```powershell
python tools/build.py --bios 'D:\Owned\segacd-us-1.10.bin' `
  --disc 'D:\Owned\Sonic CD.cue' --work-dir 'G:\Builds\SonicCD' --jobs 4
```

On Linux:

```sh
python3 tools/build.py --bios '/path/to/segacd-us-1.10.bin' \
  --disc '/path/to/Sonic CD.cue' --work-dir "$PWD/build-native" \
  --generator Ninja --jobs 4
```

The script builds the diagnostic generators, formats an empty backup RAM
through the original BIOS, obtains deterministic owned-program captures,
generates native Main/Sub68000 and Z80 catalogs, verifies source hashes and
compiles the strict native game. The floor probe is discovery-only; it isn't
an execution fallback in the shipped game. Output is under `WORK/game/runtime`
(or its `Release` directory on MSVC). `WORK/build-result.json` records the result.

Use `--resume` to verify and reuse completed generation steps. Use `--catalogs
PATH` to reuse a previously generated catalog bundle on the same filesystem;
all files are still checked against its manifest before building. Catalog
paths are platform-specific. Keep large scratch/output directories off C: when
using the upstream Windows tools. `--cmake`, `--sdl2-dir` and `--generator`
override toolchain locations without editing source.

For the detailed generation contract, see the pinned engine's
`docs/SONIC_CD_NATIVE_BUILD.md`. The compressed recipe contains addresses,
source identities and capture procedures, rather than copied instruction images.

## Tests

```sh
python3 -m unittest discover -s tests -v
cmake -S external/segagenesisrecomp/tests/segacd -B build-tests
cmake --build build-tests --target segacd_test_suite --parallel 4
ctest --test-dir build-tests --output-on-failure
```

Owned-input gameplay validation is separate from synthetic tests; see
[VALIDATION.md](VALIDATION.md). Automated runs use muted speaker output.

## Package

Use `tools/package_release.py --help` for allowlisted Windows staging and
Linux AppDir/AppImage creation. Provide a compiled game and component license
directory; owned BIOS/disc paths are never written into a public package.
An optional empty formatted BRAM seed must match the qualified blank identity.
Packages and checksums go under an explicit output directory, never a source
build directory. See [the release process](../RELEASING.md).
