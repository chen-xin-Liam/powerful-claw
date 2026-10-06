# ======================================================================
# powerful-claw Makefile —— 多平台原生构建 / 国内镜像加速
#
# 快速开始：
#   make                      编译全部 Linux 原生库（pcnative/nodecalc/effects）
#   make -j                   并行增量构建
#   make native               仅构建 pcnative（四组 C++ 内核）
#   make windows              MinGW 交叉编译 Windows DLL（x86_64 + i686）
#   make setup-mirror         配置国内 pip 镜像（默认阿里云）
#   make test                 运行自动化测试套件
#   make help                 查看全部目标与变量
#
# 常用变量覆盖：
#   make native OPT_LEVEL=O2 LTO=1 MARCH=x86-64
#   make setup-mirror MIRROR=tuna
#   make install PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
# ======================================================================

# ----------------------- 工具链 -----------------------
CXX        ?= g++
PYTHON     ?= python3
PIP        ?= pip
MINGW64    ?= x86_64-w64-mingw32-g++
MINGW32    ?= i686-w64-mingw32-g++

# ----------------------- 编译选项 -----------------------
OPT_LEVEL  ?= O3                 # O0/O1/O2/O3/Os
LTO        ?= 0                  # 1 = 链接时优化
MARCH      ?= native             # native/x86-64/generic；交叉编译时自动忽略
CXXFLAGS   ?=
EXTRA_CXXFLAGS ?=

OPT_FLAGS  := -$(OPT_LEVEL)
ifeq ($(LTO),1)
OPT_FLAGS  += -flto
endif
ARCH_FLAGS :=
ifneq ($(strip $(MARCH)),)
ARCH_FLAGS := -march=$(MARCH)
endif

# Linux 通用编译参数（不含 -shared/-fPIC，按目标追加）
BASE_FLAGS := -std=c++17 $(OPT_FLAGS) $(ARCH_FLAGS) -Wall -Wextra \
              $(CXXFLAGS) $(EXTRA_CXXFLAGS)

# MinGW 交叉参数（不能使用 -march=native；静态链接运行时，目标机免装 dll）
MINGW_FLAGS := -std=c++17 $(OPT_FLAGS) -Wall -Wextra \
               -static -static-libgcc -static-libstdc++

# ----------------------- 国内镜像 -----------------------
MIRROR     ?= aliyun
ifeq ($(MIRROR),aliyun)
  DEFAULT_INDEX := https://mirrors.aliyun.com/pypi/simple/
  DEFAULT_HOST  := mirrors.aliyun.com
else ifeq ($(MIRROR),tuna)
  DEFAULT_INDEX := https://pypi.tuna.tsinghua.edu.cn/simple
  DEFAULT_HOST  := pypi.tuna.tsinghua.edu.cn
else ifeq ($(MIRROR),ustc)
  DEFAULT_INDEX := https://pypi.mirrors.ustc.edu.cn/simple/
  DEFAULT_HOST  := pypi.mirrors.ustc.edu.cn
else ifeq ($(MIRROR),nju)
  DEFAULT_INDEX := https://mirror.nju.edu.cn/pypi/web/simple
  DEFAULT_HOST  := mirror.nju.edu.cn
else
  $(error 不支持的 MIRROR=$(MIRROR)，可选: aliyun/tuna/ustc/nju)
endif

PIP_INDEX_URL    ?= $(DEFAULT_INDEX)
PIP_TRUSTED_HOST ?= $(DEFAULT_HOST)
PIP_CONF         := .config/pip/pip.conf

# ----------------------- 路径 -----------------------
NC_DIR      := src/core/native
PCN_DIR     := $(NC_DIR)/pcnative
PCN_BUILD   := $(PCN_DIR)/build
PCN_SRC     := $(PCN_DIR)/pcnative.cpp
PCN_HDR     := $(PCN_DIR)/pcnative.h
PCN_LIB     := $(PCN_BUILD)/libpcnative.so

NODE_CAPI   := $(NC_DIR)/nodecalc_capi.cpp
NODE_HPP    := $(NC_DIR)/build/nodecalc.hpp
NODE_ENGINE := src/core/node_engine.py
NODE_LIB    := $(NC_DIR)/libnodecalc_native.so

