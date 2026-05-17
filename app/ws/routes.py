import asyncio
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
    Chat WebSocket con sincronización estricta: un mensaje a la vez.

    Flujo:
      1. ws://host/ws/chat?idUsuario=X&idEmpresa=Y
      2. Primer mensaje:  { "token": "eyJ..." }
      3. Mensajes:        { "mensaje": "Hola" }
      4. Si envías otro mensaje antes de que el bot responda recibes:
             { "tipo": "bloqueado", ... }
      5. Cuando el bot responde:
             { "tipo": "respuesta_bot", "respondido_por": "bot", "mensaje": "..." }
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

    await manager.conectar(ws, idUsuario, idEmpresa)
    await ws.send_json({
        "tipo": "sistema",
        "mensaje": f"Conectado como {idUsuario}. Escribe tu mensaje.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    historial: list[dict] = []
    cola: asyncio.Queue[str | None] = asyncio.Queue(maxsize=1)
    libre = asyncio.Event()
    libre.set()  # al inicio el usuario puede enviar

    # ── Corutina 1: escucha mensajes y valida sincronización ─────────────────
    async def receptor():
        try:
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

                # Bloquear si el bot aún no respondió el mensaje anterior
                if not libre.is_set():
                    await ws.send_json({
                        "tipo": "bloqueado",
                        "mensaje": "Espera la respuesta del bot antes de enviar otro mensaje.",
                    })
                    continue

                libre.clear()           # marcar como ocupado
                await cola.put(texto)   # enviar al procesador

        except WebSocketDisconnect:
            await cola.put(None)        # señal de cierre para el procesador

    # ── Corutina 2: llama al webhook y devuelve la respuesta ─────────────────
    async def procesador():
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                texto = await cola.get()
                if texto is None:
                    break

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

                except httpx.HTTPStatusError as e:
                    await ws.send_json({"tipo": "error", "mensaje": f"Webhook respondió {e.response.status_code}."})
                    libre.set()
                    continue
                except Exception as e:
                    await ws.send_json({"tipo": "error", "mensaje": f"No se pudo contactar el webhook: {e}"})
                    libre.set()
                    continue

                # Actualizar historial interno con el texto del bot
                historial.append({"rol": "usuario",   "contenido": texto})
                historial.append({"rol": "asistente", "contenido": data.get("mensaje", "")})

                # Mandar la respuesta del webhook tal cual al usuario
                await ws.send_json(data)

                libre.set()  # usuario puede volver a escribir

    # ── Correr ambas corutinas en paralelo ───────────────────────────────────
    try:
        await asyncio.gather(receptor(), procesador())
    finally:
        manager.desconectar(idUsuario, idEmpresa)
