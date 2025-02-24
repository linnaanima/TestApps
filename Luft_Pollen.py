import streamlit as st
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # Verhindert Probleme mit dem GUI-Backend in Streamlit
from datetime import datetime, timedelta
import requests



def get_pollen_data(region_id):
    try:
        response = requests.get("https://opendata.dwd.de/climate_environment/health/alerts/s31fg.json")
        
        if response.status_code != 200:
            print(f"❌ Fehler beim Abruf der DWD-Daten: {response.status_code}")
            return None

        data = response.json()
        pollen_vorhersage = []

        # 🔍 Suche nach der richtigen Region
        for region in data.get("content", []):
            if str(region.get("region_id")) == region_id:
                region_name = region.get("region_name", "Unbekannte Region")
                print(f"\n📍 Region: {region_name} (Kiel)")

                pollen_daten = region.get("Pollen", {})
                for pollenart, werte in pollen_daten.items():
                    pollen_vorhersage.append({
                        "Pollenart": pollenart,
                        "Heute": werte.get("today", "-1"),
                        "Morgen": werte.get("tomorrow", "-1"),
                        "Übermorgen": werte.get("dayafter_to", "-1")
                    })

                return pollen_vorhersage

        print("⚠️ Keine Pollen-Daten für diese Region gefunden.")
        return None

    except Exception as e:
        print(f"❌ Fehler beim Verarbeiten der DWD-Daten: {e}")
        return None


# 🔥 Starte die Abfragen
#pollen_info = get_pollen_data(REGION_ID)

# 📊 Ausgabe der Pollen- und Luftqualitätsbelastung
#if pollen_info:
    #print("\n🌿 Pollenflug-Vorhersage für Kiel:")
    #for pollen in pollen_info:
        #print(f"➡️ {pollen['Pollenart']}: Heute {pollen['Heute']}, Morgen {pollen['Morgen']}, Übermorgen {pollen['Übermorgen']}")''

st.title("🌿 Luft Live – PollenData")


# Verfügbare Regionen (ohne Unterregionen)
regions = {
    "Schleswig-Holstein und Hamburg": "10",
    "Mecklenburg-Vorpommern": "20",
    "Niedersachsen und Bremen": "30",
    "Nordrhein-Westfalen": "40",
    "Brandenburg und Berlin": "50",
    "Sachsen-Anhalt": "60",
    "Thüringen": "70",
    "Sachsen": "80",
    "Hessen": "90",
    "Rheinland-Pfalz und Saarland": "100",
    "Baden-Württemberg": "110",
    "Bayern": "120",
}

# Auswahlmenü für Regionen
selected_region = st.selectbox("🌍 Wähle eine Region", list(regions.keys()))
region_id = regions[selected_region]

# Hole die Polleninformationen
pollen_info = get_pollen_data(region_id)

def parse_pollen_value(value):
    if '-' in value:
        parts = value.split('-')
        return (float(parts[0]) + float(parts[1])) / 2
    return float(value) if value != '0' else 0

def assess_pollen_level(value):
    if value == 0:
        return 'Keine Belastung'
    elif value == 0.5:
        return 'Geringe Belastung'
    elif value == 1:
        return 'Gering'
    elif value == 1.5:
        return 'Gering'
    elif value == 2:
        return 'Mäßig'
    elif value == 2.5:
        return 'Mäßig'
    elif value == 3:
        return 'Stark'
    else:
        return 'Stark'

# Zeige das aktuelle Datum und Uhrzeit an
current_datetime = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
st.header(f" {current_datetime}")

# Diagramm im Darkmode (schwarzer Hintergrund)
plt.style.use('dark_background')

# Definiere die Tage für das Diagramm
today = datetime.today()
date_labels = [today.strftime('%d.%m.'), (today + timedelta(days=1)).strftime('%d.%m.'), (today + timedelta(days=2)).strftime('%d.%m.')]

# Falls keine Daten vorhanden sind
if not pollen_info:
    st.error("⚠️ Keine Pollen-Daten verfügbar für diese Region!")
else:
    for pollen in pollen_info:
        st.write(f"➡️ **{pollen['Pollenart']}**: Heute {pollen['Heute']}, Morgen {pollen['Morgen']}, Übermorgen {pollen['Übermorgen']}")

        # Extrahieren und Parsen der Daten für das Diagramm
        pollen_types = ['Heute', 'Morgen', 'Übermorgen']
        pollen_values = [parse_pollen_value(pollen[type]) for type in pollen_types]

        # Anzeige der aktuellen Pollenbelastung mit Bewertung
        today_level = assess_pollen_level(pollen_values[0])
        st.write(f" **Aktuelle Pollenbelastung heute:** {pollen_values[0]} ({today_level})")

        # Diagramm erstellen
        max_value = max(pollen_values) + 1  # Damit das Diagramm über den höchsten Wert hinaus geht
        plt.plot(date_labels, pollen_values, marker='o', linestyle='-', label=pollen['Pollenart'])

    plt.xlabel('Datum')
    plt.ylabel('Pollenwerte')
    plt.title(f"Pollenbelastung in {selected_region}")
    plt.ylim(0, 3)  # y-Achse so setzen, dass der höchste Wert passt
    plt.legend()
    
    # Diagramm anzeigen
    st.pyplot(plt)
