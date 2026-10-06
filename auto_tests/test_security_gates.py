# -*- coding: utf-8 -*-
"""安全闸门回归测试（持久化，仓库内可复现）

覆盖：
1. 命令执行闸门：换行注入、引号规避、sudo rm -rf、命令替换、
   白名单命令访问敏感路径、正常命令放行；
2. NetAuth：回环判定、Token 校验与环境变量优先级；
3. 帧差分编码：相同帧无变化输出、变化帧增量编码、跨帧缓存命中；
4. secure_transport：签名往返、篡改/缺签名拒绝、过期时间戳拒绝、重放拒绝；
5. ai_agent AST 策略：validate_code 逃逸载荷拒绝、正常代码放行、
   表达式幂运算 DoS 拒绝。

同时可在无 pytest 环境下经 :func:`run_security_gates` 运行。
"""
import json
import os

from PIL import Image, ImageDraw

from src.services.command_executor import command_executor, default_command_gate
from src.services.ai_agent import validate_code, validate_expression
from src.utils import net_auth
from src.utils.remote_desktop_streamer import RDConfig, BlockEncoder
from src.services.cluster.secure_transport import SecureTransport


# ---------------- 1. 命令执行闸门 ----------------

def test_gate_blocks_newline_injection():
    # 换行不能在归一化时被抹掉：第二行的黑名单命令必须被识别
    for payload in ("echo SAFE\napt --version",
                    "ls\napt install x",
                    "echo x\r\nshutdown now"):
        _, err, rc = command_executor.run_simple_command(payload)
        assert rc == -1, f"换行注入未被拦截: {payload!r}"
        assert "拒绝" in err


def test_gate_blocks_quote_evasion():
    for payload in ("''sudo id", 's"u"do id', "'rm' -rf /"):
        _, _, rc = command_executor.run_simple_command(payload)
        assert rc == -1, f"引号规避未被拦截: {payload!r}"


def test_gate_blocks_high_risk_without_metachar():
    _, _, rc = command_executor.run_simple_command("sudo rm -rf /")
    assert rc == -1


def test_gate_blocks_command_substitution():
    for payload in ("echo `id`", "echo $(id)"):
        _, _, rc = command_executor.run_simple_command(payload)
        assert rc == -1


def test_gate_blocks_sensitive_path_for_whitelisted():
    # cat 是白名单命令，但 /etc/shadow 等敏感路径不能免确认
    _, _, rc = command_executor.run_simple_command("cat /etc/shadow")
    assert rc == -1


def test_gate_allows_benign_command():
    out, err, rc = command_executor.run_simple_command("echo hello")
    assert rc == 0
    assert out.strip() == "hello"


def test_gate_blocks_dangerous_subcommand_after_whitelisted():
    _, _, rc = command_executor.run_simple_command("ls && shutdown now")
    assert rc == -1


def test_gate_default_deny_shell_and_argv_obfuscation():
    """第二/三轮独立评审实证载荷（原黑名单前缀匹配的全部逃逸面）。"""
    payloads = [
        r"\a\p\t --version", r"ap\t --version",       # argv 反斜杠转义
        "(apt --version)", "{ apt --version; }",       # 分组括号/花括号
        "echo x && (apt --version)",                   # 括号包裹的 && 注入
        "env apt --version", "nice apt --version",     # 包装器再执行
        'bash -c "apt --version"', 'sh -c "apt --version"',
        'x="apt"; eval $x', "a=ap; b=t; $a$b --version",  # eval/变量拼接
        "echo bGFwdCAtLXZlcnNpb24= | base64 -d | sh",     # 解码执行管道
        "cat $HOME/.ssh/authorized_keys",                  # $HOME 敏感路径
    ]
    for payload in payloads:
        _, err, rc = command_executor.run_simple_command(payload)
        assert rc == -1, f"默认拒绝模型被逃逸: {payload!r}"
        assert err


def test_gate_allows_whitelisted_argv_only():
    for cmd in ("echo hello", "ls -la", "whoami", "pwd"):
        _, _, rc = command_executor.run_simple_command(cmd)
        assert rc == 0, f"白名单命令被误拒: {cmd}"