FX_DIR      := src/ui/effects
FX_SRC      := $(FX_DIR)/gl_effects.cpp
FX_HDR      := $(FX_DIR)/gl_effects.h
FX_LIB      := $(FX_DIR)/libgl_effects.so

WIN_DIR     := dist/windows
DLL64_DIR   := $(WIN_DIR)/x86_64
DLL32_DIR   := $(WIN_DIR)/i686
PCN_DLL64   := $(DLL64_DIR)/libpcnative.dll
PCN_DLL32   := $(DLL32_DIR)/libpcnative.dll
NODE_DLL64  := $(DLL64_DIR)/nodecalc_native.dll
NODE_DLL32  := $(DLL32_DIR)/nodecalc_native.dll
FX_DLL64    := $(DLL64_DIR)/gl_effects.dll
FX_DLL32    := $(DLL32_DIR)/gl_effects.dll

# ----------------------- 目标 -----------------------
.DEFAULT_GOAL := all

.PHONY: all native nodecalc effects windows windows64 windows32 \
        test install setup-mirror check-mirror clean distclean help

all: native nodecalc effects

native: $(PCN_LIB)
nodecalc: $(NODE_LIB)
effects: $(FX_LIB)

# ---- pcnative（Linux）----
$(PCN_LIB): $(PCN_SRC) $(PCN_HDR) | $(PCN_BUILD)
	$(CXX) $(BASE_FLAGS) -fPIC -shared $(PCN_SRC) -o $@
	@echo "==> 已生成 $@"

# ---- nodecalc（Linux）----
$(NODE_LIB): $(NODE_CAPI) $(NODE_HPP)
	$(CXX) $(BASE_FLAGS) -fPIC -shared $(NODE_CAPI) -o $@
	@echo "==> 已生成 $@"

# nodecalc.hpp 从 node_engine.EMBEDDED_CPP 提取（单一事实来源）
$(NODE_HPP): $(NODE_ENGINE) | $(NC_DIR)/build
	PYTHONPATH=$(NC_DIR) $(PYTHON) -c "import build_native; build_native.generate_header()"
	@echo "==> 已生成 $@"

# ---- OpenGL 特效（Linux，可选加速）----
$(FX_LIB): $(FX_SRC) $(FX_HDR)
	$(CXX) $(BASE_FLAGS) -fPIC -shared $(FX_SRC) -o $@ -lGL -lGLU -ldl
	@echo "==> 已生成 $@"

# ---- Windows 交叉编译 ----
windows: windows64 windows32

windows64: $(PCN_DLL64) $(NODE_DLL64) $(FX_DLL64)

windows32: $(PCN_DLL32) $(NODE_DLL32) $(FX_DLL32)

$(PCN_DLL64): $(PCN_SRC) $(PCN_HDR) | $(DLL64_DIR)
	$(MINGW64) $(MINGW_FLAGS) -shared $(PCN_SRC) -o $@
	@echo "==> 已生成 $@"

$(PCN_DLL32): $(PCN_SRC) $(PCN_HDR) | $(DLL32_DIR)
	$(MINGW32) $(MINGW_FLAGS) -shared $(PCN_SRC) -o $@
	@echo "==> 已生成 $@"

$(NODE_DLL64): $(NODE_CAPI) $(NODE_HPP) | $(DLL64_DIR)
	$(MINGW64) $(MINGW_FLAGS) -shared $(NODE_CAPI) -o $@
	@echo "==> 已生成 $@"

$(NODE_DLL32): $(NODE_CAPI) $(NODE_HPP) | $(DLL32_DIR)
	$(MINGW32) $(MINGW_FLAGS) -shared $(NODE_CAPI) -o $@
	@echo "==> 已生成 $@"

$(FX_DLL64): $(FX_SRC) $(FX_HDR) | $(DLL64_DIR)
	$(MINGW64) $(MINGW_FLAGS) -shared $(FX_SRC) -o $@ -lopengl32 -lglu32
	@echo "==> 已生成 $@"

