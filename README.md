# 🏭 Fábrica IoT - MQTT Seguro con Certificados

> Reto: Módulo de Envío de Datos — Desarrollo de Aplicaciones para IoT  


## 👤 Miembros del equipo
- Jon Ochoa
- Oier Martinez

---

## 📋 Descripción

Sistema de monitorización de una fábrica inteligente con **MQTT seguro (TLS mutual)** y **control de acceso por certificados**. Dependiendo del certificado que presente cada cliente, puede acceder a distintos datos:

| Rol | Acceso |
|---|---|
| **Operario** | Velocidad y temperatura de líneas de producción |
| **Supervisor** | Operario + alertas de mantenimiento + rendimiento |
| **Director** | Todo, incluyendo costes y consumo energético |

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose                            │
│                                                              │
│  ┌──────────────┐      ┌───────────────────┐                │
│  │  Mosquitto   │◄────►│    Node-RED        │                │
│  │  (broker)    │ TLS  │  Dashboard :1880   │                │
│  │  TLS + ACL   │      │  /ui               │                │
│  └──────┬───────┘      └───────────────────┘                │
│         │                                                    │
│         │  ┌─────────────────────────────────────┐          │
│         ├─►│   Publisher (Python)                │          │
│         │  │   Genera datos de sensores          │          │
│         │  └─────────────────────────────────────┘          │
│         │                                                    │
│         │  ┌─────────────────────────────────────┐          │
│         ├─►│   Subscriber Director (Python)      │          │
│         │  │   Consume TODOS los topics          │          │
│         │  └─────────────────────────────────────┘          │
│         │                                                    │
│         │  ┌─────────────────────────────────────┐          │
│         └─►│   Subscriber Operario (Python)      │          │
│            │   Consume solo línea 1              │          │
│            └─────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Instrucciones de uso

### 1. Requisitos previos
- Docker y Docker Compose instalados
- OpenSSL instalado (en WSL: `sudo apt install openssl`)
- `mosquitto-clients` para pruebas CLI (en WSL: `sudo apt install mosquitto-clients`)

### 2. Generar certificados
```bash
chmod +x generar_certs.sh
./generar_certs.sh
```
Esto crea en `./certs/`:
- `ca.crt / ca.key` — Autoridad Certificadora
- `server.crt / server.key` — Broker Mosquitto
- `operario.crt / operario.key` — Cliente operario
- `supervisor.crt / supervisor.key` — Cliente supervisor
- `director.crt / director.key` — Cliente director
- `publisher.crt / publisher.key` — Publisher Python

### 3. Levantar los servicios
```bash
docker compose up --build
```

### 4. Acceder al dashboard
Abrir en el navegador: **http://localhost:1880/ui**

- Pestaña 🔑 **Director** → ve todos los datos incluyendo costes
- Pestaña 👷 **Operario** → solo velocidad y temperatura de líneas

### 5. Ver logs de los subscribers Python
Los subscribers Python están corriendo en contenedores y consumiendo datos en tiempo real:

```bash
# Ver logs del subscriber Director (ve todo)
docker logs -f fabrica-subscriber-director

# Ver logs del subscriber Operario (acceso limitado)
docker logs -f fabrica-subscriber-operario
```

**Nota importante:** El subscriber operario intentará suscribirse a varios topics, pero el ACL de Mosquitto **bloqueará silenciosamente** los mensajes de costes, mantenimiento, etc. Solo recibirá datos de línea 1 (velocidad y temperatura).

---

## Subscribers Python (Consumidores)

El proyecto incluye **dos subscribers Python** que consumen datos de manera segura desde el broker:

### Subscriber Director (Acceso Total)
```bash
# Ver en tiempo real todos los mensajes
docker logs -f fabrica-subscriber-director
```
- 👔 Usa certificado: `director.crt`
- ✅ Recibe **TODOS** los topics: `fabrica/#`
- 💰 Incluye: líneas, mantenimiento, producción, costes, energía

### Subscriber Operario (Acceso Limitado)
```bash
# Ver solo mensajes permitidos
docker logs -f fabrica-subscriber-operario
```
- 👷 Usa certificado: `operario.crt`
- ⚠️ Intenta suscribirse a varios topics, pero el **ACL bloquea** la mayoría
- ✅ Solo recibe: `fabrica/linea1/velocidad` y `fabrica/linea1/temperatura`
- ❌ **No recibe**: costes, mantenimiento, producción, línea 2

