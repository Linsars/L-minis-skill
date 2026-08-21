#!/usr/bin/env python3
"""人物 Skill 质量自检（Phase 4）。用法: python3 quality_check.py <SKILL.md路径>"""
import re, sys

def check(path):
    text = open(path, encoding='utf-8').read()
    fm = re.match(r'^---\n(.*?)\n---\n', text, re.S)
    items = []
    mm = len(re.findall(r'^###\s*M\d+', text, re.M)) or len(re.findall(r'心智模型', text)) // 3
    items.append(('心智模型数量≥3', mm >= 3, f'发现 {mm} 个'))
    items.append(('局限性/失效条件', bool(re.search(r'失效条件|局限性|[Ll]imitation', text)), '—'))
    items.append(('表达DNA', bool(re.search(r'表达\s*DNA|语言风格|语气特征', text)), '—'))
    items.append(('诚实边界', bool(re.search(r'诚实边界|不适用|不要用我|边界条件', text)), '—'))
    items.append(('内在张力', bool(re.search(r'内在张力|张力对|冲突点', text)), '—'))
    if fm:
        desc = fm.group(1)
        urls = len(re.findall(r'https?://', text))
        items.append(('调研来源(引用≥5)', urls >= 5, f'{urls} 个来源链接'))
    print(f'== {path} ==')
    fails = 0
    for name, ok, detail in items:
        mark = 'PASS' if ok else 'FAIL'
        if not ok: fails += 1
        print(f'  [{mark}] {name} {detail}')
    total = len(items) - fails
    print(f'  => {total}/{len(items)} 通过' + (' ✅' if fails == 0 else f' ⚠️ {fails} 项待补'))

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit('usage: quality_check.py <SKILL.md路径>')
    check(sys.argv[1])
