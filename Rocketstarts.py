import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from geopy.distance import geodesic
import folium
from streamlit_folium import folium_static
import math
import numpy as np
from folium.plugins import AntPath

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

# Funktion zur Berechnung der Orbit-Punkte für die Visualisierung
def calculate_orbit_path(launch_site_coords, inclination=51.6):
    # Erdradius in km
    earth_radius = 6371
    
    # Angenommene Orbithöhe (typisch für LEO)
    orbit_height = 300  # km
    
    # Umrechnung in Radians
    lat1_rad = math.radians(launch_site_coords[0])
    lon1_rad = math.radians(launch_site_coords[1])
    
    # Orbit-Punkte berechnen (vereinfacht)
    orbit_points = []
    
    # Kreis um die Erde mit Neigungswinkel (Inclination)
    for angle in range(0, 360, 5):  # 5-Grad-Schritte für flüssigere Kurve
        # Umrechnung von Winkel zu Position auf geneigter Umlaufbahn
        angle_rad = math.radians(angle)
        
        # Einfaches Modell für geneigte Umlaufbahn
        # (Dies ist eine Vereinfachung, tatsächliche Orbits sind komplexer)
        lat_rad = math.asin(math.sin(lat1_rad) * math.cos(math.radians(inclination)) + 
                           math.cos(lat1_rad) * math.sin(math.radians(inclination)) * math.sin(angle_rad))
        
        lon_diff = math.atan2(math.sin(angle_rad) * math.cos(math.radians(inclination)),
                             math.cos(angle_rad) - math.sin(lat1_rad) * math.sin(lat_rad))
        
        lon_rad = ((lon1_rad + lon_diff + math.pi) % (2 * math.pi)) - math.pi
        
        lat = math.degrees(lat_rad)
        lon = math.degrees(lon_rad)
        
        orbit_points.append((lat, lon))
    
    return orbit_points

