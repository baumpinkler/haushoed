# Haushöd – Stand der Entwicklung

Diese Datei ist für die Weiterarbeit gedacht, auch in einem neuen Claude-Chat: Sie beschreibt, wie die App aufgebaut ist, wie die Daten aussehen und was zuletzt dazugekommen ist. Einrichtung und Veröffentlichung stehen in der `README.md`.

Stand: 17. Oktober 2026, Service-Worker-Version `haushoed-v7`.

## Aufbau der App

Die ganze App steckt in `docs/index.html`: oben das CSS, dann ein kleines Modul-Skript, das Firebase lädt und als `window.HFB` bereitstellt, dann ein großes klassisches Skript mit der eigentlichen App. Es gibt keinen Build-Schritt und keine Abhängigkeiten außer Firebase (von gstatic) und der Barcode-Bibliothek in `docs/vendor/`.

Das große Skript ist in Abschnitte gegliedert, jeweils mit einer Kommentarzeile `/* ============ Name ============ */`:

| Abschnitt | Inhalt |
| --- | --- |
| Hilfsfunktionen | `$`, `esc`, Datumsfunktionen (`today`, `addDays`, `daysUntil`, `fmtDate`), `norm` für Namensvergleiche |
| Grunddaten | Kategorien, Lagerorte, das Wörterbuch `DICT` für Vorschläge, Einheiten, Lernen von Zuordnungen (`guess`, `learn`) |
| Zustand | `S` (alle Daten), `COLS` (Sammlungen), `UI` (Ansichtszustand) |
| Speicher-Schicht | Zwischenspeicher im Browser, Schreib-Warteschlange zu Firestore, Start und Haushalt, Aufräumen, Migrationen |
| Fachlogik | Bestand, Mindestbestand, Einheiten (Lots), Öffnen, Verbrauchen, Entsorgen |
| Darstellung | `render()` und die Ansichten Vorrat, Einkauf, Mehr |
| Artikel-Blatt | Blätter (Modals) für Neu anlegen und Bearbeiten, Einstellungsfelder |
| Rezepte & Wochenplan | Zutaten verstehen, Planrechnung, Kochen, Rezept- und Plan-Blätter |
| Wunschliste | Wünsche, Abstimmen, Einplanen aus der Liste |
| Barcodes | Scanner, Open-Food-Facts-Abfrage, Barcode-Zuordnung |
| Snackbar | Meldungen mit Rückgängig, wegwischbar |
| Ereignisse | Zurück-Taste, Wischen zwischen Bereichen, langes Drücken, zentrale Klickbehandlung |

Grundmuster: Alle Daten liegen in `S`. Änderungen laufen immer über `putArticle`, `putShop`, `putDoc(col, obj)`, `delDoc(col, id)` oder `saveMeta()`. Diese schreiben in `S`, in den Zwischenspeicher und in die Firestore-Warteschlange und rufen `render()` auf. Die Darstellung baut die aktuelle Ansicht danach komplett neu. Blätter (Modals) laufen über `openSheet(build)`; `build.refresh` wird bei jedem `render()` aufgerufen.

## Datenmodell

Ein Haushalt ist `households/{hid}` mit `members` (anonyme UIDs), `names` (UID → Name), `inviteCode` und `meta` (Einstellungen). Darunter liegen die Sammlungen aus `COLS`:

| Sammlung | Dokument | Wichtige Felder |
| --- | --- | --- |
| `articles` | ein Vorratsartikel | `name, cat, loc, mode` (`count` oder `level`), `unit, min, minAmt, buy, checkDays, maxDays, openable, openCheckDays, openMaxDays, base` (`g`, `ml`, `Stk`), `packSize, lots[], codes[]` |
| `shopping` | ein selbst eingetragener Einkaufsposten | `articleId` oder `name`, `qty, done` |
| `recipes` | ein Rezept | `name, servings, ingredients` (Text, eine Zutat pro Zeile), `steps` |
| `plan` | ein geplantes Gericht | `date, recipeId, servings, cooked` |
| `wishes` | ein Wunsch, ID = Rezept-ID | `recipeId, by` (UID), `votes` (UID → 1, -1 oder 0), `created` |
| `log` | ein Monat, ID `JJJJ-MM` | `events[]` (verbraucht/entsorgt), `meals[]` (archivierte Plan-Einträge) |

