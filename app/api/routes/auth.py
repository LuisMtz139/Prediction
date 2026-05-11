from fastapi import APIRouter
from pydantic import BaseModel

from app.security.jwt_handler import crear_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class TokenRequest(BaseModel):
    idUsuario: str
    idEmpresa: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    idUsuario: str
    idEmpresa: str


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtener token JWT",
    description=(
        "Genera un token JWT firmado con `idUsuario` e `idEmpresa`. "
        "Este token debe enviarse como query param `token` al conectar al WebSocket."
    ),
)
def obtener_token(body: TokenRequest) -> TokenResponse:
    """
    Endpoint REST para que el cliente obtenga su token JWT antes de conectarse al WebSocket.

    Flujo esperado:
    1. Cliente llama a POST /auth/token con { idUsuario, idEmpresa }
    2. Guarda el access_token recibido
    3. Se conecta a ws://host/ws/chat?idUsuario=X&idEmpresa=Y&token=ACCESS_TOKEN
    """
    token = crear_token(body.idUsuario, body.idEmpresa)
    return TokenResponse(
        access_token=token,
        idUsuario=body.idUsuario,
        idEmpresa=body.idEmpresa,
    )