# Verbesserte Funktion zur Berechnung der Sichtbarkeit während Umrundungen
def calculate_orbit_visibility(launch_site_coords, launch_time_utc, mission_type="LEO"):
    # Entfernung zwischen Deutschland und Startort berechnen
    distance_km = geodesic(germany_coords, launch_site_coords).kilometers
    
    # Verschiedene Orbithöhen basierend auf Missionstyp
    orbit_params = {
        "LEO": {"height": 300, "inclination": 51.6},  # Typisch für ISS
        "MEO": {"height": 20000, "inclination": 55},  # Medium Earth Orbit
        "GEO": {"height": 35786, "inclination": 0},   # Geostationärer Orbit
        "SSO": {"height": 600, "inclination": 97.8}   # Sonnensynchroner Orbit
    }
    
    # Standardmäßig LEO verwenden, aber versuchen, den Missionstyp zu erkennen
    orbit_type = "LEO"
    if mission_type and isinstance(mission_type, str):
        mission_lower = mission_type.lower()
        if "geo" in mission_lower:
            orbit_type = "GEO"
        elif "meo" in mission_lower:
            orbit_type = "MEO"
        elif "sun" in mission_lower and "syn" in mission_lower:
            orbit_type = "SSO"
    
    # Orbitalparameter auswählen
    orbit_height = orbit_params[orbit_type]["height"]
    inclination = orbit_params[orbit_type]["inclination"]
    
    # Erdradius in km
    earth_radius = 6371
    
    # Berechne Umlaufzeit (Periode) basierend auf Kepler'schen Gesetzen
    # T² = (4π²/GM) * r³, vereinfacht
    orbit_period_minutes = 2 * math.pi * math.sqrt(((earth_radius + orbit_height)**3) / (3.986 * 10**14)) / 60
    
    # Bei geostationärem Orbit ist die Periode immer ca. 24 Stunden
    if orbit_type == "GEO":
        orbit_period_minutes = 24 * 60
    
    # Berechne, wie oft der Orbit über Deutschland führen könnte
    # Abhängig von Inklination und Orbittyp
    visibility_frequency = 1  # Standard: jede Umrundung potenziell sichtbar
    
    if orbit_type == "LEO":
        # LEO-Satelliten sind bei etwa jeder 1-2 Umrundung potenziell sichtbar
        visibility_frequency = 2 if inclination < 50 else 1
    elif orbit_type == "MEO":
        visibility_frequency = 3
    elif orbit_type == "GEO":
        # Geostationäre Satelliten sind entweder immer oder nie sichtbar
        # Vereinfachte Annahme: wenn Startort > 60° vom Äquator, dann nie sichtbar
        if abs(launch_site_coords[0]) > 60:
            return []
    
    # Berechne die ersten 7 möglichen Sichtbarkeiten (mehr für bessere Übersicht)
    visibility_times = []
    for i in range(1, 8):
        # Zeit nach i Umrundungen
        orbit_time = launch_time_utc + timedelta(minutes=orbit_period_minutes * i)
        
        # Prüfen, ob diese Umrundung über Deutschland führen könnte
        if i % visibility_frequency == 0 or orbit_type == "GEO":
            # Zeitpunkt in deutscher Zeit
            german_tz = pytz.timezone('Europe/Berlin')
            orbit_time_german = orbit_time.astimezone(german_tz)
            
            # Detailliertere Sichtbarkeitsbewertung
            hour = orbit_time_german.hour
            
            if 22 <= hour or hour <= 4:
                visibility = "Sehr gut (dunkler Nachthimmel)"
                visibility_score = 5
            elif (20 <= hour < 22) or (4 < hour <= 6):
                visibility = "Gut (Dämmerung)"
                visibility_score = 4
            elif 6 < hour <= 8 or 18 <= hour < 20:
                visibility = "Mäßig (Heller Himmel)"
                visibility_score = 3
            elif 8 < hour < 18:
                visibility = "Schlecht (Tageslicht)"
                visibility_score = 1
            
            # Zusätzliche Faktoren für die Sichtbarkeit
            # 1. Entfernung zum Startort beeinflusst Flugbahn
            distance_factor = min(1.0, (20000 - distance_km) / 20000) if distance_km < 20000 else 0
            
            # 2. Einfluss der Inklination (Winkel zur Äquatorialebene)
            # Deutschland liegt bei ~51° N, daher sind Orbits mit ähnlicher Inklination besser sichtbar
            inclination_factor = 1.0 - min(1.0, abs(51.0 - inclination) / 90.0)
            
            # Kombinierter Sichtbarkeitswert (0-100%)
            combined_visibility = int((visibility_score / 5.0 * 0.6 + distance_factor * 0.2 + inclination_factor * 0.2) * 100)
            
            # Orbit-Typ spezifische Anpassungen
            if orbit_type == "GEO":
                combined_visibility = int(combined_visibility * 0.7)  # GEO ist schwieriger zu sehen
                visibility_note = f"Geostationärer Orbit - Position bleibt fest am Himmel"
            elif orbit_type == "SSO":
                visibility_note = f"Sonnensynchroner Orbit - Fliegt meist morgens/abends über"
            else:
                visibility_note = f"{orbit_type}-Orbit" + (f" - Sichtbarkeit {combined_visibility}%" if combined_visibility > 0 else " - Wahrscheinlich nicht sichtbar")
            
            visibility_times.append({
                "umrundung": i,
                "orbit_type": orbit_type,
                "zeit_utc": orbit_time.strftime("%d.%m.%Y, %H:%M:%S"),
                "zeit_de": orbit_time_german.strftime("%d.%m.%Y, %H:%M:%S"),
                "sichtbarkeit": visibility,
                "sichtbarkeit_prozent": combined_visibility,
                "hinweis": visibility_note
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
        
        # Mission-Beschreibung für bessere Orbit-Klassifizierung
        mission_description = launch.get("mission", {}).get("description", "")
        
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
        
        # Orbit-Typ aus Missionsbeschreibung erkennen
        orbit_type = "LEO"  # Standard: Low Earth Orbit
        if mission_description:
            if "geostationär" in mission_description.lower() or "geostationary" in mission_description.lower():
                orbit_type = "GEO"
            elif "sonnensynchron" in mission_description.lower() or "sun-synchronous" in mission_description.lower():
                orbit_type = "SSO"
            elif "medium earth" in mission_description.lower() or "meo" in mission_description.lower():
                orbit_type = "MEO"
        
        # Umrundungen und Sichtbarkeit berechnen (falls Koordinaten vorhanden sind)
        if latitude is not None and longitude is not None:
            launch_site_coords = (float(latitude), float(longitude))
            orbit_visibility = calculate_orbit_visibility(launch_site_coords, launch_time_utc, mission_description or mission_type)
            orbit_path = calculate_orbit_path(launch_site_coords)
        else:
            orbit_visibility = []
            orbit_path = []
            launch_site_coords = None
            
        # Daten für die Liste hinzufügen
        launches.append({
            "name": name,
            "rocket": rocket_name,
            "provider": launch_service_provider,
            "mission_type": mission_type,
            "mission_description": mission_description,
            "pad": pad_name,
            "location": f"{location_name}, {country_code}",
            "coordinates": launch_site_coords,
            "times": launch_times,
            "orbit_type": orbit_type,
            "orbit_visibility": orbit_visibility,
            "orbit_path": orbit_path,
            "utc_time": launch_time_utc  # Für Sortierung
        })
    
    # Nach Startzeit sortieren
    launches = sorted(launches, key=lambda x: x["utc_time"])
    
    # Seitenleiste für Filteroptionen
    st.sidebar.header("Filter")
    
    # Filter für Zeitraum
    time_range = st.sidebar.selectbox(
        "Zeitraum",
        ["Alle", "Nächste 24 Stunden", "Nächste 7 Tage", "Nächsten 30 Tage"]
    )
    
    # Filter für potenzielle Sichtbarkeit
    visibility_filter = st.sidebar.checkbox("Nur mit potenzieller Sichtbarkeit in Deutschland", value=False)
    
    # Filter für Orbit-Typ
    orbit_types = ["Alle"] + list(set([launch["orbit_type"] for launch in launches]))
    selected_orbit_type = st.sidebar.selectbox("Orbit-Typ", orbit_types)
    
    # Gefilterte Launches
    filtered_launches = launches.copy()
    
    # Zeitfilter anwenden
    now = datetime.now(pytz.utc)
    if time_range == "Nächste 24 Stunden":
        filtered_launches = [l for l in filtered_launches if l["utc_time"] <= now + timedelta(hours=24)]
    elif time_range == "Nächste 7 Tage":
        filtered_launches = [l for l in filtered_launches if l["utc_time"] <= now + timedelta(days=7)]
    elif time_range == "Nächsten 30 Tage":
        filtered_launches = [l for l in filtered_launches if l["utc_time"] <= now + timedelta(days=30)]
    
    # Sichtbarkeitsfilter anwenden
    if visibility_filter:
        filtered_launches = [l for l in filtered_launches if any(orb["sichtbarkeit_prozent"] > 30 for orb in l["orbit_visibility"])]
    
    # Orbit-Typ-Filter anwenden
    if selected_orbit_type != "Alle":
        filtered_launches = [l for l in filtered_launches if l["orbit_type"] == selected_orbit_type]
    
    # Wähle einen bestimmten Start aus für Details
    if filtered_launches:
        launch_names = [f"{launch['name']} - {launch['times']['Deutschland']} - {launch['orbit_type']}" for launch in filtered_launches]
        selected_launch_index = st.selectbox("Wähle einen Raketenstart aus:", 
                                            range(len(launch_names)),
                                            format_func=lambda i: launch_names[i])
        
        selected_launch = filtered_launches[selected_launch_index]
        
        # Detailansicht
        st.header(selected_launch["name"])
        
        # Tabbed Interface für verschiedene Ansichten
        tab1, tab2, tab3 = st.tabs(["Startdetails", "Umlaufbahn & Sichtbarkeit", "Karte"])
        
        with tab1:
            st.subheader("Startdetails")
            st.markdown(f"**Rakete:** {selected_launch['rocket']}")
            st.markdown(f"**Anbieter:** {selected_launch['provider']}")
            st.markdown(f"**Missionstyp:** {selected_launch['mission_type']}")
            st.markdown(f"**Orbit-Typ:** {selected_launch['orbit_type']}")
            st.markdown(f"**Startplatz:** {selected_launch['pad']}")
            st.markdown(f"**Standort:** {selected_launch['location']}")
            
            st.subheader("Startzeiten")
            st.markdown(f"**UTC:** {selected_launch['times']['UTC']}")
            st.markdown(f"**Deutschland:** {selected_launch['times']['Deutschland']}")
            
            if selected_launch['mission_description']:
                st.subheader("Missionsbeschreibung")
                st.markdown(selected_launch['mission_description'])
        
        with tab2:
            st.subheader("Umrundungen und Sichtbarkeit in Deutschland")
            
            # Graf für Sichtbarkeit
            if selected_launch["orbit_visibility"]:
                visibility_data = []
                for orbit in selected_launch["orbit_visibility"]:
                    orbit_time = orbit["zeit_de"].split(", ")[1]  # Nur die Uhrzeit
                    visibility_data.append({
                        "Umrundung": orbit["umrundung"],
                        "Zeit": orbit_time,
                        "Sichtbarkeit (%)": orbit["sichtbarkeit_prozent"]
                    })
                
                vis_df = pd.DataFrame(visibility_data)
                
                # Balkendiagramm mit Sichtbarkeitsprozent
                st.bar_chart(vis_df.set_index("Umrundung")["Sichtbarkeit (%)"])
                
                # Detaillierte Tabelle
                st.dataframe(vis_df)
                
                # Detaillierte Informationen zu den einzelnen Umrundungen
                st.subheader("Details zu den Umrundungen")
                for i, orbit in enumerate(selected_launch["orbit_visibility"]):
                    with st.expander(f"Umrundung {orbit['umrundung']} - {orbit['zeit_de']}"):
                        st.markdown(f"**Orbit-Typ:** {orbit['orbit_type']}")
                        st.markdown(f"**Zeit (UTC):** {orbit['zeit_utc']}")
                        st.markdown(f"**Zeit (DE):** {orbit['zeit_de']}")
                        st.markdown(f"**Sichtbarkeit:** {orbit['sichtbarkeit']}")
                        st.markdown(f"**Sichtbarkeitswahrscheinlichkeit:** {orbit['sichtbarkeit_prozent']}%")
                        st.markdown(f"**Hinweis:** {orbit['hinweis']}")
            else:
                st.markdown("Keine Daten zur Berechnung der Umrundungen verfügbar.")
        
        with tab3:
            # Karte mit dem Startort und Orbits
            if selected_launch["coordinates"] and selected_launch["orbit_path"]:
                st.subheader("Startort und Umlaufbahn")
                
                m = folium.Map(location=selected_launch["coordinates"], zoom_start=3)
                
                # Startort markieren
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
                
                # Orbit-Pfad zeichnen (vereinfacht)
                folium.PolyLine(
                    locations=selected_launch["orbit_path"],
                    color="orange",
                    weight=2,
                    opacity=0.7
                ).add_to(m)
                
                # Sichtbarkeitsbereiche visualisieren (erste 3 Umrundungen)
                if selected_launch["orbit_visibility"]:
                    for i, orbit in enumerate(selected_launch["orbit_visibility"][:3]):
                        if orbit["sichtbarkeit_prozent"] > 20:
                            # Erstelle einen Kreis um Deutschland für potenzielle Sichtbarkeit
                            # Je höher die Sichtbarkeit, desto größer der Kreis
                            visibility_radius = orbit["sichtbarkeit_prozent"] * 1000  # Meter
                            
                            folium.Circle(
                                location=germany_coords,
                                radius=visibility_radius,
                                popup=f"Potenzielle Sichtbarkeit: Umrundung {orbit['umrundung']}",
                                color=f"{'green' if orbit['sichtbarkeit_prozent'] > 60 else 'yellow' if orbit['sichtbarkeit_prozent'] > 30 else 'red'}",
                                fill=True,
                                fill_opacity=0.2
                            ).add_to(m)
                
                folium_static(m)
                
                # Erklärung zur Karte
                st.markdown("""
                    **Erklärung zur Karte:**
                    - **Roter Marker**: Startort der Rakete
                    - **Blauer Marker**: Deutschland
                    - **Orangene Linie**: Vereinfachte Darstellung der Umlaufbahn
                    - **Farbige Kreise**: Potenzielle Sichtbarkeitszonen für verschiedene Umrundungen
                """)
            else:
                st.markdown("Keine Koordinaten oder Orbitdaten für die Kartenansicht verfügbar.")
        
        # Besondere Highlights für gute Sichtbarkeit
        good_visibility_orbits = [o for o in selected_launch["orbit_visibility"] if o["sichtbarkeit_prozent"] > 70]
        if good_visibility_orbits:
            st.success(f"""
                **Highlight für Beobachter in Deutschland:**
                Diese Mission hat {len(good_visibility_orbits)} Umrundung(en) mit sehr guter potenzieller Sichtbarkeit!
                Beste Zeit für Beobachtung: {good_visibility_orbits[0]['zeit_de']}
            """)
    
        # Erklärung zur Berechnung
        with st.expander("Hinweise zur Berechnung der Umrundungen und Sichtbarkeit"):
            st.markdown("""
                **Berechnungsmethode:**
                Die Berechnungen der Orbit-Umrundungen und Sichtbarkeit basieren auf:
                
                1. **Orbit-Typ**: LEO (Low Earth Orbit), MEO (Medium Earth Orbit), GEO (Geostationärer Orbit) oder SSO (Sonnensynchroner Orbit)
                2. **Entfernung**: Abstand zwischen Deutschland und dem Startort
                3. **Tageszeit**: Nacht bietet bessere Sichtbarkeit als Tag
                4. **Inklination**: Der Winkel der Umlaufbahn relativ zum Äquator
                
                Die Sichtbarkeitswahrscheinlichkeit ist eine kombinierte Bewertung (0-100%), die diese Faktoren berücksichtigt.
                
                **Wichtig:** Die tatsächliche Sichtbarkeit hängt von weiteren Faktoren ab wie:
                - Wetterbedingungen
                - Lichtverschmutzung am Beobachtungsort
                - Genaue Flugbahnparameter (die oft erst kurz vor dem Start feststehen)
                - Helligkeit des Objekts (abhängig von Sonnenlicht und Reflexion)
            """)
    
        # Tabelle mit allen bevorstehenden Starts
        st.header("Alle gefilterten Raketenstarts")
        
    else:
        st.warning("Keine Starts entsprechen den ausgewählten Filterkriterien.")
        
    # DataFrame für die Tabelle erstellen
    df_data = []
    for launch in filtered_launches:
        # Beste Sichtbarkeit berechnen
        best_visibility = max([orb.get("sichtbarkeit_prozent", 0) for orb in launch["orbit_visibility"]]) if launch["orbit_visibility"] else 0
        
        df_data.append({
            "Name": launch["name"],
            "Rakete": launch["rocket"],
            "Orbit": launch["orbit_type"],
            "Start (UTC)": launch["times"]["UTC"],
            "Start (DE)": launch["times"]["Deutschland"],
            "Beste Sichtbarkeit (%)": best_visibility,
            "Anzahl berechneter Umrundungen": len(launch["orbit_visibility"])
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(df)
    
else:
    st.error("Keine Daten über bevorstehende Raketenstarts verfügbar. Bitte versuche es später erneut.")