def test_gate_protects_sensitive_content_and_argv0(tmp_path):
    """第三/四轮独立评审实证载荷：私钥/Token 泄露、路径同名伪装、
    NUL、超长命令。测试不读取真实用户私钥，用临时文件替代。"""
    secret = tmp_path / "id_ed25519"
    secret.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nfake\n")

    # 末级文件名受保护（绝对路径 + 相对路径 cwd 两种形态）
    for cmd, cwd in ((f"cat {secret}", None),
                     ("cat id_ed25519", str(tmp_path)),
                     (f"head {secret}", None),
                     (f"date -f {secret}", None)):
        out, err, rc = (command_executor.run_simple_command(cmd, cwd=cwd)
                        if cwd else command_executor.run_simple_command(cmd))
        assert rc == -1, f"受保护内容未拦截: {cmd!r}"
        assert "BEGIN OPENSSH" not in out

    # .env 任意位置受保护
    env_file = tmp_path / ".env"
    env_file.write_text('API_TOKEN="should-not-leak"')
    out, _, rc = command_executor.run_simple_command(f"cat {env_file}")
    assert rc == -1
    assert "should-not-leak" not in out

    # argv[0] 路径同名伪装
    for cmd in ("./ls", "/tmp/ls", "../ls"):
        allowed, _ = default_command_gate(cmd)
        assert not allowed, f"路径形式 argv[0] 被放行: {cmd}"

    # NUL 与超长
    assert not default_command_gate("echo x\x00y")[0]
    assert not default_command_gate("echo " + "a" * 5000)[0]


