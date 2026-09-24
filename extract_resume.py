import re, zlib, sys

data = open('Resume.pdf', 'rb').read()

# ---- Parse objects using absolute positions (robust for streams) ----
objs = {}      # num -> dict body bytes
streams = {}   # num -> raw stream bytes
for m in re.finditer(rb'(\d+) 0 obj', data):
    num = int(m.group(1))
    dict_start = m.end()
    dict_end = data.find(b'stream', dict_start)
    endobj = data.find(b'endobj', dict_start)
    # find whether a stream follows before endobj
    seg = data[dict_start:dict_start + (dict_end - dict_start if dict_end != -1 and dict_end < endobj else 0)]
    if dict_end != -1 and dict_end < endobj:
        dbody = data[dict_start:dict_end]
        sm = re.match(rb'\s*\r?\n', data[dict_end + len(b'stream'):])
        sstart = dict_end + len(b'stream')
        if data[sstart:sstart + 2] == b'\r\n':
            sstart += 2
        elif data[sstart:sstart + 1] in (b'\n', b'\r'):
            sstart += 1
        send = data.find(b'endstream', sstart)
        streams[num] = data[sstart:send]
        objs[num] = dbody
    else:
        objs[num] = data[dict_start:endobj]

def get_stream(num):
    raw = streams.get(num)
    if raw is None:
        return None
    try:
        return zlib.decompress(raw)
    except Exception:
        try:
            return zlib.decompress(raw.rstrip(b'\r\n'))
        except Exception:
            return raw

def ref_num(ref):
    m = re.match(rb'\s*(\d+)', ref)
    return int(m.group(1)) if m else None

# ---- ToUnicode cmaps keyed by FONT OBJECT NUMBER ----
cmaps = {}
for num, body in objs.items():
    m = re.search(rb'/ToUnicode\s+(\d+) 0 R', body)
    if not m:
        continue
    cm = get_stream(int(m.group(1)))
    if not cm:
        continue
    cmap = {}
    for bm in re.finditer(rb'beginbfchar(.*?)endbfchar', cm, re.S):
        for em in re.finditer(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', bm.group(1)):
            cmap[int(em.group(1), 16)] = bytes.fromhex(em.group(2).decode()).decode('utf-16-be', 'replace')
    for br in re.finditer(rb'beginbfrange(.*?)endbfrange', cm, re.S):
        body_r = br.group(1)
        for em in re.finditer(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>', body_r):
            lo, hi, d0 = int(em.group(1), 16), int(em.group(2), 16), int(em.group(3), 16)
            for c in range(lo, hi + 1):
                cmap[c] = chr(d0 + (c - lo))
        for em in re.finditer(rb'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]', body_r, re.S):
            lo, hi = int(em.group(1), 16), int(em.group(2), 16)
            dsts = re.findall(rb'<([0-9A-Fa-f]+)>', em.group(3))
            for i, c in enumerate(range(lo, hi + 1)):
                if i < len(dsts):
                    cmap[c] = bytes.fromhex(dsts[i].decode()).decode('utf-16-be', 'replace')
    cmaps[num] = cmap

LIT_MAP = {0x6E: '\n', 0x72: '\r', 0x74: '\t', 0x62: '\b', 0x66: '\f',
           0x28: '(', 0x29: ')', 0x5C: '\\'}
BSL = 0x5C

def decode_string(raw, cmap):
    two = any(k >= 256 for k in cmap.keys()) if cmap else False
    out = []
    i, n = 0, len(raw)
    while i < n:
        if raw[i] == BSL:
            if i + 1 >= n:
                break
            nxt = raw[i + 1]
            if nxt in LIT_MAP:
                out.append(LIT_MAP[nxt]); i += 2; continue
            if 0x30 <= nxt <= 0x37:
                j = i + 1; o = ''
                while j < n and len(o) < 3 and 0x30 <= raw[j] <= 0x37:
                    o += chr(raw[j]); j += 1
                out.append(chr(int(o, 8) & 0xFF)); i = j; continue
            out.append(chr(nxt)); i += 2; continue
        if two and i + 1 < n:
            out.append(cmap.get((raw[i] << 8) | raw[i + 1], '')); i += 2
        else:
            out.append(cmap.get(raw[i], chr(raw[i]) if raw[i] < 128 else '')); i += 1
    return ''.join(out)

TOK = re.compile(rb'\((?:[^()\\]|\\.|\((?:[^()\\]|\\.)*\))*\)|<[0-9A-Fa-f\s]*>|/[A-Za-z0-9+#_.\-]+\s+[\d.]+\s+Tf|T\*|TD|Td|ET|TJ|Tj')

def extract_text(content, alias_map):
    lines = []
    cur = []
    cur_font = None
    for m in TOK.finditer(content):
        tok = m.group(0)
        if tok.endswith(b'Tf'):
            am = re.match(rb'/([A-Za-z0-9+#_.\-]+)', tok[1:])
            if am:
                alias = am.group(1).decode('latin-1')
                cur_font = alias_map.get(alias)
        elif tok in (b'T*', b'TD', b'Td', b'ET'):
            if cur:
                lines.append(''.join(cur)); cur = []
        elif tok.startswith(b'('):
            inner = tok[1:-1]
            cmap = cmaps.get(cur_font, {})
            cur.append(decode_string(inner, cmap) if cmap else inner.decode('latin-1', 'replace'))
        elif tok.startswith(b'<'):
            hx = re.sub(rb'\s', b'', tok[1:-1])
            if not hx:
                continue
            raw = bytes.fromhex(hx.decode())
            cmap = cmaps.get(cur_font, {})
            cur.append(decode_string(raw, cmap) if cmap else raw.decode('latin-1', 'replace'))
    if cur:
        lines.append(''.join(cur))
    return lines

out_lines = []
for num, body in sorted(objs.items()):
    if not re.search(rb'/Type\s*/Page\b', body):
        continue
    # resolve resources: page-level or parent
    res_m = re.search(rb'/Resources\s+(\d+) 0 R', body)
    res_body = objs.get(ref_num(res_m.group(1))) if res_m else None
    if res_body is None:
        res_inline = re.search(rb'/Resources\s*<<(.*?)>>\s*/MediaBox|/Resources\s*<<(.*?)>>', body, re.S)
        res_body = (res_inline.group(1) or res_inline.group(2)) if res_inline else None
    alias_map = {}
    if res_body:
        fm = re.search(rb'/Font\s*<<(.*?)>>', res_body, re.S)
        if fm:
            for em in re.finditer(rb'/([A-Za-z0-9+#_.\-]+)\s+(\d+) 0 R', fm.group(1)):
                alias_map[em.group(1).decode('latin-1')] = int(em.group(2))
    cm_arr = re.search(rb'/Contents\s*\[(.*?)\]', body, re.S)
    if cm_arr:
        for r in re.finditer(rb'(\d+) 0 R', cm_arr.group(1)):
            s = get_stream(int(r.group(1)))
            if s:
                content += s + b'\n'
    else:
        cont = re.search(rb'/Contents\s+(\d+) 0 R', body, re.S)
        if cont:
            s = get_stream(int(cont.group(1)))
            if s:
                content = s
    if content:
        out_lines.extend(extract_text(content, alias_map))

sys.stdout.write('\n'.join(out_lines)[:20000])
