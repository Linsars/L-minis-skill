# CF WAF / 反爬绕过策略参考

> 源自 [pydoll-cf-waf-bypasser-skills](https://github.com/Esonhugh/pydoll-cf-waf-bypasser-skills)
> 运行时映射到 `minis-browser-use` (Minis 内置浏览器自动化)

## Cloudflare 三道防线

| 防线 | 机制 | pydoll 绕过策略 | Minis 映射 |
|------|------|----------------|------------|
| JS Challenge | 前端 JS 计算 `cf_clearance` cookie | 浏览器自动执行 JS | browser_use 浏览器自动处理 |
| Managed Challenge | CAPTCHA / 人机验证 | 人机路径切换、Bezier 鼠标轨迹 | browser_use 模拟点击 + 等待 |
| Turnstile | 无感验证 Token | 浏览器指纹伪装 + 隐式交互 | 实测可用，偶现需手动过 |

## 隐蔽浏览器配置核心参数

pydoll 的反检测设置，对应到 minis-browser-use：

```python
# pydoll 原版 (参考用)
browser = Chromium(headless=False)
browser.set_viewport(width=1280, height=720)
browser.set_user_agent("Mozilla/5.0 ...")

# minis-browser-use 等效
minis-browser-use set_viewport --viewport_width 1280 --viewport_height 720
minis-browser-use set_user_agent --user_agent mobile_safari  # 或 desktop_safari
```

## 绕过流程

```
目标 URL
  │
  ├── browser_use navigate 加载
  │     └── 302 / cf challenge 页面 → 浏览器自动执行 JS → 无需处理
  │
  ├── 出现 CAPTCHA/Turnstile
  │     ├── browser_use screenshot 查看
  │     ├── 自动解析等待（wait_for_dom_stable 10s）
  │     └── 仍不行 → 截图 + 人工过（或切换 UA）
  │
  ├── 登录/验证后需要保持 session
  │     └── browser_use get_cookies → 导出 cookie
  │
  └── 爬取目标
        ├── scroll_and_collect 连续滚动
        └── get_text / get_readable 提取内容
```

## 常用策略模板

### 策略 A: 直接访问（CF JS Challenge 自动过）

```bash
minis-browser-use navigate --url "https://example.com"
# 等待 DOM 稳定 + JS 执行完毕
minis-browser-use wait_for_dom_stable --timeout 15
minis-browser-use get_text
```

### 策略 B: 带 Cookie 持久化

```bash
# 首次访问拿到 cookie
minis-browser-use navigate --url "https://example.com"
minis-browser-use wait_for_dom_stable --timeout 15
minis-browser-use get_cookies

# 后续请求复用 cookie (自动保持 session)
```

### 策略 C: 高难度 WAF (Cloudflare Under Attack)

```python
# pydoll 策略原型: 先访问首页等 JS 完成，再访问目标页
# Minis 等效:
minis-browser-use navigate --url "https://example.com"
minis-browser-use wait_for_dom_stable --timeout 30  # 等待 challenge 完成
minis-browser-use screenshot  # 确认是否过盾
# 如未过 → 截屏给用户人工处理
```

## 已知限制

| 场景 | 可行性 |
|------|--------|
| 普通 CF JS Challenge | ✅ 浏览器自动执行，无感 |
| Turnstile（Cloudflare 最新） | ✅ 大部分可过，偶发需要人工 |
| CAPTCHA v2/v3 | ⚠️ 需要人工干预 |
| CF WAF 自定义规则 | ✅ 取决于具体规则（IP/Header/Rate limit） |
| 需要真实设备指纹 | ⚠️ browser_use 用系统 Safari，指纹透明 |

## 参考

- [pydoll-cf-waf-bypasser-skills](https://github.com/Esonhugh/pydoll-cf-waf-bypasser-skills)
- kill-2 `references/scenarios.md` — CF Workers 隐蔽 C2 场景
