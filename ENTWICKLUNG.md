# Haushöd – Stand der Entwicklung

Diese Datei ist für die Weiterarbeit gedacht, auch in einem neuen Claude-Chat: Sie beschreibt, wie die App aufgebaut ist, wie die Daten aussehen und was zuletzt dazugekommen ist. Einrichtung und Veröffentlichung stehen in der `README.md`.

Stand: 17. Oktober 2026, Service-Worker-Version `haushoed-v13`.

## Aufbau der App

Die ganze App steckt in `docs/index.html`: oben das CSS, dann ein kleines Modul-Skript, das Firebase lädt und als `window.HFB` bereitstellt, dann ein großes klassisches Skript mit der eigentlichen App. Es gibt keinen Build-Schritt und keine Abhängigkeiten außer Firebase (von gstatic) und der Barcode-Bibliothek in `docs/vendor/`.

Das große Skript ist in Abschnitte gegliedert, jeweils mit einer Kommentarzeile `/* ============ Name ============ */`:

| Abschnitt | Inhalt |
| --- | --- |
| Hilfsfunktionen | `$`, `esc`, Datumsfunktionen (`today`, `addDays`, `daysUntil`, `fmtDate`), `norm` für Namensvergleiche |
| Grunddaten | Kategorien, Lagerorte, das Wörterbuch `DICT` für Vorschläge, Einheiten, Lernen von Zuordnungen (`guess`, `learn`), Löffel-Gewichte (`EL_TABLE`, `EL_RULES`, `EL_FEEL`) |
| Zustand | `S` (alle Daten), `COLS` (Sammlungen), `UI` (Ansichtszustand, dazu zugeklappte Kategorien und Tag-Filter) |
| Speicher-Schicht | Zwischenspeicher im Browser, Schreib-Warteschlange zu Firestore, Start und Haushalt, Aufräumen, Migrationen |
| Fachlogik | Bestand, Mindestbestand, Einheiten (Lots), Öffnen, Verbrauchen, Entsorgen, Zählart „nur melden“ (`setFlag`) |
| Darstellung | `render()` und die Ansichten Vorrat, Einkauf, Mehr |
| Artikel-Blatt | Blätter (Modals) für Neu anlegen und Bearbeiten, Einstellungsfelder |
| Rezepte & Wochenplan | Zutaten verstehen, Planrechnung, Kochen, Rezept- und Plan-Blätter |
| Wunschliste | Wünsche, Abstimmen, Einplanen aus der Liste |
| Barcodes | Scanner, Open-Food-Facts-Abfrage, Barcode-Zuordnung |
| Schnell verbrauchen | Blatt „Verbraucht“ (`openQuickUse`), Vorschläge (`usualSuspects`, `noteUse`) |
| Snackbar | Meldungen mit Rückgängig, wegwischbar |
| Ereignisse | Zurück-Taste, Wischen zwischen Bereichen, langes Drücken, zentrale Klickbehandlung |

Grundmuster: Alle Daten liegen in `S`. Änderungen laufen immer über `putArticle`, `putShop`, `putDoc(col, obj)`, `delDoc(col, id)` oder `saveMeta()`. Diese schreiben in `S`, in den Zwischenspeicher und in die Firestore-Warteschlange und rufen `render()` auf. Die Darstellung baut die aktuelle Ansicht danach komplett neu. Blätter (Modals) laufen über `openSheet(build)`; `build.refresh` wird bei jedem `render()` aufgerufen.

## Datenmodell

Ein Haushalt ist `households/{hid}` mit `members` (anonyme UIDs), `names` (UID → Name), `inviteCode`, `meta` (Einstellungen), `roles` (UID → `'child'`, siehe „Rollen“) und `filters` (UID → gespeicherte Rezeptfilter). Darunter liegen die Sammlungen aus `COLS`:

