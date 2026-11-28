#!/bin/bash
# Bundle a staged Linux AppDir. All downloads/extraction/cache stay in TOOL_DIR.
set -euo pipefail
if [ "$#" -ne 3 ]; then
    printf 'Usage: %s APPDIR TOOL_DIR OUTPUT.AppImage\n' "$0" >&2
    exit 2
fi
cd_source=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd_appdir=$(realpath "$1")
cd_tools=$(realpath -m "$2")
cd_output=$(realpath -m "$3")
test -x "$cd_appdir/usr/bin/SonicCD"
test ! -e "$cd_output"
mkdir -p "$cd_tools/state" "$(dirname -- "$cd_output")"
for cd_name in tmp cache config data state; do mkdir -p "$cd_tools/state/$cd_name"; done
export TMPDIR="$cd_tools/state/tmp" TEMP="$cd_tools/state/tmp" TMP="$cd_tools/state/tmp"
export XDG_CACHE_HOME="$cd_tools/state/cache" XDG_CONFIG_HOME="$cd_tools/state/config"
export XDG_DATA_HOME="$cd_tools/state/data" XDG_STATE_HOME="$cd_tools/state/state"
export MESA_SHADER_CACHE_DIR="$cd_tools/state/cache/mesa"

# Reuse verified acquisition while retaining Sonic CD's qualified type2 runtime.
cd_engine=${SEGACD_ENGINE_ROOT:-"$cd_source/external/segacdrecomp"}
source "$cd_engine/external/segagenesisrecomp/tools/release/appimage.sh"
genesis_appimage_tools "$cd_tools"
genesis_fetch_tool \
 https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64 \
 617aa77314d57c8b8e4fae9c3f0b35af7b30d5529cb69e98f64f92510ed98a46 "$cd_tools/runtime-x86_64"
genesis_fetch_tool \
 https://raw.githubusercontent.com/AppImage/type2-runtime/fedfad51acc2860b2916a1eef32ba4a500ff31ef/LICENSE \
 aa154fc9070614bbe7921f89db11efd1dba7a1f3a41685958110e2230f9c0ca1 "$cd_tools/AppImage-runtime-LICENSE.txt"

"$LINUXDEPLOY_BIN" --appimage-extract-and-run \
 --appdir "$cd_appdir" --executable "$cd_appdir/usr/bin/SonicCD" \
 --desktop-file "$cd_appdir/sonic-cd.desktop" --icon-file "$cd_appdir/sonic-cd.svg"

# linuxdeploy may exclude compiler runtime libraries. Carry the exact host
# runtime used by this qualified build, then document every bundled library.
for cd_soname in libstdc++.so.6 libgcc_s.so.1; do
    cd_library=$(ldd "$cd_appdir/usr/bin/SonicCD" | awk -v name="$cd_soname" '$1==name {print $3;exit}')
    test -n "$cd_library" && test -f "$cd_library"
    cp -L -- "$cd_library" "$cd_appdir/usr/lib/$cd_soname"
done
strip --strip-unneeded "$cd_appdir/usr/bin/SonicCD"
# Restore the source launcher after deployment. Host dialogs never inherit the
# game's bundled LD_LIBRARY_PATH; only the native game process receives it.
if [ -L "$cd_appdir/AppRun" ]; then rm -- "$cd_appdir/AppRun"; fi
cp -- "$cd_source/launcher/AppRun" "$cd_appdir/AppRun"
chmod 0755 "$cd_appdir/AppRun"
python3 "$cd_source/tools/finalize_appdir.py" "$cd_appdir" "$cd_tools"
ARCH=x86_64 "$APPIMAGETOOL_BIN" --appimage-extract-and-run \
 --runtime-file "$cd_tools/runtime-x86_64" "$cd_appdir" "$cd_output"
chmod 0755 "$cd_output"
sha256sum "$cd_output"
