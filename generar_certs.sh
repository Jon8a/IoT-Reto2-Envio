#!/bin/bash
# ============================================================
# Generador de certificados para MQTT Seguro - Fábrica IoT
# Genera: CA, servidor, operario, supervisor, director, publisher
# ============================================================

set -e
CERTS_DIR="./certs"
mkdir -p $CERTS_DIR

echo "========================================"
echo "  Generando certificados MQTT Seguro"
echo "========================================"

# ── 1. CA (Autoridad Certificadora) ──────────────────────────
echo ""
echo "[1/6] Generando CA..."
openssl genrsa -out $CERTS_DIR/ca.key 2048
openssl req -new -x509 -days 3650 -key $CERTS_DIR/ca.key \
  -out $CERTS_DIR/ca.crt \
  -subj "/C=ES/ST=Euskadi/L=Bilbao/O=FabricaIoT/CN=FabricaCA"
echo "      ✓ ca.key y ca.crt creados"

# ── 2. Certificado del SERVIDOR (broker Mosquitto) ───────────
echo ""
echo "[2/6] Generando certificado del servidor..."
openssl genrsa -out $CERTS_DIR/server.key 2048
openssl req -new -key $CERTS_DIR/server.key \
  -out $CERTS_DIR/server.csr \
  -subj "/C=ES/ST=Euskadi/L=Bilbao/O=FabricaIoT/CN=mosquitto"
# SAN extension so the cert is valid for both 'mosquitto' (Docker) and 'localhost'
cat > /tmp/server_ext.cnf <<EOF
[SAN]
subjectAltName=DNS:mosquitto,DNS:localhost,IP:127.0.0.1
EOF
openssl x509 -req -days 3650 \
  -in $CERTS_DIR/server.csr \
  -CA $CERTS_DIR/ca.crt \
  -CAkey $CERTS_DIR/ca.key \
  -CAcreateserial \
  -extfile /tmp/server_ext.cnf \
  -extensions SAN \
  -out $CERTS_DIR/server.crt
echo "      ✓ server.key y server.crt creados"

# ── Función para generar certificados de cliente ─────────────
generar_cliente() {
  local NOMBRE=$1
  local CN=$2
  echo ""
  echo "Generando certificado: $NOMBRE..."
  openssl genrsa -out $CERTS_DIR/$NOMBRE.key 2048
  openssl req -new -key $CERTS_DIR/$NOMBRE.key \
    -out $CERTS_DIR/$NOMBRE.csr \
    -subj "/C=ES/ST=Euskadi/L=Bilbao/O=FabricaIoT/CN=$CN"
  openssl x509 -req -days 3650 \
    -in $CERTS_DIR/$NOMBRE.csr \
    -CA $CERTS_DIR/ca.crt \
    -CAkey $CERTS_DIR/ca.key \
    -CAcreateserial \
    -out $CERTS_DIR/$NOMBRE.crt
  echo "      ✓ $NOMBRE.key y $NOMBRE.crt creados"
}

# ── 3. Clientes ───────────────────────────────────────────────
echo ""
echo "[3/7] Generando certificado operario (Línea 1)..."
generar_cliente "operario" "operario"

echo "[4/7] Generando certificado operario2 (Línea 2)..."
generar_cliente "operario2" "operario2"

echo "[5/7] Generando certificado supervisor..."
generar_cliente "supervisor" "supervisor"

echo "[6/7] Generando certificado director..."
generar_cliente "director" "director"

echo "[7/7] Generando certificado publisher..."
generar_cliente "publisher" "publisher"

# ── Limpiar CSRs intermedios ──────────────────────────────────
rm -f $CERTS_DIR/*.csr $CERTS_DIR/*.srl

# ── Permisos correctos ────────────────────────────────────────
chmod 644 $CERTS_DIR/*.crt
# 644 so Docker containers (Node-RED, etc.) running as non-root can read keys
chmod 644 $CERTS_DIR/*.key

echo ""
echo "========================================"
echo "  ✅ Certificados generados en ./certs"
echo "========================================"
echo ""
echo "  Archivos creados:"
ls -la $CERTS_DIR/
