import network
import time
import ujson
from machine import Pin, ADC, unique_id
from utime import sleep
from hcsr04 import HCSR04
from umqtt.simple import MQTTClient

# --- PARÁMETROS DE CONEXIÓN ---
WIFI_RED = "Wokwi-GUEST"
WIFI_PASS = ""

# --- PARÁMETROS MQTT ---
MQTT_CLIENT_ID = "contenedor_iot_" + unique_id().hex()
MQTT_BROKER    = "broker.hivemq.com"
MQTT_TOPIC     = "datos/proyecto/grupo2"

# --- CONFIGURACIÓN DE SENSORES ---
contenedores = [
    {
        "nombre": "Contenedor 1 - Alameda San Rafael",
        "sensor_distancia": HCSR04(trigger_pin=2, echo_pin=4),
        "sensor_gas": ADC(Pin(0)),
        "ubicacion": {"lat": 5.03302, "lon": -73.99154}
    },
    {
        "nombre": "Contenedor 2 - Plaza de Mercado",
        "sensor_distancia": HCSR04(trigger_pin=10, echo_pin=5),
        "sensor_gas": ADC(Pin(1)),
        "ubicacion": {"lat": 5.02888, "lon": -74.00081}
    },
    {
        "nombre": "Contenedor 3 - Barrio Barandillas",
        "sensor_distancia": HCSR04(trigger_pin=8, echo_pin=9),
        "sensor_gas": ADC(Pin(3)),
        "ubicacion": {"lat": 5.0286, "lon": -74.0158}
    }
]

# Configurar pines ADC
for c in contenedores:
    c["sensor_gas"].atten(ADC.ATTN_11DB)
    c["sensor_gas"].width(ADC.WIDTH_12BIT)

# Este umbral ya no se usa para enviar datos, pero se puede mantener
# para imprimir alertas en la consola si lo deseas.
UMBRAL_CONTAMINACION = 3000

# --- FUNCIÓN DE CONEXIÓN WIFI ---
def conectaWifi(red, password):
    miRed = network.WLAN(network.STA_IF)
    if not miRed.isconnected():
        miRed.active(True)
        miRed.connect(red, password)
        print(f'Conectando a la red {red}...')
        timeout = time.time()
        while not miRed.isconnected():
            if (time.ticks_diff(time.time(), timeout) > 10):
                return False
    return miRed

# --- PROGRAMA PRINCIPAL ---
wifi = conectaWifi(WIFI_RED, WIFI_PASS)

if wifi:
    print("Conexión WiFi exitosa!")
    print('Datos de la red (IP/Netmask/GW/DNS):', wifi.ifconfig())

    print(f"Conectando al broker MQTT: {MQTT_BROKER}...")
    try:
        client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER)
        client.connect()
        print("¡Conectado al Broker MQTT!")
    except Exception as e:
        print(f"Error al conectar al Broker MQTT: {e}")
        
    while True:
        print("\n--- Revisando estado de los contenedores ---")
        try:
            for i, cont in enumerate(contenedores):
                distancia_cm = cont["sensor_distancia"].distance_cm()
                # Este es el valor numérico que se enviará
                valor_gas = cont["sensor_gas"].read()
                contenedor_id = i + 1

                print(f"DEBUG: Contenedor {contenedor_id} - Valor Gas Leído: {valor_gas}")
                
                nivel_llenado = max(0, min(100, (200 - distancia_cm) / 200 * 100))
                
                # Creamos el payload (el contenido del mensaje) para este contenedor
                message = ujson.dumps({
                    "id_contenedor": contenedor_id,
                    "latitud": cont["ubicacion"]["lat"],
                    "longitud": cont["ubicacion"]["lon"],
                    "nivel_llenado": round(nivel_llenado, 2),
                    # --- MODIFICACIÓN REALIZADA AQUÍ ---
                    # Ahora enviamos el valor numérico en lugar de un texto
                    "calidad_aire": valor_gas
                })

                print(f"Enviando datos para Contenedor {contenedor_id}: {message}")
                client.publish(MQTT_TOPIC, message)
                time.sleep(2)

            print("--- Fin de la revisión ---")
            time.sleep(15)

        except Exception as e:
            print(f"Ocurrió un error en el bucle principal: {e}")
            try:
                print("Intentando reconectar al Broker MQTT...")
                client.disconnect()
                client.connect()
                print("¡Reconectado al Broker MQTT!")
            except Exception as conn_err:
                print(f"Error al reconectar: {conn_err}")
            time.sleep(5)
else:
    print("Imposible conectar a la red WiFi.")