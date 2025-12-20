from flask import Flask, render_template_string, jsonify, request
import requests
import time
from math import radians, sin, cos, sqrt, atan2, degrees

app = Flask(__name__)

RAIO_KM = 25.0 

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * atan2(sqrt(a), sqrt(1-a))

def calculate_bearing(lat1, lon1, lat2, lon2):
    start_lat, start_lon = radians(lat1), radians(lon1)
    end_lat, end_lon = radians(lat2), radians(lon2)
    d_lon = end_lon - start_lon
    y = sin(d_lon) * cos(end_lat)
    x = cos(start_lat) * sin(end_lat) - sin(start_lat) * cos(end_lat) * cos(d_lon)
    return (degrees(atan2(y, x)) + 360) % 360

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Radar Boarding Pass</title>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jquery-flapper/1.1.0/flapper.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-flapper/1.1.0/jquery.flapper.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>
        <style>
            :root { --sky-blue: #87CEEB; --navy: #2A6E91; --yellow: #FFD700; }
            body { background: #F0F4F7; margin: 0; display: flex; flex-direction: column; align-items: center; min-height: 100vh; font-family: 'Helvetica Neue', Arial, sans-serif; padding: 10px; }
            
            /* BARRA DE PESQUISA SLIM */
            #search-box { background: white; width: 100%; max-width: 800px; padding: 8px 15px; border-radius: 8px; display: none; gap: 10px; margin-bottom: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); z-index: 100; transition: all 0.6s ease; }
            .hide-search { opacity: 0; transform: translateY(-15px); pointer-events: none; }
            #search-box input { flex: 1; border: 1px solid #ddd; padding: 8px; border-radius: 5px; outline: none; }
            #search-box button { background: var(--navy); color: white; border: none; padding: 0 15px; border-radius: 5px; cursor: pointer; font-size: 12px; font-weight: bold; }

            /* DESIGN DO BILHETE */
            .ticket { background: white; width: 98%; max-width: 850px; height: 480px; border-radius: 25px; display: flex; overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,0.15); position: relative; margin-top: 10px; }
            .stub { background: var(--navy); width: 220px; padding: 30px; color: white; display: flex; flex-direction: column; border-right: 3px dashed rgba(255,255,255,0.3); }
            .seat { font-size: 80px; font-weight: 900; margin: 10px 0; letter-spacing: -2px; }
            
            .main { flex: 1; display: flex; flex-direction: column; position: relative; }
            .header { background: var(--sky-blue); color: white; padding: 20px; text-align: center; letter-spacing: 10px; font-size: 24px; text-transform: uppercase; font-weight: bold; }
            
            .info-grid { padding: 30px 40px; display: grid; grid-template-columns: 1.4fr 1fr; flex: 1; }
            .label { color: #BBB; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 6px; }
            
            /* ÁREAS DE EXIBIÇÃO AUTOMÁTICA */
            .display-area { margin-bottom: 25px; pointer-events: none; height: 50px; }
            .flapper .digit { background-color: #111 !important; color: var(--yellow) !important; border-radius: 4px !important; border: 1px solid #333 !important; }
            
            #compass { font-size: 55px; color: #FF8C00; transition: transform 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275); margin: 10px 0; }
            
            /* BARRA PRETA DE STATUS EXCLUSIVA */
            .footer { background: #000; height: 75px; border-top: 5px solid var(--yellow); display: flex; align-items: center; justify-content: center; width: 100%; overflow: hidden; position: relative; }
            .status-msg { color: var(--yellow); font-family: 'Courier New', monospace; font-size: 19px; font-weight: bold; text-transform: uppercase; }

            #barcode-link { display: block; cursor: pointer; transition: transform 0.2s; }
            #barcode-link:hover { transform: scale(1.05); }
        </style>
    </head>
    <body>
        <div id="search-box">
            <input type="text" id="addr" placeholder="GPS bloqueado? Digite sua cidade...">
            <button onclick="manualSearch()">ATIVAR RADAR</button>
        </div>

        <div class="ticket">
            <div class="stub">
                <div style="font-size: 11px; opacity: 0.8; letter-spacing: 1px;">RADAR STATION</div>
                <div style="font-size: 14px; margin-top: 25px; font-weight: bold;">SEAT</div>
                <div class="seat">19 A</div>
                <div style="margin-top: auto; font-size: 16px; border: 2px solid white; padding: 10px; text-align: center; font-weight: bold;">ATC LIVE</div>
            </div>
            <div class="main">
                <div class="header">BOARDING PASS</div>
                <div class="info-grid">
                    <div>
                        <div class="label">Flight Ident (10 chars)</div>
                        <div class="display-area"><div id="f_call" class="flap"></div></div>
                        <div class="label">Distance (KM)</div>
                        <div class="display-area"><div id="f_dist" class="flap"></div></div>
                    </div>
                    <div style="display:flex; flex-direction:column; align-items:center; border-left: 2px solid #F8F8F8; padding-left: 30px;">
                        <div class="label">A/C Type (8 chars)</div>
                        <div class="display-area"><div id="f_type" class="flap"></div></div>
                        <div id="compass">↑</div>
                        <a id="barcode-link" target="_blank"><svg id="barcode"></svg></a>
                    </div>
                </div>
                <div class="footer">
                    <div id="status-text" class="status-msg">SEARCHING AIRSPACE...</div>
                </div>
            </div>
        </div>

        <script>
            const $fCall = $('#f_call').flapper({width: 10, chars_preset: 'alphanum'});
            const $fDist = $('#f_dist').flapper({width: 10, chars_preset: 'num'});
            const $fType = $('#f_type').flapper({width: 8, chars_preset: 'alphanum'});

            function start(la, lo) {
                const box = document.getElementById('search-box');
                box.classList.add('hide-search');
                setTimeout(() => box.style.display = 'none', 650);

                const updateLoop = () => {
                    fetch(`/api/data?lat=${la}&lon=${lo}&t=${Date.now()}`)
                    .then(res => res.json()).then(data => {
                        if(data.found) {
                            $('#status-text').text("TARGET: " + data.callsign);
                            $fCall.val(data.callsign).change();
                            $fDist.val(data.dist + " KM").change();
                            $fType.val(data.type).change();
                            document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                            JsBarcode("#barcode", data.callsign, {format: "CODE128", width: 1.4, height: 40, displayValue: false, lineColor: "#2A6E91"});
                            document.getElementById('barcode-link').href = `https://www.flightradar24.com/${data.callsign}`;
                        }
                    });
                };
                setInterval(updateLoop, 8000);
                updateLoop();
            }

            function manualSearch() {
                const q = document.getElementById('addr').value;
                if(!q) return;
                fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${q}`)
                .then(r => r.json()).then(res => { if(res.length > 0) start(res[0].lat, res[0].lon); });
            }

            navigator.geolocation.getCurrentPosition(
                p => start(p.coords.latitude, p.coords.longitude),
                e => document.getElementById('search-box').style.display = 'flex'
            );
        </script>
    </body>
    </html>
    ''')

@app.route('/api/data')
def get_data():
    lat_u = float(request.args.get('lat', 0))
    lon_u = float(request.args.get('lon', 0))
    try:
        url = f"https://api.adsb.lol/v2/lat/{lat_u}/lon/{lon_u}/dist/{RAIO_KM}"
        r = requests.get(url, timeout=5).json()
        if r.get('ac'):
            validos = [a for a in r['ac'] if a.get('lat')]
            if validos:
                ac = sorted(validos, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
                return jsonify({
                    "found": True, 
                    "callsign": ac.get('flight', 'N/A').strip()[:10], 
                    "dist": str(round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1)), 
                    "type": ac.get('t', 'UNKN')[:8],
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon'])
                })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run()
