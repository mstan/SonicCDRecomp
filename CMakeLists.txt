cmake_minimum_required(VERSION 3.21)
project(SonicCDRecomp VERSION 0.0.1 LANGUAGES C CXX)

if(NOT SEGACD_BUILD_NATIVE_RUNNER OR NOT SEGACD_BIOS_PROBE_MODULE_DIR)
    message(FATAL_ERROR
        "Generate and validate your owned-input catalogs first. "
        "See docs/BUILDING.md or run python tools/build.py --help.")
endif()

# The upstream feature branch owns the reusable Sega CD devices and strict
# native runner. No duplicate emulator or alternate execution path is linked.
add_subdirectory(external/segagenesisrecomp/tests/segacd runtime)
