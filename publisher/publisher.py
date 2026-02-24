"""
publisher.py - Simulador de sensores de Fábrica IoT
Publica datos realistas de dos líneas de producción
con certificado de 'publisher' (acceso total)
"""

import paho.mqtt.client as mqtt
import ssl, json, time, random, math
from datetime import datetime

# ── Configuración ────────────────────────────────────────────
BROKER_HOST = "mosquitto"   # nombre del servicio en docker-compose
BROKER_PORT = 8883
CLIENT_ID   = "publisher-sensores"

CERT_CA     = "/certs/ca.crt"
CERT_CLIENT = "/certs/publisher.crt"
CERT_KEY    = "/certs/publisher.key"

INTERVALO   = 3  # segundos entre publicaciones

# ── Estado de la fábrica (simula variaciones realistas) ──────
class Fabrica:
    def __init__(self):
        self.tiempo = 0
        # Línea 1: producción normal
        self.l1_velocidad_base = 1450  # rpm
        self.l1_temp_base = 72         # ºC
        # Línea 2: producción más intensa
        self.l2_velocidad_base = 1800
        self.l2_temp_base = 85
        # Contadores
        self.unidades_l1 = 0
        self.unidades_l2 = 0
        self.alerta_activa = False

    def tick(self):
        self.tiempo += INTERVALO

        # Simular fallo ocasional en línea 2 (cada ~2 minutos)
        if self.tiempo % 120 == 0:
            self.alerta_activa = not self.alerta_activa

    def linea1(self):
        ruido = random.gauss(0, 15)
        temp_ruido = random.gauss(0, 0.8)
        velocidad = round(self.l1_velocidad_base + ruido + 
                         20 * math.sin(self.tiempo / 60), 1)
        temperatura = round(self.l1_temp_base + temp_ruido + 
                           3 * math.sin(self.tiempo / 90), 2)
        self.unidades_l1 += int(velocidad / 300)
        return velocidad, temperatura

    def linea2(self):
        ruido = random.gauss(0, 20)
        temp_ruido = random.gauss(0, 1.2)
        # Si hay alerta, la línea va más lenta y más caliente
        factor = 0.85 if self.alerta_activa else 1.0
        velocidad = round((self.l2_velocidad_base + ruido) * factor, 1)
        temperatura = round(self.l2_temp_base + temp_ruido + 
                           (8 if self.alerta_activa else 0), 2)
        self.unidades_l2 += int(velocidad / 300)
        return velocidad, temperatura

    def rendimiento(self):
        total = self.unidades_l1 + self.unidades_l2
        objetivo = 1000
        pct = round(min((total / objetivo) * 100, 100), 1)
        return total, pct

    def energia(self):
        # kWh consumidos, sube con el tiempo
        base = 450 + (self.tiempo / 3600) * 120
        return round(base + random.gauss(0, 5), 2)

    def coste_turno(self):
        kwh = self.energia()
        return round(kwh * 0.14, 2)  # 0.14 €/kWh


# ── Callbacks MQTT ───────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    codigos = {
        0: "✅ Conectado al broker",
        1: "❌ Versión de protocolo incorrecta",
        2: "❌ ID de cliente rechazado",
        3: "❌ Broker no disponible",
        4: "❌ Usuario/contraseña incorrectos",
        5: "❌ No autorizado",
    }
    print(codigos.get(rc, f"❌ Error desconocido: {rc}"))

def on_publish(client, userdata, mid):
    pass  # silencioso para no saturar la consola


# ── Setup cliente MQTT con TLS ───────────────────────────────
def crear_cliente():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_publish = on_publish

    # Configurar TLS con certificados mutuos
    client.tls_set(
        ca_certs=CERT_CA,
        certfile=CERT_CLIENT,
        keyfile=CERT_KEY,
        tls_version=ssl.PROTOCOL_TLS
    )
    return client


