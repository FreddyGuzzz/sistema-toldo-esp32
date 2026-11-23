#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <DHT.h>
#include <ArduinoJson.h>

// Credenciales de la red Wi-Fi (cambiar por la red local o hotspot del celular)
const char* ssid = "NOMBRE_DE_TU_WIFI";
const char* password = "CONTRASENA_DE_TU_WIFI";

WebServer server(80);

// Pines de entrada para los sensores
#define PIN_LDR 34      // Fotorresistencia (entrada analógica ADC1)
#define PIN_DHT 4       // Sensor de temperatura DHT11
#define PIN_LLUVIA 35   // Sensor de lluvia YL-83 (salida analógica AO)
#define DHTTYPE DHT11

DHT dht(PIN_DHT, DHTTYPE);

// Pines de salida para el puente H L298N (Motor de corriente directa)
#define MOTOR_IN1 26
#define MOTOR_IN2 27
#define MOTOR_ENA 25    // Control de velocidad por PWM

// Pines de salida para el módulo LED RGB KY-016 (cátodo común)
#define LED_R 14
#define LED_G 12
#define LED_B 13

// Variables globales de lectura de sensores
int lecturaLuz = 0;
float lecturaTemp = 0.0;
bool hayLluvia = false;

// Parámetros configurables desde la web o desde Python
int umbralLuz = 600;
float umbralTemp = 30.0;

// Variables de control y máquina de estados
bool modoAutomatico = true;
String estadoToldo = "EN_REPOSO";       // Valores: "EXTENDIDO" o "EN_REPOSO"
String estadoNodo = "SISTEMA_ESTABLE";  // Valores: "CONFORT_SOLAR", "PROTECCION_LLUVIA", "SISTEMA_ESTABLE"

// Temporizador no bloqueante para detener el motor al terminar su recorrido
unsigned long tiempoInicioMotor = 0;
bool motorEnMovimiento = false;
const unsigned long DURACION_CARRERA_MS = 3000; // 3 segundos de giro (ajustar según la maqueta)

// Interfaz web almacenada en memoria flash (PROGMEM) para ahorrar RAM
const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sistema Automatizado de Toldo Inteligente</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; background: #f4f6f9; color: #1e293b; margin: 0; padding: 25px; }
    h1 { text-align: center; font-size: 1.75rem; margin-bottom: 4px; color: #0f172a; }
    .subtitulo { text-align: center; color: #64748b; font-size: 0.95rem; margin-bottom: 24px; }

    /* Cuadrícula 2x2 (2 arriba y 2 abajo en escritorio) */
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
  </style>
</head>
<body>
  <h1>Sistema Automatizado de Toldo Inteligente</h1>
  <div class="subtitulo">Panel de Monitoreo y Control en Tiempo Real - ESP32</div>

  <div class="grid">
    <!-- Tarjeta 1: Sensores -->
    <div class="card" id="card-sensores">
      <div class="card-body">
        <h2>1. Monitoreo de Sensores (3)</h2>
        <div class="dato"><span>Luz Solar (LDR):</span><span class="valor" id="val-luz">-- / 4095</span></div>
        <div class="dato"><span>Temperatura (DHT11):</span><span class="valor" id="val-temp">-- °C</span></div>
        <div class="dato"><span>Sensor de Lluvia (YL-83):</span><span class="valor" id="val-lluvia">--</span></div>
      </div>
      <div class="endpoint">Endpoint: GET /api/estado</div>
    </div>

    <!-- Tarjeta 2: Actuadores -->
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

    <!-- Tarjeta 3: Parámetros -->
    <div class="card">
      <div class="card-body">
        <h2>3. Parámetros Configurables (2)</h2>
        <div class="dato"><span>Umbral de Luz (LDR):</span><input type="number" id="in-luz" value="600"></div>
        <div class="dato"><span>Umbral Temperatura (°C):</span><input type="number" step="0.5" id="in-temp" value="30.0"></div>
        <button class="btn-primary" onclick="guardarConfig()">Actualizar Parámetros</button>
      </div>
      <div class="endpoint">Endpoint: POST /api/config</div>
    </div>

    <!-- Tarjeta 4: Control -->
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

  <script>
    let primeraCarga = true;

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

        if (primeraCarga && data.config) {
          document.getElementById('in-luz').value = data.config.umbral_luz;
          document.getElementById('in-temp').value = data.config.umbral_temp;
          primeraCarga = false;
        }
      } catch (e) {
        console.error('Error consultando ESP32:', e);
      }
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
      alert('Parámetros actualizados correctamente');
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
)rawliteral";

// Enciende el color indicado en el LED RGB
void setColorLED(int r, int g, int b) {
  digitalWrite(LED_R, r);
  digitalWrite(LED_G, g);
  digitalWrite(LED_B, b);
}

