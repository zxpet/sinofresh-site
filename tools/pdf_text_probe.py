#!/usr/bin/env python3
"""PDF 文本层实体审计（ground truth probe）。

回答一个具体问题：PDF 的**文本层**（浏览器选中复制走的那层）里，
究竟存放的是原始字符，还是被 HTML 实体转义过？

判定依据（三层独立证据，互不依赖）：
  1. 内容流字节：解码 Flate 流后，直接看文本算子 `[(...)] TJ` 里的码元。
     PDF 里 `&` 应为 `\\x00&`（UTF-16BE U+0026，一个字符）。
  2. ToUnicode CMap：决定"复制粘贴"取到哪个 Unicode。
     若存在"一个字形映射到多字符"的 bfchar，就是实体泄漏的真凶。
  3. 多引擎交叉：pypdf / pdfium(Chrome 引擎,≈浏览器复制) / pdfminer。

用法:
    python3 tools/pdf_text_probe.py <file.pdf> [more.pdf ...]
    python3 tools/pdf_text_probe.py --rows Flavor,Functions <file.pdf>
"""
import re
import sys

PLAIN = {
    '&': '&', 'lt': '<', 'gt': '>', 'quot': '"', 'apos': "'",
    'amp': '&', 'nbsp': ' ',
}


def decoded_streams(reader):
    out = []
    for i, page in enumerate(reader.pages):
        try:
            out.append((i + 1, page.get_contents().get_data()))
        except Exception as exc:  # noqa: BLE001
            out.append((i + 1, f'<stream error: {exc}>'.encode()))
    return out


def audit(path, row_keys):
    from pypdf import PdfReader

    print('=' * 78)
    print(f'# {path}')
    reader = PdfReader(path)
    raw = open(path, 'rb').read()
    print(f'  size={len(raw)}B  pages={len(reader.pages)}  '
          f'bytes contain b"&amp" ? {b"&amp" in raw}')

    # --- 证据 1：内容流字节 ---
    print('\n  [1] 内容流里的文本算子（真实写入的码元）')
    amp_seen = 0
    for pno, data in decoded_streams(reader):
        for m in re.finditer(rb'\[\((?:[^)]*)\)\]\s*TJ', data):
            chunk = m.group(0)
            if b'&' in chunk:
                amp_seen += 1
                # 只打印 & 前后各 6 个码元，避免刷屏
                idx = chunk.index(b'&')
                print(f'      p{pno}: ...{chunk[max(0, idx-14):idx+16]!r}...')
        if b'amp' in data:
            print(f'      p{pno}: !! 内容流出现字面 b"amp"（实体泄漏）')
    if not amp_seen:
        print('      （本文件内容流未出现 & 码元）')

    # --- 证据 2：ToUnicode CMap ---
    print('\n  [2] ToUnicode CMap（决定复制粘贴取到哪个字符）')
    for pno, page in enumerate(reader.pages):
        fonts = (page.get('/Resources') or {}).get('/Font')
        if not fonts:
            continue
        for fname, fref in fonts.items():
            font = fref.get_object()
            tu = font.get('/ToUnicode')
            if not tu:
                print(f'      p{pno+1} {fname}: 无 ToUnicode（Identity 编码）')
                continue
            cmap = tu.get_object().get_data().decode('latin-1')

            def tostr(hexs):
                try:
                    return bytes.fromhex(hexs).decode('utf-16-be')
                except Exception:  # noqa: BLE001
                    return '<bad>'

            pairs = []
            for blk in re.finditer(r'beginbfchar(.*?)endbfchar', cmap, re.S):
                pairs += re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk.group(1))
            multi = [(a, tostr(b)) for a, b in pairs if len(b) > 4]
            amp = [(a, tostr(b)) for a, b in pairs if tostr(b) == '&']
            ranges = re.findall(r'beginbfrange(.*?)endbfrange', cmap, re.S)
            rng = []
            for blk in ranges:
                rng += re.findall(r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', blk)
            identity = any(int(l, 16) == 0 and int(h, 16) == 0xFFFF and int(d, 16) == 0
                           for l, h, d in rng)
            print(f'      p{pno+1} {fname}: bfchar={len(pairs)} bfrange={len(rng)}'
                  f'{" (恒等 <0000><FFFF><0000>)" if identity else ""}')
            print(f'          多字符映射（实体泄漏真凶）: {multi if multi else "无"}')
            print(f'          U+0026(&) 的映射: {amp if amp else "见 bfrange 恒等区间"}')

    # --- 证据 3：多引擎交叉 ---
    print('\n  [3] 多引擎交叉提取（同一行，原样打印）')
    pypdf_txt = '\n'.join((pg.extract_text() or '') for pg in reader.pages)
    engines = {'pypdf': pypdf_txt}
    try:
        import pypdfium2 as pdfium
        engines['pdfium(Chrome)'] = ''.join(
            p.get_textpage().get_text_range() for p in pdfium.PdfDocument(path))
    except Exception as exc:  # noqa: BLE001
        engines['pdfium(Chrome)'] = f'<unavailable: {exc}>'
    try:
        from pdfminer.high_level import extract_text as ml_extract
        engines['pdfminer'] = ml_extract(path)
    except Exception as exc:  # noqa: BLE001
        engines['pdfminer'] = f'<unavailable: {exc}>'

    for key in row_keys:
        print(f'      「{key}」')
        for ename, txt in engines.items():
            rows = [l.strip() for l in txt.replace('\r', '\n').split('\n')
                    if l.strip().startswith(key)]
            print(f'        {ename:16s}: {rows}')

    # --- 判决 ---
    print('\n  [判决]')
    dirty = []
    for ename, txt in engines.items():
        if isinstance(txt, str) and ('&amp;' in txt or '&amp;amp;' in txt):
            dirty.append(ename)
    print(f'      文本层含 "&amp;" 的引擎: {dirty if dirty else "无 —— 文本层干净"}')
    # 注意：裸串 amp 会被单词 sample 假阳性，断言必须带分号
    bare = [l.strip() for l in pypdf_txt.split('\n') if 'amp' in l]
    if bare:
        print(f'      ⚠ 裸串 "amp" 命中 {len(bare)} 行，全部来自单词 sample，'
              f'不可作为判据: {bare[:2]}')


def main(argv):
    rows = ['Flavor', 'Functions']
    files = []
    i = 0
    while i < len(argv):
        if argv[i] == '--rows':
            rows = argv[i + 1].split(',')
            i += 2
        else:
            files.append(argv[i])
            i += 1
    if not files:
        print(__doc__)
        return 1
    for f in files:
        audit(f, rows)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
