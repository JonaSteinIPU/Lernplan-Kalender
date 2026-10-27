#!/usr/bin/env python3
"""Baut lernplan.ics aus dem Markdown-Export des Tabs „Tag für Tag“.

Aufruf: python3 build_ics.py tagfuertag.md [daten.json] [lernplan.ics]

Jeder Termin heißt nur „Anki“, „SMPP“, „ANATOMIE“ oder „SEMESTER“.
Alle Details stehen geordnet in der Beschreibung.
"""
import sys, re, json, hashlib, datetime as dt

md_path = sys.argv[1]
daten_path = sys.argv[2] if len(sys.argv) > 2 else 'daten.json'
out_path = sys.argv[3] if len(sys.argv) > 3 else 'lernplan.ics'
with open(daten_path, encoding='utf-8') as f:
    D = json.load(f)
FR, VER, PREP = D['fragen'], D['veranstaltungen'], D['praepkurs']
LAB = {'A': 'Ana', 'B': 'Bio', 'P': 'Phys'}
AB = {v: k for k, v in LAB.items()}
STAMP = '20261027T000000Z'
SEP = '\n\n'

# ---------- Hilfsfunktionen ----------
def esc(s):
    return s.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')

def fold(line):
    out, cur = [], b''
    for ch in line:
        e = ch.encode('utf-8')
        if len(cur) + len(e) > 73:
            out.append(cur.decode()); cur = b' ' + e
        else:
            cur += e
    out.append(cur.decode())
    return '\r\n'.join(out)

def refs(t):
    """Alle Fragen in der Reihenfolge des Textes, mit Markierung Wdh./Nachholen."""
    out, tag = [], ''
    for part in re.split(r' · ', t):
        tag = 'Wdh.' if part.startswith('Wdh.') else ('Nachholen' if part.startswith('Nachholen') else '')
        for m in re.finditer(r'(Ana|Bio|Phys) ((?:\d{1,2}\.\d{1,2}(?:, )?)+)', part):
            for n in re.findall(r'\d{1,2}\.\d{1,2}', m.group(2)):
                k = AB[m.group(1)] + n
                if k not in [x for x, _ in out]:
                    out.append((k, tag))
    return out

def qname(k):
    t = FR.get(k, '')
    return f"{LAB[k[0]]} {k[1:]}" + (f" – {t}" if t else '')

def qlist(rs):
    return '\n'.join('• ' + (f'[{tag}] ' if tag else '') + qname(k) for k, tag in rs)

def week_days(d):
    mon = d - dt.timedelta(d.weekday())
    return [mon + dt.timedelta(i) for i in range(d.weekday() + 1)], mon

def cards_text(cc):
    """„SMPP II 45: Ana 21.3 (Rest), 21.5 (Anfang) · Prometheus 10: …“ -> Liste."""
    if not cc or cc == '–':
        return ''
    lines = []
    for part in cc.split(' · '):
        m = re.match(r'(SMPP II|Prometheus) (\d+): (.*)', part)
        if not m:
            lines.append('• ' + part); continue
        deck, n, rest = m.groups()
        if deck == 'Prometheus':
            lines.append(f'• Prometheus-Deck, {n} Karten: die Strukturen von heute')
            continue
        lines.append(f'• SMPP-II-Deck, {n} Karten, in dieser Reihenfolge:')
        for grp in rest.split('; '):
            g = re.match(r'(Ana|Bio|Phys) (.*)', grp)
            if not g: continue
            for item in g.group(2).split(', '):
                im = re.match(r'(\d{1,2}\.\d{1,2})(?: \((\w+)\))?', item)
                if not im: continue
                k = AB[g.group(1)] + im.group(1)
                lines.append(f'   – {qname(k)}' + (f' ({im.group(2)})' if im.group(2) else ''))
    return '\n'.join(lines)

ABLAUF_SMPP = ('Ablauf je Frage (ca. 25 min):\n'
               '1. Raten: ohne Nachschauen antworten (2 min)\n'
               '2. Verstehen: Kurzüberblick und MSC-Ausarbeitung lesen (10–12 min)\n'
               '3. Abrufen: Ausarbeitung zu, laut erzählen (5 min)\n'
               '4. Abgleichen: Lücken gezielt nachfragen (3 min)\n'
               '5. Die SMPP-II-Karten der Frage freischalten (2 min)')