// Activa el puente H L298N para extender o retraer el toldo
void accionarMotor(String direccion) {
  if (direccion == "EXTENDER" && estadoToldo != "EXTENDIDO") {
    digitalWrite(MOTOR_IN1, HIGH);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, 200);
    tiempoInicioMotor = millis();
    motorEnMovimiento = true;
    estadoToldo = "EXTENDIDO";
  } else if (direccion == "RETRAER" && estadoToldo != "EN_REPOSO") {
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, HIGH);
    analogWrite(MOTOR_ENA, 200);
    tiempoInicioMotor = millis();
    motorEnMovimiento = true;
    estadoToldo = "EN_REPOSO";
  }
}

// Detiene el motor automáticamente al cumplirse el tiempo de recorrido
void detenerMotorSiTermino() {
  if (motorEnMovimiento && (millis() - tiempoInicioMotor >= DURACION_CARRERA_MS)) {
    digitalWrite(MOTOR_IN1, LOW);
    digitalWrite(MOTOR_IN2, LOW);
    analogWrite(MOTOR_ENA, 0);
    motorEnMovimiento = false;
  }
}

// Lee los 3 sensores y actualiza el estado del semáforo y del motor
void evaluarSistema() {
  lecturaLuz = analogRead(PIN_LDR);

  float t = dht.readTemperature();
  if (!isnan(t)) {
    lecturaTemp = t;
  }

  // En el sensor YL-83, entre más agua cae sobre la placa, menor es el voltaje analógico
  int valorLluvia = analogRead(PIN_LLUVIA);
  hayLluvia = (valorLluvia < 2500);

  // Evaluación de prioridad de estados para el LED indicador
  if (hayLluvia) {
    estadoNodo = "PROTECCION_LLUVIA";
    setColorLED(HIGH, LOW, LOW); // Rojo
  } else if (lecturaLuz >= umbralLuz && lecturaTemp >= umbralTemp) {
    estadoNodo = "CONFORT_SOLAR";
    setColorLED(LOW, LOW, HIGH); // Azul
  } else {
    estadoNodo = "SISTEMA_ESTABLE";
    setColorLED(LOW, HIGH, LOW); // Verde
  }

  // Si está en modo automático, mueve el motor según las condiciones ambientales
  if (modoAutomatico) {
    if (hayLluvia) {
      // Prioridad máxima: retraer el toldo para protegerlo de la lluvia
      accionarMotor("RETRAER");
    } else if (estadoNodo == "CONFORT_SOLAR") {
      accionarMotor("EXTENDER");
    } else {
      accionarMotor("RETRAER");
    }
  }
}

// Endpoint GET / -> Entrega la página HTML principal
void handleRoot() {
  server.send(200, "text/html", index_html);
}

// Endpoint GET /api/estado -> Devuelve JSON con sensores, actuadores y umbrales
void handleGetEstado() {
  StaticJsonDocument<320> doc;
  doc["modo_automatico"] = modoAutomatico;
  doc["nodo"] = estadoNodo;

  JsonObject sensores = doc.createNestedObject("sensores");
  sensores["luz"] = lecturaLuz;
  sensores["temperatura"] = lecturaTemp;
  sensores["lluvia"] = hayLluvia;

  JsonObject actuadores = doc.createNestedObject("actuadores");
  actuadores["toldo"] = estadoToldo;

  JsonObject config = doc.createNestedObject("config");
  config["umbral_luz"] = umbralLuz;
  config["umbral_temp"] = umbralTemp;

  String jsonStr;
  serializeJson(doc, jsonStr);
  server.send(200, "application/json", jsonStr);
}

// Endpoint POST /api/config -> Actualiza los umbrales de luz y temperatura
void handlePostConfig() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{"error":"Cuerpo JSON vacío"}");
    return;
  }

  StaticJsonDocument<200> doc;
  deserializeJson(doc, server.arg("plain"));

  if (doc.containsKey("umbral_luz")) {
    umbralLuz = doc["umbral_luz"];
  }
  if (doc.containsKey("umbral_temp")) {
    umbralTemp = doc["umbral_temp"];
  }

  server.send(200, "application/json", "{"status":"ok"}");
}

// Endpoint POST /api/control -> Cambia entre modo automático y control manual
void handlePostControl() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{"error":"Cuerpo JSON vacío"}");
    return;
  }

  StaticJsonDocument<200> doc;
  deserializeJson(doc, server.arg("plain"));
  String accion = doc["accion"] | "";

  if (accion == "AUTO") {
    modoAutomatico = true;
  } else if (accion == "EXTENDER") {
    modoAutomatico = false;
    accionarMotor("EXTENDER");
  } else if (accion == "RETRAER") {
    modoAutomatico = false;
    accionarMotor("RETRAER");
  }

  server.send(200, "application/json", "{"status":"ok"}");
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  pinMode(MOTOR_ENA, OUTPUT);
  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);

  // Conexión a la red Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("
Conectado. IP del ESP32: " + WiFi.localIP().toString());

  // Registro de rutas del servidor web
  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/estado", HTTP_GET, handleGetEstado);
  server.on("/api/config", HTTP_POST, handlePostConfig);
  server.on("/api/control", HTTP_POST, handlePostControl);

  server.begin();
}

void loop() {
  server.handleClient();
  evaluarSistema();
  detenerMotorSiTermino();
}
