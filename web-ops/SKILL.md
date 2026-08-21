---
name: web-ops
description: "Web 运维自动化实战经验库：Cloudflare Workers 部署（wrangler/KV/增量更新）、GitHub Actions CI/CD 排障纪律、Discourse 论坛自动化（CSRF/cron 阅读）。触发词：「CF Workers」「wrangler」「KV 绑定」「Workers 部署」「GitHub Actions」「workflow 排障」「deploy.yml」「Discourse」「自动阅读」「csrf」「_t cookie」。"
version: 1.0.0
---

# Web Ops 实战经验库

> 定位：非安全域的运维自动化经验。安全向的 WAF/CI 攻击见 kill-2 与 ios-reverse-engineering。

## Cloudflare Workers 部署

### Deploy with Workers 按钮
- `wrangler.toml` 的 `kv_namespaces` **禁止写 `id` 字段**（含 `id = ""`），否则按钮报错
- `[triggers]` 段不影响按钮解析

### 部署方式：完整 vs 增量
- **完整部署**（deploy.sh）：建 Worker + KV + Secret，首次用 CF API multipart
- **增量更新**：`curl -X PUT -F metadata= -F "worker.js=@"` 仅替换脚本，不动绑定/secrets
- 增量 PUT 的 metadata **必须含 `bindings` 数组**，否则 KV 绑定被清空（踩过）
- Content-Type 必须用 `application/javascript+module`，`application/javascript` 报 10021

## GitHub Actions 自动部署

- **验收 workflow 时必须读取完整构建日志排查错误**，禁止只读单个错误不停地缝缝补补（血泪纪律）
- `.github/workflows/deploy.yml`：推 `worker.js` 到 main → 增量 PUT 到 CF
- Secrets：`CF_API_TOKEN`, `CF_ACCOUNT_ID`, `KV_NS_ID`
- `${{ secrets.XXX }}` 不能在 job 级 `if:` 用（parse error），只能在 `run:` 用
- 公开仓库 runner 免费；账号有失败付款时 Actions 整体被封 → Billing 处理后重触发

## Discourse 自动阅读

- CSRF 优先从 cookie `_t` 提取——Discourse 登录 cookie 必有 `_t` 字段
- 无效话题跳过：页面 HTML 不包含 `t.title` 则为已删除，continue 跳过
- Cron 阅读（runNodelocBatch）：带队列 + 随机休息，不受 30s webhook 限制
- `ctx.waitUntil()` 壁钟上限 30s（HTTP webhook），cron/scheduled 不受此限
