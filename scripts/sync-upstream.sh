#!/bin/sh
# sync-upstream.sh — yaklang/hack-skills 上游更新检查（report-only，不自动覆盖本地 Darwin wrapper）
# 基线: UPSTREAM_BASE 记录上次同步时的上游 HEAD
# 用法: sh sync-upstream.sh   （输出上游新增/修改报告）
set -e
UPSTREAM_BASE="记录于 scripts/upstream-baseline.txt"
BASE=$(cat "$(dirname "$0")/upstream-baseline.txt" 2>/dev/null || echo "")
[ -z "$BASE" ] && { echo "无基线，先跑: git ls-remote https://github.com/yaklang/hack-skills HEAD"; exit 1; }
WORK=/tmp/hack-skills-sync
rm -rf "$WORK"
git clone --quiet --filter=blob:none https://github.com/yaklang/hack-skills "$WORK"
cd "$WORK"
NEW=$(git rev-parse HEAD)
echo "上游基线: $BASE"
echo "上游当前: $NEW"
echo "--- 变更的 skill 文件 ---"
git diff --stat "$BASE" HEAD -- '*SKILL.md' | tail -30
echo ""
echo "--- 吸收原则 ---"
echo "1. 只吸收 payload 表/技术内容更新，不覆盖本地 DARWIN WRAPPER 段落"
echo "2. 逐文件人工确认后 file_edit 合入，标注 <!-- synced $NEW -->"
echo "3. 失效条目同步删除（回流纪律）"
