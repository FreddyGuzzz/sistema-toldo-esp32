import tkinter as tk
from tkinter import ttk, messagebox
import requests
import csv
import os
from datetime import datetime

# Dirección IP que muestra el ESP32 en el Monitor Serie al conectarse
ESP32_IP = "http://192.168.1.100"
ARCHIVO_CSV = "historial_sensores_toldo.csv"


class AppToldo:
    def __init__(self, root):
        self.root = root
        self.root.title("Subsistema PC - Monitoreo y Registro de Toldo")
        self.root.geometry("540x480")
        self.root.resizable(False, False)

        self.inicializar_csv()
        self.crear_interfaz()
        self.consultar_esp32()

    # Crea el archivo CSV con sus encabezados si todavía no existe
    def inicializar_csv(self):
        if not os.path.exists(ARCHIVO_CSV):
            with open(ARCHIVO_CSV, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Fecha_Hora", "Luz_LDR", "Temperatura_C", "Lluvia", "Estado_Toldo", "Nodo_Estado"])

    # Construye los bloques de la ventana gráfica en Tkinter
    def crear_interfaz(self):
        frame_ip = ttk.LabelFrame(self.root, text="Conexión con ESP32", padding=10)
        frame_ip.pack(fill="x", padx=15, pady=8)

        ttk.Label(frame_ip, text="URL ESP32:").pack(side="left")
        self.entry_ip = ttk.Entry(frame_ip, width=28)
        self.entry_ip.insert(0, ESP32_IP)
        self.entry_ip.pack(side="left", padx=8)
        self.lbl_conexion = ttk.Label(frame_ip, text="Desconectado", foreground="red")
        self.lbl_conexion.pack(side="right")

        # Sección de lectura de sensores y actuadores
        frame_datos = ttk.LabelFrame(self.root, text="Telemetría en Tiempo Real", padding=10)
        frame_datos.pack(fill="x", padx=15, pady=8)

        self.lbl_luz = ttk.Label(frame_datos, text="Luz Solar (LDR): --", font=("Segoe UI", 10, "bold"))
        self.lbl_luz.pack(anchor="w", pady=2)

        self.lbl_temp = ttk.Label(frame_datos, text="Temperatura (DHT11): --", font=("Segoe UI", 10, "bold"))
        self.lbl_temp.pack(anchor="w", pady=2)

        self.lbl_lluvia = ttk.Label(frame_datos, text="Sensor de Lluvia: --", font=("Segoe UI", 10, "bold"))
        self.lbl_lluvia.pack(anchor="w", pady=2)

        self.lbl_actuadores = ttk.Label(frame_datos, text="Toldo: -- | Estado: --", font=("Segoe UI", 10))
        self.lbl_actuadores.pack(anchor="w", pady=4)

        # Sección para modificar umbrales remotos
        frame_cfg = ttk.LabelFrame(self.root, text="Parámetros Configurables (Umbrales)", padding=10)
        frame_cfg.pack(fill="x", padx=15, pady=8)

        ttk.Label(frame_cfg, text="Umbral Luz:").grid(row=0, column=0, padx=5, pady=4)
        self.entry_luz = ttk.Entry(frame_cfg, width=10)
        self.entry_luz.insert(0, "600")
        self.entry_luz.grid(row=0, column=1, padx=5)

        ttk.Label(frame_cfg, text="Umbral Temp (°C):").grid(row=0, column=2, padx=5, pady=4)
        self.entry_temp = ttk.Entry(frame_cfg, width=10)
        self.entry_temp.insert(0, "30.0")
        self.entry_temp.grid(row=0, column=3, padx=5)

        ttk.Button(frame_cfg, text="Enviar Configuración", command=self.enviar_config).grid(row=0, column=4, padx=8)

        # Botones de control manual y automático
        frame_ctrl = ttk.LabelFrame(self.root, text="Control de Operación", padding=10)
        frame_ctrl.pack(fill="x", padx=15, pady=8)

        ttk.Button(frame_ctrl, text="Extender Toldo", command=lambda: self.enviar_control("EXTENDER")).pack(side="left", expand=True, fill="x", padx=4)
        ttk.Button(frame_ctrl, text="Retraer Toldo", command=lambda: self.enviar_control("RETRAER")).pack(side="left", expand=True, fill="x", padx=4)
        ttk.Button(frame_ctrl, text="Modo Automático", command=lambda: self.enviar_control("AUTO")).pack(side="left", expand=True, fill="x", padx=4)

        self.lbl_csv = ttk.Label(self.root, text=f"Guardando registros cada 2s en: {ARCHIVO_CSV}", foreground="#475569")
        self.lbl_csv.pack(pady=8)

    # Consulta el endpoint GET /api/estado cada 2 segundos y guarda el registro en CSV
    def consultar_esp32(self):
        url_base = self.entry_ip.get().strip()
        try:
            resp = requests.get(f"{url_base}/api/estado", timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                self.lbl_conexion.config(text="Conectado", foreground="green")

                luz = data["sensores"]["luz"]
                temp = data["sensores"]["temperatura"]
                lluvia = data["sensores"]["lluvia"]
                toldo = data["actuadores"]["toldo"]
                nodo = data["nodo"]

                self.lbl_luz.config(text=f"Luz Solar (LDR): {luz} / 4095")
                self.lbl_temp.config(text=f"Temperatura (DHT11): {temp:.1f} °C")
                self.lbl_lluvia.config(
                    text=f"Sensor de Lluvia: {'¡LLUVIA DETECTADA!' if lluvia else 'Seco'}",
                    foreground="red" if lluvia else "green"
                )
                self.lbl_actuadores.config(text=f"Toldo: {toldo} | Estado: {nodo}")

                with open(ARCHIVO_CSV, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), luz, temp, lluvia, toldo, nodo])
        except Exception:
            self.lbl_conexion.config(text="Sin respuesta", foreground="red")

        self.root.after(2000, self.consultar_esp32)

    # Envía los nuevos umbrales al ESP32 mediante POST /api/config
    def enviar_config(self):
        url_base = self.entry_ip.get().strip()
        try:
            payload = {
                "umbral_luz": int(self.entry_luz.get()),
                "umbral_temp": float(self.entry_temp.get())
            }
            requests.post(f"{url_base}/api/config", json=payload, timeout=2)
            messagebox.showinfo("Configuración", "Parámetros actualizados en el sistema")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar con el sistema: {e}")

    # Envía comandos de movimiento o cambio de modo mediante POST /api/control
    def enviar_control(self, accion):
        url_base = self.entry_ip.get().strip()
        try:
            requests.post(f"{url_base}/api/control", json={"accion": accion}, timeout=2)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo enviar comando: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = AppToldo(root)
    root.mainloop()
