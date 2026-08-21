#!/usr/bin/env python3
"""SRT/VTT 字幕 → 纯文本 transcript。用法: python3 srt_to_transcript.py <input.srt|vtt> [output.txt]"""
import re, sys, html

def clean(text):
    text = re.sub(r'^WEBVTT.*$', '', text, flags=re.M)
    text = re.sub(r'^\d{2}:\d{2}:\d{2}[.,]\d{3}.*$', '', text, flags=re.M)   # 时间戳行
    text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.M)                       # 序号行
    text = re.sub(r'<[^>]+>', '', text)                                       # HTML 标签
    text = html.unescape(text)
    out, prev = [], None
    for line in (l.strip() for l in text.splitlines()):
        if not line or line == prev:  # 连续重复行（滚动字幕去重）
            continue
        out.append(line); prev = line
    return '\n'.join(out)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('usage: srt_to_transcript.py <input.srt|vtt> [output.txt]')
    src = open(sys.argv[1], encoding='utf-8', errors='replace').read()
    result = clean(src)
    dst = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1] + '.txt'
    open(dst, 'w', encoding='utf-8').write(result)
    print(f'OK {dst} ({len(result)} chars)')