| Sammlung | Dokument | Wichtige Felder |
| --- | --- | --- |
| `articles` | ein Vorratsartikel | `name, cat, loc, mode` (`count`, `level` oder `flag`), `low` (nur bei `flag`: wird knapp), `unit, min, minAmt, buy, checkDays, maxDays, openable, openCheckDays, openMaxDays, base` (`g`, `ml`, `Stk`), `packSize, lots[], codes[], elg` (Gramm pro gestrichenem EL, nur wenn selbst gesetzt) |
| `shopping` | ein selbst eingetragener Einkaufsposten | `articleId` oder `name`, `qty, done` |
| `recipes` | ein Rezept | `name, servings, ingredients` (Text, eine Zutat pro Zeile), `steps, prepTime, cookTime` (Minuten oder `null`), `tags[]` (frei vergeben), `ratings` (UID → 1 bis 5, 0 = nicht bewertet) |
| `plan` | ein geplantes Gericht | `date, recipeId, servings, cooked` |
| `wishes` | ein Wunsch, ID = Rezept-ID | `recipeId, by` (UID), `votes` (UID → 1, -1 oder 0), `created` |
| `log` | ein Monat, ID `JJJJ-MM` | `events[]` (verbraucht/entsorgt), `meals[]` (archivierte Plan-Einträge) |

Ein **Lot** ist eine Einheit oder eine Gruppe gleicher Einheiten: `{id, qty, bought, size, check, expires, opened}`. Bei `mode: 'level'` ist jedes Lot genau eine Packung und `qty` der Füllstand (1, 0,5, 0,2). `check` ist das Datum, ab dem geprüft werden soll, `expires` das Ablaufdatum. Beim Öffnen (`applyOpen`) werden beide ab heute neu gerechnet, aber nie später als vorher.

Ein **Barcode** am Artikel ist `{c, q, size, n}`: Code, wie viele Einheiten ein Scan zählt, Größe einer Einheit, Name laut Datenbank.

Jedes Dokument in diesen Sammlungen hat zusätzlich `updated`: die Serverzeit des letzten Schreibvorgangs (`serverTimestamp()`, gesetzt in `remotePut`, `remoteUpdate` und `remoteDel`; lokal als Millisekunden). Gelöschtes ist ein Dokument `{id, _del: true, updated}` (Lösch-Markierung), siehe „Abgleich“.

Die Firestore-Regeln (`firestore.rules`) erlauben Mitgliedern alles in jeder Untersammlung ihres Haushalts. Neue Sammlungen brauchen also keine Regeländerung.

## Wichtige Abläufe

**Abgleich (`startHousehold`, `applySnap`).** Beim Start bekommt jede Sammlung eine Live-Verbindung (`onSnapshot`). Ist der Zwischenspeicher aktuell, holt sie nur Dokumente mit `updated >= SYNC.since[Sammlung]`, sonst die ganze Sammlung. `SYNC` (`{hid, full, since}`) liegt im selben Zwischenspeicher wie die Daten (`haushoed:cache`, Feld `_sync`); fehlt der Zwischenspeicher, fehlt auch `SYNC`. Vollständig gelesen wird, wenn `SYNC` fehlt, zu einem anderen Haushalt gehört oder der letzte vollständige Abgleich älter als `FULL_EVERY` (3 Tage) ist; einzeln auch eine Sammlung ohne `since` (etwa der Verlauf, wenn er wegen Platzmangel nicht zwischengespeichert wurde). `since` rückt nur mit Ständen direkt vom Server weiter und nur bis zum größten `updated`, das wirklich angekommen ist. Weil `updated` die Serverzeit ist, spielt die Uhr der Handys keine Rolle.

Ein normaler Start kostet so etwa 8 Lesezugriffe (Haushalt suchen, Haushaltsdokument, je Sammlung mindestens einer) plus einen je Dokument, das sich seither geändert hat. Jede Änderung, die während der Nutzung von einem anderen Gerät kommt, kostet einen. Der vollständige Abgleich alle 3 Tage kostet etwa so viel wie die Zahl der Dokumente.

Löschen (`remoteDel`) schreibt eine Lösch-Markierung statt das Dokument zu entfernen, sonst würden Geräte, die nur Änderungen abholen, es nie erfahren. `applySnap` entfernt markierte Dokumente lokal; Markierungen älter als `TOMB_KEEP` (30 Tage) löscht der vollständige Abgleich endgültig (`remotePurge`). Lokal löscht `applySnap` nie etwas, nur weil es in einem Stand fehlt (das tut nur der vollständige Abgleich mit `replace`): Eigene, noch unbestätigte Schreibvorgänge verschwinden bei Firestore kurz aus Abfragen auf `updated`. Eigene ausstehende Schreibvorgänge (`busyIds`, `pending`) haben immer Vorrang vor dem Server.