**Demostración del control de acceso:**
Ambos subscribers intentan suscribirse a los mismos topics, pero Mosquitto aplica el ACL y **filtra silenciosamente** los mensajes según el certificado presentado. Esto demuestra que la seguridad funciona tanto en producción como en consumo.

---

## 💻 Producir y consumir desde línea de comandos

### Suscribirse como Director (ve todo)
```bash
mosquitto_sub \
  -h localhost -p 8883 \
  -t "fabrica/#" \
  --cafile ./certs/ca.crt \
  --cert ./certs/director.crt \
  --key ./certs/director.key \
  -v
```

### Suscribirse como Operario (acceso limitado)
```bash
mosquitto_sub \
  -h localhost -p 8883 \
  -t "fabrica/#" \
  --cafile ./certs/ca.crt \
  --cert ./certs/operario.crt \
  --key ./certs/operario.key \
  -v
# Solo recibirá fabrica/linea1/*
```

### Intentar acceder a datos de costes como Operario (acceso denegado)
```bash
mosquitto_sub \
  -h localhost -p 8883 \
  -t "fabrica/costes/#" \
  --cafile ./certs/ca.crt \
  --cert ./certs/operario.crt \
  --key ./certs/operario.key \
  -v
# Se conecta pero no recibe ningún mensaje → ACL deniega silenciosamente
```

### Publicar manualmente un dato
```bash
mosquitto_pub \
  -h localhost -p 8883 \
  -t "fabrica/linea1/temperatura" \
  -m '{"valor": 95.5, "unidad": "C", "linea": 1}' \
  --cafile ./certs/ca.crt \
  --cert ./certs/director.crt \
  --key ./certs/director.key
```

---

## 📊 Topics MQTT y accesos

| Topic | Operario | Supervisor | Director |
|---|:---:|:---:|:---:|
| `fabrica/linea1/velocidad` | ✅ | ✅ | ✅ |
| `fabrica/linea1/temperatura` | ✅ | ✅ | ✅ |
| `fabrica/linea2/velocidad` | ✅ | ✅ | ✅ |
| `fabrica/linea2/temperatura` | ✅ | ✅ | ✅ |
| `fabrica/mantenimiento/alertas` | ❌ | ✅ | ✅ |
| `fabrica/produccion/rendimiento` | ❌ | ✅ | ✅ |
| `fabrica/costes/energia` | ❌ | ❌ | ✅ |
| `fabrica/costes/por_unidad` | ❌ | ❌ | ✅ |

---

## 🔧 Pasos seguidos

1. Diseño de la arquitectura y roles de acceso
2. Generación de CA y certificados con OpenSSL
3. Configuración de Mosquitto con TLS mutual y ACL
4. Desarrollo del publisher Python con simulación de sensores
5. **Desarrollo de subscribers Python (director y operario) para consumo seguro**
6. Configuración de Node-RED con dos conexiones (director y operario)
7. Construcción del dashboard con gauges y gráficas en tiempo real
8. Pruebas desde línea de comandos con mosquitto_pub/sub
9. Contenedorización con Docker Compose

---

## 🚧 Problemas y retos encontrados

- **CN del certificado como username**: Mosquitto usa el CN del certificado como identificador para el ACL (`use_identity_as_username true`). Es importante que el CN coincida exactamente con el `user` en `acl.conf`
- **Rutas dentro de Docker**: Los volúmenes deben montarse correctamente; Node-RED y el publisher necesitan acceder a los mismos certificados desde rutas distintas
- **Tiempo de arranque**: El publisher puede intentar conectarse antes de que Mosquitto esté listo; se resuelve con un retry en el código Python

---

## 🔮 Posibles vías de mejora

- Añadir **InfluxDB** para persistencia de datos históricos
- Integrar **Grafana** para dashboards más avanzados
- Implementar **renovación automática de certificados** con cert-manager
- Añadir un **API REST** para consultar datos históricos
- Implementar **alertas por email** cuando se detecten anomalías
- Usar **MQTT 5.0** que incluye mejor soporte para respuestas de autorización explícitas

---

## 🔄 Alternativas consideradas

| Alternativa | Pros | Contras |
|---|---|---|
| Auth usuario/contraseña | Más simple | Menos seguro, sin identidad criptográfica |
| JWT Tokens | Estándar web | Requiere plugin adicional en Mosquitto |
| Sin Docker | Menos pasos | No reproducible, depende del SO |
| HiveMQ | Más features | Privativo, más complejo |

---

