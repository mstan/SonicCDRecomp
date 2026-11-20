cmake_minimum_required(VERSION 3.21)
project(SonicCDRecomp VERSION 0.0.5 LANGUAGES C CXX)

set(SEGACD_ENGINE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/external/segacdrecomp"
    CACHE PATH "Shared Sega CD engine source root")
if(NOT EXISTS "${SEGACD_ENGINE_ROOT}/runner/cd/machine.h")
    message(FATAL_ERROR "Initialize the Sega CD engine submodule. See docs/BUILDING.md.")
endif()
if(SEGACD_BUILD_NATIVE_RUNNER AND NOT SEGACD_BIOS_PROBE_MODULE_DIR)
    message(FATAL_ERROR "Generate and validate the owned-input catalogs with tools/build.py first.")
endif()

set(genesis_root "${SEGACD_ENGINE_ROOT}/external/segagenesisrecomp")
set(cd_runner "${SEGACD_ENGINE_ROOT}/runner/cd")
set(sonic_cd_video_sources
    game/sonic_cd_world.c game/sonic_cd_view.c game/sonic_cd_culls.c
    game/sonic_cd_scene.c game/sonic_cd_render.c game/sonic_cd_widescreen.c)
set(SEGACD_GAME_TARGET SonicCD)
set(SEGACD_GAME_SOURCES ${sonic_cd_video_sources}
    game/standalone.c game/standalone_program.c game/sonic_cd_loading.c
    game/presentation.c game/presentation_ui.c)
list(TRANSFORM SEGACD_GAME_SOURCES PREPEND "${CMAKE_CURRENT_SOURCE_DIR}/")
include(CTest)
add_subdirectory("${SEGACD_ENGINE_ROOT}" runtime)

if(BUILD_TESTING)
    add_executable(cd_loading_service_test tests/loading_service_test.c)
    target_link_libraries(cd_loading_service_test PRIVATE segacd::devices)
    target_include_directories(cd_loading_service_test PRIVATE "${cd_runner}" "${genesis_root}/runner"
        "${genesis_root}/external/m68k-recomp-core/runtime" "${genesis_root}/external/z80-recomp-core/include")
    target_compile_features(cd_loading_service_test PRIVATE c_std_11)
    if(MSVC)
        target_compile_definitions(cd_loading_service_test PRIVATE _CRT_SECURE_NO_WARNINGS)
        target_compile_options(cd_loading_service_test PRIVATE /W4 /WX)
    else()
        target_compile_options(cd_loading_service_test PRIVATE -Wall -Wextra -Werror)
    endif()
    add_test(NAME cd_loading_service COMMAND cd_loading_service_test)
    add_library(cd_scalar_render_model OBJECT tests/sonic_cd_render_reference.c)
    target_compile_definitions(cd_scalar_render_model PRIVATE segacd_render_scanline=reference_render)
    target_include_directories(cd_scalar_render_model PRIVATE game "${cd_runner}" "${genesis_root}/runner" "${genesis_root}/runner/video")
    add_executable(cd_render_diff tests/render_diff.c game/sonic_cd_render.c
        game/sonic_cd_world.c game/sonic_cd_scene.c
        $<TARGET_OBJECTS:cd_scalar_render_model>)
    target_include_directories(cd_render_diff PRIVATE game "${cd_runner}" "${genesis_root}/runner" "${genesis_root}/runner/video")
    target_compile_features(cd_render_diff PRIVATE c_std_11)
    add_test(NAME cd_render_diff COMMAND cd_render_diff)
    foreach(_lookup_variant cached reference)
        add_executable(cd_catalog_${_lookup_variant}_test tests/catalog_lookup_test.c
            "${genesis_root}/external/m68k-recomp-core/runtime/m68k_step.c")
        target_include_directories(cd_catalog_${_lookup_variant}_test PRIVATE
            "${cd_runner}" "${genesis_root}/external/m68k-recomp-core/runtime")
        target_compile_features(cd_catalog_${_lookup_variant}_test PRIVATE c_std_11)
        if(_lookup_variant STREQUAL "reference")
            target_compile_definitions(cd_catalog_${_lookup_variant}_test PRIVATE SEGACD_CATALOG_LOOKUP_CACHE=0)
        endif()
        add_test(NAME cd_catalog_${_lookup_variant} COMMAND cd_catalog_${_lookup_variant}_test)
    endforeach()

    add_executable(segacd_sonic_cd_view_test tests/sonic_cd_view_test.c
        game/sonic_cd_view.c game/sonic_cd_culls.c)
    target_include_directories(segacd_sonic_cd_view_test PRIVATE game)
    target_link_libraries(segacd_sonic_cd_view_test PRIVATE segacd::machine)
    add_test(NAME segacd_sonic_cd_view COMMAND segacd_sonic_cd_view_test)

    add_executable(segacd_machine_test tests/machine_test.c
        "${SEGACD_ENGINE_ROOT}/tests/segacd/fixtures/z80_native/proof_control_step.c"
        ${sonic_cd_video_sources})
    target_include_directories(segacd_machine_test PRIVATE game "${SEGACD_ENGINE_ROOT}/tests/segacd")
    target_link_libraries(segacd_machine_test PRIVATE segacd::machine)
    add_test(NAME segacd_machine COMMAND segacd_machine_test)
endif()