Der vollständige Abgleich ist auch das Netz für Sonderfälle: Ein Gerät mit alter App-Version schreibt ohne `updated` und wäre im Änderungs-Abgleich unsichtbar. Unter „Mehr → Daten“ erzwingt „Alles neu abgleichen“ einen vollständigen Abgleich.

**Aufräumen (`housekeeping`).** Einmal am Tag pro Gerät wandern Plan-Einträge, die älter als 14 Tage sind, als kurzer Eintrag in `log/{Monat}.meals` (per `arrayUnion`) und werden aus `plan` gelöscht. So wächst die Zahl der Dokumente nicht mit der Zeit. Die archivierten Gerichte werden derzeit nirgends angezeigt.

**Teil-Updates (`remoteUpdate`).** Für Stimmen, Bewertungen, Tags und das Archiv werden nur einzelne Felder geschrieben (`votes.<uid>`), immer zusammen mit `updated`. Gibt es das Dokument noch nicht, wird ersatzweise das ganze lokale Dokument geschrieben.

**Zwischenspeicher (`localSave`).** `S` wird als JSON in `localStorage` gelegt. Passt das nicht, wird zuerst ohne Verlauf gespeichert (`STORE.state = 'partial'`), sonst wird der Zwischenspeicher gelöscht (`'full'`). Die App warnt einmal per Meldung und zeigt unter „Mehr“ einen Hinweis. Firestore hat zusätzlich seinen eigenen Gerätespeicher.

**Planrechnung (`planCalc`).** Geht alle künftigen, nicht gekochten Gerichte in Datumsreihenfolge durch und verbraucht einen simulierten Vorrat Einheit für Einheit. Offene und früh ablaufende Einheiten gehen zuerst weg. Für jedes Gericht gilt der Stand an seinem Tag: Abgelaufenes zählt nicht, was zu prüfen ist, wird als „prüfen“ gemeldet. Ergebnis sind `status` (Übersicht), `detail` (pro Zutat: da, prüfen, kaufen) und `buy` (Einkaufsliste für die nächsten `meta.planDays` Tage). `mealPreview` zeigt `detail` im geplanten Gericht an.

**Zutaten verstehen.** `parseIngredient` liest Zeilen wie „200 g Mehl“, „2 Eier“, „1 Dose Kokosmilch“, „1 EL Öl“, „Salz“. `matchArticle` ordnet sie Vorratsartikeln zu (gleicher Name, Ein-/Mehrzahl, enthaltenes Wort). `ingNeed` entscheidet, ob nach Menge (`amt`), Anzahl (`cnt`) oder nur „vorhanden“ (`any`) gerechnet wird.

**Löffel (EL, TL).** `parseIngredient` erkennt „EL“, „TL“, „Esslöffel“, „Teelöffel“ (auch ohne Leerzeichen, „5EL“) und gibt ihnen eine Menge in ml (`SPOON_ML`: EL 15, TL 5) mit `spoon: true`. Die Art bleibt `soft`: Fehlt die Zutat im Vorrat, gilt sie wie bisher als „nicht im Vorrat erfasst“ und kommt nicht auf die Liste. Ist sie im Vorrat, rechnet `amtNeed`: Flaschen in ml direkt, Pulver in g über `elgOf(a)` (eigener Wert `a.elg`, sonst `elTable(name)`). Geht es nicht, bleibt es bei „vorhanden“, und `why` sagt warum (`size`: Packungsgröße fehlt, `weight`: Gewicht pro EL fehlt). Das geplante Gericht zeigt dann „Menge ungeprüft …“ als Link in den Artikel.

