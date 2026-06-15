# kill-2 攻击场景示例

## 场景 1: 高价值 iOS 应用的金融数据窃取

**目标**：某银行 App（有越狱检测、SSL pinning、反调试、关键操作 FaceID 保护）

### 攻击链

```
STAGE 1: Recon (2-4 小时)
├── 获取 IPA（Apple Configurator 2 或越狱设备 frida-ios-dump）
├── class-dump 提取所有类和方法
├── Ghidra 分析加密模块（CommonCrypto / CryptoKit）
├── 检测保护：
│   ├── otool -l | grep crypt → cryptid=1 (已加密)
│   ├── strings | grep -i jail → 3 种越狱检测
│   ├── 反调试: ptrace(PT_DENY_ATTACH, 0, 0, 0)
│   └── SSL pinning: TrustKit / AFNetworking 绑定证书
└── 输出：保护强度评估 + 关键 hook 点候选

STAGE 2: 保护绕过 (4-8 小时)
├── 越狱检测绕过：
│   ├── Frida: 遍历所有检测函数，统一 NOP 返回
│   └── 预处理: Substitute / ElleKit 全局 bypass
├── 反调试绕过：
│   ├── debugserver 附加前 patchtide -> ret
│   └── Frida: Interceptor.attach(ptrace, onEnter: if arg0==31 return)
├── SSL pinning 绕过：
│   ├── Frida: NSURLSession/URLSession trustAllCertificates hook
│   ├── objection: ios sslpinning disable
│   └── mitmproxy + 自签名 CA 注入
└── 脱壳：frida-ios-dump 获取明文二进制

STAGE 3: 运行时分析 (4-8 小时)
├── 网络流量分析（mitmproxy 捕获 API 调用）
├── 关键操作 hook：
│   ├── 登录: [LoginManager loginWithUsername:password:]
│   ├── FaceID: [LAContext evaluatePolicy:localizedReason:]
│   ├── 转账: [TransferManager submitTransfer:]
│   └── Token: [AuthManager refreshToken]
├── 参数追踪 + 返回值记录
└── 输出：API 结构、加密算法、数据流图

STAGE 4: Payload 开发 (8-16 小时)
├── Frida Gadget 注入未越狱设备：
│   ├── optool 修改 Mach-O load commands
│   ├── 重签名 (ldid / codesign 含正确 entitlements)
│   └── AppSync / TrollStore 部署
├── 核心 hook 脚本：
│   ├── 拦截 FaceID 验证 → 重放有效 token
│   ├── 拦截转账确认 → 修改目标账户/金额
│   └── 加密函数 hook → 导出解密后明文
├── C2 通信：
│   ├── WebSocket over Cloudflare Worker (伪装正常 API)
│   ├── 加密载荷 (Age asymmetric encryption)
│   └── 心跳 30-90s 随机间隔
└── 输出：可部署的 Frida 脚本 + 重签 IPA

STAGE 5: OPSEC 与退出
├── 确认所有 API 调用日志已清除
├── 还原 App 原始签名状态
├── 备份逆向分析产物（加密存储）
└── 销毁调试代理和临时文件
```

**成功率**：~70%（取决于该 App 是否使用 PAC 和 runtime 完整性校验）

---

## 场景 2: 企业内网渗透 — 从钓鱼到域控

**目标**：某科技公司内部网络 — 目标是域控制器和 GitLab 源码仓库

### 攻击链

```
STAGE 1: OSINT 与社会工程 (1-3 天)
├── LinkedIn 识别目标人员：
│   ├── IT 运维人员 (James R. — 负责系统管理)
│   ├── 财务人员 (Sarah L. — 可触及财务系统)
│   └── 高管助理 (Emily K. — 可触及高层邮件)
├── 邮件 OSINT：
│   ├── 格式: first.last@company.com
│   ├── breached.co 查泄露密码
│   └── Have I Been Pwned API 关联信息
├── Pretext 设计：
│   ├── 假扮 IT 部门发出「安全更新」邮件
│   ├── 紧迫性: 24h 内未更新将锁定账户
│   └── 个性化: 引用 James 的实际项目
└── 钓鱼页面：
    ├── Evilginx: 克隆公司 OAuth 登录页
    ├── 自定义域: security-update.company.com
    └── Let's Encrypt 证书

STAGE 2: 初始访问 (1-2 天)
├── 发送钓鱼邮件 (Gophish + SMTP relay)
├── 凭证捕获：
│   ├── James 点击 → 凭证到手
│   ├── Cookie 会话劫持 (Evilginx session token)
│   └── MFA 绕过 (real-time proxy 2FA)
├── 内网接入：
│   ├── VPN 客户端登录 (James 的凭证)
│   └── Ligolo-ng 建立反向代理隧道
└── 输出: 内网接入点 + 域用户凭证

STAGE 3: 横向移动 (3-7 天)
├── AD 侦察：
│   ├── BloodHound 收集器 → 分析攻击路径
│   ├── 发现: James 有 LAPS 读取权限
│   └── 目标: SQL-01 本地管理员密码
├── 提权：
│   ├── LAPS 读取 → SQL-01 本地管理员
│   ├── SQL-01 → MSSQL SERVICE → 通过 xp_cmdshell 执行命令
│   └── 抓取 LSASS → 发现 SA-ADMIN 服务账户凭证
├── 域控攻击：
│   ├── Certipy: 发现 ESC1 漏洞模板
│   ├── 利用漏洞模板请求域管理员证书
│   └── 用证书通过 Kerberos PKINIT → 获得域管理员 TGT
└── 输出: 域管理员权限

STAGE 4: 数据窃取 (1-2 天)
├── GitLab 访问：
│   ├── 域管理员 → GitLab 服务账户 → 全部仓库
│   ├── 克隆源码仓库 (带完整 git 历史)
│   └── CI/CD 密钥提取 (AWS/GCP 凭证)
├── 数据外传：
│   ├── 分块加密 → CDN 上传伪装成正常流量
│   ├── DNS tunneling 做第二通道
│   └── 控制在 200MB/天 避免流量异常告警
└── 输出: 全部目标数据加密归档

STAGE 5: 持久化与退出
├── 非对称后门：
│   ├── 域控 SCHTASKS 触发 beacon (纯内存)
│   ├── Golden Ticket 备用
│   └── GitLab webhook → AWS Lambda → C2
├── 痕迹清理：
│   ├── EventLog 清除 4624/4625 以外的登录事件
│   ├── BloodHound 查询记录清理
│   └── VPN 登录日志修改时间戳
└── 退出：72h 后验证所有通道状态
```