WDH_HINWEIS = '[Wdh.] = steht im Lernplan des MSC-Trainers erneut: frei beantworten und neu bewerten (ca. 5 min).'
NACH_HINWEIS = '[Nachholen] = aus der Liste „Nachholen“ im MSC-Trainer (Woche 1–2).'
ABLAUF_ANA = ('Ablauf je Struktur:\n'
              '1. Raten: Ursprung, Ansatz, Innervation aufschreiben (1 min)\n'
              '2. Erarbeiten im Prometheus, am Skelett zeigen (15 min)\n'
              '3. Abrufen: Buch zu, laut sagen und zeigen (8 min)\n'
              '4. Abgleichen und korrigieren (4 min)\n'
              '5. Prometheus-Karten genau dieser Strukturen freischalten (2 min)')

def legend(rs):
    tags = {t for _, t in rs}
    out = []
    if 'Wdh.' in tags: out.append(WDH_HINWEIS)
    if 'Nachholen' in tags: out.append(NACH_HINWEIS)
    return '\n'.join(out)

def classify(d, t, cc, notes):
    """Gibt (Titel, Beschreibung) für einen Block zurück."""
    forts = t.endswith('(Forts.)')
    base = t.replace(' (Forts.)', '')
    head = []
    if forts:
        head.append('Fortsetzung des Blocks davor.')

    # ---- Anki ----
    if base.startswith('Anki'):
        lines = ['Anki-Reviews', '1. Erst alle fälligen Reviews (SMPP II und Prometheus).']
        ct = cards_text(cc) if not forts else ''
        if ct:
            lines.append('2. Danach neue Karten freischalten:\n' + ct)
        desc = '\n'.join(lines)
        if notes and not forts:
            desc += SEP + 'Hinweis für heute: ' + notes
        return 'Anki', SEP.join(head + [desc])

    # ---- SMPP ----
    rs = refs(base)
    if base.startswith('SMPP-II-Woche abschließen'):
        body = ['SMPP-II-Woche abschließen',
                'So geht’s: jede Frage frei und laut beantworten (3–4 min), mit dem Kurzüberblick abgleichen, im MSC-Trainer bewerten.',
                'Fragen der Woche:\n' + qlist(rs)]
        return 'SMPP', SEP.join(head + body)
    if base.startswith('SMPP-II-Altthemen'):
        return 'SMPP', SEP.join(head + ['SMPP-II-Altthemen',
            'So geht’s: ältere Fragen frei beantworten und im MSC-Trainer bewerten. Zuerst Fragen, die du länger nicht hattest.'])
    if '„Auch berührt“' in base:
        return 'SMPP', SEP.join(head + ['SMPP II: „Auch berührt“ wiederholen',
            'So geht’s: nur Fragen, die du schon gelernt hast, frei beantworten und im MSC-Trainer bewerten.',
            'Fragen:\n' + qlist(rs)])
    if 'nochmal“ oder „unsicher' in base:
        return 'SMPP', SEP.join(head + ['SMPP II: „nochmal“ und „unsicher“',
            'So geht’s: im MSC-Trainer alle Fragen öffnen, die auf „nochmal“ oder „unsicher“ stehen, frei beantworten und neu bewerten.'])
    if 'Simulator' in base:
        return 'SMPP', SEP.join(head + ['SMPP II: mündlicher Durchlauf',
            'So geht’s: im Simulator des MSC-Trainers einen Durchlauf wie in der Prüfung machen, laut antworten.'])
    if base.startswith('SMPP-II-Block'):
        return 'SMPP', SEP.join(head + ['Freier SMPP-II-Block',
            'Nutze ihn in dieser Reihenfolge:\n1. Offene Fragen aus dem Aufholplan\n2. Fragen auf „nochmal“ im MSC-Trainer\n3. SMPP-II-Altthemen'])
    if base.startswith('Puffer'):
        return 'SMPP', SEP.join(head + ['Puffer',
            'Nutze ihn in dieser Reihenfolge:\n1. Offene SMPP-II-Fragen aus dem Aufholplan\n2. Fragen auf „nochmal“ im MSC-Trainer\n3. SMPP-II-Altthemen'])
    if base.startswith('SMPP-II-Gesamtwiederholung'):
        topic = base.split(':', 1)[1].strip() if ':' in base else ''
        return 'SMPP', SEP.join(head + ['SMPP-II-Gesamtwiederholung' + (f': {topic}' if topic else ''),
            'So geht’s: alle Fragen dieses Bereichs frei beantworten und im MSC-Trainer bewerten.'])
    if base.startswith('SMPP-II-Lücken'):
        return 'SMPP', SEP.join(head + ['SMPP II: Lücken nachlesen',
            'So geht’s: nur die Stellen in der MSC-Ausarbeitung nachlesen, die eben gefehlt haben, danach einmal laut erzählen.'])
    if rs or base.startswith(('SMPP II', 'SMPP-II-Fragen', 'letzte SMPP-II-Fragen')):
        kind = 'SMPP-II-Einstiegsfragen erarbeiten'
        if 'nicht gepasst' in base: kind = 'SMPP-II-Fragen, die unter der Woche nicht gepasst haben'
        elif 'aus der letzten Woche' in base: kind = 'SMPP-II-Fragen aus der letzten Woche'
        elif base.startswith('letzte'): kind = 'Letzte SMPP-II-Fragen vor der Semester-MC'
        body = [kind]
        if rs: body.append('Fragen:\n' + qlist(rs))
        lg = legend(rs)
        if lg: body.append(lg)
        if not forts: body.append(ABLAUF_SMPP)
        body.append('Wortlaut der Fragen: MSC-Ausarbeitung.')
        return 'SMPP', SEP.join(head + body)

    # ---- ANATOMIE ----
    _, mon = week_days(d)
    p = PREP.get(mon.isoformat(), '')
    prep = f'Präpkurs diese Woche: {p}' if p else ''
    if base.startswith('Anatomie-Liste'):
        n = re.search(r'(\d+) Strukturen', base)
        body = [f'Anatomie-Wochenliste: {n.group(1) if n else "2–3"} Strukturen'] + ([prep] if prep else []) + [ABLAUF_ANA]
        return 'ANATOMIE', SEP.join(head + body)
    if base.startswith('Anatomie: alte Wochenlisten'):
        return 'ANATOMIE', SEP.join(head + ['Anatomie: alte Wochenlisten',
            'So geht’s: leere Tabelle (Muskel, Ursprung, Ansatz, Innervation, Funktion) aus dem Kopf füllen, dann mit Prometheus abgleichen. Lücken als Prometheus-Karten freischalten.'])
    if base.startswith('Anatomie:'):
        body = ['Anatomie: 2 Strukturen und Wochenliste'] + ([prep] if prep else []) + [
            '1. Die 2 Strukturen von heute wie unter der Woche (30 min)',
            '2. Leere Tabelle der ganzen Wochenliste aus dem Kopf füllen, dann abgleichen (20 min)']
        return 'ANATOMIE', SEP.join(head + body)
    if base.startswith('Wochenliste aus dem Kopf'):
        return 'ANATOMIE', SEP.join(['Anatomie: Wochenliste aus dem Kopf (10 min)',
            'Die ganze Wochenliste ohne Nachschauen durchgehen, als Vorbereitung auf den Präpkurs.'] + ([prep] if prep else []))
    if base.startswith('neue Wochenliste'):
        return 'ANATOMIE', SEP.join(head + ['Anatomie: neue Wochenliste',
            'Liste anschauen und raten, was du schon weißt (15 min).'])
    if base.startswith('3D-Anatomie'):
        what = base.split(':', 1)[1].strip() if ':' in base else ''
        return 'ANATOMIE', SEP.join(head + ['3D-Anatomie für die Semester-MC' + (f': {what}' if what else ''),
            'So geht’s: Abbildungen mit abgedeckter Beschriftung, Struktur benennen, dann aufdecken.'])

    # ---- SEMESTER ----
    if base.startswith('Vorlesung lesen'):
        v = VER.get(d.isoformat(), [])
        if v:
            heute = 'Heute:\n' + '\n'.join('• ' + x for x in v)
        else:
            days, _ = week_days(d)
            w = [x for dd in days for x in VER.get(dd.isoformat(), [])]
            heute = ('Heute keine Vorlesung. Nimm eine aus dieser Woche, die du noch nicht gelesen hast:\n'
                     + '\n'.join('• ' + x for x in w)) if w else 'Nimm die nächste ungelesene Vorlesung.'
        return 'SEMESTER', SEP.join(head + ['Vorlesungen und Seminare', heute,
            'Ablauf:\n1. Lesen und Unklares am Rand notieren (ca. 25 min)\n2. Ausarbeitung zu: die 3 wichtigsten Punkte aus dem Kopf aufschreiben (3 min)\n3. Abgleichen und korrigieren (1 min)'])
    if base.startswith('3-Punkte-Zettel'):
        return 'SEMESTER', SEP.join(head + ['3-Punkte-Zettel der Woche (10 min)',
            'Alle Zettel der Woche einmal durchgehen, ohne die Ausarbeitungen erneut zu lesen.'])
    if base.startswith('Semester-MC:'):
        what = base.split(':', 1)[1].strip()
        return 'SEMESTER', SEP.join(head + ['Semester-MC: ' + what])
    return 'SEMESTER', SEP.join(head + [base])