Die Gewichte kommen in drei Stufen: `EL_TABLE` (rund 100 Begriffe, Wortanfang oder Wortende, längster gewinnt, gilt sofort), `EL_RULES` (Wortteile wie „mehl“, „gewürz“, „flocken“, nur als Vorschlag zum Übernehmen) und `EL_FEEL` (Auswahl „wie Kräuter / Gewürzpulver / Mehl / Zucker / Salz“). Namen mit Paste, Sauce, Öl, Sirup und Ähnlichem (`EL_SKIP`) bekommen keinen Wert aus Tabelle oder Regel. Im Artikel steht der Abschnitt „Für Rezepte“ (`recipeField`) nur, wenn ein Rezept den Artikel in g, ml, EL oder TL braucht oder es schon einen Wert oder Vorschlag gibt. Dort lässt sich auch die Packungsgröße für vorhandene Einheiten ohne Größe nachtragen. Beim Kochen werden Löffel-Mengen wie jede andere Menge ausgetragen.

**Zählart „nur melden“ (`mode: 'flag'`).** Für Dinge, bei denen sich Abhaken nicht lohnt (Salz, Gewürze, Klopapier). Der Stand ist da, wird knapp oder aus (`flagState`): da = genau ein Lot mit `qty: 1` (trägt Einkaufs- und Haltbarkeitsdaten), knapp = zusätzlich `low: true`, aus = keine Lots. `setFlag` setzt den Stand; aus zählt im Verlauf als verbraucht. Knapp und aus gelten als „unter Mindestbestand“ (`belowMin`) und kommen damit von selbst auf die Einkaufsliste; `addStock` macht den Artikel wieder „da“, egal ob über Einkaufsliste, Scanner oder „+“. Rezepte prüfen nur „vorhanden“ (`ingNeed`) und ziehen beim Kochen nichts ab. `consumeOne` auf einem solchen Artikel (etwa beim Scannen „Verbraucht“) meldet ihn als aus. In der Vorratsliste steht statt „−“ ein Knopf „Knapp“, danach „Aus“, dann „+“. Beim Wechsel der Zählart rechnet `convertLots` um (zu „flag“: ein Lot, falls etwas da war).

**Schnell verbrauchen.** Das Blatt „Verbraucht“ (`openQuickUse`, Knopf neben dem Scanner im Vorrat) hat eine sofort aktive Suche. Ohne Suchbegriff zeigt `usualSuspects` die Artikel, die zuletzt und oft verbraucht wurden: Verbrauch im Verlauf des Haushalts (60 Tage, die letzte Woche doppelt) plus die letzten Griffe auf diesem Gerät (`noteUse` in `consumeOne`, `openOne`, `setFlag`; `localStorage` `haushoed:recentUse`, so zählen auch Füllstände und Öffnen). Ein Tipp zieht 1 ab, öffnet oder meldet knapp bzw. aus; das Blatt bleibt offen, `refresh` zeichnet nur die Liste neu, damit die Suche den Fokus behält.

**Kurzbefehle.** `manifest.webmanifest` hat `shortcuts` für langes Drücken auf das App-Symbol (Android): `?do=use` öffnet „Verbraucht“, `?do=scan-use` und `?do=scan-add` den Scanner im passenden Modus. Ausgewertet wird `LAUNCH` im Abschnitt „Start“, danach verschwindet der Parameter aus der Adresse. Symbole: `docs/icons/shortcut-*.png`.

**Rezeptfilter.** Ein Filter ist `{tags, rate: {uid: {lo, hi}}, prep: {lo, hi}, cook: {lo, hi}}` mit inklusiven Grenzen (`null` = egal). `matchRecipe` prüft: alle Tags, je Person die eigene Bewertung im Bereich (wer nicht bewertet hat, fällt heraus, sobald für diese Person ein Bereich gesetzt ist), Arbeits- und Kochzeit im Bereich (ohne Zeitangabe fällt das Rezept heraus). Der aktive Filter liegt pro Gerät in `UI.tagFilter` und `UI.rf`; das Blatt `openRecipeFilter` stellt ihn ein, die Liste zeigt eine Zusammenfassung (`filterText`) und „Filter löschen“. Gespeicherte Filter liegen im Haushaltsdokument unter `filters.<uid>` (Liste `{id, name, ...Filter}`, höchstens 20), geschrieben als Teil-Update nur des eigenen Felds (`saveMyFilters`). Sie erscheinen als Chips über den Tags; ein Tipp wendet an, nochmal tippen hebt auf (`sameFilter` vergleicht über `normFilter`). Umbenennen oder Löschen eines Tags zieht gespeicherte Filter aller Personen nach (`fixSavedTags`). „Tags verwalten“ sitzt jetzt im Filter-Blatt.

