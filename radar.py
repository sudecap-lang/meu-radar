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
    v = int(time.time())
    return render_template_string(f'''
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Radar Boarding Pass v{{v}}</title>
        
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jquery-flapper/1.1.0/flapper.min.css">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-flapper/1.1.0/jquery.flapper.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/jsbarcode@3.11.0/dist/JsBarcode.all.min.js"></script>

        <style>
            :root {{ 
                --sky-blue: #87CEEB; 
                --navy: #2A6E91; 
                --yellow: #FFD700; 
            }}
            
            body {{ 
                background: #F0F4F7; 
                margin: 0; 
                display: flex; 
                flex-direction: column; 
                align-items: center; 
                min-height: 100vh; 
                font-family: sans-serif; 
                padding: 10px;
            }}
            
            /* BARRA DE PESQUISA SLIM */
            #search-box {{ 
                background: white; 
                width: 100%; 
                max-width: 850px; 
                padding: 10px 15px; 
                border-radius: 8px; 
                display: none; 
                gap: 10px; 
                margin-bottom: 15px; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.05);
                transition: opacity 0.6s ease, transform 0.6s ease;
                z-index: 100;
            }}
            
            .hide-search {{ opacity: 0; transform: translateY(-10px); pointer-events: none; }}

            #search-box input {{ flex: 1; border: 1px solid #ddd; padding: 8px; border-radius: 5px; outline: none; }}
            #search-box button {{ background: var(--navy); color: white; border: none; padding: 0 15px; border-radius: 5px; cursor: pointer; font-size: 12px; font-weight: bold; }}

            /* DESIGN DO BILHETE */
            .ticket {{ 
                background: white; 
                width: 100%; 
                max-width: 850px; 
                height: 480px; 
                border-radius: 25px; 
                display: flex; 
                overflow: hidden; 
                box-shadow: 0 30px 60px rgba(0,0,0,0.12);
                position: relative;
            }}
            
            .stub {{ 
                background: var(--navy); 
                width: 220px; 
                padding: 30px; 
                color: white; 
                display: flex; 
                flex-direction: column; 
                border-right: 2px dashed rgba(255,255,255,0.3); 
            }}
            
            .seat {{ font-size: 80px; font-weight: 900; margin: 10px 0; line-height: 1; }}
            
            .main {{ flex: 1; display: flex; flex-direction: column; position: relative; }}
            
            .header {{ 
                background: var(--sky-blue); 
                color: white; 
                padding: 20px; 
                text-align: center; 
                letter-spacing: 8px; 
                font-size: 22px; 
                text-transform: uppercase; 
                font-weight: bold; 
            }}
            
            .info-grid {{ padding: 30px 40px; display: grid; grid-template-columns: 1.4fr 1fr; flex: 1; }}
            .label {{ color: #BBB; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-bottom: 5px; }}
            
            /* AJUSTE DAS PLAQUINHAS PARA NÃO INVADIR O BILHETE */
            .flapper .digit {{ 
                background-color: #1A1A1A !important; 
                color: var(--yellow) !important; 
                border-radius: 3px !important; 
                border: 1px solid #333 !important;
            }}
            
            #compass {{ font-size: 50px; color: #FF8C00; transition: transform 1s; margin: 15px 0; }}
            
            /* BARRA PRETA DE STATUS EXCLUSIVA ABAIXO */
            .footer {{ 
                background: #000; 
                height: 70px; 
                border-top: 5px solid var(--yellow); 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                width: 100%;
                overflow: hidden;
            }}
            
            .status-msg {{ 
                color: var(--yellow); 
                font-family: 'Courier New', monospace; 
                font-weight: bold; 
                font-size: 18px; 
                position: absolute; 
                opacity: 0; 
                transition: opacity 0.6s; 
                text-transform: uppercase;
                pointer-events: none;
            }}
            
            .status-msg.active {{ opacity: 1; }}
        </style>
    </head>
    <body>
        <div id="search-box">
            <input type="text" id="addr" placeholder="Digite sua localização (Ex: São Paulo)">
            <button onclick="manualSearch()">BUSCAR</button>
        </div>

        <div class="ticket">
            <div class="stub">
                <div style="font-size: 10px; opacity: 0.8; letter-spacing: 1px;">FLIGHT STATION</div>
                <div style="font-size: 13px; margin-top: 20px; font-weight: bold;">SEAT</div>
                <div class="seat">19 A</div>
                <div style="margin-top: auto; font-size: 15px; font-weight: bold; text-align: center; border: 1px solid white; padding: 5px;">ATC OK</div>
            </div>
            <div class="main">
                <div class="header">BOARDING RADAR</div>
                <div class="info-grid">
                    <div>
                        <div class="label">Flight (10 Chars)</div>
                        <input id="f_call" class="flap">
                        <div class="label" style="margin-top:20px">Distance (KM)</div>
                        <input id="f_dist" class="flap">
                    </div>
                    <div style="display:flex; flex-direction:column; align-items:center; border-left: 1px solid #F0F0F0; padding-left: 20px;">
                        <div class="label">Type (8 Chars)</div>
                        <input id="f_type" class="flap">
                        <div id="compass">↑</div>
                        <svg id="barcode"></svg>
                    </div>
                </div>
                <div class="footer">
                    <div id="m1" class="status-msg active">SCANNING AIRSPACE...</div>
                    <div id="m2" class="status-msg">WAITING FOR TARGET...</div>
                </div>
            </div>
        </div>

        <script>
            // CONFIGURAÇÃO DAS PLAQUINHAS (10 e 8)
            const $fCall = $('#f_call').flapper({{width: 10, chars_preset: 'alphanum'}});
            const $fDist = $('#f_dist').flapper({{width: 10, chars_preset: 'num'}});
            const $fType = $('#f_type').flapper({{width: 8, chars_preset: 'alphanum'}});

            let lat, lon, flightFound = false, msgIdx = 1;

            // LÓGICA DAS MENSAGENS QUE GIRAM NA BARRA PRETA
            setInterval(() => {{
                if(flightFound) return;
                $(`#m${{msgIdx}}`).removeClass('active');
                msgIdx = msgIdx === 2 ? 1 : msgIdx + 1;
                $(`#m${{msgIdx}}`).addClass('active');
            }}, 4000);

            function start(la, lo) {{
                const box = document.getElementById('search-box');
                box.classList.add('hide-search');
                setTimeout(() => box.style.display = 'none', 600);

                lat = la; lon = lo;
                setInterval(update, 8000);
                update();
            }}

            function update() {{
                fetch(`/api/data?lat=${{lat}}&lon=${{lon}}&t=` + Date.now())
                .then(res => res.json()).then(data => {{
                    if(data.found) {{
                        flightFound = true;
                        document.getElementById('m1').textContent = "TARGET: " + data.callsign;
                        $fCall.val(data.callsign).change();
                        $fDist.val(data.dist + " KM").change();
                        $fType.val(data.type).change();
                        document.getElementById('compass').style.transform = `rotate(${{data.bearing}}deg)`;
                        JsBarcode("#barcode", data.callsign, {{format: "CODE128", width: 1.2, height: 40, displayValue: false, lineColor: "#2A6E91"}});
                    }}
                }});
            }}

            function manualSearch() {{
                const q = document.getElementById('addr').value;
                if(!q) return;
                fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${{q}}`)
                .then(r => r.json()).then(res => {{
                    if(res.length > 0) start(res[0].lat, res[0].lon);
                }});
            }}

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
        url = f"https://api.adsb.lol/v2/lat/{{lat_u}}/lon/{{lon_u}}/dist/{{RAIO_KM}}"
        r = requests.get(url, timeout=5).json()
        if r.get('ac'):
            validos = [a for a in r['ac'] if a.get('lat')]
            if validos:
                ac = sorted(validos, key=lambda x: haversine(lat_u, lon_u, x['lat'], x['lon']))[0]
                return jsonify({{
                    "found": True, 
                    "callsign": ac.get('flight', 'UNKN').strip()[:10], 
                    "dist": str(round(haversine(lat_u, lon_u, ac['lat'], ac['lon']), 1)), 
                    "bearing": calculate_bearing(lat_u, lon_u, ac['lat'], ac['lon']),
                    "type": ac.get('t', 'UNKN')[:8]
                }})
    except: pass
    return jsonify({{"found": False}})

if __name__ == '__main__':
    app.run()
