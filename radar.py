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
            :root { 
                --sky-blue: #87CEEB; /* AZUL CLARO QUE PEDISTE */
                --navy: #2A6E91; 
                --yellow: #FFD700; 
            }
            body { 
                background: #E0F2F7; 
                margin: 0; 
                display: flex; 
                flex-direction: column; 
                align-items: center; 
                min-height: 100vh; 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            #search-box { 
                background: white; 
                width: 90%; 
                max-width: 800px; 
                padding: 10px; 
                border-radius: 0 0 15px 15px; 
                display: none; 
                gap: 10px; 
                box-shadow: 0 5px 15px rgba(0,0,0,0.1); 
                z-index: 100;
            }
            #search-box input { flex: 1; border: 1px solid #ddd; padding: 10px; border-radius: 8px; }
            #search-box button { background: var(--sky-blue); color: white; border: none; padding: 0 20px; border-radius: 8px; cursor: pointer; font-weight: bold; }

            .ticket { 
                background: white; 
                width: 95%; 
                max-width: 850px; 
                height: 460px; 
                border-radius: 30px; 
                display: flex; 
                overflow: hidden; 
                box-shadow: 0 25px 50px rgba(0,0,0,0.1); 
                margin-top: 30px;
                border: 1px solid #d1eef7;
            }
            
            .stub { 
                background: var(--navy); 
                width: 200px; 
                padding: 30px; 
                color: white; 
                display: flex; 
                flex-direction: column; 
                border-right: 3px dashed #87CEEB; 
            }
            
            .main { flex: 1; display: flex; flex-direction: column; }
            
            .header { 
                background: var(--sky-blue); 
                color: white; 
                padding: 15px; 
                text-align: center; 
                font-size: 28px; 
                font-weight: 800; 
                letter-spacing: 5px;
            }
            
            .info-grid { 
                padding: 30px; 
                display: grid; 
                grid-template-columns: 1.2fr 1fr; 
                flex: 1;
                background: linear-gradient(to bottom, #ffffff, #f0fbff);
            }
            
            .label { color: var(--sky-blue); font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }
            .display-area { margin-bottom: 20px; }
            
            .flapper .digit { background-color: #000 !important; color: var(--yellow) !important; border-radius: 3px !important; }
            
            #compass { font-size: 50px; color: #ff9800; transition: transform 1s; margin: 10px 0; }
            
            #barcode-link { display: block; margin-top: 10px; cursor: pointer; }

            /* BARRA PRETA SLIM NO FUNDO */
            .footer { 
                background: #000; 
                height: 60px; 
                border-top: 4px solid var(--yellow); 
                display: flex; 
                align-items: center; 
                justify-content: center;
            }
            .status-msg { color: var(--yellow); font-family: 'Courier New', monospace; font-size: 18px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div id="search-box">
            <input type="text" id="addr" placeholder="Digite a sua localização...">
            <button onclick="manualSearch()">ATIVAR</button>
        </div>

        <div class="ticket">
            <div class="stub">
                <div style="font-size: 10px; opacity: 0.7;">BOARDING PASS</div>
                <div style="font-size: 80px; font-weight: 900; margin: 20px 0;">19A</div>
                <div style="margin-top: auto; border: 2px solid white; padding: 10px; text-align: center; font-weight: bold;">LIVE</div>
            </div>
            <div class="main">
                <div class="header">FLIGHT RADAR</div>
                <div class="info-grid">
                    <div>
                        <div class="label">Flight / Ident</div>
                        <div class="display-area"><div id="f_call" class="flap"></div></div>
                        <div class="label">Distance (KM)</div>
                        <div class="display-area"><div id="f_dist" class="flap"></div></div>
                    </div>
                    <div style="display:flex; flex-direction:column; align-items:center; border-left: 1px solid #e1f5fe; padding-left: 20px;">
                        <div class="label">Aircraft Type</div>
                        <div class="display-area"><div id="f_type" class="flap"></div></div>
                        <div id="compass">↑</div>
                        <a id="barcode-link" target="_blank"><svg id="barcode"></svg></a>
                    </div>
                </div>
                <div class="footer">
                    <div id="status-text" class="status-msg">SEARCHING...</div>
                </div>
            </div>
        </div>

        <script>
            const $fCall = $('#f_call').flapper({width: 10, chars_preset: 'alphanum'});
            const $fDist = $('#f_dist').flapper({width: 10, chars_preset: 'num'});
            const $fType = $('#f_type').flapper({width: 8, chars_preset: 'alphanum'});

            function start(lat, lon) {
                $('#search-box').hide();
                setInterval(() => {
                    fetch(`/api/data?lat=${lat}&lon=${lon}&t=${Date.now()}`)
                    .then(r => r.json()).then(data => {
                        if(data.found) {
                            $('#status-text').text("ACQUIRED: " + data.callsign);
                            $fCall.val(data.callsign).change();
                            $fDist.val(data.dist).change();
                            $fType.val(data.type).change();
                            document.getElementById('compass').style.transform = `rotate(${data.bearing}deg)`;
                            JsBarcode("#barcode", data.callsign, {format: "CODE128", width: 1.2, height: 40, displayValue: false, lineColor: "#2A6E91"});
                            document.getElementById('barcode-link').href = `https://www.flightradar24.com/${data.callsign}`;
                        }
                    });
                }, 8000);
            }

            function manualSearch() {
                const q = document.getElementById('addr').value;
                fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${q}`)
                .then(r => r.json()).then(res => { if(res.length > 0) start(res[0].lat, res[0].lon); });
            }

            navigator.geolocation.getCurrentPosition(
                p => start(p.coords.latitude, p.coords.longitude),
                e => $('#search-box').css('display', 'flex')
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
            ac = sorted([a for a in r['ac'] if a.get('lat')], key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
            return jsonify({
                "found": True, 
                "callsign": ac.get('flight', 'N/A').strip(), 
                "dist": str(round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1)), 
                "type": ac.get('t', 'UNKN')[:8],
                "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon'])
            })
    except: pass
    return jsonify({"found": False})

if __name__ == '__main__':
    app.run()
