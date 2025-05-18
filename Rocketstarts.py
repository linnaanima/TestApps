import datetime
import math
import pytz
from geopy.distance import geodesic

def calculate_rocket_visibility(
    launch_coords,
    launch_time,
    orbit_height=400,  # km, typische Höhe für LEO
    inclination=51.6,  # Grad, typische ISS-Inklination
    observer_coords=(51.1657, 10.4515),  # Deutschland (Mittelpunkt)
    total_orbits=20,  # Anzahl der zu berechnenden Umrundungen
    visibility_days=3  # Tage, für die Sichtbarkeit berechnet wird
):
    """
    Berechnet, wann eine Rakete nach dem Start von Deutschland aus sichtbar sein könnte.
    
    Args:
        launch_coords: Tuple (lat, lon) der Startkoordinaten
        launch_time: datetime-Objekt des Starts (UTC)
        orbit_height: Höhe der Umlaufbahn in km
        inclination: Inklination der Umlaufbahn in Grad
        observer_coords: Koordinaten des Beobachters (Deutschland)
        total_orbits: Anzahl der zu berechnenden Umlaufbahnen
        visibility_days: Anzahl der Tage, für die die Sichtbarkeit berechnet wird
        
    Returns:
        Liste von Sichtbarkeitszeitfenstern
    """
    # Grundlegende physikalische Konstanten
    earth_radius = 6371  # km
    gravitational_parameter = 3.986004418e14  # m³/s² (GM für die Erde)
    
    # Umrechnen der Orbithöhe in Meter für die Berechnungen
    orbit_radius = (earth_radius + orbit_height) * 1000  # m
    
    # Berechnen der Umlaufzeit nach Kepler
    orbit_period_seconds = 2 * math.pi * math.sqrt(orbit_radius**3 / gravitational_parameter)
    orbit_period_minutes = orbit_period_seconds / 60
    
    print(f"Orbithöhe: {orbit_height} km")
    print(f"Inklination: {inclination}°")
    print(f"Umlaufzeit: {orbit_period_minutes:.2f} Minuten ({orbit_period_minutes/60:.2f} Stunden)")
    
    # Berechnung der Erdrotation pro Orbit
    earth_rotation_per_orbit = (orbit_period_seconds / (24 * 3600)) * 360  # Grad
    
    # Berechnung der Entfernung zwischen Start und Beobachter
    distance_km = geodesic(launch_coords, observer_coords).kilometers
    
    # Beobachterfaktor je nach Inklination 
    # (Deutschland liegt bei ~51°N, daher sind Inklinationen nahe 51° besser sichtbar)
    inclination_factor = 1.0 - min(1.0, abs(51.0 - inclination) / 90.0)
    
    # Zeitgrenze für die Berechnung
    end_time = launch_time + datetime.timedelta(days=visibility_days)
    
    # Mögliche Sichtungszeitfenster
    visibility_windows = []
    
    # Zeit des aktuellen Orbits
    current_orbit_time = launch_time
    orbit_number = 0
    
    # Orbits durchgehen bis zur maximalen Anzahl oder Zeitgrenze
    while orbit_number < total_orbits and current_orbit_time < end_time:
        orbit_number += 1
        
        # Zeit der aktuellen Umrundung berechnen
        current_orbit_time = launch_time + datetime.timedelta(minutes=orbit_period_minutes * orbit_number)
        
        # Berechnung der Längengrad-Verschiebung durch Erdrotation
        longitude_shift = (orbit_number * earth_rotation_per_orbit) % 360
        
        # Position entlang der Umlaufbahn zum aktuellen Zeitpunkt
        orbit_position_rad = 2 * math.pi * (orbit_number % 1)
        
        # Berechnen des Breitengrades der aktuellen Position
        latitude = math.degrees(math.asin(math.sin(math.radians(inclination)) * 
                                         math.sin(orbit_position_rad)))
        
        # Berechnen des umgerechneten Längengrades (berücksichtigt Erdrotation)
        longitude = (launch_coords[1] + longitude_shift) % 360
        if longitude > 180:
            longitude -= 360
            
        # Aktuelle Satellitenposition
        current_position = (latitude, longitude)
        
        # Entfernung zur aktuellen Position
        current_distance = geodesic(observer_coords, current_position).kilometers
        
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
        elif (20 <= hour < 22) or (4 < hour <= 6):
            time_factor = 0.8  # Dämmerung
        elif (18 <= hour < 20) or (6 < hour <= 8):
            time_factor = 0.4  # Morgen/Abend
        else:
            time_factor = 0.1  # Tag
            
        # Gesamte Sichtbarkeitswahrscheinlichkeit (0-100%)
        visibility_chance = min(100, int(
            (distance_factor * 0.5 + inclination_factor * 0.3 + time_factor * 0.2) * 100
        ))
        
        # Bestimmen, ob dieser Orbit potenziell sichtbar ist
        is_visible = False
        visibility_quality = "Nicht sichtbar"
        if visibility_chance > 10:
            is_visible = True
            if visibility_chance > 70:
                visibility_quality = "Sehr gute Sichtbarkeit"
            elif visibility_chance > 40:
                visibility_quality = "Gute Sichtbarkeit"
            elif visibility_chance > 20:
                visibility_quality = "Mäßige Sichtbarkeit"
            else:
                visibility_quality = "Geringe Sichtbarkeit"
        
        # Zeitfenster für die Sichtbarkeit (typischerweise 5-10 Minuten)
        visibility_duration = int(5 + (visibility_chance / 100) * 5)  # Minuten
        
        # Zeitfenster berechnen
        window_start = orbit_time_de - datetime.timedelta(minutes=visibility_duration/2)
        window_end = orbit_time_de + datetime.timedelta(minutes=visibility_duration/2)
        
        # Informationen zum Orbit sammeln
        orbit_info = {
            "orbit_number": orbit_number,
            "time_utc": current_orbit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "time_de": orbit_time_de.strftime("%Y-%m-%d %H:%M:%S"),
            "visibility_chance": visibility_chance,
            "is_visible": is_visible,
            "quality": visibility_quality,
            "window_start": window_start.strftime("%H:%M:%S"),
            "window_end": window_end.strftime("%H:%M:%S"),
            "visibility_date": orbit_time_de.strftime("%Y-%m-%d"),
            "duration_minutes": visibility_duration
        }
        
        visibility_windows.append(orbit_info)
    
    return visibility_windows

