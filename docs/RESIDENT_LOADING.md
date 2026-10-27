# Resident file loading

The original US SP has one coroutine, `ReadSectors` at Sub PC `0x7AFA`, used by
the ISO directory reader and ordinary file requests. The title prepends a guarded
native module at this boundary. It copies the requested sectors' actual 2048
user bytes, including padding, then resumes the original success and return
instructions at `0x7C24`. Original callers still parse directories, reset the
operation, decompress assets, transfer Word RAM and run scene/music logic.

The engine optionally retains the first data track while verifying the complete
SGCD payload. Residency is bounded to 256 MiB; audio tracks remain file-backed.
Allocation failure leaves the original reader and native game path available.
On Windows, platform SHA-256 accelerates the same full verification. Provider
failure restarts the entire portable pass; no timestamp-only validation or
persistent trust shortcut is used.

The service checks the entire live SP code region against the qualified resident
disc, the file-engine mode and CDC destination, return stack, complete sector
range, MODE1 EDC/header addresses, writable destination bounds and Word RAM
ownership before changing anything. Unsupported requests execute the original
generated instruction and continue through the original native coroutine. PCM
device writes, backup RAM, 1M Word RAM, movies and arbitrary custom loaders are
outside this service. A failed last-sector preflight cannot leave partial writes.

This replaces a file service rather than changing CD speed or host pacing. The
drive, audio and game clocks continue at their normal rates. It does not restore
cached gameplay state, set scene completion flags, skip fades, or replay decoded
snapshots. The BIOS boot UI and authored cutscenes still execute.

## Representative measurements, 2026-10-27

Windows x64 Release, same host, qualified disc/BIOS, disposable blank backup RAM,
presentation settings and normal emulation clocks:

| Workload | Original | Resident |
|---|---:|---:|
| Process initialization, median of three runs each | 2.09 s | 0.62 s |
| PPZ1 Present: first file request to active game loop | 7.36 s | 2.20 s |
| Native time-travel trigger to active PPZ1 Past | 11.87 s | 9.06 s |

Startup alternates the published 0.0.2 executable and candidate, measuring
process creation to the QA listener before window creation. This excludes CUE
launcher/conversion checks and is not a cold-disk or exclusive-host claim.
Transition comparisons use the original and resident file routine in the same
candidate executable. Seconds derive from the native active-loop frame counter
and machine NTSC clocks; QA pauses are excluded. These are representative routes,
not whole-game speedup measurements.

All 13 boot/title/stage transfers and all 15 transfers through time travel match
in full-transfer hashes and file-engine endpoint fields. Both arms reach active
Past gameplay and pass actual displacement/alive checks. The fixture bypasses
touching a time post and supplies speed, then corrects its saved arrival to the
source-defined Past start; the game executes its timer, trigger, cutscene and
reload. An earlier invalid arrival caused identical deaths in both arms and is
retained as a superseded fixture failure. Native floor counters, audio faults,
and audio event underflow/overflow/backwards counters are zero. Stereo audio
capture is nonzero. Owner visual clearance remains pending.

The cached raw data track occupies 139,734,672 bytes (133.26 MiB). Measured median
private process memory rises from 24.14 MiB to 157.69 MiB, about 134 MiB more.
The CDDA soundtrack is not preloaded. Full disc identity is still verified on
every launch. Raw samples, binary/source identities, scripts, logs and captures
are retained in the owning Bead and optimization campaign evidence.

`cd_loading_service_test` uses synthetic sectors to check copied bytes, endpoint
fields, unchanged device clocks/state, whole-request preflight and fallback.
Engine image-reader tests exercise known hashes, malformed/corrupt images and
residency bounds. Windows also builds a forced-portable SHA test.

For matched developer QA, `SONIC_CD_LOADING_ORIGINAL=1` keeps the original file
routine; the default enables residency. `SONIC_CD_LOADING_TRACE=<path>` records
bounded begin/success observations and complete-transfer FNV-1a hashes. These
diagnostics are process-local and have no game UI controls. Compare matching
request LBA/count/destination and endpoint fields/bytes; compare transitions at
the same logical point, because load completion now occurs earlier in time.
