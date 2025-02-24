import requests
import datetime
import pytz
import streamlit as st

def get_upcoming_launches():
    # API-URL für die nächsten fünf Raketenstarts (Free Access)
    url = "https://fdo.rocketlaunch.live/json/launches/next/5"
    
    response = requests.get(url)
    if response.status_code == 200:
        launches = response.json().get("result", [])
        cet = pytz.timezone("Europe/Berlin")  # Mitteleuropäische Zeitzone
        
        launch_data = []
        for launch in launches:
            name = launch.get("name", "Unbekannt")
            vehicle = launch.get("vehicle", {}).get("name", "Unbekannte Rakete")
            t0_utc = launch.get("t0")
            
            if t0_utc:
                t0_utc_dt = datetime.datetime.fromisoformat(t0_utc.replace("Z", "+00:00"))
                t0_cet = t0_utc_dt.astimezone(cet).strftime('%Y-%m-%d %H:%M:%S %Z')
            else:
                t0_cet = "Unbekannt"
            
            launch_data.append((t0_cet, vehicle, name))
        
        return launch_data
    else:
        return []

st.title("Next 5 Rocket Launches")
launches = get_upcoming_launches()

if launches:
    for launch in launches:
        st.write(f"**Start:** {launch[0]}")
        st.write(f"**Rakete:** {launch[1]}")
        st.write(f"**Mission:** {launch[2]}")
        st.write("---")
else:
    st.write("Keine Daten verfügbar.")
