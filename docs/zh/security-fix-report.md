# powerful-claw 安全漏洞与缺陷修复报告

> 适用范围：本次"安全加固 · C++ 化 · Makefile"专项（Task 1–15）
> 结论概览：共修复 **1 个认证缺失类漏洞、2 个命令/代码执行类漏洞、1 个重放/伪造类漏洞、3 个权限与业务逻辑缺陷、3 个性能/可用性问题**；自动化测试 `auto_tests/` 149 项、`tests/` 11 项全部通过。

---

## 一、修复清单总览

| 编号 | 类别 | 位置 | 风险等级 | 状态 |
|------|------|------|----------|------|
| SEC-01 | API/WebSocket 无鉴权（远程可完全控制主机） | api_server / cluster_api / websocket_server | 严重 | 已修复 |
| SEC-02 | 高危命令可绕过检测（`sudo rm -rf /` 无 shell 元字符） | command_executor | 严重 | 已修复 |
| SEC-03 | 命令替换注入（`` ` `` / `$()` / 管道串联子命令） | command_executor | 高 | 已修复 |
| SEC-04 | 集群消息无时间窗/无重放防护/可跳过验签 | secure_transport | 高 | 已修复 |
| SEC-05 | AI Agent 使用裸 `eval` / 动态代码可导入任意模块 | ai_agent | 高 | 已修复 |
| SEC-06 | LIMITED 权限可触发系统热键 | system_controller | 中 | 已修复 |
| DEF-01 | 远控指令未经过统一权限入口 | websocket_server | 高 | 已修复 |
| DEF-02 | 视觉处理器指令映射到不存在的 API | websocket_server | 中 | 已修复 |
| DEF-03 | 远控流关键帧/自适应质量缺陷 | remote_desktop_streamer | 中 | 已修复 |
| PERF-01 | 帧差分稀疏变化时仍复制整帧 | remote_desktop_streamer | 性能 | 已优化 |
| PERF-02 | adler32 逐字节取模、图像转换重复拷贝 | pcnative / 接入层 | 性能 | 已优化 |

---

## 二、严重与高危漏洞详情

### SEC-01　网络服务无任何鉴权（严重）

- **位置**：[api_server.py](file:///home/liam/ollama/powerful-claw/src/services/api_server.py)、[cluster_api.py](file:///home/liam/ollama/powerful-claw/src/services/cluster/cluster_api.py)、[websocket_server.py](file:///home/liam/ollama/powerful-claw/src/services/websocket_server.py)
- **原问题**：HTTP API 与 WebSocket 端口不校验任何身份，同网段（或端口暴露到公网时）任意主机均可连接并下发截屏、键鼠、关机、执行命令等远控指令，等价于主机被完全接管。
- **修复方案**：
  1. 新增 [net_auth.py](file:///home/liam/ollama/powerful-claw/src/utils/net_auth.py)：`get_token()`（优先级 `PCNATIVE_API_TOKEN` 环境变量 → `.env` 的 `API_TOKEN` → `secrets.token_urlsafe(32)` 生成并回写）、`is_loopback()`、`token_valid()`、`authorize_websocket()`（异步握手）、`TokenAuthMixin`。
  2. **回环放行**：来源为 `127.0.0.0/8`、`::1`、`localhost` 时本机自用免 token；**非回环连接强制 Token**。
  3. Token 可通过 WebSocket 查询参数 `?token=` 或连接后首条消息提交，握手超时 `HANDSHAKE_TOKEN_TIMEOUT=5.0`，超时即拒绝。
  4. 三类服务统一接入 `TokenAuthMixin`。
- **验证**：无 token / 错误 token 的非回环连接被拒；携带正确 token 放行。

### SEC-02　高危命令绕过检测（严重）

- **位置**：[command_executor.py](file:///home/liam/ollama/powerful-claw/src/services/command_executor.py)
- **原问题**：命令门控只检查 shell 元字符。`sudo rm -rf /` 这类不含元字符的命令可直接通过并执行。
- **最终修复（默认拒绝架构）**：闸门不再使用"黑名单前缀 startswith"单层判定（两轮独立评审证明反斜杠转义、括号分组、`env/nice/bash -c` 包装、变量拼接、解码管道等变形均可绕过），改为：
  - POSIX 下含**任何 shell 语法特征**（分隔符、分组括号/花括号、重定向、换行、反斜杠、`$` 展开、`!`、`**`）的命令**一律拒绝**——本服务层没有交互式授权管理器，需要 shell 的高级命令必须由带确认能力的自定义闸门（`set_gate`）显式放行；
  - 其余命令经 **shlex 切分为 argv（与执行层同一词法分析）**，程序名必须是 PATH 裸名（拒绝 `./x`、`/tmp/x` 路径同名伪装）且在只读命令白名单内；
  - 每个 argv 参数经**组件级受保护内容检查**，自动剥离 getopt 粘连（`-fPATH`、`--file=PATH` 中的 PATH 与独立 token 同判）：`.ssh/.gnupg/.aws/.docker/.kube/.config` 目录、`id_*/identity`（含 `.bak` 等后缀）、`.env/.netrc/.pypirc/.git-credentials/.bash_history/credentials` 等文件名、`/etc`/`/root` 等系统目录、`..` 跳转均拒绝；
  - **文件系统边界**：默认闸门下绝对路径仅允许指向**项目根目录之内**（项目外文件一律不可读），cwd 锁定在项目根（`None` 即项目根），防止经 AI 可控参数/cwd 读取用户主目录、/tmp 等任意位置；
  - 命令长度上限 4096 字节、拒绝 NUL，防解析器 DoS；执行始终 `shell=False`，从根本上消除元字符解释。
  - Windows 保留高危黑名单检测（平台命令模型不同）。

### SEC-03　命令替换注入（高）

- **位置**：[command_executor.py](file:///home/liam/ollama/powerful-claw/src/services/command_executor.py)
- **原问题**：含反引号、`$()` 的命令可在 shell 中执行隐藏的嵌套命令；管道/`;`/`&&` 串联的多个子命令只对整串做一次判定，危险子命令可"搭车"执行。
- **修复方案**：`has_command_substitution()` 识别 `` ` ``、`$()`、`${` 并拒绝；结合 SEC-02 的默认拒绝模型，管道、`;`、`&&`、换行等串联结构整体拒绝；`run_simple_command()` 默认超时 30 秒，仅以 argv 直执行。

