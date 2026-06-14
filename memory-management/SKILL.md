---
name: memory-management
description: >
  Maintain agent memory in Minis environment. Use when memory files grow
  large, duplicates accumulate, or patterns need distilling into GLOBAL.md.
  Triggers on: "记忆维护", "整理记忆", "清理记忆", "提炼知识", "检查冲突",
  "memory maintenance", "conflict check". Proactively suggest when daily logs
  exceed 50 lines or GLOBAL.md approaches 60 lines.
---

# Memory Management (Minis Native)

## Architecture

Minis 记忆系统分三层，各有用途：

```
GLOBAL.md (≤60行，每轮自动注入)
  └── 持久知识：偏好、约定、项目经验

memory/2026-06-15.md (日记，自动注入昨天+今天)
  └── 会话日志：每轮 memory_write 追加

memory_get (搜索工具，跨全部文件)
  └── 按关键词模糊搜索 GLOBAL.md + 所有日记
```

## When to Use

| 触发条件 | 操作 |
|----------|------|
| GLOBAL.md > 55 行 | 审查冗余，合并相似条目 |
| 日记文件堆积 > 10 个 | 提炼跨会话模式入 GLOBAL.md |
| 同一问题出现 > 2 次 | 蒸馏为 GLOBAL.md 可复用原则 |
| 用户说"记得这个吗"但你没查到 | memory_get 未命中 → 写日记 |
| GLOBAL.md 与用户新输入矛盾 | 检查冲突，更新或澄清 |

## Procedure

执行 memory 管理时按以下步骤：

1. **🔴 评估范围** — 用户指定范围？还是全面审查 GLOBAL.md + 日记？
2. **扫描** — `memory_get` 检索相关主题；`file_read GLOBAL.md` 看全文
3. **诊断** — 冗余、过时、矛盾、遗漏、噪音？
4. **🔴 确认修改** — 给用户展示要删/改/合并的内容，禁止单方面删减
5. **执行** — `file_edit` 精确修改，`memory_write` 追加新记忆
6. **验证** — 确认修改后文件仍在限制内

## 异常与边界条件

| 触发条件 | 一线修复 | 兜底 |
|----------|----------|------|
| GLOBAL.md > 60 行 | 合并同类条目，删过时内容 | 拆分类子主题（但 Minis 不推荐） |
| memory_get 返回空 | 用更短/更多的关键词重试 | 手动 grep /var/minis/memory/ |
| 用户说不该删某条 | git revert GLOBAL.md 修改 | 恢复后标注"保留"并跳过 |
| 时间线混乱 | 按日期排序日记文件 | 合并重复日期条目 |

## 反例

- **不要手动搬日记** — Minis 自动管理 `memory/YYYY-MM-DD.md`，搬了会破坏自动注入
- **不要删昨天/今天的日记** — 系统每轮注入两天最近日志，删了会导致 boot 时空
- **不要用 P0/P1/P2** — Minis 没有优先级系统，平铺即可
- **不要建 memory/projects/** — Minis 没有内存搜索的 domain 概念，知识统一放在 GLOBAL.md
- **不要跟 memory_write 打架** — 自动追加是 Minis 设计，不要试图手工覆盖
