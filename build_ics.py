#!/usr/bin/env python3
"""Baut lernplan.ics aus dem Markdown-Export des Tabs „Tag für Tag“.
Aufruf: python3 build_ics.py tagfuertag.md [daten.json] [lernplan.ics]"""
import sys, re, json, hashlib, datetime as dt

md_path = sys.argv[1]
daten_path = sys.argv[2] if len(sys.argv) > 2 else 'daten.json'
out_path = sys.argv[3] if len(sys.argv) > 3 else 'lernplan.ics'
D = json.load(open(daten_path, encoding='utf-8'))
FR, VER, PREP = D['fragen'], D['veranstaltungen'], D['praepkurs']
LAB = {'A': 'Ana', 'B': 'Bio', 'P': 'Phys'}
AB = {v: k for k, v in LAB.items()}
STAMP = '20261027T000000Z'

def esc(s): return s.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')
def fold(line):
    out, cur = [], b''
    for ch in line:
        e = ch.encode('utf-8')
        if len(cur) + len(e) > 73: out.append(cur.decode()); cur = b' ' + e
        else: cur += e
    out.append(cur.decode()); return '\r\n'.join(out)

def refs(t):
    out = []
    for m in re.finditer(r'(Ana|Bio|Phys) ((?:\d{1,2}\.\d{1,2}(?:, )?)+)', t):
        for n in re.findall(r'\d{1,2}\.\d{1,2}', m.group(2)):
            k = AB[m.group(1)] + n
            if k not in out: out.append(k)
    return out
def qname(k): return f"{LAB[k[0]]} {k[1:]} {FR.get(k, '')}".strip()

def week_days(d):
    mon = d - dt.timedelta(d.weekday())
    return [(mon + dt.timedelta(i)) for i in range(d.weekday() + 1)], mon

REVIEW = ('MSC-Woche abschließen', 'MSC „Auch berührt“', 'MSC: alle Fragen')
def enrich(d, t, desc):
    add = lambda s: (desc + '\n\n' if desc else '') + s
    rs = refs(t)
    if rs and t.startswith(REVIEW):
        return t, add('Fragen:\n' + '\n'.join(qname(k) for k in rs))
    if rs:
        head, sep, body = t.partition(': ')
        if not sep: head, body = '', t
        parts, tparts, tags = body.split(' · '), [], {}
        for p in parts:
            tag = ''
            for pre in ('Wdh. ', 'Nachholen '):
                if p.startswith(pre): tag, p = pre.strip(), p[len(pre):]
            ks = refs(p)
            for k in ks: tags[k] = tag
            tparts.append((tag + ': ' if tag else '') + ', '.join(qname(k) for k in ks))
        if len(rs) <= 3: t = (head + ': ' if head else '') + ' · '.join(tparts)
        lines = [(f'[{tags[k]}] ' if tags.get(k) else '') + qname(k) for k in rs]
        return t, add('Fragen (Wortlaut in deiner MSC-Ausarbeitung):\n' + '\n'.join(lines))
    if t.startswith('Vorlesung lesen'):
        v = VER.get(d.isoformat(), [])
        if v: desc = add('Heute:\n' + '\n'.join(v))
        else:
            days, _ = week_days(d); w = [x for dd in days for x in VER.get(dd.isoformat(), [])]
            if w: desc = add('Heute keine Vorlesung. Diese Woche bisher, nimm die, die du noch nicht gelesen hast:\n' + '\n'.join(w))
    if t.startswith(('Anatomie-Liste', 'Anatomie:')):
        _, mon = week_days(d); p = PREP.get(mon.isoformat(), '')
        desc = add('Strukturen aus deiner Wochenliste: Ursprung, Ansatz, Innervation erst aus dem Kopf, dann mit Prometheus abgleichen.' + ('\nPräpkurs diese Woche: ' + p if p else ''))
    return t, desc

