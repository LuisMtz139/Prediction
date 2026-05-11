from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.ws.routes import router as ws_router

app = FastAPI(
    title="Servicio de Mensajería WebSocket",
    version="2.0.0",
    description=(
        "Servicio de mensajería en tiempo real basado en WebSockets con autenticación JWT.\n\n"
        "**Flujo de uso:**\n"
        "1. Obtén un token → `POST /auth/token`\n"
        "2. Conéctate al chat → `ws://host/ws/chat?idUsuario=X&idEmpresa=Y&token=TOKEN`\n"
        "3. Envía mensajes en formato JSON: `{ \"mensaje\": \"Hola\" }`"
    ),
)

# Registrar routers
app.include_router(auth_router)
app.include_router(ws_router)


@app.get("/", tags=["Health"])
def health_check():
    """Verifica que el servicio está activo."""
    return {"status": "ok", "service": "Mensajería WebSocket", "version": "2.0.0"}
