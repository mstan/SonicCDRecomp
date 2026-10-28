cmake_minimum_required(VERSION 3.21)
project(SonicCDRecomp VERSION 0.0.4 LANGUAGES C CXX)

if(NOT SEGACD_BUILD_NATIVE_RUNNER OR NOT SEGACD_BIOS_PROBE_MODULE_DIR)
    message(FATAL_ERROR
        "Generate and validate your owned-input catalogs first. "
        "See docs/BUILDING.md or run python tools/build.py --help.")
endif()

# The upstream feature branch owns the reusable Sega CD devices and strict
# native runner. No duplicate emulator or alternate execution path is linked.
set(GENESIS_RECOMP_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/external/segagenesisrecomp"
    CACHE PATH "Shared GenesisRecomp engine source root")
set(SEGACD_GAME_RENDER_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/game/sonic_cd_render.c"
    CACHE FILEPATH "Game-owned complete-row renderer" FORCE)
set(SEGACD_GAME_SERVICES_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/game/sonic_cd_loading.c"
    CACHE FILEPATH "Game-owned resident file service" FORCE)
add_subdirectory("${GENESIS_RECOMP_ROOT}/tests/segacd" runtime)

enable_testing()
set(_cd_engine "${GENESIS_RECOMP_ROOT}")
add_executable(cd_loading_service_test tests/loading_service_test.c "${_cd_engine}/runner/cd/sector.c")
target_include_directories(cd_loading_service_test PRIVATE "${_cd_engine}/runner/cd"
    "${_cd_engine}/external/m68k-recomp-core/runtime" "${_cd_engine}/external/z80-recomp-core/include")
target_compile_features(cd_loading_service_test PRIVATE c_std_11)
if(MSVC)
    target_compile_definitions(cd_loading_service_test PRIVATE _CRT_SECURE_NO_WARNINGS)
    target_compile_options(cd_loading_service_test PRIVATE /W4 /WX)
else()
    target_compile_options(cd_loading_service_test PRIVATE -Wall -Wextra -Werror)
endif()
add_test(NAME cd_loading_service COMMAND cd_loading_service_test)
add_library(cd_scalar_render_model OBJECT "${_cd_engine}/runner/cd/sonic_cd_render.c")
target_compile_definitions(cd_scalar_render_model PRIVATE segacd_render_scanline=reference_render)
target_include_directories(cd_scalar_render_model PRIVATE "${_cd_engine}/runner/cd" "${_cd_engine}/runner/video")
add_executable(cd_render_diff tests/render_diff.c game/sonic_cd_render.c
    "${_cd_engine}/runner/cd/sonic_cd_world.c" "${_cd_engine}/runner/cd/sonic_cd_scene.c"
    $<TARGET_OBJECTS:cd_scalar_render_model>)
target_include_directories(cd_render_diff PRIVATE "${_cd_engine}/runner/cd" "${_cd_engine}/runner/video")
target_compile_features(cd_render_diff PRIVATE c_std_11)
add_test(NAME cd_render_diff COMMAND cd_render_diff)
foreach(_lookup_variant cached reference)
    add_executable(cd_catalog_${_lookup_variant}_test tests/catalog_lookup_test.c
        "${_cd_engine}/external/m68k-recomp-core/runtime/m68k_step.c")
    target_include_directories(cd_catalog_${_lookup_variant}_test PRIVATE
        "${_cd_engine}/runner/cd" "${_cd_engine}/external/m68k-recomp-core/runtime")
    target_compile_features(cd_catalog_${_lookup_variant}_test PRIVATE c_std_11)
    if(_lookup_variant STREQUAL "reference")
        target_compile_definitions(cd_catalog_${_lookup_variant}_test PRIVATE SEGACD_CATALOG_LOOKUP_CACHE=0)
    endif()
    add_test(NAME cd_catalog_${_lookup_variant} COMMAND cd_catalog_${_lookup_variant}_test)
endforeach()
