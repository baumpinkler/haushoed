# Haushöd

Vorrat, Einkauf und Kochen für euren Haushalt. Eine installierbare Web-App (PWA), gehostet auf GitHub Pages, mit Daten in Firestore (Firebase Spark-Plan, kostenlos).

Konzept mit Datenmodell, Regeln, Architektur und Roadmap: <https://claude.ai/code/artifact/336e5df7-e808-4d8c-8f5e-8584a5187aa4>

**Weitermachen in einem neuen Claude-Chat:** dieses Projekt (ZIP oder Repository) hochladen und kurz schreiben, was als Nächstes ansteht. Den aktuellen Stand mit Aufbau, Datenmodell und offenen Ideen beschreibt `ENTWICKLUNG.md`; das ursprüngliche Konzept unter dem Link oben ist älter.

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `docs/index.html` | die ganze App (Oberfläche, Logik, Firebase-Anbindung) |
| `docs/sw.js` | Service Worker, damit die App offline startet |
| `docs/manifest.webmanifest`, `docs/icons/` | Name, Farben, Icons und Kurzbefehle für die Installation am Handy |
| `docs/vendor/` | Barcode-Erkennung für Geräte ohne eingebauten Scanner (ZXing, MIT-Lizenz). Wird erst beim ersten Scannen geladen. |
| `firestore.rules` | Sicherheitsregeln: nur Mitglieder sehen ihren Haushalt |
| `ENTWICKLUNG.md` | Stand der Entwicklung: Aufbau, Datenmodell, Abläufe, offene Ideen |
| `tests/` | Firestore-Imitat und automatischer Test (wird nicht veröffentlicht) |
| `firebase.json`, `.firebaserc`, `firestore.indexes.json` | nur nötig, wenn du die Regeln per Kommandozeile einspielen willst |

GitHub Pages veröffentlicht den Ordner `docs/`. Alle Pfade in der App sind relativ, sie läuft also unter `https://<dein-name>.github.io/haushoed/` genauso wie unter einer eigenen Domain.

## Einmalig einrichten

### 1. Daten aus dem Prototyp sichern
Im Claude-Prototyp unter „Mehr“ auf **„Sicherung speichern“**.

### 2. Firebase vorbereiten (in der Firebase-Konsole)
1. **Authentication → Anmeldeanbieter → Anonym** aktivieren.
2. **Authentication → Einstellungen → Autorisierte Domains:** `<dein-name>.github.io` hinzufügen.
3. **Firestore Database → Regeln:** den Inhalt von `firestore.rules` komplett einfügen und **Veröffentlichen**.

### 3. Auf GitHub hochladen
1. Auf GitHub ein neues **öffentliches** Repository `haushoed` anlegen (GitHub Pages ist für private Repositories nur in bezahlten Plänen verfügbar).
2. Dateien hochladen, eine der beiden Varianten:
   - **Im Browser:** im leeren Repository „uploading an existing file“, dann den Inhalt dieses Ordners (inklusive `docs`) ins Fenster ziehen und „Commit changes“.
   - **Mit Git:**
     ```
     git init
     git add .
     git commit -m "Haushöd"
     git branch -M main
     git remote add origin https://github.com/<dein-name>/haushoed.git
     git push -u origin main
     ```
3. Im Repository **Settings → Pages:** bei „Build and deployment“ als Quelle **Deploy from a branch**, Branch **main**, Ordner **/docs**, speichern.
4. Nach ein, zwei Minuten ist die App unter `https://<dein-name>.github.io/haushoed/` erreichbar. Die genaue Adresse zeigt GitHub auf derselben Seite an.

### 4. Haushalt anlegen und Daten laden
App öffnen, Namen eingeben, **„Neuen Haushalt anlegen“**, dann unter „Mehr“ auf **„Sicherung laden“** und die Datei aus Schritt 1 wählen.

## Am Handy installieren

- **iPhone:** in Safari öffnen → Teilen-Symbol → „Zum Home-Bildschirm“. Die installierte App hat einen eigenen Speicher, dort also einmal Name und Code eingeben.
- **Android:** in Chrome öffnen → Menü ⋮ → „App installieren“.

## Familie und weitere Geräte