### SEC-04　集群消息重放与伪造（高）

- **位置**：[secure_transport.py](file:///home/liam/ollama/powerful-claw/src/services/cluster/secure_transport.py)
- **原问题**：消息无时间窗口或窗口形同虚设、无 nonce 去重、验签可被跳过，攻击者可重放历史控制消息或伪造消息。
- **修复方案**：时间戳窗口收紧为 **300 秒**；新增 nonce 重放缓存（LRU 上限 5000 条）；**强制验签**，签名缺失或不匹配一律拒绝。

### SEC-05　AI Agent 代码执行注入（高）

- **位置**：[ai_agent.py](file:///home/liam/ollama/powerful-claw/src/services/ai_agent.py)
- **原问题**：策略层使用裸 `eval`，且动态代码执行可导入任意模块、访问双下划线魔术属性，模型一旦被提示注入即可执行任意 Python 代码。
- **修复方案**：AST 策略层新增
  - `validate_expression()`：表达式白名单，仅允许安全节点；并限制嵌套幂运算与超大指数（防 CPU 型 DoS）；
  - `safe_eval_expression()`：以 `__builtins__={}` 执行；
  - `validate_code()`：import 拒绝；`eval/exec/compile/open/getattr/setattr` 等危险内置**连别名引用都拒绝**；双下划线属性/标识符拒绝；字符串常量含 `__` 拒绝；按名调用必须在白名单内；
  - CommandTool 统一改走 `run_simple_command()`，不经 shell。

### SEC-06　LIMITED 权限可触发系统热键（中）

- **位置**：SystemController 权限表
- **原问题**：LIMITED（受限）级别下 `keyboard_hotkey=True`，而热键可触发锁屏、切窗口、系统快捷操作等，属于越权。
- **修复方案**：收紧为 `False`，与测试期望及最小权限原则一致（鼠标移动等只读/低危操作仍保留）。

---

## 三、功能缺陷修复

### DEF-01　远控指令绕过权限入口（高）

- **位置**：[websocket_server.py](file:///home/liam/ollama/powerful-claw/src/services/websocket_server.py)
- **问题**：WebSocket 远控的 24 条指令原先直接调用底层实现，不经过权限校验。
- **修复**：全部改经 `SystemController.execute_operation` 统一入口，按 `PermissionLevel`（NONE/VIEW/LIMITED/FULL）与 `OperationPermission` 鉴权。

### DEF-02　视觉处理器指令映射错误（中）

- **修复**：将映射对齐 `VisionCapture` 真实 API；截屏指令返回 base64 data URL。同时补全控制器缺失的 `mouse_move_relative/drag`、`window_minimize/maximize/restore/close`、`system_lock/shutdown/restart/sleep` 及音量控制操作。

### DEF-03　远控流关键帧 / 自适应质量缺陷（中）

- **位置**：[remote_desktop_streamer.py](file:///home/liam/ollama/powerful-claw/src/utils/remote_desktop_streamer.py)
- **修复**：修正关键帧请求与质量自适应逻辑；无变化块时不重复发送；块缓存键统一为 `quality:adler32raw`，跨帧命中缓存。

---

## 四、性能问题修复

| 项 | 原问题 | 优化 | 效果（best-of） |
|----|--------|------|-----------------|
| PERF-01 | 仅 2 块变化时仍把整帧 6MB 送进规划器 | 稀疏路径 `pcn_scan_mask` 只扫掩码 + 逐块 `pcn_adler32` | 典型掩码 **8.8×**（31.2ms→3.6ms） |
| PERF-02 | adler32 逐字节 `% 65521`（整数除法） | 每 5552 字节批量取模一次 | 全帧块规划 **5.6×** |
| PERF-02 | `np.ascontiguousarray(img).tobytes()` 需 11–25ms | 改用 PIL `img.tobytes()`（约 1ms） | 图像路径整体提速 |
| — | CRC32 逐字节 | 升级为 slicing-by-8（8 表并行），与 zlib 结果一致 | 封包吞吐提升 |

性能门禁 [test_performance.py](file:///home/liam/ollama/powerful-claw/auto_tests/test_performance.py) 已做抗噪改造（主机负载检测 + best-of-N + 清洁窗口不足时 skip），避免高负载机器上的误报。

---

## 五、已接受的残留风险（按用户决策保留，未删除）

以下问题已识别，依据"**已跟踪文件全部保留、禁止 git rm**"的明确决策，本次**不移除、不改名**，仅在此披露：

1. **`.env` 保持 Git 跟踪，且 `API_TOKEN` 已入库**
   - 现状：`.env` 受版本控制，文件末尾由鉴权模块回写了 `API_TOKEN`（`secrets.token_urlsafe(32)` 生成）。
   - 风险：任何能访问该仓库的人都能看到此 Token；若仓库公开或将同步到远端，Token 即泄露。
   - 缓解建议（后续可选，本次不执行）：更换 Token（删除该行后重启服务会自动重新生成）、将 `.env` 移出跟踪并改用 `.env.example` 模板、在远端轮换密钥。
2. **仓库内的大体积二进制文件保留**：`python-3.13.15-amd64.exe`、`start.exe`、`yolov8n.pt` 均为已跟踪文件，本次原样保留；`.exe` 文件建议仅从官方渠道分发，运行前校验来源。

---

## 六、验证结论

- `auto_tests/`：**149 passed**（含持久化安全闸门测试 [test_security_gates.py](file:///home/liam/ollama/powerful-claw/auto_tests/test_security_gates.py)，覆盖命令注入/换行/引号、反斜杠与括号变形、包装器与解码执行、getopt 粘连路径、私钥/.env/凭据组件级保护、argv[0] 伪装、cwd 项目根锁定、NetAuth 回环与 Token、帧差缓存、secure_transport 篡改/过期/重放、AST 策略逃逸）；`tests/`：**11 passed**。
- pcnative 四组内核双后端（native / 强制 Python）结果逐字节一致，详见 [C++ 化模块说明](./cpp-modules.md)。
- 无 DISPLAY 的无头环境使用 `xvfb-run` 验证键鼠/控制器相关用例。
- 四轮独立评审均判 FAIL（R1：换行注入/validate_code 逃逸/测试未持久化；R2：黑名单前缀模型的反斜杠、括号、包装器、变量拼接等变形绕过；R3：私钥/.env 泄露、argv[0] 路径伪装、解析器 DoS；R4：`time` 包装器、getopt 粘连读项目外文件、凭据名枚举不全），均已修复：闸门最终为默认拒绝 + argv 白名单 + 组件级内容保护 + 项目根文件系统边界，全部实证载荷已持久化，第五轮重新评审。
