import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
import math

# Seitentitel und Beschreibung
st.title("🚀 Raketenstarts - Weltweit")
st.markdown("Diese App zeigt kommende Raketenstarts und wann sie in verschiedenen Zeitzonen stattfinden.")

# Funktion zum Abrufen von Daten über bevorstehende Raketenstarts
@st.cache_data(ttl=3600)  # Cache der Daten für 1 Stunde
def get_launch_data():
    url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=20&mode=detailed"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Fehler beim Abrufen der Daten: {response.status_code}")
        return None

# Daten abrufen
launch_data = get_launch_data()

# Deutschland-Koordinaten (ungefährer Mittelpunkt)
germany_coords = (51.1657, 10.4515)

# Funktion zur Berechnung der theoretischen Sichtbarkeit
def is_visible_from_germany(launch_site_coords, launch_time_utc):
    # Entfernung zwischen Deutschland und Startort berechnen
    distance_km = geodesic(germany_coords, launch_site_coords).kilometers
    
    # Zeitpunkt des Starts in Deutschland
    german_tz = pytz.timezone('Europe/Berlin')
    launch_time_german = launch_time_utc.astimezone(german_tz)
    
    # Prüfen, ob es nachts ist (grobe Schätzung: zwischen 20:00 und 5:00 Uhr)
    is_night = 20 <= launch_time_german.hour or launch_time_german.hour <= 5
    
    # Berechnung des Elevationswinkels (sehr vereinfacht)
    # Wir nehmen an, dass Raketen bis zu einer Höhe von etwa 200 km sichtbar sein könnten
    earth_radius = 6371  # Erdradius in km
    rocket_height = 200  # angenommene maximale Sichthöhe in km
    
    # Maximale Entfernung, bei der die Rakete über dem Horizont sichtbar sein könnte
    # Basierend auf der Erdkrümmung und der Flughöhe
    max_distance = math.sqrt((earth_radius + rocket_height)**2 - earth_radius**2)
    
    if distance_km <= 1000 and is_night:
        return "Wahrscheinlich sichtbar (bei klarem Nachthimmel)"
    elif distance_km <= max_distance and is_night:
        return "Möglicherweise sichtbar (am Horizont, perfekte Bedingungen nötig)"
    elif distance_km <= 1000 and not is_night:
        return "Eventuell als Kondensstreifen sichtbar (tagsüber)"
    else:
        return "Nicht sichtbar"

# Zeitzonen, die angezeigt werden sollen
timezones = {
    "Deutschland": "Europe/Berlin",
    "UTC": "UTC",
    "US Ostküste": "America/New_York",
    "US Westküste": "America/Los_Angeles",
    "Japan": "Asia/Tokyo",
    "Indien": "Asia/Kolkata"
}