Jedes Gerät meldet sich anonym an, ohne Konto und Passwort. Verbunden werden die Geräte über den **6-stelligen Haushalts-Code**, der in der App unter „Mehr“ steht. Auf einem neuen Gerät Namen und Code eingeben, fertig. „Code teilen“ schickt Code und Link direkt per Messenger.

Werden die Browserdaten gelöscht oder die App entfernt, ist die anonyme Anmeldung dieses Geräts weg. Die Daten bleiben im Haushalt; einfach mit dem Code wieder beitreten.

„Code erneuern“ macht den alten Code ungültig. Bereits verbundene Geräte bleiben verbunden.

## Barcode-Scanner

Im Vorrat neben der Suche. Drei Arten zu scannen:

- **Einräumen:** jeder Scan zählt 1 dazu, ideal nach dem Einkauf oder für die Inventur.
- **Verbraucht:** jeder Scan zieht 1 ab.
- **Nachschauen:** öffnet den Artikel.

Kennt die App einen Barcode noch nicht, schlägt sie ihn bei [Open Food Facts](https://world.openfoodfacts.org) nach (dazu Open Beauty Facts und Open Products Facts). Dann entweder **neu anlegen** oder **einem vorhandenen Artikel zuordnen**, etwa die Bio-Vollmilch der „Milch“. Ab dann erkennt jedes Gerät im Haushalt diesen Barcode sofort. Ein Artikel kann beliebig viele Barcodes haben. Pro Barcode merkt sich die App die Packungsgröße und wie viel ein Scan zählt: Beim Kiwi-3er-Pack zählt ein Scan 3 Stück. Einstellen lässt sich das direkt nach dem Scan unter „Ein Scan zählt“ oder im Artikel bei den Barcodes. Beim Verbrauchen zieht ein Scan immer 1 ab. Barcodes verwalten: im Artikel ganz unten.

An Open Food Facts geht nur die Ziffernfolge des Barcodes, sonst nichts.

Die Kamera braucht HTTPS (GitHub Pages hat das). Android mit Chrome nutzt den eingebauten Scanner, iPhone und andere Browser die Bibliothek in `docs/vendor/`. Das erste Scannen auf einem Gerät braucht einmal Internet, danach geht es auch offline. Auf dem iPhone fragt die installierte App bei jedem Start einmal nach der Kamera; das lässt sich von der App aus nicht ändern.

## Zutaten und Vorrat verbinden

Normalerweise erkennt die App selbst, welcher Vorratsartikel zu einer Zutat passt. Wo das nicht klappt, tippst du in einem Rezept oder geplanten Gericht auf den Stand rechts neben der Zutat. Dort legst du fest, was dafür zählt, auch mehrere Artikel („Nudeln“ = Spaghetti und Penne; gekocht wird der Reihe nach, nachgekauft der erste), legst Fehlendes direkt im Vorrat an oder sagst „nicht im Vorrat führen“ (etwa für Wasser). Das gilt für alle Rezepte mit dieser Zutat und für den ganzen Haushalt.

## Rezepte filtern

Unter „Kochen → Rezepte → Filter“ wählst du pro Person einen Bereich der Sterne (etwa „Nina ab 5 ★“, „Alexander 2 ★“), Tags sowie Arbeits- und Kochzeit von–bis. „Filter speichern“ legt die Auswahl unter einem Namen ab; gespeicherte Filter erscheinen als Chips über der Liste und gelten auf allen deinen Geräten. Die anderen im Haushalt haben ihre eigenen.

## Kinder

Unter „Mehr → Euer Haushalt“ kannst du andere Mitglieder als Kind markieren. Kinder sehen nur „Kochen“: was geplant ist, die Wunschliste (wünschen und abstimmen) und die Rezepte mit Bewertung, Tags und den Zutaten, ohne Portionen, Zeiten, Zubereitung und ohne zu sehen, was im Vorrat ist. Bewerten und filtern können sie, ändern nichts. Die Sperre gilt in der App; wer sich technisch auskennt, könnte sie umgehen.

## Weniger abhaken

**Nur melden, wenn's ausgeht:** Für Salz, Gewürze, Klopapier und Co. im Artikel unter „Mehr Einstellungen → Wie zählst du?“ „Nur melden“ wählen. Dann wird nichts abgehakt; in der Liste steht „Knapp“, später „Aus“, und beides setzt den Artikel auf die Einkaufsliste. Nach dem Einräumen ist er wieder da.

**Verbraucht:** Der Knopf mit dem Minus neben dem Scanner öffnet ein Blatt mit sofort aktiver Suche. Darunter stehen die Dinge, die ihr zuletzt und oft verbraucht habt; ein Tipp zieht 1 ab oder öffnet eine Packung.

**Kurzbefehle (Android):** Langes Drücken auf das App-Symbol bietet „Verbraucht“, „Verbraucht scannen“ und „Einräumen scannen“. Auf dem iPhone gibt es das für Web-Apps leider nicht.

## Rezepte bewerten, Zeiten und Tags

Im Rezept vergibt jede und jeder eigene Sterne (nochmal auf den eigenen Stern tippen nimmt die Bewertung zurück), dazu Arbeits- und Kochzeit in Minuten und beliebige Tags wie „schnell“ oder „vegetarisch“. Tags legt ihr einfach durch Eintippen an, schon vorhandene schlägt die App vor. Unter „Kochen → Rezepte“ lässt sich nach Tags filtern und nach Name, Bewertung oder Zeit sortieren; den Tag-Filter gibt es auch beim Einplanen und Wünschen. Über „Tags verwalten“ benennst du einen Tag für alle Rezepte auf einmal um oder löschst ihn.

## Rezepte mit EL und TL

Zutaten wie „5 EL Sojasauce“ oder „1 TL Curry“ prüft die App gegen den Vorrat, wenn die Packung eine Größe hat. Flaschen in Milliliter rechnet sie direkt (1 EL = 15 ml, 1 TL = 5 ml). Für Pulver in Gramm braucht sie, wie viel ein gestrichener Löffel wiegt: Für rund 100 Zutaten kennt sie den Wert schon, bei anderen schlägt sie einen vor oder lässt dich aussuchen, was sich ähnlich anfühlt (im Artikel unter „Für Rezepte“). Fehlt etwas, zeigt das geplante Gericht „Menge ungeprüft“ mit einem Link zum Nachtragen.

## Wunschliste

Unter „Kochen → Wünsche“ kann sich jede und jeder bis zu 7 Gerichte wünschen und bei den Wünschen der anderen dafür oder dagegen stimmen. Ein Gericht steht nur einmal auf der Liste; wer es sich wünscht, stimmt automatisch dafür. Im Wochenplan steht die gemeinsame Liste oben, nach Stimmen sortiert, und beim Planen eines Tages kommen die Wünsche zuerst. Wird ein Gericht eingeplant, verschwindet es von der Wunschliste.

## Speicher und Firebase-Limits

Der kostenlose Firebase-Plan erlaubt 50.000 Lesezugriffe pro Tag für den ganzen Haushalt. Beim Start holt die App nur, was sich seit dem letzten Mal geändert hat (ein normaler Start kostet etwa 8 Lesezugriffe plus einen je geänderten Eintrag). Alle 3 Tage liest jedes Gerät einmal alles, als Sicherheitsnetz; unter „Mehr → Daten“ geht das auch sofort mit „Alles neu abgleichen“. Plan-Einträge, die älter als 14 Tage sind, wandern in den Monatsverlauf, und Gelöschtes wird nach 30 Tagen endgültig entfernt, damit die Zahl der Einträge nicht mit der Zeit wächst. Wird der Speicher im Browser knapp (etwa 5 MB), zeigt die App unter „Mehr“ einen Hinweis; die Daten bleiben in der Cloud vollständig erhalten.

## Updates veröffentlichen

Geänderte Dateien in `docs/` auf GitHub ersetzen (im Browser per Upload oder per `git push`). GitHub Pages veröffentlicht automatisch, meist innerhalb weniger Minuten.

Nach jeder Änderung an der App in `docs/sw.js` die Zahl in `VERSION` erhöhen (z. B. `haushoed-v3`). Dann holen sich alle Geräte die neue Version, sobald sie die App das nächste Mal öffnen.

Geänderte Sicherheitsregeln werden nicht über GitHub veröffentlicht, sondern wie in Schritt 2.3 in der Firebase-Konsole eingefügt.
