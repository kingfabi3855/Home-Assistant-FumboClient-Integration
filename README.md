# Home-Assistant-FumboClient-Integration

**FumboClient direkt mit Home Assistant verbinden – ohne MQTT, Mosquitto oder separates Serverprogramm.**

Made by Fumbo.

> **Integration 0.1.0:** Benötigt FumboClient ab **1.24.0** mit lokaler API v1.
> [Client herunterladen](https://github.com/kingfabi3855/FumboClient/releases/tag/v1.24.0).
> Ältere Client-Versionen funktionieren damit nicht.
> Dieses Repository enthält nur die Home-Assistant-Integration, keine
> Minecraft-JAR und keinen Client-/Link-Backend-Quellcode.

## So funktioniert es

```text
Home Assistant + FumboClient-Integration
                 │
                 └── HTTP im Heimnetz, mit Kopplungstoken
                                    │
                       Minecraft + FumboClient
                       eingebauter Server :25809
```

Minecraft muss laufen. Die Integration ist kein eigener Bot und startet weder
Minecraft noch deinen Computer. Es gibt keine Cloud-Verbindung.

## Installation über HACS

1. In HACS **Benutzerdefinierte Repositories / Custom repositories** öffnen.
2. `https://github.com/kingfabi3855/Home-Assistant-FumboClient-Integration` hinzufügen,
   Kategorie **Integration** wählen.
3. **FumboClient** herunterladen und Home Assistant neu starten.
4. Anschließend unter **Einstellungen → Geräte & Dienste → Integration hinzufügen**
   nach **FumboClient** suchen.

Das Repository ist als benutzerdefiniertes HACS-Repository vorgesehen. Eine
Veröffentlichung hier bedeutet **keine automatische Aufnahme in den offiziellen
HACS-/Marketplace-Katalog**. Dafür ist eine gesonderte Einreichung nötig.

Ohne HACS: Den Ordner `custom_components/fumboclient` nach
`config/custom_components/fumboclient` kopieren und HA neu starten.
Für die Laufzeit werden keine zusätzlichen Python-Pakete installiert
(`requirements: []`). Voraussetzung ist Home Assistant ab 2025.8; CI prüft die
aktuelle unterstützte Testversion, siehe `requirements_test.txt`.

## Im Minecraft-Client

1. FumboClient ab 1.24.0 mit lokaler API installieren.
2. **H → Einstellungen → Home Assistant** öffnen.
3. **Integration: AN** wählen. Läuft HA auf einem anderen Gerät, **Erreichbar: LAN**
   aktivieren. Standard ist aus Sicherheitsgründen nur der eigene PC.
4. Port standardmäßig **25809** lassen. Optional die erlaubte Home-Assistant-IP
   einschränken; leer erlaubt authentifizierte Zugriffe aus dem privaten Netz.
5. **Speichern & Anwenden**, dann **Token kopieren**.
6. In Home Assistant die **LAN-IP des Minecraft-PCs**, Port und Token eingeben.

Keine Home-Assistant-Admin-Zugangsdaten und keine Minecraft-/Microsoft-Passwörter
eintragen. Die Kopplung verwendet einen vom Client erzeugten zufälligen Token.
Änderungen werden erst mit „Speichern & Anwenden“ aktiv.

**Wichtig bei Containern:** `localhost` bezeichnet innerhalb von HA in der Regel
den HA-Container und nicht den Minecraft-PC. Auch bei demselben physischen Rechner
kann deshalb die LAN-IP und LAN-Freigabe erforderlich sein. Nur explizite private
IP-Adressen/Loopback sind erlaubt, keine Domains, URLs oder öffentliche IPs.
Firewall ggf. **nur im privaten Netz** für den Client-Port freigeben. Es werden
keine Firewall-Regeln automatisch angelegt.

## Funktionen

Je nach lokalen Freigaben bis zu **39 native HA-Entitäten**:

| Bereich | Inhalt |
|---|---|
| Basis | In einer Welt, AFK, Zeit ohne Eingabe, Sitzungsdauer |
| Vitalwerte | Leben, maximales Leben, Hunger, Rüstung, Luftvorrat, lebendig, brennt, Warnschwellen, XP |
| Leistung | FPS und Ping |
| Optionales Inventar | Freie Plätze, Inventar voll, Werkzeug-Haltbarkeit der Haupthand |
| Optionale Standortdaten | Dimension und Blockkoordinaten |
| Optionale Serverdaten | Aktuelle Serveradresse |
| Helfer | Vorhandene AutoEat-/AutoSell-/AutoFish-/AutoBreak-/AutoReplant-Helfer und Warnungen schalten |
| Steuerung | Helfer stoppen, Mehrspieler-Verbindung verlassen, AFK-Modus wählen, Cosmetics-Anzeige schalten |
| Hinweis | Kurzer Text ausschließlich lokal im Minecraft-Chat, nicht an den Spielserver |
| Ereignisse | Join/Leave, AFK, Schaden, Tod, wenig Leben/Hunger, Werkzeugwarnung, volles Inventar, Feuer |

Fernsteuerung ist standardmäßig **AUS**. In Minecraft müssen der Master-Schalter
**und** die jeweilige Rechtekategorie aktiviert werden. HA kann diese Freigaben
nicht selbst erteilen. Neu freigegebene Entitäten erscheinen beim nächsten
Aktualisieren; widerrufene Entitäten werden nicht verfügbar. Alte Registry-Einträge
werden nicht automatisch gelöscht, um Benennungen und Historie zu erhalten.

Die Schalter spiegeln die **konfigurierte** Aktivierung wider. Bestehende
Serverbeschränkungen der Helfer bleiben erhalten. Beachte die Serverregeln.
Helferänderungen bleiben in der normalen Client-Konfiguration gespeichert.

AFK ist eine Statusfunktion, **kein Anti-AFK-Bot**. Sie erzeugt keine Bewegung.
Leben/Hunger sind Minecraft-Punkte: 6 Lebenspunkte entsprechen normalerweise
3 Herzen. Der Luftvorrat wird in Minecraft-Ticks angegeben. Die Integration liest
keine privaten Chatverläufe. Ein leerer/nicht abnutzbarer Gegenstand meldet 100 %
Haltbarkeit; „Inventarplätze“ meint die 36 normalen Inventar-/Hotbar-Slots.

## Automationen

Das Event-Entity bietet diese `event_type`-Werte:

```text
joined, left, afk_on, afk_off, damage, death,
low_health, low_hunger, tool_low, inventory_full, fire
```

Beispiele: Push-Nachricht bei Schaden, Licht bei wenig Leben, Inventarwarnung,
lokaler Hinweis von der Türklingel oder ein bewusst freigegebener Not-Stopp.
Eine Smartphone-Benachrichtigung benötigt wie üblich die HA-Companion-App.
Die Integration selbst benötigt keinen zusätzlichen Dienst.

In HA ein passendes Event-/Sensor-Entity als Auslöser wählen und eigene Aktionen
hinzufügen. Die genauen Entity-IDs hängen vom Gerätenamen und der HA-Registry ab.
Der optionale Blueprint liegt unter `blueprints/fumboclient-events.yaml`.
Er löst erst nach Auswahl deiner gewünschten Aktionen etwas aus.

Historische Events werden beim Einrichten und nach einem Client-Neustart nicht
erneut ausgelöst. Im Betrieb enthält die API höchstens 64 gepufferte Ereignisse;
bei längeren Ausfällen können Ereignisse fehlen. Es werden Zustände einmal pro
Sekunde abgetastet, keine lückenlose Echtzeit-Sicherheitsüberwachung versprochen.
Aufgrund deaktivierter Sensorkategorien nicht erhobene Warnungen entfallen.

## Sicherheit, Datenschutz und Grenzen

- Kein MQTT, kein Zusatz-Server, kein HACS-Add-on nötig: Der HTTP-Server ist im
  Minecraft-Client eingebaut und standardmäßig deaktiviert.
- Nur Loopback bzw. ausdrücklich freigegebenes privates Heimnetz. Keine
  Portfreigabe, öffentliche URL oder Internet-Weiterleitung einrichten.
- HTTP ist **unverschlüsselt**. Token und Daten ausschließlich in einem
  vertrauenswürdigen LAN verwenden. Diese Version bietet kein eingebautes TLS.
- API-Token nie öffentlich posten. Er liegt auf dem Minecraft-PC separat in
  `config/fumboclient/home-assistant-token.json` und in HAs geschützter
  Konfigurationsspeicherung. Die Datei ist nicht verschlüsselt: Betriebssystem-
  Dateirechte und Backups schützen. Nicht mit Client-Konfigurationen weitergeben.
- **Token erneuern → Speichern** widerruft die alte Kopplung. HA bietet eine
  erneute Anmeldung; IP und Port können über „Neu konfigurieren“ geändert werden.
- Erlaubte Kommandos, kurze Warteschlange, Sitzungsbindung und Request-IDs
  verhindern alte/versehentlich doppelte Steueraufträge. API-Server greift nie
  direkt aus HTTP-Threads auf die Minecraft-Welt zu.
- Kommandos werden bestätigt, nicht bloß als erfolgreich angenommen. Nach einem
  Timeout **nicht blind wiederholen**, da eine Aktion bereits ausgeführt sein kann.
- Kein freier Chat, keine Shell, keine Dateizugriffe und keine Account-Anmeldung.
- Nur explizit freigegebene Positions-/Server-/Inventardaten werden ausgegeben.
  HA kann empfangene Daten in seiner eigenen Historie speichern. Diagnosen
  enthalten weder Token/IP noch Standort, Serveradresse oder Hinweistext.
- Wenn Minecraft aus ist, ist das Gerät nicht verfügbar. Hängt der Client-Thread,
  werden alte Zustände nach 15 Sekunden als nicht verfügbar behandelt.
- Mehrere Instanzen brauchen getrennte Minecraft-Spielverzeichnisse mit eigenen
  Geräte-IDs und, auf demselben Rechner, unterschiedlichen API-Ports.

## Fehlerbehebung

| Problem | Prüfen |
|---|---|
| Nicht erreichbar | Passender neuer Client läuft, Integration AN, gespeichert, richtige PC-IP/Port, LAN-Freigabe, Firewall |
| Token ungültig / Zugriff verweigert | Aktuellen gespeicherten Token kopieren; optionale HA-IP-Freigabe prüfen |
| Port belegt | Anderen freien Port im Client einstellen und in HA neu konfigurieren |
| Keine Schalter | Master-Fernsteuerung und gewünschte Kategorie im Client speichern |
| Neue Entität nicht sichtbar | Poll abwarten; ggf. in der HA-Entitätenliste prüfen |
| HACS findet das Repository nicht | Als **Integration** unter benutzerdefinierten Repositories hinzufügen |
| Client 1.23.1 | Inkompatibel; auf FumboClient 1.24.0 oder neuer aktualisieren |

## Entwicklung

`python -m unittest discover -s tests -p test_api.py` prüft die eigenständige
HTTP-Client-Implementierung. Die GitHub-Actions-Prüfung testet zusätzlich gegen
echtes Home Assistant auf Linux und führt Hassfest aus. Ein erfolgreicher Build
ersetzt keinen Test mit deiner konkreten Minecraft-/HA-/Firewall-Installation.

Lizenz: MIT **für diese Integration**. Daraus folgt keine Open-Source-Lizenz für
FumboClient oder sein Backend. Minecraft ist ein Produkt von Mojang/Microsoft;
dies ist kein offizielles Minecraft-Produkt und keine offizielle HA-Core-Integration.