Ein **Lot** ist eine Einheit oder eine Gruppe gleicher Einheiten: `{id, qty, bought, size, check, expires, opened}`. Bei `mode: 'level'` ist jedes Lot genau eine Packung und `qty` der Füllstand (1, 0,5, 0,2). `check` ist das Datum, ab dem geprüft werden soll, `expires` das Ablaufdatum. Beim Öffnen (`applyOpen`) werden beide ab heute neu gerechnet, aber nie später als vorher.

Ein **Barcode** am Artikel ist `{c, q, size, n}`: Code, wie viele Einheiten ein Scan zählt, Größe einer Einheit, Name laut Datenbank.

Die Firestore-Regeln (`firestore.rules`) erlauben Mitgliedern alles in jeder Untersammlung ihres Haushalts. Neue Sammlungen brauchen also keine Regeländerung.

## Wichtige Abläufe

**Start (`startHousehold`).** Jede Sammlung wird genau einmal gelesen, über ihre Live-Verbindung (`onSnapshot`). Bis alle Sammlungen ihren ersten Stand geliefert haben, merkt sich die App nur den jeweils neuesten; danach laufen Änderungen über `mergeSnap` ein. Eigene, noch nicht bestätigte Schreibvorgänge haben dabei Vorrang. Lesezugriffe pro Start entsprechen also etwa der Zahl der Dokumente. Der kostenlose Firebase-Plan erlaubt 50.000 am Tag.

**Aufräumen (`housekeeping`).** Einmal am Tag pro Gerät wandern Plan-Einträge, die älter als 14 Tage sind, als kurzer Eintrag in `log/{Monat}.meals` (per `arrayUnion`) und werden aus `plan` gelöscht. So wächst die Zahl der Dokumente nicht mit der Zeit. Die archivierten Gerichte werden derzeit nirgends angezeigt.

**Teil-Updates (`remoteUpdate`).** Für Stimmen und das Archiv werden nur einzelne Felder geschrieben (`votes.<uid>`). Gibt es das Dokument noch nicht, wird ersatzweise das ganze lokale Dokument geschrieben.

**Zwischenspeicher (`localSave`).** `S` wird als JSON in `localStorage` gelegt. Passt das nicht, wird zuerst ohne Verlauf gespeichert (`STORE.state = 'partial'`), sonst wird der Zwischenspeicher gelöscht (`'full'`). Die App warnt einmal per Meldung und zeigt unter „Mehr“ einen Hinweis. Firestore hat zusätzlich seinen eigenen Gerätespeicher.

**Planrechnung (`planCalc`).** Geht alle künftigen, nicht gekochten Gerichte in Datumsreihenfolge durch und verbraucht einen simulierten Vorrat Einheit für Einheit. Offene und früh ablaufende Einheiten gehen zuerst weg. Für jedes Gericht gilt der Stand an seinem Tag: Abgelaufenes zählt nicht, was zu prüfen ist, wird als „prüfen“ gemeldet. Ergebnis sind `status` (Übersicht), `detail` (pro Zutat: da, prüfen, kaufen) und `buy` (Einkaufsliste für die nächsten `meta.planDays` Tage). `mealPreview` zeigt `detail` im geplanten Gericht an.

**Zutaten verstehen.** `parseIngredient` liest Zeilen wie „200 g Mehl“, „2 Eier“, „1 Dose Kokosmilch“, „1 EL Öl“, „Salz“. `matchArticle` ordnet sie Vorratsartikeln zu (gleicher Name, Ein-/Mehrzahl, enthaltenes Wort). `ingNeed` entscheidet, ob nach Menge (`amt`), Anzahl (`cnt`) oder nur „vorhanden“ (`any`) gerechnet wird.

