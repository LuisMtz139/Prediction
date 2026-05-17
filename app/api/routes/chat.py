from fastapi import APIRouter
from pydantic import BaseModel

from app.ws.manager import manager

router = APIRouter(prefix="/chat", tags=["Chat"])


class MensajeWebhook(BaseModel):
    idUsuario: str
    idEmpresa: str
    mensaje: str
    historial: list[dict] = []


@router.post(
    "/responder",
    summary="Webhook — recibe mensaje del usuario y devuelve la respuesta",
    description=(
        "FastAPI llama a este endpoint cada vez que un usuario envía un mensaje. "
        "Recibe el mensaje y el historial, y debe devolver JSON con campo `respuesta`."
    ),
)
async def responder(body: MensajeWebhook):
    """
    Aquí defines tu lógica de respuesta.

    Recibe:
        {
            "idUsuario": "user1",
            "idEmpresa": "emp1",
            "mensaje": "hola",
            "historial": [ { "rol": "usuario", "contenido": "..." }, ... ]
        }

    Debe devolver:
        { "respuesta": "tu respuesta aquí" }
    """

    # ── PON TU LÓGICA AQUÍ ────────────────────────────────────────────────────
    # Ejemplos:
    #   - Llamar a una IA (OpenAI, Claude, etc.)
    #   - Consultar una base de datos
    #   - Aplicar reglas de negocio
    #   - Respuesta fija para pruebas:

    respuesta = f"Recibí tu mensaje: '{body.mensaje}'. (Reemplaza esto con tu lógica)"

    return {"respuesta": respuesta}


@router.get(
    "/conectados",
    summary="Ver usuarios conectados por empresa",
)
def usuarios_conectados(idEmpresa: str):
    usuarios = manager.usuarios_conectados(idEmpresa)
    return {"idEmpresa": idEmpresa, "usuarios": usuarios, "total": len(usuarios)}