**Rollen (Kinder).** `households/{hid}.roles = {uid: 'child'}`, sonst erwachsen. Erwachsene vergeben die Rolle unter „Mehr → Euer Haushalt“ (`setRole`, Teil-Update `roles.<uid>`); sich selbst kann man nicht umstellen, ein Kind gar niemanden. `kid()` liest die Rolle aus `HH.data`, beim Start vor dem Laden aus `localStorage` (`haushoed:kid`), damit ein Kind nie kurz die ganze App sieht. In der Kinderansicht (`body.kid`) gibt es nur „Kochen“ ohne Reiterleiste: Wochenplan zum Ansehen (ohne Planen, ohne Portionen und „fehlt“), Wünsche mit Abstimmen (ohne Einplanen), Rezepte ohne Portionen, Zeiten, Zubereitung und Vorrat (`openRecipeKid`, `kidIngredients`: die Zutatenzeilen, wie sie im Rezept stehen). Bewerten und Filtern (ohne Zeiten) gehen. `openRecipe` und `openMeal` leiten für Kinder auf die Kinderansicht um; die zentrale Klickbehandlung lässt Vorrats- und Planungsaktionen für Kinder ins Leere laufen; Wischen bleibt in „Kochen“, Kurzbefehle wirken nicht. Wird jemand zum Kind, schließt ein offenes Blatt. Die Sperre gilt in der App; die Firestore-Regeln unterscheiden nicht nach Rollen, und Lesen lässt sich in Firestore ohnehin nicht feldweise einschränken.

**Bewertung, Zeiten, Tags.** Jede Person bewertet ein Rezept mit 1 bis 5 Sternen; nochmal auf den eigenen Stern tippen nimmt die Bewertung zurück (Wert 0). `rateRecipe` schreibt wie die Stimmen nur `ratings.<uid>`. Beim Speichern des Rezepts übernimmt `collect` die Bewertungen aus dem aktuellen Stand von `S.recipes`, damit eine Bewertung, die inzwischen jemand anderes abgegeben hat, nicht verloren geht. Tags gibt es, solange ein Rezept sie hat (`allTags`); Groß- und Kleinschreibung zählt nicht, es gilt die Schreibweise, in der es den Tag zuerst gab. In „Rezepte“ filtern Chips nach Tags (`UI.tagFilter`, mehrere zusammen heißt: alle müssen passen). Die Liste zeigt Schnitt der Bewertungen, Gesamtzeit und Tags und lässt sich nach A–Z, Bewertung oder Zeit sortieren (`sortRecipes`, pro Gerät gemerkt unter `haushoed:recipeSort`; Unbewertetes bzw. Rezepte ohne Zeit stehen am Ende). Auch beim Einplanen (`openPicker`) und Wünschen (`openWishPicker`) gibt es den Tag-Filter, dort jeweils eigen und nur für dieses Blatt (`tagChipsHTML`, `toggleIn`).

**Tags verwalten.** `openTagManager` listet alle Tags mit der Zahl ihrer Rezepte. `renameTag` benennt in allen Rezepten um; heißt der neue Name wie ein anderer Tag, werden beide zusammengeführt. `deleteTag` entfernt einen Tag überall. Beide schreiben über `setTagsMany` nur das Feld `tags` (Teil-Update) und bieten „Rückgängig“.

**Vorrat zuklappen.** Kategorien lassen sich über ihre Überschrift auf- und zuklappen (`toggleCat`). Gemerkt wird das pro Gerät in `localStorage` (`haushoed:collapsed`), nicht im Haushalt. Beim Suchen und beim Filter „prüfen“ ist alles offen. Zugeklappt zeigt die Überschrift die Zahl der Artikel und wie viele davon zu prüfen sind.

**Wischen.** Im Bereich „Kochen“ wechselt Wischen zuerst zwischen Wochenplan, Wünschen und Rezepten (`COOK_VIEWS`), erst am Rand in den nächsten Bereich. Wer von links nach „Kochen“ wischt, landet beim Wochenplan, von rechts bei den Rezepten.

