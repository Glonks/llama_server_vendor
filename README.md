# llama_server_vendor

ROS 2 vendor package for [llama.cpp](https://github.com/ggml-org/llama.cpp) `llama-server`.
Works on Humble (Ubuntu 22.04) and Jazzy (Ubuntu 24.04), on x86_64 and Jetson (Orin, Thor).

The llama.cpp source (release `b11243`) is in `vendor/`, so the build does not need internet.
The web UI is not included. The API works.

## Build

```zsh
cd ~/ros2_ws/src && git clone <this repo> llama_server_vendor
cd ~/ros2_ws
rosdep install --from-paths src -y --ignore-src
colcon build --packages-select llama_server_vendor
```

CUDA is found automatically (also `/usr/local/cuda/bin/nvcc`). The GPU arch is set from the device:

| Device | Detect | CUDA arch |
|---|---|---|
| Jetson Orin (JetPack 6, Humble) | `tegra234` | 87 |
| Jetson Thor (JetPack 7, Jazzy) | `tegra264` | 110 (CUDA 13), 101 (CUDA 12.x) |
| x86 GPU | llama.cpp `native` (CMake >= 3.24), else `nvidia-smi` | compute cap |

On Jetson, limit parallel jobs to prevent out-of-memory during the CUDA compile:

```zsh
MAKEFLAGS=-j4 colcon build --packages-select llama_server_vendor
```

### CMake options (`--cmake-args -D<opt>=<val>`)

| Option | Default | Use |
|---|---|---|
| `LLAMA_CPP_SOURCE_DIR` | empty | Use a different llama.cpp source tree (for development) |
| `LLAMA_SERVER_VENDOR_CUDA` | `AUTO` | `ON` / `OFF` / `AUTO` |
| `LLAMA_SERVER_VENDOR_CUDA_ARCHS` | auto | For example `87` or `87;110` (for cross builds / Docker without a GPU) |
| `LLAMA_SERVER_VENDOR_NATIVE` | `ON` | Set `OFF` for binaries that run on other CPUs |
| `LLAMA_SERVER_VENDOR_EXTRA_CMAKE_ARGS` | empty | More llama.cpp args |

## Use

```zsh
source install/setup.zsh
llama-server --version                                   # on PATH
ros2 run llama_server_vendor llama-server -m model.gguf  # with ros2 run
ros2 launch llama_server_vendor llama_server.launch.py model:=/path/model.gguf port:=8080
ros2 launch llama_server_vendor llama_server.launch.py hf_repo:=ggml-org/gemma-3-1b-it-GGUF
```

Launch args: `model`, `hf_repo`, `host`, `port`, `n_gpu_layers`, `ctx_size`, `extra_args`.
If you do not set an arg, llama-server uses its own default.

The server gives an OpenAI-compatible API at `http://<host>:<port>/v1`.

Only `llama-server` is built (no other llama.cpp tools). C++ packages can link the llama.cpp libraries with `find_package(llama REQUIRED)` and `target_link_libraries(<tgt> llama)`.

## Update llama.cpp

```zsh
scripts/update_llama_cpp.sh b12000   # download the new release to vendor/ and set the tag
```
