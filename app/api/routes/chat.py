from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.security.jwt_handler import validar_token
from app.ws.manager import manager

router = APIRouter(prefix="/chat", tags=["Chat"])


class RespuestaBot(BaseModel):
    respuesta: str


@router.post(
    "/responder",
    summary="El bot manda su respuesta aquí",
    description=(
        "El bot llama a este endpoint con la URL que encontró en el archivo .txt. "
        "Se valida el token para confirmar que tiene permiso de responder a ese usuario."
    ),
)
async def responder(
    numeroCelular: str = Query(..., description="Número de celular del usuario"),
    numeroEmpresa: str = Query(..., description="Número/ID de la empresa"),
    token: str = Query(..., description="JWT del usuario para validar permiso"),
    body: RespuestaBot = ...,
):
    # Validar que el token pertenece a este usuario
    try:
        payload = validar_token(token)
        if payload.get("sub") != numeroCelular or payload.get("empresa") != numeroEmpresa:
            raise HTTPException(status_code=403, detail="Token no coincide con numeroCelular o numeroEmpresa.")
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"Token inválido: {e}")

    # Verificar que el usuario está conectado esperando respuesta
    if not manager.esta_conectado(numeroCelular, numeroEmpresa):
        raise HTTPException(status_code=404, detail=f"El usuario {numeroCelular} no está conectado.")

    # Entregar la respuesta al WebSocket del usuario
    entregado = await manager.entregar_respuesta(numeroCelular, numeroEmpresa, body.respuesta)
    if not entregado:
        raise HTTPException(status_code=404, detail="El usuario no está esperando respuesta.")

    return {"ok": True, "numeroCelular": numeroCelular, "numeroEmpresa": numeroEmpresa}


@router.get(
    "/conectados",
    summary="Ver usuarios conectados por empresa",
)
def usuarios_conectados(numeroEmpresa: str):
    usuarios = manager.usuarios_conectados(numeroEmpresa)
    return {"numeroEmpresa": numeroEmpresa, "usuarios": usuarios, "total": len(usuarios)}


@router.post(
    "/test-responder",
    summary="[PRUEBA] Simula la respuesta del bot",
    description=(
        "Endpoint de prueba para simular que el bot responde. "
        "Envía un mensaje fijo al usuario conectado sin necesitar token. "
        "Úsalo para verificar que el WebSocket funciona correctamente."
    ),
)
async def test_responder(
    numeroCelular: str = Query(..., description="Número de celular del usuario"),
    numeroEmpresa: str = Query(..., description="Número/ID de la empresa"),
    respuesta: str = Query(default="Hola, ¿en qué puedo ayudarte? Soy tu asistente virtual."),
):
    if not manager.esta_conectado(numeroCelular, numeroEmpresa):
        raise HTTPException(
            status_code=404,
            detail=f"El usuario {numeroCelular} no está conectado o no ha enviado ningún mensaje."
        )

    entregado = await manager.entregar_respuesta(numeroCelular, numeroEmpresa, respuesta)
    if not entregado:
        raise HTTPException(status_code=404, detail="El usuario no está esperando respuesta.")

    return {"ok": True, "numeroCelular": numeroCelular, "respuestaEnviada": respuesta}
