import csv
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# 1. Konfiguration für Mailversand
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = "dein.email@gmail.com"         # ✅ ersetzen!
SMTP_PASS = "dein_app_passwort"            # ✅ ersetzen!

# 2. Hole DWD-Daten
def get_pollen_data():
    try:
        url = "https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json"
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Fehler beim Abrufen: {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        print(f"Fehler: {e}")
        return None

# 3. Extrahiere die Daten für Region + Pollenarten
def extract_user_pollen_data(data, region_id, pollen_filter):
    result = []
    for region in data.get("content", []):
        if str(region.get("region_id")) == str(region_id):
            pollen_daten = region.get("Pollen", {})
            for pollenart, werte in pollen_daten.items():
                if pollenart in pollen_filter:
                    result.append({
                        "Pollenart": pollenart,
                        "Heute": werte.get("today", "-"),
                        "Morgen": werte.get("tomorrow", "-"),
                        "Übermorgen": werte.get("dayafter_to", "-")
                    })
    return result

# 4. E-Mail senden
def send_email(recipient, subject, html_body):
    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = recipient

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

# 5. Benutzer durchgehen und E-Mails senden
def main():
    data = get_pollen_data()
    if not data:
        return

    with open("userdata/subscribers.csv", newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 3:
                continue
            email, region_id, pollen_str = row[0], row[1], row[2]
            pollenarten = pollen_str.split(",")

            pollen_infos = extract_user_pollen_data(data, region_id, pollenarten)
            if not pollen_infos:
                continue

            today = datetime.now().strftime('%d.%m.%Y')
            html = f"<h2>🌿 Pollenprognose für {today}</h2><ul>"
            for pollen in pollen_infos:
                html += f"<li><strong>{pollen['Pollenart']}</strong>: Heute {pollen['Heute']}, Morgen {pollen['Morgen']}, Übermorgen {pollen['Übermorgen']}</li>"
            html += "</ul><p>🔁 Automatischer Pollenservice – abbestellen: antworten mit 'STOP'.</p>"

            try:
                send_email(email, "🌿 Deine tägliche Pollenwarnung", html)
                print(f"✅ E-Mail gesendet an {email}")
            except Exception as e:
                print(f"❌ Fehler beim Senden an {email}: {e}")

if __name__ == "__main__":
    main()