L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Lernplan 3. Semester//DE', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
     'X-WR-CALNAME:Lernplan 3. Semester', 'X-WR-TIMEZONE:Europe/Berlin',
     'REFRESH-INTERVAL;VALUE=DURATION:PT1H', 'X-PUBLISHED-TTL:PT1H',
     'BEGIN:VTIMEZONE', 'TZID:Europe/Berlin',
     'BEGIN:DAYLIGHT', 'TZOFFSETFROM:+0100', 'TZOFFSETTO:+0200', 'TZNAME:CEST', 'DTSTART:19700329T020000', 'RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU', 'END:DAYLIGHT',
     'BEGIN:STANDARD', 'TZOFFSETFROM:+0200', 'TZOFFSETTO:+0100', 'TZNAME:CET', 'DTSTART:19701025T030000', 'RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU', 'END:STANDARD',
     'END:VTIMEZONE']
n = 0
def ev(d, start, end, title, desc='', allday=False):
    global n
    uid = hashlib.md5(f'{d}|{start}|{title}'.encode()).hexdigest() + '@lernplan-3-semester'
    L.extend(['BEGIN:VEVENT', 'UID:' + uid, 'DTSTAMP:' + STAMP])
    if allday:
        L.append('DTSTART;VALUE=DATE:' + d.strftime('%Y%m%d')); L.append('DTEND;VALUE=DATE:' + (d + dt.timedelta(1)).strftime('%Y%m%d'))
    else:
        dd = d.strftime('%Y%m%d')
        L.append(f'DTSTART;TZID=Europe/Berlin:{dd}T{start.replace(":", "")}00'); L.append(f'DTEND;TZID=Europe/Berlin:{dd}T{end.replace(":", "")}00')
    L.append(fold('SUMMARY:' + esc(title)))
    if desc: L.append(fold('DESCRIPTION:' + esc(desc)))
    L.extend(['TRANSP:OPAQUE', 'END:VEVENT']); n += 1

TM = re.compile(r'^(\d\d:\d\d)–(\d\d:\d\d) (.*)$')
ROW = re.compile(r'^\| (Mo|Di|Mi|Do|Fr|Sa|So) (\d\d)\.(\d\d)\. \|(.*)\|\s*$')
for line in open(md_path, encoding='utf-8'):
    m = ROW.match(line.rstrip('\n'))
    if not m: continue
    day, mon = int(m.group(2)), int(m.group(3))
    d = dt.date(2026 if mon >= 8 else 2027, mon, day)
    cols = [c.strip() for c in m.group(4).split(' | ')]
    if len(cols) < 3: continue
    plan, cc = cols[1].replace('**', ''), cols[2]
    if 'Semester-MC' in plan: ev(d, None, None, 'Semester-MC (ca.)', allday=True); continue
    if plan.startswith('Frei.'): ev(d, '09:00', '09:45', 'Anki: nur fällige Reviews', 'Freier Tag, keine neuen Karten.'); continue
    items, notes = [], []
    for s in plan.split(' · '):
        mm = TM.match(s)
        if mm: items.append([mm.group(1), mm.group(2), mm.group(3)])
        elif s.startswith('abends 10 min'): notes.append(('evening', s))
        elif s.startswith('passt nicht'): notes.append(('sat', s))
        elif s.startswith('danach frei'): pass
        elif items: items[-1][2] += ' · ' + s
    first_anki = True
    for a, b, t in items:
        desc = ''
        if t.startswith('Anki') and first_anki:
            first_anki = False
            if cc and cc != '–': desc = 'Neue Karten freischalten: ' + cc + '\nFällige Reviews immer zuerst.'
        for k, s in notes:
            if k == 'sat': desc = (desc + '\n' if desc else '') + 'Heute nicht geschafft, auf Samstag: ' + s.split(':', 1)[1].strip()
        notes = [x for x in notes if x[0] != 'sat']
        t, desc = enrich(d, t, desc)
        ev(d, a, b, t, desc)
    for k, s in notes:
        if k == 'evening': ev(d, '20:45', '20:55', 'Anatomie: Wochenliste aus dem Kopf', '10 min Vorabruf vor dem Präpkurs.')
L.append('END:VCALENDAR')
open(out_path, 'w', encoding='utf-8', newline='').write('\r\n'.join(L) + '\r\n')
print(n, 'Termine ->', out_path)
