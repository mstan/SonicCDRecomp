# Build from owned inputs

This branch uses the private Sega CD engine. Use a GitHub SSH identity with
read access to `mstan/segacdrecomp`. The game pins the engine and a Z80
generation frontend. BIOS images, discs and generated catalogs stay in your
local build directory.

```sh
git clone --branch codex/segacdrecomp-migration https://github.com/mstan/SonicCDRecomp.git
cd SonicCDRecomp
git submodule update --init external/segacdrecomp external/z80-frontend
git -C external/segacdrecomp submodule update --init external/segagenesisrecomp
git -C external/segacdrecomp/external/segagenesisrecomp submodule update --init \
  external/m68k-recomp-core external/z80-recomp-core
```

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

See [native catalog generation](SONIC_CD_NATIVE_BUILD.md) for details. The compressed recipe contains addresses,
source identities and capture procedures, rather than copied instruction images.

## Tests

```sh
python3 -m unittest discover -s tests -v
cmake -S . -B build-tests
cmake --build build-tests --config Release --parallel 4
ctest --test-dir build-tests -C Release --output-on-failure --timeout 0
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
