import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.security.jwt_handler import validar_token
from app.ws.manager import manager

router = APIRouter(tags=["WebSocket"])

CHATS_DIR = Path(r"C:\MsgsWhatsAppUltraMsg\92937")
CHATS_DIR.mkdir(parents=True, exist_ok=True)


@router.websocket("/ws/ping")
async def ping(ws: WebSocket):
    await ws.accept()
    await ws.send_text("pong")
    await ws.close()


@router.websocket("/ws/chat")
async def chat_websocket(
    ws: WebSocket,
    numeroCelular: str = Query(..., description="Número de celular del usuario"),
    numeroEmpresa: str = Query(..., description="Número/ID de la empresa"),
    token: str = Query(default=""),
):
    """
    Chat WebSocket con archivo por usuario.

    Flujo:
      1. ws://host/ws/chat?numeroCelular=123&numeroEmpresa=456
      2. Primer mensaje:  { "token": "eyJ..." }
      3. Mensajes:        { "mensaje": "Hola" }
      4. FastAPI crea/sobreescribe chats/123-456.txt con el mensaje y url_respuesta
      5. El bot llama POST a esa url_respuesta con { "respuesta": "..." }
      6. Usuario recibe la respuesta por WebSocket
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
        if payload.get("sub") != numeroCelular or payload.get("empresa") != numeroEmpresa:
            await ws.send_json({"tipo": "error", "mensaje": "Token no coincide con numeroCelular o numeroEmpresa."})
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

    await manager.conectar(ws, numeroCelular, numeroEmpresa)
    await ws.send_json({
        "tipo": "sistema",
        "mensaje": f"Conectado como {numeroCelular}. Escribe tu mensaje.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    libre = asyncio.Event()
    libre.set()

    # ── Corutina 1: escucha mensajes y valida sincronización ─────────────────
    cola: asyncio.Queue[str | None] = asyncio.Queue()

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

                if not libre.is_set():
                    await ws.send_json({
                        "tipo": "bloqueado",
                        "mensaje": "Espera la respuesta del bot antes de enviar otro mensaje.",
                    })
                    continue

                libre.clear()
                await cola.put(texto)

        except WebSocketDisconnect:
            await cola.put(None)

    # ── Corutina 2: escribe el archivo y espera la respuesta del bot ──────────
    async def procesador():
        archivo = CHATS_DIR / f"{numeroCelular}-{numeroEmpresa}.app"
        url_respuesta = (
            f"{settings.BASE_URL}/chat/responder"
            f"?numeroCelular={numeroCelular}"
            f"&numeroEmpresa={numeroEmpresa}"
            f"&token={token}"
        )

        while True:
            texto = await cola.get()
            if texto is None:
                break

            # Sobreescribir el archivo con el mensaje actual
            archivo.write_text(
                json.dumps({
                    "numeroCelular": numeroCelular,
                    "numeroEmpresa": numeroEmpresa,
                    "mensaje": texto,
                    "url_respuesta": url_respuesta,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            await ws.send_json({
                "tipo": "enviado",
                "mensaje": texto,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # Esperar que el bot llame a url_respuesta
            respuesta = await manager.esperar_respuesta(numeroCelular, numeroEmpresa)

            await ws.send_json({
                "numeroCelular": numeroCelular,
                "numeroEmpresa": numeroEmpresa,
                "mensaje": respuesta,
                "responseBot": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            libre.set()

    try:
        await asyncio.gather(receptor(), procesador())
    finally:
        manager.desconectar(numeroCelular, numeroEmpresa)
