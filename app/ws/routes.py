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
    idEmpresa: str = Query(..., description="ID de la empresa"),
    token: str = Query(default=""),
):
    """
    Chat WebSocket individual.

    Flujo:
      1. Cliente conecta:  ws://host/ws/chat?idUsuario=X&idEmpresa=Y
      2. Primer mensaje:   { "token": "eyJ..." }
      3. Mensajes:         { "mensaje": "Hola" }
      4. Alguien llama a:  POST /chat/responder?idUsuario=X  { "respuesta": "..." }
      5. Cliente recibe:   { "tipo": "respuesta", "mensaje": "..." }
    """

    await ws.accept()

    # ── Autenticación ────────────────────────────────────────────────────────
    try:
        raw_auth = await ws.receive_text()
        auth = json.loads(raw_auth)
        token = auth.get("token", "")
    except Exception:
        await ws.send_json({"tipo": "error", "mensaje": "Primer mensaje debe ser JSON con campo 'token'."})
        await ws.close(code=1008)
        return

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

    # ── Registrar y confirmar conexión ───────────────────────────────────────
    await manager.conectar(ws, idUsuario, idEmpresa)
    await ws.send_json({
        "tipo": "sistema",
        "mensaje": f"Conectado como {idUsuario}. Escribe tu mensaje.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # ── Loop principal ───────────────────────────────────────────────────────
    try:
        while True:
            # 1. Recibir mensaje del usuario
            try:
                raw = await ws.receive_text()
                body = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"tipo": "error", "mensaje": "Envía JSON con campo 'mensaje'."})
                continue

            texto = body.get("mensaje", "").strip()
            if not texto:
                await ws.send_json({"tipo": "error", "mensaje": "El campo 'mensaje' no puede estar vacío."})
                continue

            # 2. Confirmar que se recibió y queda en espera
            await ws.send_json({
                "tipo": "recibido",
                "mensaje": texto,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # 3. Esperar la respuesta que llegue por POST /chat/responder
            respuesta = await manager.esperar_respuesta(idUsuario)

            # 4. Enviar la respuesta al usuario
            await ws.send_json({
                "tipo": "respuesta",
                "mensaje": respuesta,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

    except WebSocketDisconnect:
        pass
    finally:
        manager.desconectar(idUsuario, idEmpresa)
