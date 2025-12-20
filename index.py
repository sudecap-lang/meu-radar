from flask import Flask, jsonify, request
import requests
from geopy.distance import geodesic

app = Flask(__name__)

# Configuração da API de Clima (wttr.in - Gratuita)
def get_weather_data(lat, lon):
    try:
        url = f"https://wttr.in/{lat},{lon}?format=%C+%t+%v"
        res = requests.get(url, timeout=5).text
        return res.upper()
    except:
        return "CLIMA: INDISPONÍVEL"

@app.route('/api/radar')
def flight_radar():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    
    if not lat or not lon:
        return jsonify({"error": "Localização necessária"}), 400

    u_lat, u_lon = float(lat), float(lon)
    radius_km = 100.0
    
    # Bounding box para API (aproximadamente 1 grau ~ 111km)
    bbox = {
        "lamin": u_lat - 1.0, "lomin": u_lon - 1.0,
        "lamax": u_lat + 1.0, "lomax": u_lon + 1.0
    }
    
    opensky_url = f"https://opensky-network.org/api/states/all?lamin={bbox['lamin']}&lomin={bbox['lomin']}&lamax={bbox['lamax']}&lomax={bbox['lomax']}"
    
    try:
        resp = requests.get(opensky_url, timeout=10).json()
        states = resp.get('states', [])
        weather = get_weather_data(u_lat, u_lon)
        
        nearby_flights = []
        if states:
            for s in states:
                if s[6] and s[5]: # Se houver lat/lon
                    f_coords = (s[6], s[5])
                    dist = geodesic((u_lat, u_lon), f_coords).km
                    if dist <= radius_km:
                        nearby_flights.append({
                            "icao": s[0].upper(),
                            "callsign": s[1].strip() or "S/INFO",
                            "dist": round(dist, 2),
                            "heading": s[10] or 0,
                            "alt": s[7] or 0,
                            "lat": s[6], "lon": s[5]
                        })
        
        nearby_flights.sort(key=lambda x: x['dist'])
        
        return jsonify({
            "flights": nearby_flights,
            "weather": weather,
            "status": "RADAR CONECTADO"
        })
    except Exception as e:
        return jsonify({"error": "Erro na consulta", "weather": "ERRO"}), 500
