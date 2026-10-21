# Supported BIOS and disc

0.0.1 supports the **US Sonic CD disc** with the **US Model 1 v1.10 Sega CD
BIOS**. Other regions and revisions are rejected by this build.

| Input | Qualified identity |
|---|---|
| BIOS size | 131,072 bytes |
| BIOS SHA-256 | `807384678ef259494d943eddb6954dfc7069693d0dde0c424e2028488d88e81a` |
| BIOS CRC32 | `c6d10268` |
| Converted SGCD payload SHA-256 | `4e822010e42092681b238ddc7cbff41802c0cfc006c9b1510dcebd6b9dd452b1` |

Select an extracted BIOS `.bin` or `.rom`, and either an existing `.sgcd`
image or a raw `.cue`/`.bin` disc set. Archives must be extracted first.
The launcher remembers paths and never bundles or uploads these inputs.

The converter accepts quoted `BINARY` track sources with `MODE1/2352` and
`AUDIO` tracks. Keep every referenced BIN alongside the CUE as authored.
Conversion preserves the disc layout and audio tracks; an ISO-only data dump
does not replace the supported mixed-mode disc.

The included `tools/segacd/disc_image.py` can also be used directly:

```sh
python3 tools/segacd/disc_image.py "Sonic CD.cue" "Sonic CD.sgcd"
```

The launcher caches a converted image under `userdata/disc`, keyed by the CUE
and all referenced track content hashes. Changing tracks invalidates the cache.
The game independently verifies its input identity before execution.

No BIOS, original disc, extracted game image or personal save is included in
the repository or release archives. A package may contain an empty formatted
backup-RAM seed used only to initialize a new save file.
