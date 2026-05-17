import json
from datetime import datetime, timezone

import httpx
import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import settings
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
    Chat WebSocket con webhook.

    Flujo:
      1. Cliente conecta:   ws://host/ws/chat?idUsuario=X&idEmpresa=Y
      2. Primer mensaje:    { "token": "eyJ..." }
      3. Mensajes:          { "mensaje": "Hola" }
      4. FastAPI llama a:   POST WEBHOOK_URL  →  { "idUsuario", "idEmpresa", "mensaje", "historial" }
      5. Tu webhook responde { "respuesta": "..." }
      6. Cliente recibe:    { "tipo": "respuesta", "mensaje": "..." }
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

    historial: list[dict] = []

    # ── Loop principal ───────────────────────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
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

                # Llamar al webhook con el mensaje y el historial
                try:
                    resp = await client.post(
                        settings.WEBHOOK_URL,
                        json={
                            "idUsuario": idUsuario,
                            "idEmpresa": idEmpresa,
                            "mensaje": texto,
                            "historial": historial.copy(),
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    respuesta_texto = data.get("respuesta") or data.get("mensaje") or str(data)
                except httpx.HTTPStatusError as e:
                    await ws.send_json({"tipo": "error", "mensaje": f"Webhook respondió {e.response.status_code}."})
                    continue
                except Exception as e:
                    await ws.send_json({"tipo": "error", "mensaje": f"No se pudo contactar el webhook: {e}"})
                    continue

                # Actualizar historial
                historial.append({"rol": "usuario",    "contenido": texto})
                historial.append({"rol": "asistente", "contenido": respuesta_texto})

                # Enviar respuesta al usuario
                await ws.send_json({
                    "tipo": "respuesta",
                    "mensaje": respuesta_texto,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        pass
    finally:
        manager.desconectar(idUsuario, idEmpresa)
