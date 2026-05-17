from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ws.manager import manager

router = APIRouter(prefix="/chat", tags=["Chat"])


class RespuestaBody(BaseModel):
    respuesta: str


@router.post(
    "/responder",
    summary="Enviar respuesta a un usuario conectado",
    description=(
        "Deposita una respuesta para el usuario indicado. "
        "El usuario debe estar conectado al WebSocket y haber enviado un mensaje previo."
    ),
)
async def responder(idUsuario: str, body: RespuestaBody):
    if not manager.esta_conectado(idUsuario):
        raise HTTPException(status_code=404, detail=f"Usuario '{idUsuario}' no está conectado.")

    enviado = await manager.entregar_respuesta(idUsuario, body.respuesta)
    if not enviado:
        raise HTTPException(status_code=404, detail=f"Usuario '{idUsuario}' no tiene mensajes pendientes.")

    return {"ok": True, "idUsuario": idUsuario}


@router.get(
    "/conectados",
    summary="Ver usuarios conectados por empresa",
)
def usuarios_conectados(idEmpresa: str):
    usuarios = manager.usuarios_conectados(idEmpresa)
    return {"idEmpresa": idEmpresa, "usuarios": usuarios, "total": len(usuarios)}
