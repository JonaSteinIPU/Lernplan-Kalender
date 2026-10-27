# Lernplan-Kalender

Kalenderabo für den Lernplan 3. Semester (27.10.2026 bis zur MC am 14.02.2027).

**Abo-Link:** `https://raw.githubusercontent.com/JonaSteinIPU/Lernplan-Kalender/main/lernplan.ics`

In Apple Kalender: Ablage → Neues Kalenderabonnement → Link einfügen → „Automatisch aktualisieren: Jede Stunde“.

## Wie die Datei entsteht

- `tagfuertag.md`: Markdown-Export des Tabs „Tag für Tag“ aus dem Lernplan-Dokument
- `daten.json`: Kurztitel der MSC-Einstiegsfragen, Vorlesungs- und Seminarthemen pro Tag, Präpkurs-Thema pro Woche
- `build_ics.py`: baut daraus `lernplan.ics`. Jeder Termin heißt nur „Anki“, „SMPP“, „ANATOMIE“ oder „SEMESTER“; die Details (Fragen, Karten, Ablauf, Vorlesungen) stehen geordnet in der Beschreibung.

```
python3 build_ics.py tagfuertag.md daten.json lernplan.ics
```

Eine geplante Aufgabe exportiert jeden Abend den aktuellen Stand des Dokuments, baut die Datei neu und lädt sie hier hoch, wenn sich etwas geändert hat.
