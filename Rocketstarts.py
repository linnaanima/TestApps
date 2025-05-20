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
st.title("Raketenstarts - Weltweit")
st.markdown("Diese App zeigt kommende Raketenstarts mit UTC und deutscher Zeit sowie Sichtbarkeit während Umrundungen.")

# Funktion zum Abrufen von Daten über bevorstehende Raketenstarts
@st.cache_data(ttl=3600)  # Cache der Daten für 1 Stunde
def get_launch_data():
    url = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?limit=20&mode=detailed"
    headers = {"Accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Fehler beim Abrufen der Daten: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Verbindungsfehler: {str(e)}")
        return None

# Verbesserte Funktion zur Berechnung der Orbit-Umlaufzeit
def calculate_orbit_period(orbit_height):
    """
    Berechnet die Umlaufzeit eines Orbits basierend auf der Höhe
    """
    earth_radius = 6371  # km
    gravitational_parameter = 3.986004418e14  # m³/s² (GM für die Erde)
    orbit_radius = (earth_radius + orbit_height) * 1000  # m
    
    # Kepler's Third Law: T² = (4π²/GM) * r³
    orbit_period_seconds = 2 * math.pi * math.sqrt(orbit_radius**3 / gravitational_parameter)
    return orbit_period_seconds / 60  # Minuten

# Funktion zur Berechnung der Orbit-Punkte für die Visualisierung
def calculate_orbit_path(launch_site_coords, inclination=51.6):
    """
    Erstellt einen vereinfachten Orbit-Pfad für die Visualisierung
    """
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

# Deutschland-Koordinaten (ungefährer Mittelpunkt)
germany_coords = (51.1657, 10.4515)

