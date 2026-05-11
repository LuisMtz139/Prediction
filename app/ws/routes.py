import json
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.security.jwt_handler import validar_token
from app.ws.manager import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/chat")
async def chat_websocket(
    ws: WebSocket,
    idUsuario: str = Query(..., description="ID del usuario que se conecta"),
    idEmpresa: str = Query(..., description="ID de la empresa (sala de chat)"),
    token: str = Query(..., description="Token JWT obtenido desde POST /auth/token"),
):
    """
    Endpoint WebSocket de mensajería.

    Conexión:
        ws://host/ws/chat?idUsuario=42&idEmpresa=7&token=eyJ...

    Mensaje que debe enviar el cliente (JSON):
        { "mensaje": "Hola a todos" }

    Mensaje que recibirán todos los conectados de la misma empresa:
        {
            "de": "42",
            "idEmpresa": "7",
            "mensaje": "Hola a todos",
            "timestamp": "2025-05-11T21:00:00+00:00"
        }

    Errores de conexión:
        - Código 1008 (Policy Violation): token inválido, expirado, o no coincide con idUsuario/idEmpresa
    """

    # ── PASO 1: Validar el token JWT ──────────────────────────────────────────
    try:
        payload = validar_token(token)

        # Verificar que el token pertenece exactamente a este usuario y empresa
        if payload.get("sub") != idUsuario or payload.get("empresa") != idEmpresa:
            await ws.close(code=1008, reason="Token no coincide con idUsuario o idEmpresa")
            return

    except jwt.ExpiredSignatureError:
        await ws.close(code=1008, reason="Token expirado")
        return
    except jwt.InvalidTokenError:
        await ws.close(code=1008, reason="Token inválido")
        return

    # ── PASO 2: Registrar la conexión ─────────────────────────────────────────
    await manager.conectar(ws, idUsuario, idEmpresa)

    # Notificar a la sala que un usuario se conectó
    await manager.broadcast_empresa(
        idEmpresa,
        {
            "tipo": "sistema",
            "mensaje": f"Usuario {idUsuario} se conectó",
            "idEmpresa": idEmpresa,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    # ── PASO 3: Escuchar mensajes ─────────────────────────────────────────────
    try:
        while True:
            raw = await ws.receive_text()

            # Parsear el JSON enviado por el cliente
            try:
                body = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"tipo": "error", "mensaje": "Formato inválido. Envía JSON con campo 'mensaje'."})
                continue

            texto = body.get("mensaje", "").strip()
            if not texto:
                await ws.send_json({"tipo": "error", "mensaje": "El campo 'mensaje' no puede estar vacío."})
                continue

            # Construir y difundir el mensaje a toda la sala de la empresa
            mensaje_out = {
                "tipo": "mensaje",
                "de": idUsuario,
                "idEmpresa": idEmpresa,
                "mensaje": texto,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await manager.broadcast_empresa(idEmpresa, mensaje_out)

    except WebSocketDisconnect:
        # ── PASO 4: Limpiar la conexión al desconectarse ──────────────────────
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
