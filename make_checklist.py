#!/usr/bin/env python3
"""Erzeugt den Markdown-Inhalt für den Tab „Abhaken“ aus tagfuertag.md."""
import re, sys, json
md = open(sys.argv[1], encoding='utf-8').read().split('\n')
TM = re.compile(r'^(\d\d:\d\d)–(\d\d:\d\d) (.*)$')
ROW = re.compile(r'^\| (Mo|Di|Mi|Do|Fr|Sa|So) (\d\d)\.(\d\d)\. \|(.*)\|\s*$')
def cat(t):
    if t.startswith('Anki'): return 'Anki'
    if t.startswith(('Anatomie', '3D-Anatomie', 'neue Wochenliste', 'Wochenliste')): return 'ANATOMIE'
    if t.startswith(('Vorlesung', '3-Punkte', 'Semester-MC')): return 'SEMESTER'
    return 'SMPP'
def short(t):
    t = t.replace(' (Forts.)', '')
    rep = [('SMPP-II-Woche abschließen, frei beantworten und im MSC-Trainer bewerten: ', 'Woche abschließen: '),
           ('SMPP II, „Auch berührt“ wiederholen: ', '„Auch berührt“: '),
           ('SMPP II: alle Fragen, die im MSC-Trainer auf „nochmal“ oder „unsicher“ stehen', '„nochmal“/„unsicher“'),
           ('SMPP II: ein mündlicher Durchlauf im Simulator des MSC-Trainers', 'Simulator-Durchlauf'),
           ('SMPP-II-Block: frei, Altthemen oder „nochmal“-Fragen', 'freier Block'),
           ('Puffer, sonst SMPP-II-Altthemen', 'Puffer'),
           ('SMPP-II-Fragen, die unter der Woche nicht gepasst haben: ', 'nachholen: '),
           ('SMPP-II-Fragen aus der letzten Woche: ', ''), ('letzte SMPP-II-Fragen: ', 'letzte Fragen: '), ('SMPP-II-Fragen: ', ''),
           ('SMPP-II-Gesamtwiederholung frei beantworten: ', 'Gesamtwiederholung '),
           ('SMPP-II-Altthemen frei beantworten und im MSC-Trainer bewerten', 'Altthemen'),
           ('SMPP-II-Lücken daraus nachlesen', 'Lücken nachlesen'), ('SMPP-II-Lücken nachlesen', 'Lücken nachlesen'),
           ('SMPP II: ', ''), ('Vorlesung lesen + 3-Punkte-Abruf', 'Vorlesung + 3-Punkte-Abruf'),
           ('Anatomie: 2 Strukturen + leere Tabelle der Wochenliste', '2 Strukturen + leere Tabelle'),
           ('Anatomie: alte Wochenlisten, leere Tabelle', 'alte Wochenlisten'), ('Anatomie: alte Wochenlisten', 'alte Wochenlisten'),
           ('Anatomie-Liste: ', ''), ('neue Wochenliste anschauen und raten', 'neue Wochenliste anschauen'),
           ('3-Punkte-Zettel der Woche', '3-Punkte-Zettel der Woche'), ('Semester-MC: ', ''), ('3D-Anatomie: ', '3D: ')]
    for a, b in rep: t = t.replace(a, b)
    return t
out = {}; month = None; week = None; moved = []
sect = None
for line in md:
    hm = re.match(r'^## (Oktober und November|Dezember|Januar|Februar)\s*$', line)
    if hm:
        sect = {'Oktober und November': 'nov', 'Dezember': 'dez', 'Januar': 'jan', 'Februar': 'feb'}[hm.group(1)]
        continue
    h = re.match(r'^### (KW \d+ · [^·]+)(?: · (.*))?$', line)
    if h:
        week = '### ' + h.group(1).strip() + (' · ' + h.group(2) if h.group(2) else '')
        continue
    m = ROW.match(line)
    if not m: continue
    wd, day, mon = m.group(1), m.group(2), int(m.group(3))
    key = sect
    cols = [c.strip() for c in m.group(4).split(' | ')]
    plan = cols[1].replace('**', '')
    items = []
    if 'Semester-MC (ca.)' in plan and not TM.match(plan.split(' · ')[0]):
        items = [('SEMESTER', [], 'Semester-MC')]
    elif plan.startswith('Frei.'):
        items = [('Anki', ['09:00'], 'nur fällige Reviews')]
    else:
        prev = None
        for s in plan.split(' · '):
            pre = re.match(r'^.{1,60}?:\s+(\d\d:\d\d–\d\d:\d\d .*)$', s)
            if pre and not TM.match(s): s = pre.group(1)
            mm = TM.match(s)
            if mm:
                a, t = mm.group(1), mm.group(3)
                c = cat(t)
                if t.endswith('(Forts.)') and prev and prev[0] == c:
                    prev[1].append(a); continue
                prev = [c, [a], (('fällige Reviews, dann neue Karten' if cols[2] not in ('', '–') else 'nur fällige Reviews') if c == 'Anki' else short(t))]; items.append(prev)
            elif s.startswith('abends 10 min'):
                items.append(['ANATOMIE', ['20:45'], 'Wochenliste aus dem Kopf'])
            elif s.startswith('nicht geschafft'): pass
            elif s.startswith('passt nicht'):
                for x in s.split(':', 1)[1].strip().split(', '):
                    mins = re.search(r'\((\d+) min\)', x)
                    x = re.sub(r' \(\d+ min\)', '', x)
                    if x == 'SMPP II': x = f'Rest des SMPP-Blocks ({mins.group(1)} min)' if mins else 'Rest des SMPP-Blocks'
                    moved.append(('ANATOMIE' if x.startswith('Anatomie') else ('SEMESTER' if x.startswith('Vorlesung') else 'SMPP'), f'von {wd} {day}.{mon:02d}.: ' + short(x)))
            elif s.startswith('danach frei'): pass
            elif prev: prev[2] += ' · ' + short(s)
    if wd == 'Sa' and moved:
        items += [[c, [], t] for c, t in moved]; moved.clear()
    lines = out.setdefault(key, [])
    if week:
        lines.append(week); lines.append(''); week = None
    lines.append(f'**{wd} {day}.{mon:02d}.**'); lines.append('')
    for c, times, txt in items:
        tt = ' + '.join(times)
        lines.append(f'- [ ] {c} {tt}' + (f' · {txt}' if txt else '')) if tt else lines.append(f'- [ ] {c} · {txt}')
    lines.append('')
heads = {'nov': '## Oktober und November', 'dez': '## Dezember', 'jan': '## Januar', 'feb': '## Februar'}
res = {k: heads[k] + '\n\n' + '\n'.join(v).strip() for k, v in out.items()}
json.dump(res, open(sys.argv[2], 'w'), ensure_ascii=False)
for k, v in res.items(): print(k, len(v))
