import json
import paho.mqtt.client as mqtt
import requests
import time

# Credenciales de Arduino IoT Cloud (Tus datos)
CLIENT_ID = "foXCtV5AOmQXV1AKD25z296X6S93PXmG"
CLIENT_SECRET = "HzUcuoPvMzr3FqBVAzWM7NCehjAUQK7z51szubPHRKO6UoaBcA90bZeNbjE8KSyG"
THING_ID = "290d1ad9-0b01-4b89-a65c-06c9130d9dad"

# IDs de las propiedades en Arduino Cloud (Tu estructura)
VARIABLES = {
    "contenedor1": {
        "calidad_aire": "70cc0e27-e191-4805-ad48-b9f6998a1df2",
        "nivel_llenado": "b9d03e71-8c1d-417e-b194-02f4ea228a7e"
        # Los IDs de las variables de tipo float lat/lon no los usaremos
    },
    "contenedor2": {
        "calidad_aire": "744d07f1-4503-4141-b130-c2cd52d46cf9",
        
        
        "nivel_llenado": "f5284deb-503c-4b47-8815-da8eeacb87c0"
    },
    "contenedor3": {
        "calidad_aire": "8dde61c1-30ae-4d02-bf01-b5baafc996c5",
        "nivel_llenado": "77d8cc11-fa1e-45dc-abbe-f22c614eeb9c"
    },
    "ubicaciones": {
        # IDs de las variables tipo Location para los mapas
        "ubicacionContenedor1": "02e11197-752f-47d6-a006-a5aee65aeb16",
        "ubicacionContenedor2": "4870e76a-e961-48a3-833b-f6676b09fa05",
        "ubicacionContenedor3": "f52e62cc-67db-4ba8-8260-cd26eeb2d053",
        "ubicacionRelleno": "b025d0fc-5d8d-4d9d-8aa9-2463fece55bc"
    }
}


# Configuración MQTT
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883 # Mantener 1883, ver explicación abajo
MQTT_TOPIC = "datos/proyecto/grupo2"

token_info = {}

# --- FUNCIÓN PARA OBTENER TOKEN (SIN CAMBIOS) ---
def obtener_token():
    global token_info
    url = "https://api2.arduino.cc/iot/v1/clients/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "audience": "https://api2.arduino.cc/iot"
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        token_info = response.json()
        token_info["timestamp"] = time.time()
        print("[AUTH] Token obtenido correctamente.")
    except Exception as e:
        print(f"[ERROR al obtener token]: {e}")

# --- FUNCIÓN PARA VALIDAR TOKEN (SIN CAMBIOS) ---
def token_valido():
    if not token_info: return False
    expires_in = token_info.get("expires_in", 0)
    timestamp = token_info.get("timestamp", 0)
    return time.time() - timestamp < expires_in - 60

# --- TU FUNCIÓN PARA ACTUALIZAR VARIABLES (SIN CAMBIOS) ---
def actualizar_variable(property_id, value):
    if not token_valido():
        obtener_token()
    
    headers = {
        "Authorization": f"Bearer {token_info['access_token']}",
        "Content-Type": "application/json"
    }
    url = f"https://api2.arduino.cc/iot/v2/things/{THING_ID}/properties/{property_id}/publish"
    
    # El cuerpo del mensaje para la API
    data = json.dumps({"value": value})
    
    response = requests.put(url, headers=headers, data=data)
    if response.status_code == 200:
        print(f"[✔] Enviado a {property_id} = {value}")
    else:
        print(f"[API ERROR] {property_id} | Estado: {response.status_code} | Respuesta: {response.text}")

# --- FUNCIÓN on_connect (MODIFICADA) ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[MQTT] Conectado correctamente")
        client.subscribe(MQTT_TOPIC)
        
        # --- ENVIAMOS LA UBICACIÓN DEL RELLENO UNA SOLA VEZ ---
        try:
            print("Enviando ubicación fija del relleno sanitario...")
            id_relleno = VARIABLES["ubicaciones"]["ubicacionRelleno"]
            coords_relleno = {"lat": 4.6458, "lon": -74.2858}
            actualizar_variable(id_relleno, coords_relleno)
        except Exception as e:
            print(f"[ERROR] No se pudo enviar la ubicación del relleno: {e}")
        # --------------------------------------------------------
        
    else:
        print(f"[MQTT] Error de conexión: {rc}")


# ======================================================================
# --- FUNCIÓN on_message (ÚNICO CAMBIO, LÓGICA CORREGIDA) ---
# ======================================================================
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[MQTT] Mensaje recibido: {payload}")

        # 1. Obtener el ID del contenedor (ej: 1, 2, o 3)
        contenedor_id_num = payload.get("id_contenedor")
        if not contenedor_id_num:
            return # Si no hay ID, ignoramos el mensaje

        # 2. Construir las claves para buscar en nuestro diccionario de VARIABLES
        contenedor_key = f"contenedor{contenedor_id_num}"
        ubicacion_key = f"ubicacionContenedor{contenedor_id_num}"

        if contenedor_key in VARIABLES and ubicacion_key in VARIABLES["ubicaciones"]:
            # 3. Extraer los datos del payload
            lat = payload.get("latitud")
            lon = payload.get("longitud")
            nivel = payload.get("nivel_llenado")
            calidad = payload.get("calidad_aire")

            # 4. Obtener los IDs de las propiedades de Arduino Cloud
            prop_ids = VARIABLES[contenedor_key]
            id_ubicacion = VARIABLES["ubicaciones"][ubicacion_key]

            # 5. Actualizar las variables en la nube
            if nivel is not None:
                # Usamos los IDs de las variables float para los gauges
                actualizar_variable(prop_ids["nivel_llenado"], nivel)

            if calidad is not None:
                # Usamos los IDs de las variables string para la calidad
                actualizar_variable(prop_ids["calidad_aire"], calidad)

            if lat is not None and lon is not None:
                # ¡IMPORTANTE! Para la variable Location, el valor debe ser un diccionario
                location_value = {"lat": lat, "lon": lon}
                actualizar_variable(id_ubicacion, location_value)
        
    except Exception as e:
        print(f"[ERROR] Error procesando el mensaje: {e}")

# --- CÓDIGO DE INICIO (SIN CAMBIOS) ---
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_forever()