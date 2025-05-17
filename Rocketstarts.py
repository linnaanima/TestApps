import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
import math

# Seitentitel und Beschreibung
st.title("🚀 Raketenstarts - Weltweit")
st.markdown("Diese App zeigt kommende Raketenstarts mit UTC und deutscher Zeit sowie Sichtbarkeit während Umrundungen.")

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

# Funktion zur Berechnung der Sichtbarkeit während Umrundungen
def calculate_orbit_visibility(launch_site_coords, launch_time_utc):
    # Entfernung zwischen Deutschland und Startort berechnen
    distance_km = geodesic(germany_coords, launch_site_coords).kilometers
    
    # Berechne durchschnittliche Orbithöhe (typischerweise zwischen 200km und 400km für LEO)
    orbit_height = 300  # km
    
    # Erdradius in km
    earth_radius = 6371
    
    # Berechne Umlaufzeit (Periode) basierend auf Kepler'schen Gesetzen
    # T² = (4π²/GM) * r³, vereinfacht für typische LEO
    orbit_period_minutes = math.sqrt(((earth_radius + orbit_height)/6700)**3) * 225
    
    # Berechne, wie oft der Orbit über Deutschland führt (grobe Schätzung)
    # Bei LEO typischerweise alle 1-2 Umrundungen
    visibility_frequency = 2  # Sichtbar jede zweite Umrundung
    
    # Berechne die ersten 5 möglichen Sichtbarkeiten
    visibility_times = []
    for i in range(1, 6):
        # Zeit nach i Umrundungen
        orbit_time = launch_time_utc + timedelta(minutes=orbit_period_minutes * i)
        
        # Prüfen, ob diese Umrundung über Deutschland führen könnte
        if i % visibility_frequency == 0:
            # Zeitpunkt in deutscher Zeit
            german_tz = pytz.timezone('Europe/Berlin')
            orbit_time_german = orbit_time.astimezone(german_tz)
            
            # Prüfen, ob es nachts ist (zwischen 20:00 und 5:00 Uhr)
            is_night = 20 <= orbit_time_german.hour or orbit_time_german.hour <= 5
            
            if is_night:
                visibility = "Gute Sichtbarkeit (Nachthimmel)"
            else:
                visibility = "Eingeschränkte Sichtbarkeit (Tageslicht)"
                
            visibility_times.append({
                "umrundung": i,
                "zeit_utc": orbit_time.strftime("%d.%m.%Y, %H:%M:%S"),
                "zeit_de": orbit_time_german.strftime("%d.%m.%Y, %H:%M:%S"),
                "sichtbarkeit": visibility
            })
    
    return visibility_times

# Vereinfachte Zeitzonen-Liste
timezones = {
    "Deutschland": "Europe/Berlin",
    "UTC": "UTC"
}

if launch_data:
    # Daten vorbereiten
    launches = []
    for launch in launch_data["results"]:
        # Grundlegende Informationen extrahieren
        name = launch.get("name", "Unbekannt")
        rocket_name = launch.get("rocket", {}).get("configuration", {}).get("name", "Unbekannte Rakete")
        launch_service_provider = launch.get("launch_service_provider", {}).get("name", "Unbekannter Anbieter")
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
        
        # Startzeiten in den vereinfachten Zeitzonen
        launch_times = {}
        for tz_name, tz_code in timezones.items():
            timezone = pytz.timezone(tz_code)
            local_time = launch_time_utc.astimezone(timezone)
            launch_times[tz_name] = local_time.strftime("%d.%m.%Y, %H:%M:%S")
        
        # Umrundungen und Sichtbarkeit berechnen (falls Koordinaten vorhanden sind)
        if latitude is not None and longitude is not None:
            launch_site_coords = (float(latitude), float(longitude))
            orbit_visibility = calculate_orbit_visibility(launch_site_coords, launch_time_utc)
        else:
            orbit_visibility = []
            launch_site_coords = None
            
        # Daten für die Liste hinzufügen
        launches.append({
            "name": name,
            "rocket": rocket_name,
            "provider": launch_service_provider,
            "mission_type": mission_type,
            "pad": pad_name,
            "location": f"{location_name}, {country_code}",
            "coordinates": launch_site_coords,
            "times": launch_times,
            "orbit_visibility": orbit_visibility,
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
        st.markdown(f"**UTC:** {selected_launch['times']['UTC']}")
        st.markdown(f"**Deutschland:** {selected_launch['times']['Deutschland']}")
            
        st.subheader("Mögliche Umrundungen und Sichtbarkeit")
        if selected_launch["orbit_visibility"]:
            for orbit in selected_launch["orbit_visibility"]:
                st.markdown(f"**Umrundung {orbit['umrundung']}:**")
                st.markdown(f"  UTC: {orbit['zeit_utc']}")
                st.markdown(f"  DE: {orbit['zeit_de']}")
                st.markdown(f"  Sichtbarkeit: {orbit['sichtbarkeit']}")
        else:
            st.markdown("Keine Daten zur Berechnung der Umrundungen verfügbar.")
    
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
            "Start (UTC)": launch["times"]["UTC"],
            "Start (DE)": launch["times"]["Deutschland"],
            "Anzahl berechneter Umrundungen": len(launch["orbit_visibility"])
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df)
    
    # Hinweis zur Sichtbarkeit
    st.info("""
        **Hinweis zur Berechnung der Umrundungen:** 
        Die Berechnungen der Orbit-Umrundungen und der Sichtbarkeit sind vereinfachte Schätzungen basierend auf typischen
        Umlaufbahnen für erdnahe Orbits (LEO). Die tatsächlichen Umlaufbahnen, Zeiten und Sichtbarkeiten hängen von der 
        spezifischen Flugbahn, dem Orbit-Eintrittswinkel, Wetterbedingungen und weiteren Faktoren ab. Diese Angaben
        dienen nur zur groben Orientierung.
    """)
    
else:
    st.error("Keine Daten über bevorstehende Raketenstarts verfügbar. Bitte versuche es später erneut.")
