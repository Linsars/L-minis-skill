#!/usr/bin/env python3
"""Phase 1.5 调研摘要：扫描 references/research/*.md，统计来源与占比。
用法: python3 merge_research.py <skill目录>"""
import os, re, glob, sys

def main(skill_dir):
    rd = os.path.join(skill_dir, 'references', 'research')
    files = sorted(glob.glob(os.path.join(rd, '*.md')))
    if not files:
        sys.exit(f'未找到 {rd} 下的调研文件')
    total, first_hand = 0, 0
    findings = []
    for f in files:
        text = open(f, encoding='utf-8').read()
        urls = set(re.findall(r'https?://[^\s)」」]+', text))
        n = len(urls)
        # 一手来源标记：官方文档/论文/仓库/一手访谈
        fh = len([u for u in urls if re.search(r'docs?\.|arxiv|github\.com|developer\.|official|whitepaper', u, re.I)])
        total += n; first_hand += fh
        heads = re.findall(r'^#+\s*(关键发现|核心观点|Key [Ff]indings.*)$', text, re.M)
        if heads: findings.append((os.path.basename(f), len(heads)))
    ratio = first_hand / total * 100 if total else 0
    print('| 文件 | 来源数 |')
    print('|---|---|')
    for f in files:
        text = open(f, encoding='utf-8').read()
        n = len(set(re.findall(r'https?://[^\s)]+', text)))
        print(f'| {os.path.basename(f)} | {n} |')
    print(f'\n总来源: {total} | 一手占比: {ratio:.0f}% (Phase 1.5 检查点要求 ≥40%)')
    print('结论:', '✅ 达标' if ratio >= 40 and total >= 10 else '⚠️ 需补充一手来源或总量')

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit('usage: merge_research.py <skill目录>')
    main(sys.argv[1])
