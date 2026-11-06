# Contributing

Start with [the source build guide](docs/BUILDING.md). Runtime/device changes
belong in the pinned segagenesisrecomp feature branch; game packaging, launchers
and public documentation live here. Keep dependency revisions explicit.

For issues, include version/platform, stage and time period, reproduction steps
and relevant logs. Keep original BIOS/disc images, generated game-code catalogs,
personal saves and memory dumps out of commits and issue attachments.

Tests should validate meaningful behavior: input selection and cache integrity,
save preservation, release contents and runtime transitions. Gameplay QA may use
stage selection, teleports/protection and forced hits, but must exercise the
actual completion trigger under test. Record bypassed prerequisites and keep
pass, fail and unverified outcomes distinct.

Public releases must include source pins, project/component licenses, checksums,
supported-input requirements and platform smoke evidence. Use the package tools
instead of archiving a build directory.

## Licensing

License each contribution under the terms already applicable to the files
being changed. For contributions to code covered by the
[PolyForm Noncommercial License](LICENSE), also grant the
[additional permissions in `PERMISSIONS.md`](PERMISSIONS.md) for the rights
you control in your contribution, and authorize Matthew Stanley to grant
those same additional permissions for it.

These terms do not replace the licenses of third-party code or project
components expressly licensed under other terms. Do not contribute material
you lack permission to license, or copy from incompatible or proprietary sources.
