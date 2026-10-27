# Changelog

## Unreleased

- Keep the verified data track resident and service ordinary game file reads
  directly from those sectors, shortening stage and time-travel loading.
- Use Windows platform SHA-256 for full disc verification at startup, retaining
  complete portable verification when the provider is unavailable.
- Preserve original file parsing, resource bytes, decompression, scene handoffs,
  music calls and movie streaming. Unsupported requests use the original native
  file routine; game speed and audio clocks remain unchanged.

## 0.0.1 - Initial public release

- Original Sonic CD US running through native Main/Sub68000 and Z80 recompilation.
- Windows x64 and Linux x86_64 downloads with owned BIOS/disc selection.
- Original audio and persistent backup RAM saves.
- recomp-ui display, graphics and audio settings.
- Adaptive normal-stage widescreen with Fit to screen.
- Reproducible owned-input generation/build instructions and published validation limits.