# Beispiel für einen Raketenstart
def main():
    # Beispiel: SpaceX Start von Cape Canaveral nach LEO
    launch_coords = (28.5618, -80.5772)  # Cape Canaveral
    launch_time = datetime.datetime.now(pytz.UTC)  # Aktueller Zeitpunkt als Beispiel
    
    print(f"Startzeit (UTC): {launch_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Startkoordinaten: {launch_coords}")
    print("Berechne mögliche Sichtbarkeitsfenster von Deutschland aus...\n")
    
    # Verschiedene Orbits berechnen
    orbit_configs = [
        {"name": "Niedriger Erdorbit (LEO) - ISS-ähnlich", "height": 400, "inclination": 51.6},
        {"name": "Niedriger Erdorbit (LEO) - Polar", "height": 500, "inclination": 97.5},
        {"name": "Sonnensynchroner Orbit (SSO)", "height": 600, "inclination": 97.8}
    ]
    
    for config in orbit_configs:
        print(f"\n{'='*80}")
        print(f"Orbit-Konfiguration: {config['name']}")
        print(f"{'='*80}")
        
        windows = calculate_rocket_visibility(
            launch_coords,
            launch_time,
            orbit_height=config["height"],
            inclination=config["inclination"]
        )
        
        # Filtern und sortieren der sichtbaren Überflüge
        visible_passes = [w for w in windows if w["is_visible"]]
        visible_passes.sort(key=lambda x: x["visibility_chance"], reverse=True)
        
        # Sichtbare Überflüge nach Datum gruppieren
        passes_by_date = {}
        for window in visible_passes:
            date = window["visibility_date"]
            if date not in passes_by_date:
                passes_by_date[date] = []
            passes_by_date[date].append(window)
        
        # Ausgabe der Ergebnisse
        if visible_passes:
            print(f"\nInsgesamt {len(visible_passes)} mögliche sichtbare Überflüge gefunden.")
            print("\nBeste Sichtbarkeitschancen:")
            
            for i, window in enumerate(visible_passes[:3], 1):
                print(f"{i}. {window['time_de']} (Umrundung {window['orbit_number']}): " + 
                      f"{window['quality']} ({window['visibility_chance']}%)")
                print(f"   Zeitfenster: {window['window_start']} - {window['window_end']} " + 
                      f"({window['duration_minutes']} Minuten)")
            
            print("\nÜberflüge nach Datum:")
            for date, passes in passes_by_date.items():
                print(f"\n{date}:")
                for p in passes:
                    print(f"  • Umrundung {p['orbit_number']}: {p['window_start']} - {p['window_end']} " + 
                          f"({p['quality']})")
        else:
            print("\nKeine sichtbaren Überflüge innerhalb des Berechnungszeitraums gefunden.")

if __name__ == "__main__":
    main()