# ---------- Kalender ----------
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
        L.append('DTSTART;VALUE=DATE:' + d.strftime('%Y%m%d'))
        L.append('DTEND;VALUE=DATE:' + (d + dt.timedelta(1)).strftime('%Y%m%d'))
    else:
        dd = d.strftime('%Y%m%d')
        L.append(f'DTSTART;TZID=Europe/Berlin:{dd}T{start.replace(":", "")}00')
        L.append(f'DTEND;TZID=Europe/Berlin:{dd}T{end.replace(":", "")}00')
    L.append(fold('SUMMARY:' + esc(title)))
    if desc: L.append(fold('DESCRIPTION:' + esc(desc)))
    L.extend(['TRANSP:OPAQUE', 'END:VEVENT']); n += 1

TM = re.compile(r'^(\d\d:\d\d)–(\d\d:\d\d) (.*)$')
ROW = re.compile(r'^\| (Mo|Di|Mi|Do|Fr|Sa|So) (\d\d)\.(\d\d)\. \|(.*)\|\s*$')
with open(md_path, encoding='utf-8') as f:
    lines = f.read().split('\n')
for line in lines:
    m = ROW.match(line.rstrip('\r'))
    if not m: continue
    day, mon = int(m.group(2)), int(m.group(3))
    d = dt.date(2026 if mon >= 8 else 2027, mon, day)
    cols = [c.strip() for c in m.group(4).split(' | ')]
    if len(cols) < 3: continue
    plan, cc = cols[1].replace('**', ''), cols[2]
    if 'Semester-MC' in plan and not TM.match(plan.split(' · ')[0]):
        ev(d, None, None, 'SEMESTER', 'Semester-MC (ca.)', allday=True); continue
    if plan.startswith('Frei.'):
        ev(d, '09:00', '09:45', 'Anki', 'Freier Tag: nur fällige Reviews, keine neuen Karten.'); continue
    items, notes, evening = [], '', False
    for s in plan.split(' · '):
        mm = TM.match(s)
        if mm: items.append([mm.group(1), mm.group(2), mm.group(3)])
        elif s.startswith('abends 10 min'): evening = True
        elif s.startswith('passt nicht'): notes = 'passt nicht in den Tag und wandert auf Samstag: ' + s.split(':', 1)[1].strip()
        elif s.startswith('danach frei'): pass
        elif items: items[-1][2] += ' · ' + s
    first_anki = True
    prev = ''
    for a, b, t in items:
        if t.endswith('(Forts.)') and prev and not t.startswith('Anki'):
            t = prev.replace(' (Forts.)', '') + ' (Forts.)'
        prev = t
        if t.startswith('Anki') and not first_anki:
            title, desc = classify(d, t + ('' if t.endswith('(Forts.)') else ' (Forts.)'), '', '')
        else:
            title, desc = classify(d, t, cc, notes if t.startswith('Anki') else '')
        if t.startswith('Anki'): first_anki = False
        ev(d, a, b, title, desc)
    if evening:
        title, desc = classify(d, 'Wochenliste aus dem Kopf', '', '')
        ev(d, '20:45', '20:55', title, desc)
L.append('END:VCALENDAR')
with open(out_path, 'w', encoding='utf-8', newline='') as f:
    f.write('\r\n'.join(L) + '\r\n')
print(n, 'Termine ->', out_path)