# Verbesserte Funktion zur präzisen Berechnung der Sichtbarkeitszeiten und Umrundungen
def calculate_rocket_visibility(
    launch_site_coords, 
    launch_time_utc, 
    mission_type="LEO",
    total_orbits=20,
    visibility_days=3
):
    """
    Berechnet wann eine Rakete nach dem Start von Deutschland aus sichtbar sein könnte,
    unter Berücksichtigung der Erdrotation und des orbitalen Mechanismus.
    """
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
        elif ("sun" in mission_lower and "syn" in mission_lower) or "sso" in mission_lower:
            orbit_type = "SSO"
    
    # Orbitalparameter auswählen
    orbit_height = orbit_params[orbit_type]["height"]
    inclination = orbit_params[orbit_type]["inclination"]
    
    # Berechnen der Umlaufzeit in Minuten basierend auf Kepler'schen Gesetzen
    orbit_period_minutes = calculate_orbit_period(orbit_height)
    
    # Bei geostationärem Orbit ist die Periode immer ca. 24 Stunden
    if orbit_type == "GEO":
        orbit_period_minutes = 24 * 60
    
    # Berechnung der Erdrotation pro Orbit (Grad)
    earth_rotation_per_orbit = (orbit_period_minutes / (24 * 60)) * 360
    
    # Berechnung der Entfernung zwischen Startort und Deutschland
    distance_km = geodesic(launch_site_coords, germany_coords).kilometers
    
    # Beobachterfaktor je nach Inklination
    # (Deutschland liegt bei ~51°N, daher sind Inklinationen nahe 51° besser sichtbar)
    inclination_factor = 1.0 - min(1.0, abs(51.0 - inclination) / 90.0)
    
    # Zeitgrenze für die Berechnung
    end_time = launch_time_utc + timedelta(days=visibility_days)
    
    # Mögliche Sichtungszeitfenster
    visibility_windows = []
    
    # Zeit des aktuellen Orbits
    current_orbit_time = launch_time_utc
    orbit_number = 0
    
    # Orbits durchgehen bis zur maximalen Anzahl oder Zeitgrenze
    while orbit_number < total_orbits and current_orbit_time < end_time:
        orbit_number += 1
        
        # Zeit der aktuellen Umrundung berechnen
        current_orbit_time = launch_time_utc + timedelta(minutes=orbit_period_minutes * orbit_number)
        
        # Berechnung der Längengrad-Verschiebung durch Erdrotation
        longitude_shift = (orbit_number * earth_rotation_per_orbit) % 360
        
        # Position entlang der Umlaufbahn zum aktuellen Zeitpunkt
        orbit_position_rad = 2 * math.pi * (orbit_number % 1)
        
        # Berechnen des Breitengrades der aktuellen Position
        latitude = math.degrees(math.asin(math.sin(math.radians(inclination)) * 
                                         math.sin(orbit_position_rad)))
        
        # Berechnen des umgerechneten Längengrades (berücksichtigt Erdrotation)
        longitude = (launch_site_coords[1] + longitude_shift) % 360
        if longitude > 180:
            longitude -= 360
            
        # Aktuelle Satellitenposition
        current_position = (latitude, longitude)
        
        # Entfernung zur aktuellen Position
        current_distance = geodesic(germany_coords, current_position).kilometers
        
        # Sichtbarkeitsfaktor basierend auf der Entfernung
        # Je näher, desto besser sichtbar (max. Sichtweite ca. 2000km bei dieser Orbithöhe)
        max_visibility_distance = 2000  # km
        distance_factor = max(0, 1 - (current_distance / max_visibility_distance))
        
        # Zeit in Deutschland
        de_timezone = pytz.timezone('Europe/Berlin')
        orbit_time_de = current_orbit_time.replace(tzinfo=pytz.UTC).astimezone(de_timezone)
        
        # Tageszeit-Faktor (Nachts besser sichtbar)
        hour = orbit_time_de.hour
        if 22 <= hour or hour <= 4:
            time_factor = 1.0  # Optimale Nacht
            visibility_text = "Sehr gut (dunkler Nachthimmel)"
        elif (20 <= hour < 22) or (4 < hour <= 6):
            time_factor = 0.8  # Dämmerung
            visibility_text = "Gut (Dämmerung)"
        elif (18 <= hour < 20) or (6 < hour <= 8):
            time_factor = 0.4  # Morgen/Abend
            visibility_text = "Mäßig (Heller Himmel)"
        else:
            time_factor = 0.1  # Tag
            visibility_text = "Schlecht (Tageslicht)"
            
        # Gesamte Sichtbarkeitswahrscheinlichkeit (0-100%)
        visibility_chance = min(100, int(
            (distance_factor * 0.5 + inclination_factor * 0.3 + time_factor * 0.2) * 100
        ))
        
        # Orbit-Typ spezifische Anpassungen
        if orbit_type == "GEO":
            visibility_chance = int(visibility_chance * 0.7)  # GEO ist schwieriger zu sehen
            visibility_note = f"Geostationärer Orbit - Position bleibt fest am Himmel"
        elif orbit_type == "SSO":
            visibility_note = f"Sonnensynchroner Orbit - Fliegt meist morgens/abends über"
        else:
            visibility_note = f"{orbit_type}-Orbit" + (f" - Sichtbarkeit {visibility_chance}%" if visibility_chance > 0 else " - Wahrscheinlich nicht sichtbar")
        
        # Zeitfenster für die Sichtbarkeit (typischerweise 5-10 Minuten)
        visibility_duration = int(5 + (visibility_chance / 100) * 5)  # Minuten
        
        # Zeitfenster berechnen
        window_start = orbit_time_de - timedelta(minutes=visibility_duration/2)
        window_end = orbit_time_de + timedelta(minutes=visibility_duration/2)
        
        # Informationen zum Orbit sammeln
        orbit_info = {
            "orbit_number": orbit_number,
            "time_utc": current_orbit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "time_de": orbit_time_de.strftime("%Y-%m-%d %H:%M:%S"),
            "visibility_chance": visibility_chance,
            "visibility_text": visibility_text,
            "window_start": window_start.strftime("%H:%M:%S"),
            "window_end": window_end.strftime("%H:%M:%S"),
            "visibility_date": orbit_time_de.strftime("%Y-%m-%d"),
            "duration_minutes": visibility_duration,
            "orbit_type": orbit_type,
            "hinweis": visibility_note,
            "coords": current_position
        }
        
        visibility_windows.append(orbit_info)
    
    return visibility_windows