**Wunschliste.** Pro Person höchstens 7 eigene Wünsche (`WISH_MAX`), jedes Rezept nur einmal (Dokument-ID = Rezept-ID). Wer sich etwas wünscht, stimmt automatisch dafür. Nochmal Tippen nimmt eine Stimme zurück. `planRecipe` plant ein Gericht ein und nimmt es dabei von der Wunschliste. Alle Wege zum Einplanen laufen über diese Funktion.

**Barcodes.** Android-Chrome nutzt den eingebauten `BarcodeDetector`, alle anderen die ZXing-Bibliothek aus `docs/vendor/`, die erst beim ersten Scannen geladen wird. Unbekannte Codes werden bei Open Food Facts nachgeschlagen (dazu Open Beauty Facts und Open Products Facts). Angaben wie „6 x 0,5 l“ oder „3 Stk“ werden als Menge pro Scan übernommen.

**Zurück-Taste.** Solange ein Blatt offen ist, liegt genau ein eigener Eintrag im Browserverlauf (`HIST`). Beim Schließen wird er erst entfernt, wenn danach wirklich kein Blatt mehr offen ist. So bleibt der Verlauf auch bei Blatt-zu-Blatt-Wechseln richtig.

## Konventionen

Nach jeder Änderung an Dateien in `docs/` die Zahl in `VERSION` in `docs/sw.js` erhöhen, sonst bekommen installierte Apps die neue Version nicht.

Datenänderungen am Bestand alter Daten gehören in `migrate()` (mit Versionsnummer `meta.v`), Aufräumarbeiten in `housekeeping()`.

Texte in der App sind Deutsch (Österreich), in der Du-Form, ohne Fachbegriffe. Meldungen nach Änderungen bieten möglichst „Rückgängig“ an.

## Testen

Im Ordner `tests/` liegt `fakefb.js`, ein kleines Firestore-Imitat. Es ersetzt `window.HFB`, zählt Lesezugriffe und protokolliert Schreibvorgänge. `plan_und_wuensche.py` spielt damit in einem Headless-Chromium (Playwright) einen Haushalt mit zwei Personen durch: Start, Archiv, Tagesansicht eines Gerichts, Einkaufsliste, Wunschliste mit Abstimmen und Limit, Einplanen aus der Liste, Speicher voll.

Für Scanner-Tests eignet sich Chromium mit `--use-fake-device-for-media-stream --use-file-for-fake-video-capture=<datei.y4m>`; ein solches Video mit einem Barcode lässt sich mit Python (Pillow) und `ffmpeg` erzeugen. Open Food Facts lässt sich in Playwright mit `context.route` beantworten.

## Verlauf

- **Barcode-Scanner:** Scannen zum Einräumen, Verbrauchen und Nachschauen, Open Food Facts, Barcodes als lernbare Zuordnung, Menge pro Scan (z. B. 3er-Pack).
- **Bedienung:** Zurück-Taste schließt Blätter, Wischen zwischen den Bereichen, Meldungen wegwischen.
- **Vorrat:** Neu anlegen auch mit Menge 0. „Öffenbar“ mit eigenen Fristen für geöffnete Einheiten; öffnen im Artikel oder durch langes Drücken auf „−“ in der Liste.
- **Firebase:** Start liest jede Sammlung nur noch einmal, alte Plan-Einträge werden archiviert, Warnung bei vollem Gerätespeicher.
- **Kochen:** Wunschliste mit Abstimmen; geplante Gerichte zeigen, was an ihrem Tag da ist, geprüft oder nachgekauft werden muss. Die Einkaufsliste berücksichtigt, was bis zum Kochtag abläuft.

## Offene Ideen

- Scanner im Einkauf: Artikel durch Scannen auf der Liste abhaken.
- Archivierte Gerichte nutzen, z. B. „zuletzt gekocht am …“ im Rezept oder Vorschläge für lange nicht Gekochtes.
- Verlauf (`log.events`) für Statistiken über mehr als einen Monat nutzen.
- Hinweis, wenn das Firebase-Tageslimit näher rückt (derzeit nur eine Meldung, wenn es erreicht ist).
