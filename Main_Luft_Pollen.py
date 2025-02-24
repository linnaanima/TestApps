import streamlit as st
import matplotlib.pyplot as plt
from Pollen import get_pollen_data
from datetime import datetime, timedelta

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