**Wunschliste.** Pro Person höchstens 7 eigene Wünsche (`WISH_MAX`), jedes Rezept nur einmal (Dokument-ID = Rezept-ID). Wer sich etwas wünscht, stimmt automatisch dafür. Nochmal Tippen nimmt eine Stimme zurück. `planRecipe` plant ein Gericht ein und nimmt es dabei von der Wunschliste. Alle Wege zum Einplanen laufen über diese Funktion.

**Barcodes.** Android-Chrome nutzt den eingebauten `BarcodeDetector`, alle anderen die ZXing-Bibliothek aus `docs/vendor/`, die erst beim ersten Scannen geladen wird. Unbekannte Codes werden bei Open Food Facts nachgeschlagen (dazu Open Beauty Facts und Open Products Facts). Angaben wie „6 x 0,5 l“ oder „3 Stk“ werden als Menge pro Scan übernommen.

**Zurück-Taste.** Solange ein Blatt offen ist, liegt genau ein eigener Eintrag im Browserverlauf (`HIST`). Beim Schließen wird er erst entfernt, wenn danach wirklich kein Blatt mehr offen ist. So bleibt der Verlauf auch bei Blatt-zu-Blatt-Wechseln richtig.

## Konventionen

Nach jeder Änderung an Dateien in `docs/` die Zahl in `VERSION` in `docs/sw.js` erhöhen, sonst bekommen installierte Apps die neue Version nicht.

Datenänderungen am Bestand alter Daten gehören in `migrate()` (mit Versionsnummer `meta.v`), Aufräumarbeiten in `housekeeping()`.

Texte in der App sind Deutsch (Österreich), in der Du-Form, ohne Fachbegriffe. Meldungen nach Änderungen bieten möglichst „Rückgängig“ an.

## Testen

Im Ordner `tests/` liegt `fakefb.js`, ein kleines Firestore-Imitat. Es ersetzt `window.HFB`, zählt Lesezugriffe und protokolliert Schreibvorgänge. `plan_und_wuensche.py` spielt damit in einem Headless-Chromium (Playwright) einen Haushalt mit zwei Personen durch: Start, Archiv, Tagesansicht eines Gerichts, Einkaufsliste, Wunschliste mit Abstimmen und Limit, Einplanen aus der Liste, Speicher voll. `loeffel.py` prüft EL und TL: Tabelle und Regeln für viele Namen, Flasche in ml, Pulver in g, Vorschlag übernehmen, fehlende Packungsgröße nachtragen und das Austragen beim Kochen. `abgleich.py` prüft den Abgleich nur der Änderungen: Lesezugriffe beim ersten und zweiten Start, Änderungen und Löschen von einem anderen Gerät, während die App zu war, Live-Änderungen, ein altes Gerät ohne Zeitstempel, das Aufräumen alter Lösch-Markierungen, den Knopf „Alles neu abgleichen“ und einen gelöschten Zwischenspeicher. `fakefb.js` zählt Lesezugriffe wie Firebase, kennt Serverzeit und Abfragen auf `updated`, behält den Datenbestand über ein Neuladen (`sessionStorage`) und kann mit `FAKE.mute` ein geschlossenes Gerät nachstellen. `kinder.py` prüft den Rezeptfilter (Bewertungen einzelner Personen, Tags, Arbeits- und Kochzeit, speichern, anwenden, aufheben, Tag umbenennen) und die Kinderrolle (vergeben, Ansicht eines Kindes in Plan, Gericht, Rezepten, Wünschen, Filter, Wischen, Kurzbefehl, Start vor dem Laden, Rolle live zurücknehmen). `schnell.py` prüft die Zählart „nur melden“ (Knöpfe, Einkaufsliste, Rezepte, Kochen, Rückgängig, Bearbeiten-Blatt, Wechsel der Zählart), das Blatt „Verbraucht“ (Fokus, Vorschläge, Verbrauchen, Öffnen, Suche) und die Kurzbefehle. `rezepte.py` prüft Bewertungen zweier Personen, Zeiten, Tags samt Filter, das Zuklappen im Vorrat, das Wischen in „Kochen“, Sortieren, Tags verwalten (umbenennen, zusammenführen, löschen, rückgängig) und den Tag-Filter beim Einplanen und Wünschen.

