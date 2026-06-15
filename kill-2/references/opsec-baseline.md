# kill-2 OPSEC 基线手册

## 环境配置要求

```bash
# 1. 隔离操作环境
#    macOS: 专用 VM (UTM/Parallels) 运行 Linux
#    Linux: 专用用户 + firejail
#    Windows: Sandboxie + 专用 VM

# 2. 浏览器指纹保护
#    使用 Firefox ESR + arkenfox user.js
#    禁用 WebRTC, Canvas fingerprinting
#    每次操作新 identity

# 3. 网络隔离
#    VPN → Tor → 操作机
#    iptables: 仅允许特定出口 IP
#    DNS over HTTPS (加密且非默认)
```

## 操作机标准

```
OS: Tails 6.x / Whonix 17 / 专用 Qubes 模板
存储: LUKS 全盘加密 + VeraCrypt 容器
通信: ALL traffic over Tor
剪贴板: 禁用（防止跨 VM 泄露）
麦克风/摄像头: 物理禁用
时间: 保持在 UTC
日志: RAM only (tmpfs)
```

## C2 通信规范

### 心跳设计
```json
{
  "interval": "30-300s 随机",
  "jitter": "±30%",
  "protocol": "WebSocket > HTTPS > DNS",
  "payload": {
    "size": "64-256 bytes 随机",
    "padding": "随机填充至固定大小",
    "encoding": "base64( XOR(data, rolling_key) )"
  }
}
```

### 域名策略
- 使用 .com/.org/.net 等常见 TLD（不选 .xyz/.top 等可疑后缀）
- 域名购买: 匿名加密货币 + 隐私保护
- 内容: 伪装成个人博客/技术文档/API 文档
- 证书: Let's Encrypt (自动轮换)
- 每 30 天轮换域名（逐步迁移流量）

### 载荷安全
```
编译: -Os -fvisibility=hidden -s -Wl,-dead_strip
加壳: UPX / UPX 修改版 (修改特征头)
签名: 伪造或窃取的代码签名证书
交付: 分片 + 多源下载 + 校验和验证
自毁: 执行后内存清零 + 文件粉碎
```

## 反取证流程

### 内存
```bash
# 操作完成后清空内存中的敏感数据
# Python
import ctypes; libc = ctypes.CDLL("libc.so.6")
buf = ctypes.create_string_buffer(1024)
ctypes.memset(buf, 0, 1024)

# 避免留下 core dumps
ulimit -c 0
sysctl -w kernel.core_pattern=/dev/null
```

### 磁盘
```bash
# 安全删除文件
shred -z -n 3 -u target_file

# 删除目录
find /tmp/ops/ -type f -exec shred -z -n 1 -u {} \;
rm -rf /tmp/ops/

# 日志清理（需 root）
echo > /var/log/auth.log
echo > /var/log/syslog
journalctl --rotate && journalctl --vacuum-time=1s
```

### 网络痕迹
```bash
# 清理 ARP 缓存
ip neigh flush all

# 清理 DNS 缓存
systemd-resolve --flush-caches || true

# 清理 conntrack
conntrack -D -p tcp 2>/dev/null || true
```

## 每日操作检查表

### 操作前
- [ ] 操作机已更新（apt update && apt upgrade）
- [ ] VPN/Tor 连接正常（ip leak test）
- [ ] 目标最新情报检查（DNS/TLS 证书/Whois 变化）
- [ ] 测试 C2 通道（三路全部验证）
- [ ] 确认时间同步（chrony/NTP）

### 操作中
- [ ] 每次 shell 操作后清除历史（history -c）
- [ ] 不保存任何文件到持久存储
- [ ] 使用临时 VM 快照（操作完回滚）
- [ ] 禁用所有不必要的网络服务

### 操作后
- [ ] 回滚操作机快照
- [ ] 更换 VPN/Tor exit node
- [ ] 检查目标是否发现（搜索引擎/社交媒体/暗网）
- [ ] 更新操作日志（加密存储）
- [ ] 轮换所有凭证和域名

## 紧急自毁流程

```
1. 检测到告警（Terminus/监控触发）
   → 立即停止所有操作
   → 断开所有 C2 连接
   → 启动计时器（默认 60 秒）

2. 60 秒窗口内：
   ├── 清理所有开放连接
   ├── 内存中的 keys/buffers 全部 memset
   ├── 删除操作机上的目标相关文件
   ├── 回滚到干净快照
   └── 物理断开网络

3. 事后：
   ├── 24h 不触碰任何相关基础设施
   ├── 全面归因分析（如何被检测）
   └── 更新 OPSEC 措施
```
