"""
subscriber_director.py - Consumidor MQTT con rol Director
Se suscribe a TODOS los topics de la fábrica (acceso completo)
"""

import paho.mqtt.client as mqtt
import ssl, json, time
from datetime import datetime

# ── Configuración ────────────────────────────────────────────
BROKER_HOST = "mosquitto"
BROKER_PORT = 8883
CLIENT_ID   = "subscriber-director"

CERT_CA     = "/certs/ca.crt"
CERT_CLIENT = "/certs/director.crt"
CERT_KEY    = "/certs/director.key"

# Topics a los que se suscribe el Director (acceso total)
TOPICS = [
    ("fabrica/#", 0),  # Wildcard: todos los topics
]

# ── Callbacks MQTT ───────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    codigos = {
        0: "✅ Director conectado al broker",
        1: "❌ Versión de protocolo incorrecta",
        2: "❌ ID de cliente rechazado",
        3: "❌ Broker no disponible",
        4: "❌ Usuario/contraseña incorrectos",
        5: "❌ No autorizado",
    }
    print(codigos.get(rc, f"❌ Error desconocido: {rc}"))
    
    if rc == 0:
        # Suscribirse a los topics
        for topic, qos in TOPICS:
            client.subscribe(topic, qos)
            print(f"   📡 Suscrito a: {topic}")

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
    
    # Colorear según el tipo de topic
    topic = msg.topic
    if "costes" in topic:
        emoji = "💰"
        color = "\033[93m"  # Amarillo
    elif "mantenimiento" in topic or "alerta" in topic:
        emoji = "🔧"
        color = "\033[91m"  # Rojo
    elif "produccion" in topic:
        emoji = "📊"
        color = "\033[94m"  # Azul
    elif "linea" in topic:
        emoji = "⚙️"
        color = "\033[92m"  # Verde
    else:
        emoji = "📨"
        color = "\033[0m"   # Normal
    
    reset = "\033[0m"
    
    print(f"{color}[{timestamp}] {emoji} {topic}{reset}")
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
    print("  👔 Subscriber DIRECTOR - Acceso Total a la Fábrica")
    print("=" * 60)
    print(f"  Broker:   {BROKER_HOST}:{BROKER_PORT}")
    print(f"  Cliente:  {CLIENT_ID}")
    print(f"  Rol:      Director (ve TODOS los datos)")
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
        print("\n\n  ⏹️  Subscriber Director detenido")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()
