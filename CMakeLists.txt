cmake_minimum_required(VERSION 3.17)
project(llama_server_vendor NONE)

find_package(ament_cmake REQUIRED)
include(ExternalProject)
include(CheckLanguage)

# Silence the CMP0135 warning (CMake >= 3.24)
if(POLICY CMP0135)
  cmake_policy(SET CMP0135 NEW)
endif()

# Change with scripts/update_llama_cpp.sh
set(LLAMA_CPP_TAG "b11243")

# options
set(LLAMA_CPP_SOURCE_DIR "" CACHE PATH
  "Use a local llama.cpp source tree instead of the one in vendor/")

set(LLAMA_SERVER_VENDOR_CUDA "AUTO" CACHE STRING "Build with CUDA: AUTO, ON or OFF")
set_property(CACHE LLAMA_SERVER_VENDOR_CUDA PROPERTY STRINGS AUTO ON OFF)

set(LLAMA_SERVER_VENDOR_CUDA_ARCHS "" CACHE STRING
  "CUDA archs, for example 87. Empty = auto-detect")

option(LLAMA_SERVER_VENDOR_NATIVE "Tune CPU code for the build machine (GGML_NATIVE)" ON)

set(LLAMA_SERVER_VENDOR_EXTRA_CMAKE_ARGS "" CACHE STRING
  "Extra ;-separated CMake args for llama.cpp (for example -DGGML_CUDA_FA_ALL_QUANTS=ON)")

# cuda
# nvcc is often not on PATH
if(NOT CMAKE_CUDA_COMPILER AND NOT DEFINED ENV{CUDACXX} AND EXISTS "/usr/local/cuda/bin/nvcc")
  set(CMAKE_CUDA_COMPILER "/usr/local/cuda/bin/nvcc")
endif()

set(_use_cuda OFF)

if(NOT LLAMA_SERVER_VENDOR_CUDA STREQUAL "OFF")
  check_language(CUDA)

  if(CMAKE_CUDA_COMPILER)
    set(_use_cuda ON)
  elseif(LLAMA_SERVER_VENDOR_CUDA STREQUAL "ON")
    message(FATAL_ERROR "LLAMA_SERVER_VENDOR_CUDA=ON but no CUDA compiler found")
  endif()
endif()

# gpu arch. Empty = llama.cpp picks it
set(_cuda_archs "${LLAMA_SERVER_VENDOR_CUDA_ARCHS}")

if(_use_cuda AND NOT _cuda_archs)
  # Tegra: from the chip name (works with no GPU access)
  if(EXISTS "/proc/device-tree/compatible")
    file(READ "/proc/device-tree/compatible" _device_tree_compatible)

    if(_device_tree_compatible MATCHES "tegra234")
      set(_cuda_archs "87")
    elseif(_device_tree_compatible MATCHES "tegra264")
      get_filename_component(_cuda_bin_dir "${CMAKE_CUDA_COMPILER}" DIRECTORY)
      get_filename_component(CUDAToolkit_ROOT "${_cuda_bin_dir}" DIRECTORY)
      find_package(CUDAToolkit REQUIRED)

      # CUDA 13 renamed sm_101 to sm_110
      if(CUDAToolkit_VERSION_MAJOR LESS 13)
        set(_cuda_archs "101")
      else()
        set(_cuda_archs "110")
      endif()
    elseif(_device_tree_compatible MATCHES "tegra")
      message(WARNING "Unknown Tegra chip. Set LLAMA_SERVER_VENDOR_CUDA_ARCHS.")
    endif()
  endif()

  # Other GPUs, CMake < 3.24 only (no "native")
  if(NOT _cuda_archs AND LLAMA_SERVER_VENDOR_NATIVE AND CMAKE_VERSION VERSION_LESS 3.24)
    find_program(NVIDIA_SMI nvidia-smi)

    if(NVIDIA_SMI)
      execute_process(
        COMMAND "${NVIDIA_SMI}" --query-gpu=compute_cap --format=csv,noheader
        OUTPUT_VARIABLE _compute_capabilities
        RESULT_VARIABLE _nvidia_smi_result
        ERROR_QUIET
        OUTPUT_STRIP_TRAILING_WHITESPACE
      )

      string(REPLACE "." "" _compute_capabilities "${_compute_capabilities}")
      string(REGEX REPLACE "[\r\n]+" ";" _compute_capabilities "${_compute_capabilities}")

      # nvidia-smi prints errors to stdout
      if(_nvidia_smi_result EQUAL 0 AND _compute_capabilities MATCHES "^[0-9;]+$")
        list(REMOVE_DUPLICATES _compute_capabilities)
        set(_cuda_archs "${_compute_capabilities}")
      endif()
    endif()
  endif()
