# Haushöd

Vorrat, Einkauf und Kochen für euren Haushalt. Eine installierbare Web-App (PWA), gehostet auf GitHub Pages, mit Daten in Firestore (Firebase Spark-Plan, kostenlos).

## Aufbau

| Pfad | Inhalt |
| --- | --- |
| `docs/index.html` | die ganze App (Oberfläche, Logik, Firebase-Anbindung) |
| `docs/sw.js` | Service Worker, damit die App offline startet |
| `docs/manifest.webmanifest`, `docs/icons/` | Name, Farben und Icons für die Installation am Handy |
| `firestore.rules` | Sicherheitsregeln: nur Mitglieder sehen ihren Haushalt |
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

## Updates veröffentlichen

Geänderte Dateien in `docs/` auf GitHub ersetzen (im Browser per Upload oder per `git push`). GitHub Pages veröffentlicht automatisch, meist innerhalb weniger Minuten.

Nach jeder Änderung an der App in `docs/sw.js` die Zahl in `VERSION` erhöhen (z. B. `haushoed-v3`). Dann holen sich alle Geräte die neue Version, sobald sie die App das nächste Mal öffnen.

Geänderte Sicherheitsregeln werden nicht über GitHub veröffentlicht, sondern wie in Schritt 2.3 in der Firebase-Konsole eingefügt.
