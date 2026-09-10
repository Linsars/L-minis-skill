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

### CI/CD 排障纪律（2026-08-26 MinisFix v2.6.38→42 血泪实锤）

#### 1. push 事件静默丢失（最高频陷阱）
- **机制**：对同一 ref 连续快速 push，GitHub Actions 只处理第一个 push 事件，后续事件**静默丢弃**（git push 成功、远程 SHA 已更新，但没有任何 run）
- **症状**：`git push` 成功后 `gh run list` 无新 run；commit 的 check-runs 为空（`total_count=0`）
- **已验证**：v2.6.40/41/42 连续三次 push 全部丢事件；v2.6.41 的事件延迟 ~10 分钟后以**旧 SHA** 补跑（反而误导排障——补跑的 failure 用的是旧代码）

#### 2. 正确触发/兜底方式（结论）
- push 后 30~45s 用**原始 API** 确认 run 出现，看不到就**立即 `gh workflow run build.yml --ref main` dispatch 兜底**
- **dispatch 每次都能立即 in_progress（可靠），push 事件不可靠**——连续迭代时直接声明「push 后必 dispatch」
- dispatch 可能产生僵尸 run（API 显示 queued 但 cancel 拒绝 409「has not been queued yet」）——无法取消，等系统回收，不影响后续新 dispatch

#### 3. 诊断命令链（都是本次验证有效的）
```bash
# ① commit 有没有 run（0=事件丢）
gh api repos/OWNER/REPO/commits/<sha>/check-runs --jq '.total_count'
# ② 全部 run 的事件类型+sha（区分 push/dispatch、看清是哪个代码跑的）
gh api "repos/OWNER/REPO/actions/runs?per_page=5" --jq '.workflow_runs[] | "\(.id) \(.event) \(.status)/\(.conclusion) \(.head_sha[0:7])"'
# ③ 远程 SHA 是否真的更新（排除 push 假成功）
git fetch origin -q && git rev-parse --short origin/main
```
- **gh CLI 有状态缓存**：`gh run list` 显示 queued、`gh run cancel` 却报 completed——永远用 `gh api` 原始接口下结论
- run view 失败日志要看 `Undefined symbols` 的**完整列表**（一行一个符号，错误会互相淹没：2.6.39 一次 failure 里其实藏了 4 个错，只修 3 个）

#### 4. 「排队」vs「事件丢失」判据
- 曾误判「runner 限流排队 15min+」，实际是 push 事件丢+dispatch 僵尸——**dispatch 立即 in_progress 证明 runner 完全可用**
- 判据：run 存在且 queued（无 job）= 真排队；**run 根本不存在 = 事件丢**
- 不要只读 `gh run list` 的 status 字段就对外下「排队」结论

#### 5. 删符号前的全量引用检查
- 删除/改名 C 函数前：`find . -name "*.m" -o -name "*.h" | xargs grep -ln "<符号>"`，链接错误（undefined symbol）编译期不报
- 保留兼容别名最省事：`void mfShowMethodTracePage(void) { mfShowObjCHookPage(); }`
- 已删函数的残留调用链：MFClassDump 左滑 → `mfShowMethodTracePage()`（C 函数）→ 指向 ObjC 规则页；`mfTraceSetPrefill` 同类（声明+调用都在、实现被删 = 隐藏 undefined symbol）

## Discourse 自动阅读

- CSRF 优先从 cookie `_t` 提取——Discourse 登录 cookie 必有 `_t` 字段
- 无效话题跳过：页面 HTML 不包含 `t.title` 则为已删除，continue 跳过
- Cron 阅读（runNodelocBatch）：带队列 + 随机休息，不受 30s webhook 限制
- `ctx.waitUntil()` 壁钟上限 30s（HTTP webhook），cron/scheduled 不受此限
