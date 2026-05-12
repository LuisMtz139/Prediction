import json
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.security.jwt_handler import validar_token
from app.ws.manager import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/ping")
async def ping(ws: WebSocket):
    """Endpoint de diagnóstico — sin JWT, solo verifica conectividad WebSocket."""
    await ws.accept()
    await ws.send_text("pong")
    await ws.close()


@router.websocket("/ws/chat")
async def chat_websocket(
    ws: WebSocket,
    idUsuario: str = Query(..., description="ID del usuario que se conecta"),
    idEmpresa: str = Query(..., description="ID de la empresa (sala de chat)"),
    token: str = Query(default=""),  # ignorado en URL; el JWT real llega en el primer mensaje
):
    """
    Endpoint WebSocket de mensajería.

    Conexión:
        ws://host/ws/chat?idUsuario=42&idEmpresa=7

    Primer mensaje que DEBE enviar el cliente (autenticación):
        { "token": "eyJ..." }

    Mensajes siguientes:
        { "mensaje": "Hola a todos" }

    Mensajes que recibirán todos los conectados de la misma empresa:
        {
            "tipo": "mensaje",
            "de": "42",
            "idEmpresa": "7",
            "mensaje": "Hola a todos",
            "timestamp": "2025-05-11T21:00:00+00:00"
        }
    """

    # ── PASO 1: Aceptar la conexión para poder intercambiar mensajes ──────────
    await ws.accept()

    # ── PASO 2: Esperar el primer mensaje con el token JWT ────────────────────
    try:
        raw_auth = await ws.receive_text()
        auth = json.loads(raw_auth)
        token = auth.get("token", "")
    except (json.JSONDecodeError, Exception):
        await ws.send_json({"tipo": "error", "mensaje": "Primer mensaje debe ser JSON con campo 'token'."})
        await ws.close(code=1008)
        return

    # ── PASO 3: Validar el token JWT ──────────────────────────────────────────
    try:
        payload = validar_token(token)
        if payload.get("sub") != idUsuario or payload.get("empresa") != idEmpresa:
            await ws.send_json({"tipo": "error", "mensaje": "Token no coincide con idUsuario o idEmpresa."})
            await ws.close(code=1008)
            return
    except jwt.ExpiredSignatureError:
        await ws.send_json({"tipo": "error", "mensaje": "Token expirado."})
        await ws.close(code=1008)
        return
    except jwt.InvalidTokenError:
        await ws.send_json({"tipo": "error", "mensaje": "Token inválido."})
        await ws.close(code=1008)
        return

    # ── PASO 4: Registrar la conexión y notificar a la sala ──────────────────
    await manager.conectar(ws, idUsuario, idEmpresa)

    await manager.broadcast_empresa(
        idEmpresa,
        {
            "tipo": "sistema",
            "mensaje": f"Usuario {idUsuario} se conectó",
            "idEmpresa": idEmpresa,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # ── PASO 5: Escuchar mensajes ─────────────────────────────────────────────
    try:
        while True:
            raw = await ws.receive_text()

            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"tipo": "error", "mensaje": "Formato inválido. Envía JSON con campo 'mensaje'."})
                continue

            texto = body.get("mensaje", "").strip()
            if not texto:
                await ws.send_json({"tipo": "error", "mensaje": "El campo 'mensaje' no puede estar vacío."})
                continue

            mensaje_out = {
                "tipo": "mensaje",
                "de": idUsuario,
                "idEmpresa": idEmpresa,
                "mensaje": texto,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await manager.broadcast_empresa(idEmpresa, mensaje_out)

    except WebSocketDisconnect:
        manager.desconectar(idUsuario, idEmpresa)
        await manager.broadcast_empresa(
            idEmpresa,
            {
                "tipo": "sistema",
                "mensaje": f"Usuario {idUsuario} se desconectó",
                "idEmpresa": idEmpresa,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
