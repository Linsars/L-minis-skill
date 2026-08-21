# Runtime 可移植性说明（PORTABILITY）

本 skill 库原生运行在 Minis (iOS iSH/Alpine) 环境，**现已基本 runtime-neutral**。

## 路径约定

- 命令中的 `$SKILLS_ROOT` = 本仓库根目录（Minis 默认 `/var/minis/skills`；其他 runtime export 为 clone 目录即可）
- 仅 `memory-management` 依赖 Minis 记忆系统（memory_get/memory_write 工具），其他 runtime 无对应系统时跳过该 skill

## 绑定清单（仅剩）

| 文件 | 绑定 | 说明 |
|------|------|------|
| `memory-management/SKILL.md` | Minis 记忆工具 + `/var/minis/memory/` | skill 本体就是 Minis 记忆系统维护，属设计内绑定 |
| `ios-reverse-engineering/SKILL.md` | artifact 下载目录提示 | 已标注"Minis: /var/minis/workspace，其他自定"，非硬依赖 |

## 设计上已中立的

- 其余 22 个 SKILL.md 零平台绑定（payload 表、Workflow、Failure Modes 全部通用）
- 所有 workflow YAML 用 `gh` CLI + 标准 actions，任何有 GitHub 的环境可跑
- python/shell scripts 均为零依赖标准库
- kill-2 的 `local/github-macos/device-only` 三级分流概念通用