if launch_data:
    # Daten vorbereiten
    launches = []
    for launch in launch_data["results"]:
        # Grundlegende Informationen extrahieren
        name = launch.get("name", "Unbekannt")
        rocket_name = launch.get("rocket", {}).get("configuration", {}).get("name", "Unbekannte Rakete")
        launch_service_provider = launch.get("launch_service_provider", {}).get("name", "Unbekannter Anbieter")
        mission_description = launch.get("mission", {}).get("description", "Keine Beschreibung verfügbar")
        mission_type = launch.get("mission", {}).get("type", "Unbekannter Missionstyp")
        
        # Startzeit und -ort
        launch_time_str = launch.get("net", None)
        if not launch_time_str:
            continue
            
        try:
            launch_time_utc = datetime.fromisoformat(launch_time_str.replace("Z", "+00:00"))
        except ValueError:
            continue
            
        pad_name = launch.get("pad", {}).get("name", "Unbekannter Startplatz")
        location_name = launch.get("pad", {}).get("location", {}).get("name", "Unbekannter Ort")
        country_code = launch.get("pad", {}).get("location", {}).get("country_code", "??")
        
        # Koordinaten des Startorts
        latitude = launch.get("pad", {}).get("latitude")
        longitude = launch.get("pad", {}).get("longitude")
        
        # Prüfen, ob Koordinaten vorhanden sind
        if latitude is not None and longitude is not None:
            launch_site_coords = (float(latitude), float(longitude))
            visibility = is_visible_from_germany(launch_site_coords, launch_time_utc)
        else:
            visibility = "Keine Daten zur Berechnung verfügbar"
            launch_site_coords = None
        
        # Startzeiten in verschiedenen Zeitzonen
        launch_times = {}
        for tz_name, tz_code in timezones.items():
            timezone = pytz.timezone(tz_code)
            local_time = launch_time_utc.astimezone(timezone)
            launch_times[tz_name] = local_time.strftime("%d.%m.%Y, %H:%M:%S")
            
        # Daten für die Liste hinzufügen
        launches.append({
            "name": name,
            "rocket": rocket_name,
            "provider": launch_service_provider,
            "description": mission_description,
            "mission_type": mission_type,
            "pad": pad_name,
            "location": f"{location_name}, {country_code}",
            "coordinates": launch_site_coords,
            "times": launch_times,
            "visibility": visibility,
            "utc_time": launch_time_utc  # Für Sortierung
        })
    
    # Nach Startzeit sortieren
    launches = sorted(launches, key=lambda x: x["utc_time"])
    
    # Wähle einen bestimmten Start aus für Details
    launch_names = [f"{launch['name']} - {launch['times']['Deutschland']}" for launch in launches]
    selected_launch_index = st.selectbox("Wähle einen Raketenstart aus:", 
                                         range(len(launch_names)),
                                         format_func=lambda i: launch_names[i])
    
    selected_launch = launches[selected_launch_index]
    
    # Detailansicht
    st.header(selected_launch["name"])
    
    # Zwei Spalten für Informationen und Karte
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.subheader("Details")
        st.markdown(f"**Rakete:** {selected_launch['rocket']}")
        st.markdown(f"**Anbieter:** {selected_launch['provider']}")
        st.markdown(f"**Missionstyp:** {selected_launch['mission_type']}")
        st.markdown(f"**Startplatz:** {selected_launch['pad']}")
        st.markdown(f"**Standort:** {selected_launch['location']}")
        
        st.subheader("Startzeiten")
        for tz_name, time_str in selected_launch["times"].items():
            st.markdown(f"**{tz_name}:** {time_str}")
            
        st.subheader("Sichtbarkeit von Deutschland")
        st.markdown(f"**{selected_launch['visibility']}**")
        
        if len(selected_launch['description']) > 0:
            st.subheader("Missionsbeschreibung")
            st.markdown(selected_launch['description'])
    
    with col2:
        # Karte mit dem Startort
        if selected_launch["coordinates"]:
            m = folium.Map(location=selected_launch["coordinates"], zoom_start=4)
            folium.Marker(
                location=selected_launch["coordinates"],
                popup=f"{selected_launch['name']}<br>{selected_launch['location']}",
                icon=folium.Icon(icon="rocket", prefix="fa", color="red")
            ).add_to(m)
            
            # Deutschland markieren
            folium.Marker(
                location=germany_coords,
                popup="Deutschland",
                icon=folium.Icon(icon="home", prefix="fa", color="blue")
            ).add_to(m)
            
            # Linie zwischen Deutschland und dem Startort zeichnen
            folium.PolyLine(
                locations=[germany_coords, selected_launch["coordinates"]],
                color="gray",
                weight=2,
                opacity=0.7,
                dash_array="5"
            ).add_to(m)
            
            folium_static(m)
    
    # Tabelle mit allen bevorstehenden Starts
    st.header("Alle bevorstehenden Raketenstarts")
    
    # DataFrame für die Tabelle erstellen
    df_data = []
    for launch in launches:
        df_data.append({
            "Name": launch["name"],
            "Rakete": launch["rocket"],
            "Anbieter": launch["provider"],
            "Standort": launch["location"],
            "Start (DE)": launch["times"]["Deutschland"],
            "Start (UTC)": launch["times"]["UTC"],
            "Sichtbarkeit": launch["visibility"]
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df)
    
    # Hinweis zur Sichtbarkeit
    st.info("""
        **Hinweis zur Sichtbarkeit:** 
        Die Sichtbarkeitsinformationen sind nur grobe Schätzungen basierend auf der Entfernung und Tageszeit. 
        Die tatsächliche Sichtbarkeit hängt von vielen Faktoren ab, einschließlich Wetter, genauer Flugbahn, 
        Startwinkel, Atmosphärenbedingungen und mehr. Für genauere Informationen konsultieren Sie bitte 
        spezialisierte Astronomie-Websites oder Apps.
    """)
    
else:
    st.error("Keine Daten über bevorstehende Raketenstarts verfügbar. Bitte versuche es später erneut.")
