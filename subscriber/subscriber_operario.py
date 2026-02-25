"""
subscriber_operario.py - Consumidor MQTT con rol Operario
Se suscribe solo a líneas de producción (acceso limitado)
"""

import paho.mqtt.client as mqtt
import ssl, json, time
from datetime import datetime

# ── Configuración ────────────────────────────────────────────
BROKER_HOST = "mosquitto"
BROKER_PORT = 8883
CLIENT_ID   = "subscriber-operario"

CERT_CA     = "/certs/ca.crt"
CERT_CLIENT = "/certs/operario.crt"
CERT_KEY    = "/certs/operario.key"

# Topics a los que se suscribe el Operario (acceso limitado)
# Según el ACL, solo puede ver velocidad y temperatura de línea 1
TOPICS = [
    ("fabrica/linea1/velocidad", 0),
    ("fabrica/linea1/temperatura", 0),
    # También se suscribe a otros topics, pero el ACL los bloqueará
    ("fabrica/linea2/#", 0),
    ("fabrica/mantenimiento/#", 0),
    ("fabrica/costes/#", 0),
]

# ── Callbacks MQTT ───────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    codigos = {
        0: "✅ Operario conectado al broker",
        1: "❌ Versión de protocolo incorrecta",
        2: "❌ ID de cliente rechazado",
        3: "❌ Broker no disponible",
        4: "❌ Usuario/contraseña incorrectos",
        5: "❌ No autorizado",
    }
    print(codigos.get(rc, f"❌ Error desconocido: {rc}"))
    
    if rc == 0:
        # Suscribirse a los topics
        print("   📡 Intentando suscribirse a:")
        for topic, qos in TOPICS:
            client.subscribe(topic, qos)
            print(f"      - {topic}")
        print("\n   ⚠️  Nota: Algunos topics serán bloqueados por el ACL")

def on_message(client, userdata, msg):
    """
    Callback cuando llega un mensaje
    """
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    
    try:
        # Intentar parsear como JSON
        payload = json.loads(msg.payload.decode())
        payload_str = json.dumps(payload, ensure_ascii=False)
    except:
        # Si no es JSON, mostrar como texto
        payload_str = msg.payload.decode()
    
    # Solo recibirá mensajes de línea 1 (velocidad y temperatura)
    emoji = "⚙️"
    color = "\033[92m"  # Verde
    reset = "\033[0m"
    
    print(f"{color}[{timestamp}] {emoji} {msg.topic}{reset}")
    print(f"          {payload_str}")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"⚠️  Desconexión inesperada. Código: {rc}")

# ── Setup cliente MQTT con TLS ───────────────────────────────
def crear_cliente():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    # Configurar TLS con certificados mutuos
    client.tls_set(
        ca_certs=CERT_CA,
        certfile=CERT_CLIENT,
        keyfile=CERT_KEY,
        tls_version=ssl.PROTOCOL_TLS
    )
    return client

# ── Bucle principal ──────────────────────────────────────────
def main():
    print("=" * 60)
    print("  👷 Subscriber OPERARIO - Acceso Limitado (Solo Línea 1)")
    print("=" * 60)
    print(f"  Broker:   {BROKER_HOST}:{BROKER_PORT}")
    print(f"  Cliente:  {CLIENT_ID}")
    print(f"  Rol:      Operario (solo velocidad/temp línea 1)")
    print("=" * 60)

    client = crear_cliente()

    # Reintentar conexión si el broker aún no está listo
    while True:
        try:
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            break
        except Exception as e:
            print(f"  ⏳ Esperando broker... ({e})")
            time.sleep(3)

    print("\n  📡 Escuchando mensajes...\n")

    try:
        # Loop bloqueante - procesa mensajes
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n\n  ⏹️  Subscriber Operario detenido")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
