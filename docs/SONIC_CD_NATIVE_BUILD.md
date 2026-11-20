# Owned-input Sonic CD build and portable package

The supported inputs are the US Model 1 v1.10 BIOS (128 KiB, SHA-256
`807384678ef259494d943eddb6954dfc7069693d0dde0c424e2028488d88e81a`)
and the qualified Sonic CD US disc (SGCD payload SHA-256
`4e822010e42092681b238ddc7cbff41802c0cfc006c9b1510dcebd6b9dd452b1`).
The runner rejects other inputs. BIOS and media are supplied externally.

`external/segacdrecomp/tools/segacd/disc_image.py` converts supported raw BIN/CUE images; its
`inspect-cue` subcommand binds the canonical CUE and every referenced track to
content hashes. The portable launcher uses that identity for conversion caches.

## Catalog generation

Run `tools/build.py` as described in the [build guide](BUILDING.md). It builds
`segacd_module_recompiler` and `segacd_bios_floor_probe` from the engine's root
CMake project and `SmsRecomp` from the pinned Z80 frontend. The floor probe
formats private empty backup RAM through the original BIOS and captures
transient program states. It is a diagnostic tool. The packaged runner uses
strict native execution for the main and sub 68000s and Z80.

`tools/segacd/sonic_cd_us_recipe.json.gz` is the title's generation recipe. It
contains input identities, source mappings, guarded entry addresses and capture
procedures. The pipeline checks each required 68000 guard against its source
bytes, length and nominal cycles. Z80 captures feed guarded native variants
covering all 16,384 logical PCs.

`--resume` verifies and reuses completed generation steps. `--catalogs PATH`
validates an existing bundle on the same filesystem. The native build records
both Git dependencies and their CPU cores in `game/source-build-provenance.json`.
Keep the generated source, input images and diagnostic captures local.
