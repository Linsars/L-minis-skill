# Runtime 可移植性说明（PORTABILITY）

本 skill 库原生运行在 Minis (iOS iSH/Alpine) 环境。其他 skills-compatible runtime
(Claude Code / Codex / Cursor / OpenClaw 等) 装载时，只需适配以下 3 个文件的 Minis 专属绑定。

## 绑定清单

| 文件 | Minis 专属引用 | 通用替代 |
|------|---------------|---------|
| `kill-2/SKILL.md` | `/var/minis/skills/ios-reverse-engineering/scripts/ios-quick-scan.py` 绝对路径 | 改为相对路径 `../ios-reverse-engineering/scripts/ios-quick-scan.py`，或按 `$SKILLS_ROOT` 环境变量解析 |
| `ios-reverse-engineering/SKILL.md` | `/var/minis/workspace/` artifact 下载目录 | 换成本地工作目录；`minis 内操作` 一节换成对应 runtime 的 gh CLI 等价流程（命令本身通用） |
| `memory-management/SKILL.md` | `memory_get` / `memory_write` / `file_edit` 工具名、`/var/minis/memory/` 路径 | 映射到目标 runtime 的记忆系统；无记忆系统的 runtime 此 skill 不适用，跳过 |

## 设计上已中立的

- 其余 20 个 SKILL.md 零平台绑定（payload 表、Workflow、Failure Modes 全部通用）
- 所有 workflow YAML 用 `gh` CLI + 标准 actions，任何有 GitHub 的环境可跑
- python/shell scripts 均为零依赖标准库

## 已知限制

- `apple-*` CLI（healthkit/homekit 等）是 iOS 原生框架桥，无替代——但当前没有任何安全 skill 依赖它们
- kill-2 的 `local/github-macos/device-only` 三级分流概念通用，具体工具表在别的 runtime 同样成立