$(FX_DLL32): $(FX_SRC) $(FX_HDR) | $(DLL32_DIR)
	$(MINGW32) $(MINGW_FLAGS) -shared $(FX_SRC) -o $@ -lopengl32 -lglu32
	@echo "==> 已生成 $@"

# ---- 目录（order-only）----
$(PCN_BUILD) $(NC_DIR)/build $(DLL64_DIR) $(DLL32_DIR):
	mkdir -p $@

# ----------------------- 测试 -----------------------
test:
	MAX_TOKENS=8192 $(PYTHON) auto_tests/run_tests.py
	@echo '另可运行: pytest tests/  与  MAX_TOKENS=8192 pytest auto_tests/'

# ----------------------- 依赖安装（走镜像）----
install:
	PIP_CONFIG_FILE=$(abspath $(PIP_CONF)) $(PIP) install \
	  -i $(PIP_INDEX_URL) --trusted-host $(PIP_TRUSTED_HOST) \
	  -r requirements.txt

# ----------------------- 国内镜像配置 -----------------------
setup-mirror:
	@mkdir -p $(dir $(PIP_CONF))
	@printf '[global]\nindex-url = %s\ntrusted-host = %s\ntimeout = 60\n\n[install]\nindex-url = %s\ntrusted-host = %s\n' \
	  "$(PIP_INDEX_URL)" "$(PIP_TRUSTED_HOST)" \
	  "$(PIP_INDEX_URL)" "$(PIP_TRUSTED_HOST)" > $(PIP_CONF)
	@echo "==> 已生成 $(PIP_CONF)"
	@echo "    index-url = $(PIP_INDEX_URL)"
	@echo "    使用方式: export PIP_CONFIG_FILE=$(abspath $(PIP_CONF))"
	@echo "    或直接:   make check-mirror / make install"

check-mirror:
	@echo "==> 通过 $(PIP_INDEX_URL) 下载测试包"
	PIP_CONFIG_FILE=$(abspath $(PIP_CONF)) $(PIP) download --no-deps \
	  --dest /tmp/pcn-pipcheck -i $(PIP_INDEX_URL) \
	  --trusted-host $(PIP_TRUSTED_HOST) six
	@echo "==> 镜像连通正常"

# ----------------------- 清理 -----------------------
clean:
	rm -f $(PCN_LIB) $(NODE_LIB) $(FX_LIB) $(NODE_HPP)
	rm -rf $(FX_DIR)/build $(FX_DIR)/bin
	@echo "==> 已清理原生构建产物（保留 dist/ 与镜像配置）"

distclean: clean
	rm -rf dist
	rm -f $(PIP_CONF)
	@echo "==> 已清理 dist/ 与 pip 镜像配置"

# ----------------------- 帮助 -----------------------
help:
	@echo 'powerful-claw Makefile 目标:'
	@echo '  make all           构建全部 Linux 原生库（默认目标）'
	@echo '  make native        构建 pcnative（图像/块编码/表达式/封包）'
	@echo '  make nodecalc      构建数学引擎原生库'
	@echo '  make effects       构建 OpenGL 特效库（需 libGL/libGLU）'
	@echo '  make windows       交叉编译 x86_64 + i686 Windows DLL'
	@echo '  make windows64 / windows32'
	@echo '  make test          运行自动化测试套件'
	@echo '  make install       经国内镜像安装 requirements.txt'
	@echo '  make setup-mirror  生成 pip 镜像配置 (MIRROR=aliyun/tuna/ustc/nju)'
	@echo '  make check-mirror  验证镜像可下载'
	@echo '  make clean         清理构建产物'
	@echo '  make distclean     额外清理 dist/ 与镜像配置'
	@echo ''
	@echo '可覆盖变量（当前值）:'
	@echo '  CXX=$(CXX)  PYTHON=$(PYTHON)'
	@echo '  OPT_LEVEL=$(OPT_LEVEL)  LTO=$(LTO)  MARCH=$(MARCH)'
	@echo '  MIRROR=$(MIRROR)'
	@echo '  PIP_INDEX_URL=$(PIP_INDEX_URL)'
	@echo '  MINGW64=$(MINGW64)'
	@echo '  MINGW32=$(MINGW32)'
