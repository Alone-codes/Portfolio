import re, zlib, sys

data = open('Resume.pdf', 'rb').read()

objs = {}
streams = {}
for m in re.finditer(rb'(\d+) 0 obj', data):
    num = int(m.group(1))
    dict_start = m.end()
    endobj = data.find(b'endobj', dict_start)
    dict_end = data.find(b'stream', dict_start)
    if dict_end != -1 and dict_end < endobj:
        objs[num] = data[dict_start:dict_end]
        sstart = dict_end + 6
        if data[sstart:sstart+2] == b'\r\n': sstart += 2
        elif data[sstart:sstart+1] in (b'\n', b'\r'): sstart += 1
        send = data.find(b'endstream', sstart)
        streams[num] = data[sstart:send]
    else:
        objs[num] = data[dict_start:endobj]

def get_stream(num):
    raw = streams.get(num)
    if raw is None: return None
    try: return zlib.decompress(raw)
    except Exception: return raw

# find page objects and print their dicts
for num, body in sorted(objs.items()):
    if re.search(rb'/Type\s*/Page\b', body):
        print('PAGE', num, 'DICT:', body[:500])
        print('---')

# print a content stream Tf ops
for num, body in sorted(objs.items()):
    if re.search(rb'/Type\s*/Page\b', body):
        cont = re.search(rb'/Contents\s+(\d+) 0 R', body)
        if cont:
            cs = get_stream(int(cont.group(1)))
            tfs = re.findall(rb'/[A-Za-z0-9+#_.\-]+\s+[\d.]+\s+Tf', cs)[:10]
            print('PAGE', num, 'Tf ops sample:', tfs[:8])
        break

# what do resources look like for that page?
