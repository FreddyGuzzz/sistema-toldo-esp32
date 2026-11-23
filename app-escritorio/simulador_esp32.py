from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import random

# Estado inicial en memoria para pruebas sin hardware conectado
estado = {
    "luz": 780,
    "temperatura": 32.5,
    "lluvia": False,
    "umbral_luz": 600,
    "umbral_temp": 30.0,
    "modo_automatico": True,
    "toldo": "EXTENDIDO",
    "nodo": "CONFORT_SOLAR"
}

HTML_DASHBOARD = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sistema Automatizado de Toldo Inteligente</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; background: #f4f6f9; color: #1e293b; margin: 0; padding: 25px; }
    h1 { text-align: center; font-size: 1.75rem; margin-bottom: 4px; color: #0f172a; }
    .subtitulo { text-align: center; color: #64748b; font-size: 0.95rem; margin-bottom: 24px; }

    .grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 24px;
      max-width: 950px;
      margin: auto;
    }

    @media (max-width: 768px) {
      .grid { grid-template-columns: 1fr; }
    }

    .card {
      background: #ffffff;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
      border: 1.5px solid #e2e8f0;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      min-height: 280px;
      box-sizing: border-box;
      transition: border-color 0.3s, background-color 0.3s;
    }

    .card.alerta-lluvia { border-color: #f87171; background: #fef2f2; }
    .card-body { flex-grow: 1; }
    .card h2 { font-size: 1.15rem; font-weight: 700; margin-top: 0; margin-bottom: 16px; border-bottom: 1.5px solid #f1f5f9; padding-bottom: 8px; color: #0f172a; }
    .card.alerta-lluvia h2 { border-bottom-color: #fca5a5; }

    .dato { display: flex; justify-content: space-between; align-items: center; margin: 13px 0; font-weight: 500; font-size: 0.95rem; }
    .valor { font-weight: 700; color: #2563eb; font-size: 1.05rem; }
    .lluvia-activa { color: #dc2626 !important; font-weight: 800; }
    .seco { color: #16a34a !important; }

    .barra-bg { background: #e2e8f0; border-radius: 8px; height: 18px; overflow: hidden; margin: 14px 0; border: 1px solid #cbd5e1; }
    .barra-fill { background: #2563eb; height: 100%; width: 0%; transition: width 0.6s ease-out; }

    .led-badge { display: inline-flex; align-items: center; gap: 8px; font-weight: 700; }
    .dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; box-shadow: 0 0 6px rgba(0,0,0,0.15); }

    input { width: 85px; padding: 6px; border: 1.5px solid #cbd5e1; border-radius: 6px; text-align: center; font-size: 0.95rem; font-weight: 600; color: #1e293b; background: #f8fafc; }
    input:focus { outline: none; border-color: #2563eb; background: #ffffff; }

    button { width: 100%; padding: 11px; border: none; border-radius: 8px; font-weight: 700; cursor: pointer; margin-top: 8px; font-size: 0.95rem; transition: background 0.2s; }
    .btn-primary { background: #2563eb; color: #ffffff; }
    .btn-primary:hover { background: #1d4ed8; }
    .btn-danger { background: #dc2626; color: #ffffff; }
    .btn-danger:hover { background: #b91c1c; }
    .btn-group { display: flex; gap: 10px; }
    .badge-modo { padding: 4px 10px; border-radius: 6px; color: #ffffff; font-size: 0.85rem; font-weight: 700; }

    .endpoint {
      font-size: 0.75rem;
      color: #94a3b8;
      text-align: right;
      font-family: monospace;
      margin-top: 15px;
      padding-top: 10px;
      border-top: 1px dashed #f1f5f9;
    }
    .card.alerta-lluvia .endpoint { border-top-color: #fee2e2; color: #f87171; }

    .sim-bar { max-width: 950px; margin: 24px auto 0; background: #e2e8f0; padding: 12px 24px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
    .sim-btn { width: auto; margin-top: 0; padding: 8px 16px; background: #0284c7; color: #ffffff; border-radius: 6px; font-size: 0.85rem; }
    .sim-btn:hover { background: #0369a1; }
  </style>
</head>
<body>
  <h1>Sistema Automatizado de Toldo Inteligente</h1>
  <div class="subtitulo">Panel de Monitoreo y Control en Tiempo Real - ESP32</div>

  <div class="grid">
    <div class="card" id="card-sensores">
      <div class="card-body">
        <h2>1. Monitoreo de Sensores (3)</h2>
        <div class="dato"><span>Luz Solar (LDR):</span><span class="valor" id="val-luz">-- / 4095</span></div>
        <div class="dato"><span>Temperatura (DHT11):</span><span class="valor" id="val-temp">-- °C</span></div>
        <div class="dato"><span>Sensor de Lluvia (YL-83):</span><span class="valor" id="val-lluvia">--</span></div>
      </div>
      <div class="endpoint">Endpoint: GET /api/estado</div>
    </div>

    <div class="card">
      <div class="card-body">
        <h2>2. Estado de Actuadores (2)</h2>
        <div class="dato"><span>Actuador 1 (Motor CD):</span><span class="valor" id="val-toldo">--</span></div>
        <div class="barra-bg"><div class="barra-fill" id="barra-toldo"></div></div>
        <div class="dato">
          <span>Actuador 2 (LED RGB KY-016):</span>
          <span class="led-badge"><span class="dot" id="led-dot"></span><span id="val-led">--</span></span>
        </div>
      </div>
      <div class="endpoint">Endpoint: GET /api/estado</div>
    </div>

    <div class="card">
      <div class="card-body">
        <h2>3. Parámetros Configurables (2)</h2>
        <div class="dato"><span>Umbral de Luz (LDR):</span><input type="number" id="in-luz" value="600"></div>
        <div class="dato"><span>Umbral Temperatura (°C):</span><input type="number" step="0.5" id="in-temp" value="30.0"></div>
        <button class="btn-primary" onclick="guardarConfig()">Actualizar Parámetros</button>
      </div>
      <div class="endpoint">Endpoint: POST /api/config</div>
    </div>

    <div class="card">
      <div class="card-body">
        <h2>4. Control de Operación</h2>
        <div class="dato">
          <span>Modo del Sistema:</span>
          <span class="badge-modo" id="badge-modo" style="background:#16a34a;">Automático</span>
        </div>
        <div class="btn-group">
          <button class="btn-primary" onclick="enviarControl('EXTENDER')">Extender Toldo (Abrir)</button>
          <button class="btn-danger" onclick="enviarControl('RETRAER')">Retraer Toldo (Cerrar)</button>
        </div>
        <button style="background:#475569; color:#ffffff;" onclick="enviarControl('AUTO')">Volver a Modo Automático</button>
      </div>
      <div class="endpoint">Endpoint: POST /api/control</div>
    </div>
  </div>

  <div class="sim-bar">
    <span><strong>Herramienta de prueba sin hardware:</strong></span>
    <button class="sim-btn" onclick="enviarControl('TOGGLE_LLUVIA')">Simular / Quitar Lluvia</button>
  </div>

  <script>
    async function actualizarEstado() {
      try {
        const res = await fetch('/api/estado');
        const data = await res.json();

        document.getElementById('val-luz').innerText = `${data.sensores.luz} / 4095`;
        document.getElementById('val-temp').innerText = `${data.sensores.temperatura.toFixed(1)} °C`;

        const elLluvia = document.getElementById('val-lluvia');
        const cardSensores = document.getElementById('card-sensores');
        if (data.sensores.lluvia) {
          elLluvia.innerText = '¡Lluvia Detectada!';
          elLluvia.className = 'valor lluvia-activa';
          cardSensores.classList.add('alerta-lluvia');
        } else {
          elLluvia.innerText = 'Seco (Sin lluvia)';
          elLluvia.className = 'valor seco';
          cardSensores.classList.remove('alerta-lluvia');
        }

        const extendido = data.actuadores.toldo === 'EXTENDIDO';
        document.getElementById('val-toldo').innerText = extendido ? 'Toldo Extendido (100%)' : 'En Reposo (0%)';
        document.getElementById('barra-toldo').style.width = extendido ? '100%' : '0%';

        const dot = document.getElementById('led-dot');
        const txtLed = document.getElementById('val-led');
        if (data.nodo === 'PROTECCION_LLUVIA') {
          dot.style.background = '#dc2626'; txtLed.innerText = 'Rojo (Protección Lluvia)';
        } else if (data.nodo === 'CONFORT_SOLAR') {
          dot.style.background = '#2563eb'; txtLed.innerText = 'Azul (Confort Solar)';
        } else {
          dot.style.background = '#16a34a'; txtLed.innerText = 'Verde (Sistema Estable)';
        }

        const badge = document.getElementById('badge-modo');
        badge.innerText = data.modo_automatico ? 'Automático' : 'Manual';
        badge.style.background = data.modo_automatico ? '#16a34a' : '#d97706';
      } catch (e) { console.error(e); }
    }

    async function guardarConfig() {
      const payload = {
        umbral_luz: parseInt(document.getElementById('in-luz').value),
        umbral_temp: parseFloat(document.getElementById('in-temp').value)
      };
      await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      actualizarEstado();
    }

    async function enviarControl(accion) {
      await fetch('/api/control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accion: accion })
      });
      actualizarEstado();
    }

    setInterval(actualizarEstado, 1500);
    actualizarEstado();
  </script>
</body>
</html>
"""

# Replica la lógica de estados del ESP32 con variaciones aleatorias leves
def evaluar_logica():
    estado["luz"] = max(100, min(4095, estado["luz"] + random.randint(-25, 25)))
    estado["temperatura"] = round(max(18.0, min(42.0, estado["temperatura"] + random.uniform(-0.4, 0.4))), 1)

    if estado["lluvia"]:
        estado["nodo"] = "PROTECCION_LLUVIA"
    elif estado["luz"] >= estado["umbral_luz"] and estado["temperatura"] >= estado["umbral_temp"]:
        estado["nodo"] = "CONFORT_SOLAR"
    else:
        estado["nodo"] = "SISTEMA_ESTABLE"

    if estado["modo_automatico"]:
        if estado["lluvia"]:
            estado["toldo"] = "EN_REPOSO"
        elif estado["nodo"] == "CONFORT_SOLAR":
            estado["toldo"] = "EXTENDIDO"
        else:
            estado["toldo"] = "EN_REPOSO"


class SimuladorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_DASHBOARD.encode("utf-8"))
        elif self.path == "/api/estado":
            evaluar_logica()
            respuesta = {
                "modo_automatico": estado["modo_automatico"],
                "nodo": estado["nodo"],
                "sensores": {
                    "luz": estado["luz"],
                    "temperatura": estado["temperatura"],
                    "lluvia": estado["lluvia"]
                },
                "actuadores": {
                    "toldo": estado["toldo"]
                },
                "config": {
                    "umbral_luz": estado["umbral_luz"],
                    "umbral_temp": estado["umbral_temp"]
                }
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(respuesta).encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

        if self.path == "/api/config":
            if "umbral_luz" in body:
                estado["umbral_luz"] = int(body["umbral_luz"])
            if "umbral_temp" in body:
                estado["umbral_temp"] = float(body["umbral_temp"])
        elif self.path == "/api/control":
            accion = body.get("accion", "")
            if accion == "AUTO":
                estado["modo_automatico"] = True
            elif accion == "EXTENDER":
                estado["modo_automatico"] = False
                estado["toldo"] = "EXTENDIDO"
            elif accion == "RETRAER":
                estado["modo_automatico"] = False
                estado["toldo"] = "EN_REPOSO"
            elif accion == "TOGGLE_LLUVIA":
                estado["lluvia"] = not estado["lluvia"]

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8080), SimuladorHandler)
    print("Servidor local activo en: http://127.0.0.1:8080")
    server.serve_forever()