# Hauptfunktion der App
def main():
    # Daten abrufen
    with st.spinner("Rufe aktuelle Raketenstartdaten ab..."):
        launch_data = get_launch_data()

    # Vereinfachte Zeitzonen-Liste
    timezones = {
        "Deutschland": "Europe/Berlin",
        "UTC": "UTC"
    }

    # Fortschrittsbalken für die Berechnungen
    progress_bar = None

    if launch_data:
        # Seitenleiste für Filteroptionen
        st.sidebar.header("Filter")
        
        # Filter für Zeitraum
        time_range = st.sidebar.selectbox(
            "Zeitraum",
            ["Alle", "Nächste 24 Stunden", "Nächste 7 Tage", "Nächsten 30 Tage"]
        )
        
        # Filter für potenzielle Sichtbarkeit
        visibility_filter = st.sidebar.checkbox("Nur mit potenzieller Sichtbarkeit in Deutschland", value=False)
        
        # Anzahl der zu berechnenden Umrundungen
        orbit_count = st.sidebar.slider("Anzahl der Umrundungen für Berechnung", 5, 50, 20)
        
        # Anzahl der Tage für die Sichtbarkeitsberechnung
        visibility_days = st.sidebar.slider("Berechnungszeitraum (Tage)", 1, 7, 3)
        
        # Daten vorbereiten
        launches = []
        
        # Fortschrittsbalken für die Datenverarbeitung
        progress_bar = st.progress(0)
        
        for idx, launch in enumerate(launch_data["results"]):
            # Aktualisiere Fortschrittsbalken
            progress = (idx + 1) / len(launch_data["results"])
            progress_bar.progress(progress)
            
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
                if "geostationär" in mission_description.lower() or "geostationary" in mission_description.lower() or "geo" in mission_description.lower():
                    orbit_type = "GEO"
                elif "sonnensynchron" in mission_description.lower() or "sun-synchronous" in mission_description.lower() or "sso" in mission_description.lower():
                    orbit_type = "SSO"
                elif "medium earth" in mission_description.lower() or "meo" in mission_description.lower():
                    orbit_type = "MEO"
            
            # Umrundungen und Sichtbarkeit berechnen (falls Koordinaten vorhanden sind)
            if latitude is not None and longitude is not None:
                try:
                    launch_site_coords = (float(latitude), float(longitude))
                    orbit_visibility = calculate_rocket_visibility(
                        launch_site_coords, 
                        launch_time_utc, 
                        mission_description or mission_type,
                        total_orbits=orbit_count,
                        visibility_days=visibility_days
                    )
                    orbit_path = calculate_orbit_path(launch_site_coords)
                except Exception as e:
                    st.warning(f"Fehler bei der Berechnung für {name}: {str(e)}")
                    orbit_visibility = []
                    orbit_path = []
                    launch_site_coords = None
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
        
        # Fortschrittsbalken entfernen
        if progress_bar:
            progress_bar.empty()
        
        # Nach Startzeit sortieren
        launches = sorted(launches, key=lambda x: x["utc_time"])
        
        # Zeitfilter anwenden
        now = datetime.now(pytz.utc)
        filtered_launches = launches.copy()
        
        if time_range == "Nächste 24 Stunden":
            filtered_launches = [l for l in filtered_launches if l["utc_time"] <= now + timedelta(hours=24)]
        elif time_range == "Nächste 7 Tage":
            filtered_launches = [l for l in filtered_launches if l["utc_time"] <= now + timedelta(days=7)]
        elif time_range == "Nächsten 30 Tage":
            filtered_launches = [l for l in filtered_launches if l["utc_time"] <= now + timedelta(days=30)]
        
        # Sichtbarkeitsfilter anwenden
        if visibility_filter:
            filtered_launches = [
                l for l in filtered_launches 
                if any(orb.get("visibility_chance", 0) > 30 for orb in l["orbit_visibility"])
            ]
        
        # Wähle einen bestimmten Start aus für Details
        if filtered_launches:
            st.header("Raketeninformationen")
            launch_names = [f"{launch['name']} - {launch['times']['Deutschland']} - {launch['orbit_type']}" for launch in filtered_launches]
            selected_launch_index = st.selectbox("Wähle einen Raketenstart aus:", 
                                                range(len(launch_names)),
                                                format_func=lambda i: launch_names[i])
            
            selected_launch = filtered_launches[selected_launch_index]
            
            # Detailansicht
            st.header(selected_launch["name"])
            
            # Tabbed Interface für verschiedene Ansichten
            tab1, tab2, tab3 = st.tabs(["🚀 Startdetails", "🌎 Umlaufbahn & Sichtbarkeit", "🗺️ Karte"])
            
            with tab1:
                st.subheader("Startdetails")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Rakete:** {selected_launch['rocket']}")
                    st.markdown(f"**Anbieter:** {selected_launch['provider']}")
                    st.markdown(f"**Missionstyp:** {selected_launch['mission_type']}")
                    st.markdown(f"**Orbit-Typ:** {selected_launch['orbit_type']}")
                
                with col2:
                    st.markdown(f"**Startplatz:** {selected_launch['pad']}")
                    st.markdown(f"**Standort:** {selected_launch['location']}")
                    st.markdown(f"**UTC Startzeit:** {selected_launch['times']['UTC']}")
                    st.markdown(f"**DE Startzeit:** {selected_launch['times']['Deutschland']}")
                
                if selected_launch['mission_description']:
                    st.subheader("Missionsbeschreibung")
                    st.markdown(selected_launch['mission_description'])
            
            with tab2:
                st.subheader("Umrundungen und Sichtbarkeit in Deutschland")
                
                # Graf für Sichtbarkeit
                if selected_launch["orbit_visibility"]:
                    # Nach Datum gruppieren
                    visibility_by_date = {}
                    for orbit in selected_launch["orbit_visibility"]:
                        date = orbit["visibility_date"]
                        if date not in visibility_by_date:
                            visibility_by_date[date] = []
                        visibility_by_date[date].append(orbit)
                    
                    # Balkendiagramm mit Sichtbarkeitsprozent
                    visibility_data = []
                    for orbit in selected_launch["orbit_visibility"]:
                        orbit_time = orbit["time_de"].split(" ")[1]  # Nur die Uhrzeit
                        visibility_data.append({
                            "Umrundung": orbit["orbit_number"],
                            "Zeit": orbit_time,
                            "Datum": orbit["visibility_date"],
                            "Sichtbarkeit (%)": orbit["visibility_chance"]
                        })
                    
                    vis_df = pd.DataFrame(visibility_data)
                    
                    st.bar_chart(vis_df.set_index("Umrundung")["Sichtbarkeit (%)"])
                    
                    # Beste Sichtbarkeiten hervorheben
                    good_visibility = [o for o in selected_launch["orbit_visibility"] if o["visibility_chance"] > 60]
                    if good_visibility:
                        st.success(f"""
                            **Beste Sichtbarkeitschancen:**
                            Es gibt {len(good_visibility)} Umrundung(en) mit guter bis sehr guter Sichtbarkeit von Deutschland aus!
                        """)
                        
                        # Die besten 3 anzeigen
                        for i, orbit in enumerate(sorted(good_visibility, key=lambda x: x["visibility_chance"], reverse=True)[:3], 1):
                            st.markdown(f"""
                                **Top {i}:** Umrundung {orbit['orbit_number']} am {orbit['visibility_date']} 
                                - Zeitfenster: {orbit['window_start']} - {orbit['window_end']} Uhr 
                                - Sichtbarkeit: {orbit['visibility_chance']}%
                            """)
                    
                    # Sichtbarkeiten nach Datum anzeigen
                    st.subheader("Sichtbarkeit nach Datum")
                    for date, orbits in visibility_by_date.items():
                        with st.expander(f"Datum: {date}"):
                            orbits_df = pd.DataFrame([
                                {
                                    "Umrundung": o["orbit_number"],
                                    "Uhrzeit (DE)": o["time_de"].split(" ")[1],
                                    "Sichtbarkeitsfenster": f"{o['window_start']} - {o['window_end']}",
                                    "Sichtbarkeit (%)": o["visibility_chance"],
                                    "Qualität": o["visibility_text"]
                                } for o in orbits
                            ])
                            st.dataframe(orbits_df)
                    
                    # Detaillierte Informationen zu einzelnen Umrundungen
                    st.subheader("Details zu den Umrundungen")
                    
                    # Gruppe die Umrundungen nach ihrer Sichtbarkeit
                    visibility_groups = {
                        "Sehr gute Sichtbarkeit (>70%)": [],
                        "Gute Sichtbarkeit (40-70%)": [],
                        "Mäßige Sichtbarkeit (20-40%)": [],
                        "Geringe Sichtbarkeit (<20%)": []
                    }
                    
                    for orbit in selected_launch["orbit_visibility"]:
                        chance = orbit["visibility_chance"]
                        if chance > 70:
                            visibility_groups["Sehr gute Sichtbarkeit (>70%)"].append(orbit)
                        elif chance > 40:
                            visibility_groups["Gute Sichtbarkeit (40-70%)"].append(orbit)
                        elif chance > 20:
                            visibility_groups["Mäßige Sichtbarkeit (20-40%)"].append(orbit)
                        else:
                            visibility_groups["Geringe Sichtbarkeit (<20%)"].append(orbit)
                    
                    # Zeige die Gruppen in Expandern an
                    for group_name, orbits in visibility_groups.items():
                        if orbits:
                            with st.expander(f"{group_name} ({len(orbits)} Umrundungen)"):
                                for orbit in sorted(orbits, key=lambda x: x["orbit_number"]):
                                    st.markdown(f"""
                                        **Umrundung {orbit['orbit_number']}** - {orbit['time_de']}
                                        - Zeitfenster: {orbit['window_start']} - {orbit['window_end']} ({orbit['duration_minutes']} Min.)
                                        - Sichtbarkeit: {orbit['visibility_chance']}%
                                        - Hinweis: {orbit['hinweis']}
                                    """)
                else:
                    st.warning("Keine Daten zur Berechnung der Umrundungen verfügbar.")
            
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
                    
                    # Orbit-Pfad zeichnen
                    folium.PolyLine(
                        locations=selected_launch["orbit_path"],
                        color="orange",
                        weight=2,
                        opacity=0.7
                    ).add_to(m)
                    
                    # Sichtbarkeitspunkte für die ersten Umrundungen visualisieren
                    visible_orbits = [o for o in selected_launch["orbit_visibility"] if o.get("visibility_chance", 0) > 30]
                    
                    # Die Farbe basierend auf der Sichtbarkeit wählen
                    def get_visibility_color(chance):
                        if chance > 70:
                            return "green"
                        elif chance > 40:
                            return "orange"
                        elif chance > 20:
                            return "yellow"
                        else:
                            return "red"
                    
                    # Füge Sichtbarkeitspunkte zur Karte hinzu
                    for orbit in visible_orbits[:10]:  # Begrenzen auf die ersten 10 für Übersichtlichkeit
                        if "coords" in orbit:
                            folium.CircleMarker(
                                location=orbit["coords"],
                                radius=5,
                                popup=f"Umrundung {orbit['orbit_number']}<br>Sichtbarkeit: {orbit['visibility_chance']}%<br>Zeit (DE): {orbit['time_de']}",
                                color=get_visibility_color(orbit["visibility_chance"]),
                                fill=True,
                                fill_opacity=0.8
                            ).add_to(m)
                    
                    # Zeichne die Verbindung zwischen Deutschland und den sichtbaren Orbits
                    for orbit in visible_orbits[:5]:  # Nur die ersten 5 für Übersichtlichkeit
                        if "coords" in orbit and orbit.get("visibility_chance", 0) > 40:
                            # AntPath für die Animation
                            AntPath(
                                locations=[germany_coords, orbit["coords"]],
                                color=get_visibility_color(orbit["visibility_chance"]),
                                weight=2,
                                opacity=0.7,
                                dash_array=[10, 20],
                                pulse_color=get_visibility_color(orbit["visibility_chance"]),
                                delay=800
                            ).add_to(m)
                    
                    # Karte anzeigen
                    folium_static(m)
                    
                    # Erklärung zur Karte
                    st.markdown("""
                        **Erklärung zur Karte:**
                        - **Roter Marker**: Startort der Rakete
                        - **Blauer Marker**: Deutschland
                        - **Orangene Linie**: Vereinfachte Darstellung der Umlaufbahn
                        - **Farbige Punkte**: Positionen der Rakete während potenziell sichtbarer Umrundungen:
                            - Grün: Sehr gute Sichtbarkeit (>70%)
                            - Orange: Gute Sichtbarkeit (40-70%)
                            - Gelb: Mäßige Sichtbarkeit (20-40%)
                            - Rot: Geringe Sichtbarkeit (<20%)
                        - **Animierte Linien**: Verbindungen zwischen Deutschland und gut sichtbaren Orbits
                    """)
                else:
                    st.warning("Keine Koordinaten oder Orbitdaten für die Kartenansicht verfügbar.")
            
            # Erklärung zur Berechnung
            with st.expander("Hinweise zur Berechnung der Umrundungen und Sichtbarkeit"):
                st.markdown("""
                    ## Berechnungsmethode
                    
                    Die Berechnung der Orbit-Umrundungen und Sichtbarkeit basiert auf mehreren Faktoren:
                    
                    ### 1. Physikalische Grundlagen
                    - **Kepler'sche Gesetze**: Berechnung der Umlaufzeit basierend auf Orbithöhe
                    - **Erdrotation**: Berücksichtigung der Erdrotation für jede Umrundung (ca. 15° pro Stunde)
                    - **Orbittyp**: Unterschiedliche Berechnungen für LEO (niedrige Erdumlaufbahn), MEO (mittlere Erdumlaufbahn), GEO (geostationäre Umlaufbahn) und SSO (sonnensynchrone Umlaufbahn)
                    
                    ### 2. Sichtbarkeitsfaktoren
                    - **Entfernung**: Abstand zwischen Rakete und Beobachter (Deutschland)
                    - **Tageszeit**: Nacht bietet bessere Sichtbarkeit als Tag
                    - **Inklination**: Der Winkel der Umlaufbahn relativ zum Äquator (für Deutschland ist ~51° optimal)
                    
                    ### 3. Zeitfensterberechnung
                    - Die Sichtbarkeitsdauer hängt von der Qualität der Sichtbarkeit ab
                    - Typischerweise 5-10 Minuten pro Überflug
                    - Für jede Umrundung wird ein präzises Zeitfenster berechnet
                    
                    ### Wichtige Hinweise
                    
                    Die tatsächliche Sichtbarkeit hängt von weiteren Faktoren ab wie:
                    - **Wetterbedingungen** vor Ort
                    - **Lichtverschmutzung** am Beobachtungsort
                    - **Genaue Flugbahnparameter** (die oft erst kurz vor dem Start feststehen)
                    - **Helligkeit des Objekts** (abhängig von Sonnenlicht und Reflexion)
                    - **Höhenwinkel** über dem Horizont (Berge, Gebäude können die Sicht versperren)
                    
                    Diese Berechnungen dienen als Orientierungshilfe für potenzielle Beobachtungszeitpunkte.
                """)
        
            # Tabelle mit allen bevorstehenden Starts
            st.header("Alle gefilterten Raketenstarts")
            
            # DataFrame für die Tabelle erstellen
            df_data = []
            for launch in filtered_launches:
                # Beste Sichtbarkeit berechnen
                best_visibility = max([orb.get("visibility_chance", 0) for orb in launch["orbit_visibility"]]) if launch["orbit_visibility"] else 0
                
                # Anzahl guter Sichtbarkeitsfenster
                good_visibility_count = len([o for o in launch["orbit_visibility"] if o.get("visibility_chance", 0) > 40])
                
                df_data.append({
                    "Name": launch["name"],
                    "Rakete": launch["rocket"],
                    "Orbit": launch["orbit_type"],
                    "Start (UTC)": launch["times"]["UTC"],
                    "Start (DE)": launch["times"]["Deutschland"],
                    "Beste Sichtbarkeit (%)": best_visibility,
                    "Gute Sichtbarkeitsfenster": good_visibility_count,
                    "Berechnete Umrundungen": len(launch["orbit_visibility"])
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df)
            
            # Download-Button für die Daten
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Daten als CSV herunterladen",
                csv,
                "raketenstarts.csv",
                "text/csv",
                key='download-csv'
            )
            
        else:
            st.warning("Keine Starts entsprechen den ausgewählten Filterkriterien.")
            
        # Informationen zur App
        st.sidebar.markdown("---")
        st.sidebar.header("Informationen")
        st.sidebar.markdown("""
            Diese App zeigt kommende Raketenstarts und berechnet, 
            wann diese möglicherweise von Deutschland aus sichtbar sein könnten.
            
            Datenquelle: [The Space Devs Launch Library](https://thespacedevs.com/llapi)
            
            Die Berechnungen sind Näherungswerte und 
            dienen als Orientierungshilfe für die Beobachtung.
        """)
        
    else:
        st.error("Keine Daten über bevorstehende Raketenstarts verfügbar. Bitte versuche es später erneut.")
        
        # Offline-Demo-Modus
        if st.button("Offline-Demo-Modus starten"):
            st.info("Der Offline-Demo-Modus würde hier Beispieldaten laden, wenn er implementiert wäre.")