endif()

# llama.cpp build
string(REGEX REPLACE "^b" "" _build_number "${LLAMA_CPP_TAG}")

# Stage with DESTDIR so config files get the real prefix
set(_stage_dir "${CMAKE_BINARY_DIR}/stage")
set(_llama_build_dir "${CMAKE_BINARY_DIR}/llama_cpp-build")

set(_llama_cmake_args
  -DCMAKE_BUILD_TYPE=Release
  -DCMAKE_INSTALL_PREFIX=${CMAKE_INSTALL_PREFIX}
  -DCMAKE_INSTALL_LIBDIR=lib
  # For bin/ and lib/<pkg>/
  -DCMAKE_INSTALL_RPATH=$ORIGIN/../lib:$ORIGIN/../../lib
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
  -DLLAMA_BUILD_TESTS=OFF
  -DLLAMA_BUILD_EXAMPLES=OFF
  -DLLAMA_BUILD_APP=OFF
  -DLLAMA_TOOLS_INSTALL=OFF
  -DLLAMA_USE_PREBUILT_UI=OFF
  -DLLAMA_BUILD_NUMBER=${_build_number}
  -DGGML_NATIVE=${LLAMA_SERVER_VENDOR_NATIVE}
  -DGGML_CUDA=${_use_cuda}
)

if(_use_cuda)
  list(APPEND _llama_cmake_args -DCMAKE_CUDA_COMPILER=${CMAKE_CUDA_COMPILER})
endif()

if(_use_cuda AND _cuda_archs)
  string(REPLACE ";" "\\;" _cuda_archs_escaped "${_cuda_archs}")
  list(APPEND _llama_cmake_args "-DCMAKE_CUDA_ARCHITECTURES=${_cuda_archs_escaped}")
endif()

list(APPEND _llama_cmake_args ${LLAMA_SERVER_VENDOR_EXTRA_CMAKE_ARGS})

if(LLAMA_CPP_SOURCE_DIR)
  set(_llama_source SOURCE_DIR "${LLAMA_CPP_SOURCE_DIR}")
else()
  set(_llama_source URL "${CMAKE_CURRENT_SOURCE_DIR}/vendor/llama.cpp-${LLAMA_CPP_TAG}.tar.gz")
endif()

# Build only llama-server. $(MAKE) keeps colcon's parallel jobs
if(CMAKE_GENERATOR MATCHES "Make")
  set(_build_command $(MAKE) llama-server)
else()
  set(_build_command ${CMAKE_COMMAND} --build <BINARY_DIR> --target llama-server)
endif()

message(STATUS "llama_server_vendor: llama.cpp ${LLAMA_CPP_TAG} CUDA=${_use_cuda} archs='${_cuda_archs}'")

ExternalProject_Add(llama_cpp
  ${_llama_source}
  BINARY_DIR ${_llama_build_dir}
  CMAKE_ARGS ${_llama_cmake_args}
  BUILD_COMMAND ${_build_command}
  # Plain "install" would build all targets
  INSTALL_COMMAND ${CMAKE_COMMAND} -E env DESTDIR=${_stage_dir} ${CMAKE_COMMAND} --install <BINARY_DIR>
)

# install
install(
  DIRECTORY ${_stage_dir}${CMAKE_INSTALL_PREFIX}/
  DESTINATION .
  USE_SOURCE_PERMISSIONS
)

# Skipped by LLAMA_TOOLS_INSTALL=OFF
install(
  DIRECTORY ${_llama_build_dir}/bin/
  DESTINATION lib
  USE_SOURCE_PERMISSIONS
  FILES_MATCHING PATTERN "libllama-server-impl.so*"
)

# For ros2 run
install(
  PROGRAMS ${_stage_dir}${CMAKE_INSTALL_PREFIX}/bin/llama-server
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})

ament_package()