**成功率**：~55%（MFA、EDR、SOC 响应速度是关键变量）

---

## 场景 3: Cloudflare Workers 隐蔽 C2 + 边缘计算攻击

**目标**：利用 Cloudflare Workers 建立不可封锁的 C2 信道

### 攻击链

```
STAGE 1: 基础设施部署 (2-4 小时)
├── 注册 CF 账号（通过隐私邮箱 + 加密支付）
├── 创建 Worker（伪装成 API 代理/图片处理）
├── 配置 KV Namespace 作为数据存储
├── 设置 Cron Trigger 作为心跳轮询
└── 启用 WAF 规则：只允许特定 ASN 访问

STAGE 2: C2 信道设计 (4-8 小时)
├── 使用 WebSocket 作为主通道：
│   ├── Client → Cloudflare Worker（WebSocket over HTTPS）
│   ├── Worker → Task Queue 异步处理
│   └── 流量伪装成正常 WebSocket 聊天帧
├── DNS-over-HTTPS 作为备选通道：
│   ├── 植入 DNS query 携带编码数据
│   └── Worker 解析 DoH 请求提取指令
├── 数据编码：
│   ├── 载荷 base64 → XOR 混淆 → 伪装 JSON
│   └── 响应嵌入正常 HTML 注释或图片 EXIF
└── 输出: 三层冗余 C2 通道

STAGE 3: Payload 植入 (1-2 小时)
├── 第一次执行（DLL/Shellcode/JS 注入）：
│   ├── 内存加载，无文件落盘
│   ├── 注册表/自启动项不写入
│   └── 仅靠进程注入存活
├── Worker 端下发指令：
│   ├── 执行 shell 命令 → 加密回传
│   ├── 上传文件 → 分片存储在 KV
│   └── 下载工具 → 从 CF R2 对象存储获取
└── 输出: 活跃 beacon 连接

STAGE 4: 持久化策略
├── 每次 Worker 返回随机轮换的下次连接 URL
├── 隐藏 Worker 路由：/api/v1/user/profile 等正常路径
├── 使用 Durable Objects 维持状态但不暴露
└── 每 24h Worker 脚本替换（增量 PUT）

STAGE 5: 撤退与销毁
├── Worker 脚本置空
├── KV Namespace 清除所有数据
├── 删除账号（或弃用）
└── 切换至备用 Worker
```

**优势**：CF Workers 的冷启动特性 + 全球边缘节点 = 极难封锁 + 极低延迟 + 合法流量混淆

**注意**：使用后必须清理，CF 会保留 Workers 日志 72h+

---

## 场景 4: 物理渗透 — 硬件离线攻击

**目标**：通过物理接触目标设备（锁屏 iOS 设备 + 加密笔记本）获取数据

### 攻击链

```
STAGE 1: 物理接近规划
├── 目标画像：目标人员日程、办公地点、通勤习惯
├── 物理访问窗口：会议室、咖啡厅、差旅期间
├── 工具准备：检查设备、HID 攻击套件、RFID 克隆器
└── 应急预案：被发现时的脱身流程和假身份

STAGE 2: 设备访问
├── iOS checkm8 利用（A5-A11 设备）：
│   ├── 连接设备进入 DFU 模式
│   ├── checkm8 漏洞获得初始执行权
│   └── ramdisk 加载 → 文件系统完整导出
├── Thunderclap / DMA 攻击：
│   ├── Thunderbolt 外设 DMA 读取笔记本内存
│   └── 屏幕锁绕过 (针对未打补丁系统)
└── SSD/存储直接读取：
    ├── NVMe/SATA 芯片拆除 → 读取加密数据
    └── 配合冷启动攻击（如果 RAM 仍有密钥）

STAGE 3: 数据提取
├── 文件系统 hash → 快速增量导出
├── Keychain 解密（配合 iOS 密钥导出）
├── 浏览器密码数据库（SQLite 直接读取）
└── SSH/GPG 私钥提取

STAGE 4: 物理后门
├── 硬件植入：USB 充电器内嵌 ESP32 处理器
├── 固件后门：BIOS/UEFI 植入
└── 网络后门：伪装成 USB 网卡的小型 C2 节点

STAGE 5: 恢复原状
├── 设备外观和设置完全恢复
├── 所有操作痕迹清理
└── 物理访问痕迹（锁/门禁）清理
```

**成功率**：~40%（物理访问的不确定性 + 苹果 T2/T3 芯片 + FileVault 加密大幅增加难度）