# ── Publicar un mensaje JSON ─────────────────────────────────
def publicar(client, topic, payload):
    payload["timestamp"] = datetime.now().isoformat()
    msg = json.dumps(payload)
    result = client.publish(topic, msg, qos=1)
    return result.rc == mqtt.MQTT_ERR_SUCCESS


# ── Bucle principal ──────────────────────────────────────────
def main():
    print("=" * 50)
    print("  🏭 Publisher - Fábrica IoT Segura")
    print("=" * 50)
    print(f"  Broker:   {BROKER_HOST}:{BROKER_PORT}")
    print(f"  Intervalo: {INTERVALO}s")
    print("=" * 50)

    fabrica = Fabrica()
    client = crear_cliente()

    # Reintentar conexión si el broker aún no está listo
    while True:
        try:
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            break
        except Exception as e:
            print(f"  ⏳ Esperando broker... ({e})")
            time.sleep(3)

    client.loop_start()
    time.sleep(1)

    print("\n  📡 Publicando datos...\n")

    try:
        while True:
            fabrica.tick()
            ts = datetime.now().strftime("%H:%M:%S")

            # ── Línea 1 ──────────────────────────────────────
            vel1, temp1 = fabrica.linea1()
            publicar(client, "fabrica/linea1/velocidad",
                     {"valor": vel1, "unidad": "rpm", "linea": 1})
            publicar(client, "fabrica/linea1/temperatura",
                     {"valor": temp1, "unidad": "C", "linea": 1})

            # ── Línea 2 ──────────────────────────────────────
            vel2, temp2 = fabrica.linea2()
            publicar(client, "fabrica/linea2/velocidad",
                     {"valor": vel2, "unidad": "rpm", "linea": 2})
            publicar(client, "fabrica/linea2/temperatura",
                     {"valor": temp2, "unidad": "C", "linea": 2})

            # ── Mantenimiento ─────────────────────────────────
            estado_l2 = "ALERTA" if fabrica.alerta_activa else "OK"
            publicar(client, "fabrica/mantenimiento/alertas",
                     {"linea": 2, "estado": estado_l2,
                      "mensaje": "Temperatura elevada - revisar refrigeración"
                                 if fabrica.alerta_activa else "Sin incidencias"})
            publicar(client, "fabrica/mantenimiento/estado",
                     {"linea1": "OK", "linea2": estado_l2})

            # ── Producción ────────────────────────────────────
            unidades, rendimiento = fabrica.rendimiento()
            publicar(client, "fabrica/produccion/rendimiento",
                     {"porcentaje": rendimiento, "objetivo": 1000})
            publicar(client, "fabrica/produccion/unidades",
                     {"total": unidades, "linea1": fabrica.unidades_l1,
                      "linea2": fabrica.unidades_l2})

            # ── Costes y energía (solo director) ─────────────
            kwh = fabrica.energia()
            coste = fabrica.coste_turno()
            publicar(client, "fabrica/costes/energia",
                     {"kwh": kwh, "coste_eur": coste})
            publicar(client, "fabrica/costes/por_unidad",
                     {"eur_por_unidad": round(coste / max(unidades, 1), 4)})

            alerta_str = "🚨 ALERTA L2" if fabrica.alerta_activa else "✅ OK"
            coste_ud = round(coste / max(unidades, 1), 4)

            # Print de datos en consola
            print(
                f"[{ts}] "
                f"L1: {vel1}rpm {temp1}°C | "
                f"L2: {vel2}rpm {temp2}°C | "
                f"Mant: {estado_l2} {alerta_str} | "
                f"Uds: {unidades} (L1:{fabrica.unidades_l1} L2:{fabrica.unidades_l2}) "
                f"Rend:{rendimiento}% | "
                f"Energía:{kwh}kWh Coste:{coste}€ ({coste_ud}€/ud)"
            )

            time.sleep(INTERVALO)

    except KeyboardInterrupt:
        print("\n\n  ⏹️  Publisher detenido")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