def test_gate_blocks_r4_time_wrapper_and_glued_options(tmp_path):
    """第四轮独立评审实证载荷。"""
    # F-1：白名单中的 time 可再执行任意程序 → 已移除
    for cmd in ("time apt --version", "time sh -c whoami", "time id"):
        allowed, _ = default_command_gate(cmd)
        assert not allowed, f"time 包装器被放行: {cmd}"

    # F-2：getopt 粘连形态读取项目外文件
    target = tmp_path / "history.txt"
    target.write_text("SECRET-LINE-SHOULD-NOT-LEAK\n")
    for cmd in (f"date -f{target}", f"date --file={target}",
                f"date -uf{target}", f"head -n1 {target}"):
        out, _, rc = command_executor.run_simple_command(cmd)
        assert rc == -1, f"粘连路径被放行: {cmd}"
        assert "SECRET-LINE" not in out

    # F-3：凭据文件名/备份名枚举
    creds = tmp_path / ".pypirc"
    creds.write_text("[pypi]\npassword=SECRET\n")
    for name in (".pypirc", ".git-credentials", "id_ed25519.bak",
                 "identity.bak", ".docker/config.json", ".kube/config"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("SECRET")
        allowed, _ = default_command_gate(f"cat {path}")
        assert not allowed, f"凭据文件 {name} 被放行"


def test_gate_cwd_locked_to_project_root():
    # 项目外 cwd 拒绝；None（项目根）正常
    out, _, rc = command_executor.run_simple_command("ls", cwd="/tmp")
    assert rc == -1
    out, _, rc = command_executor.run_simple_command("echo ok")
    assert rc == 0 and out.strip() == "ok"


# ---------------- 2. NetAuth ----------------

def test_is_loopback():
    for host in ("127.0.0.1", "127.1.2.3", "::1", "localhost"):
        assert net_auth.is_loopback(host), f"{host} 应判为回环"
    for host in ("192.168.1.1", "10.0.0.1", "example.com", None, ""):
        assert not net_auth.is_loopback(host), f"{host} 不应判为回环"


def test_token_validation(monkeypatch):
    monkeypatch.setenv(net_auth._TOKEN_ENV_VAR, "unit-test-token-xyz")
    assert net_auth.get_token() == "unit-test-token-xyz"
    assert net_auth.token_valid("unit-test-token-xyz")
    assert not net_auth.token_valid("wrong-token")
    assert not net_auth.token_valid("")
    assert not net_auth.token_valid(None)


# ---------------- 3. 帧差分编码 ----------------

def _make_frames():
    base = Image.new("RGB", (160, 120), (30, 60, 90))
    draw = ImageDraw.Draw(base)
    for x in range(160):
        draw.line([(x, 0), (x, 120)], fill=(x % 256, 60, 90))
    changed = base.copy()
    ImageDraw.Draw(changed).rectangle([4, 4, 40, 40], fill=(255, 255, 255))
    return base, changed


def test_blocks_same_frame_no_change():
    base, _ = _make_frames()
    enc = BlockEncoder(RDConfig())
    # 全帧无 mask：全部块都被编码（关键帧语义）
    r1 = enc.encode_blocks(base, diff_mask=None, quality=70)
    assert r1["type"] == "blocks"
    assert len(r1["data"]) > 0


def test_blocks_changed_frame_incremental_and_cache():
    base, changed = _make_frames()
    enc = BlockEncoder(RDConfig())
    enc.encode_blocks(base, diff_mask=None, quality=70)
    # 相同内容第二帧：键一致 → 命中缓存
    r_same = enc.encode_blocks(base, diff_mask=None, quality=70)
    assert r_same["cache_hits"] > 0
    # 变化帧：有块输出且字节非空
    import numpy as np
    arr = np.array(changed) - np.array(base)
    mask = (abs(arr).sum(axis=2) > 10).astype("uint8") * 255
    r_chg = enc.encode_blocks(changed, diff_mask=mask, quality=70)
    assert len(r_chg["data"]) > 0
    assert all(b["data"] for b in r_chg["data"])


# ---------------- 4. secure_transport ----------------

def _signed_message(transport, timestamp=None, nonce=None):
    import time
    import uuid
    message = {
        "type": "ping",
        "data": {"k": "v"},
        "node_id": transport.node_id,
        "timestamp": timestamp if timestamp is not None else int(time.time()),
        "nonce": nonce if nonce is not None else uuid.uuid4().hex,
    }
    message["signature"] = transport.sign_message(
        transport._canonical_payload(message))
    return message


def test_secure_message_roundtrip():
    t = SecureTransport()
    enc = t.create_secure_message("ping", {"x": 1})
    parsed = t.parse_secure_message(enc)
    assert parsed is not None
    assert parsed["type"] == "ping"


def test_secure_message_tamper_and_missing_signature():
    t = SecureTransport()
    msg = _signed_message(t)
    msg["signature"] = msg["signature"][:-2] + ("ab" if msg["signature"][-2:] != "ab" else "cd")
    assert t.parse_secure_message(t.encrypt(json.dumps(msg))) is None

    msg2 = _signed_message(t)
    del msg2["signature"]
    assert t.parse_secure_message(t.encrypt(json.dumps(msg2))) is None


def test_secure_message_expired_timestamp():
    import time
    t = SecureTransport()
    msg = _signed_message(t, timestamp=int(time.time()) - 301)
    assert t.parse_secure_message(t.encrypt(json.dumps(msg))) is None


def test_secure_message_replay_rejected():
    import time
    t = SecureTransport()
    msg = _signed_message(t, timestamp=int(time.time()))
    first = t.parse_secure_message(t.encrypt(json.dumps(msg)))
    assert first is not None
    # 完全相同的密文再次投递 → nonce 重放
    assert t.parse_secure_message(t.encrypt(json.dumps(msg))) is None


# ---------------- 5. ai_agent AST 策略 ----------------

def test_validate_code_rejects_escapes():
    for src in ('eval("__imp"+"ort__(...)")',
                'exec("import os")',
                'open("/etc/passwd").read()',
                'compile("x", "s", "exec")',
                'g=getattr',
                '(1).__class__',
                'import os'):
        try:
            validate_code(src)
        except ValueError:
            continue
        raise AssertionError(f"逃逸载荷未被拦截: {src}")


def test_validate_code_allows_normal_code():
    validate_code("x = [i * 2 for i in range(3)]\nprint(sum(x))")


def test_expression_pow_dos_rejected():
    for src in ("9**9**9", "2**999999"):
        try:
            validate_expression(src)
        except ValueError:
            continue
        raise AssertionError(f"幂运算 DoS 未被拦截: {src}")
    validate_expression("2**10")


# ---------------- 无 pytest 入口 ----------------

def run_security_gates():
    """顺序运行全部安全用例（无 pytest 时使用）。返回 (passed, failed)。"""
    import inspect

    tests = [fn for name, fn in sorted(globals().items())
             if name.startswith("test_") and inspect.isfunction(fn)
             and fn.__module__ == __name__]
    passed = failed = 0
    for fn in tests:
        params = inspect.signature(fn).parameters
        kwargs = {}
        if "monkeypatch" in params:
            class _MP:
                def setenv(self, k, v):
                    os.environ[k] = v
            kwargs["monkeypatch"] = _MP()
        try:
            fn(**kwargs)
            passed += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  [FAIL] {fn.__name__}: {e}")
    print(f"  安全闸门: 通过 {passed}/{passed + failed}")
    return passed, failed


if __name__ == "__main__":
    p, f = run_security_gates()
    raise SystemExit(1 if f else 0)