Für Scanner-Tests eignet sich Chromium mit `--use-fake-device-for-media-stream --use-file-for-fake-video-capture=<datei.y4m>`; ein solches Video mit einem Barcode lässt sich mit Python (Pillow) und `ffmpeg` erzeugen. Open Food Facts lässt sich in Playwright mit `context.route` beantworten.

## Verlauf

- **Barcode-Scanner:** Scannen zum Einräumen, Verbrauchen und Nachschauen, Open Food Facts, Barcodes als lernbare Zuordnung, Menge pro Scan (z. B. 3er-Pack).
- **Bedienung:** Zurück-Taste schließt Blätter, Wischen zwischen den Bereichen, Meldungen wegwischen.
- **Vorrat:** Neu anlegen auch mit Menge 0. „Öffenbar“ mit eigenen Fristen für geöffnete Einheiten; öffnen im Artikel oder durch langes Drücken auf „−“ in der Liste.
- **Firebase:** Start liest jede Sammlung nur noch einmal, alte Plan-Einträge werden archiviert, Warnung bei vollem Gerätespeicher.
- **Filter und Kinder:** Rezepte nach Bewertungen einzelner Personen, Tags und Zeiten filtern, Filter pro Person speichern; Kinderrolle mit eigener Ansicht.
- **Weniger abhaken:** Zählart „nur melden“, Blatt „Verbraucht“ mit Vorschlägen, Kurzbefehle am App-Symbol.
- **Firebase sparen:** Beim Start nur noch Änderungen lesen statt alles (Serverzeit in `updated`, Lösch-Markierungen, vollständiger Abgleich alle 3 Tage).
- **Rezepte, Teil 2:** Sortieren nach A–Z, Bewertung, Zeit; Tag-Filter beim Einplanen und Wünschen; Tags für alle Rezepte umbenennen, zusammenführen und löschen.
- **Rezepte:** Sterne pro Person, Arbeits- und Kochzeit, eigene Tags mit Filter. Vorrat: Kategorien zuklappbar. Kochen: Wischen wechselt zuerst innerhalb des Bereichs.
- **Löffel:** EL und TL werden gegen den Vorrat gerechnet, mit Gewichtstabelle für Pulver, Vorschlägen und Auswahl nach Gefühl; Hinweis im Gericht, wenn eine Menge nicht geprüft werden kann.
- **Kochen:** Wunschliste mit Abstimmen; geplante Gerichte zeigen, was an ihrem Tag da ist, geprüft oder nachgekauft werden muss. Die Einkaufsliste berücksichtigt, was bis zum Kochtag abläuft.

## Offene Ideen

- Kinderrolle auch in den Firestore-Regeln absichern (Kinder dürfen dann nur noch die eigene Bewertung, Wünsche und Stimmen schreiben); braucht vorher einen Test mit dem Firestore-Emulator.

- Stück-Artikel automatisch als geöffnet markieren, wenn man etwas davon verbraucht (bei Füllständen passiert das schon).
- Bilderkennung (Einkauf fotografieren, Kassenbon, Inventur per Foto), etwa über Gemini mit Firebase AI Logic; Datenschutz des kostenlosen Tarifs beachten.


- Rezept in Gramm, Vorrat in Milliliter (etwa „200 g Sahne“ gegen einen 250-ml-Becher): wird noch nicht umgerechnet. `amtNeed` hat dafür schon die Stelle; es fehlt ein Wert „1 EL wiegt“ für Flüssigkeiten samt passender Auswahl (Öl, Wasser, Honig).

- Scanner im Einkauf: Artikel durch Scannen auf der Liste abhaken.
- Archivierte Gerichte nutzen, z. B. „zuletzt gekocht am …“ im Rezept oder Vorschläge für lange nicht Gekochtes.
- Verlauf (`log.events`) für Statistiken über mehr als einen Monat nutzen.
- Hinweis, wenn das Firebase-Tageslimit näher rückt (derzeit nur eine Meldung, wenn es erreicht ist). Mit dem Änderungs-Abgleich ist das deutlich unwahrscheinlicher geworden.
