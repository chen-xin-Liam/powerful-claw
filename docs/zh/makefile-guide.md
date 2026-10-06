# powerful-claw Makefile 使用指南

> 根目录 [Makefile](file:///home/liam/ollama/powerful-claw/Makefile) 支持 Linux 原生库增量构建、MinGW 交叉编译 Windows DLL（x86_64 + i686），并内置国内 pip 镜像加速。

## 一、环境要求

- Linux 主机，GNU Make、g++（支持 C++17，本机验证版本 g++ 15.2.0 / Make 4.4.1）。
- Python 3（用于生成 nodecalc 头文件；运行测试）。
- 交叉编译 Windows 需安装：`g++-mingw-w64-x86-64`、`g++-mingw-w64-i686`（提供 `x86_64-w64-mingw32-g++` 与 `i686-w64-mingw32-g++`）。
- OpenGL 特效库（可选）需系统存在 `libGL`/`libGLU` 开发文件。

Ubuntu/Debian 一次性安装：

```bash
sudo apt install build-essential mingw-w64 python3 libgl1-mesa-dev libglu1-mesa-dev
```

## 二、快速开始

```bash
make            # 构建全部 Linux 原生库（= native + nodecalc + effects）
make -j         # 并行构建
make test       # 运行自动化测试
make windows    # 交叉编译 64 位 + 32 位 Windows DLL
make clean      # 清理构建产物
make help       # 查看全部目标与变量当前值
```

## 三、构建目标

| 目标 | 说明 | 产物 |
|------|------|------|
| `all`（默认） | native + nodecalc + effects | 见下 |
| `native` | pcnative 四组 C++ 内核 | `src/core/native/pcnative/build/libpcnative.so` |
| `nodecalc` | 数学引擎原生库（`nodecalc.hpp` 由 `node_engine.EMBEDDED_CPP` 自动生成） | `src/core/native/libnodecalc_native.so` |
| `effects` | OpenGL 特效（链接 `-lGL -lGLU -ldl`） | `src/ui/effects/libgl_effects.so` |
| `windows` | windows64 + windows32 | `dist/windows/x86_64/`、`dist/windows/i686/` 下各 3 个 DLL |
| `windows64` / `windows32` | 单独构建 64 / 32 位 | `libpcnative.dll`、`nodecalc_native.dll`、`gl_effects.dll` |
| `test` | 运行 `auto_tests/run_tests.py`（自动带 `MAX_TOKENS=8192`） | — |
| `install` | 经国内镜像安装 `requirements.txt` | — |
| `setup-mirror` | 生成 pip 镜像配置 `.config/pip/pip.conf` | — |
| `check-mirror` | 用 `pip download six` 验证镜像连通 | — |
| `clean` | 删除 Linux 构建产物（保留 `dist/` 与镜像配置） | — |
| `distclean` | 在 clean 基础上再删 `dist/` 与镜像配置 | — |
| `help` | 打印目标与变量说明 | — |

构建为增量式：头文件/源文件未变化时二次执行 `make` 不会重复编译。Windows DLL 静态链接运行时，拷贝到目标 Windows 机器即可用，无需另装 MinWG 运行库。

## 四、可覆盖变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CXX` | `g++` | C++ 编译器 |
| `PYTHON` / `PIP` | `python3` / `pip` | Python 与 pip 命令 |
| `MINGW64` / `MINGW32` | `x86_64-w64-mingw32-g++` / `i686-w64-mingw32-g++` | 交叉编译器 |
| `OPT_LEVEL` | `O3` | 优化级别：`O0/O1/O2/O3/Os` |
| `LTO` | `0` | 设为 `1` 增加 `-flto` 链接时优化 |
| `MARCH` | `native` | 指令集架构，如 `x86-64`/`generic`；**交叉编译自动忽略** |
| `CXXFLAGS` / `EXTRA_CXXFLAGS` | 空 | 追加编译参数 |
| `MIRROR` | `aliyun` | pip 镜像：`aliyun/tuna/ustc/nju` |
| `PIP_INDEX_URL` / `PIP_TRUSTED_HOST` | 随 `MIRROR` 自动设置 | pip 源地址与可信主机 |

示例：

```bash
make native OPT_LEVEL=O2 LTO=1 MARCH=x86-64
make setup-mirror MIRROR=tuna
make install PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

## 五、国内镜像加速

`make setup-mirror` 会在 `.config/pip/pip.conf` 写入 `[global]` 与 `[install]` 段的 `index-url`、`trusted-host`，并设置 `timeout = 60`。可选镜像：

| MIRROR | 地址 |
|--------|------|
| `aliyun`（默认） | https://mirrors.aliyun.com/pypi/simple/ |
| `tuna` | https://pypi.tuna.tsinghua.edu.cn/simple |
| `ustc` | https://pypi.mirrors.ustc.edu.cn/simple/ |
| `nju` | https://mirror.nju.edu.cn/pypi/web/simple |

典型流程：

```bash
make setup-mirror          # 生成配置（默认阿里云）
make check-mirror          # 验证可下载
export PIP_CONFIG_FILE=$PWD/.config/pip/pip.conf
make install               # 或直接 pip install -r requirements.txt
```

`make install` 已自动通过 `-i`/`--trusted-host` 指向镜像，不导出环境变量也能加速。

## 六、产物部署

- **Linux**：三个 `.so` 生成在源码对应目录，程序经 `PCNATIVE_LIB` 或默认候选路径自动加载。
- **Windows**：将 `dist/windows/x86_64/`（64 位 Python/系统）或 `dist/windows/i686/`（32 位）下的 DLL 放到程序可查找位置；无原生库时程序自动回退纯 Python，功能不受影响。

## 七、故障排查

| 现象 | 处理 |
|------|------|
| `x86_64-w64-mingw32-g++: command not found` | 安装 `mingw-w64` 包，或用 `MINGW64=<编译器名> make windows64` 覆盖 |
| effects 构建报 `GL/gl.h: No such file` | 安装 `libgl1-mesa-dev`、`libglu1-mesa-dev`；不需要特效可只 `make native` |
| pip 下载超时 | 换镜像 `make setup-mirror MIRROR=tuna`，确认已 `export PIP_CONFIG_FILE` |
| 怀疑原生库导致行为异常 | 用 `PCNATIVE_BACKEND=python` 临时强制纯 Python 后端对比 |
| 需要彻底重来 | `make distclean` 后重新 `make` |
