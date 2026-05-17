from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
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

# CORS — permite que el test_chat.html pueda llamar a la API desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # En producción, reemplaza "*" por tu dominio
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(ws_router)


@app.get("/", tags=["Health"])
def health_check():
    """Verifica que el servicio está activo."""
    return {"status": "ok", "service": "Mensajería WebSocket", "version": "2.0.0"}


@app.get("/chat", tags=["Cliente de prueba"], include_in_schema=False)
def test_chat():
    return FileResponse("test_chat.html")
