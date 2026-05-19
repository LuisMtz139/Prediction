from fastapi import APIRouter
from pydantic import BaseModel

from app.security.jwt_handler import crear_token

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class TokenRequest(BaseModel):
    numeroCelular: str
    numeroEmpresa: str
    idUsuario: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    numeroCelular: str
    numeroEmpresa: str
    idUsuario: str


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtener token JWT",
    description=(
        "Genera un token JWT firmado con `numeroCelular`, `numeroEmpresa` e `idUsuario`. "
        "Úsalo para conectarte al WebSocket y como hash en la url_respuesta del archivo."
    ),
)
def obtener_token(body: TokenRequest) -> TokenResponse:
    token = crear_token(body.numeroCelular, body.numeroEmpresa, body.idUsuario)
    return TokenResponse(
        access_token=token,
        numeroCelular=body.numeroCelular,
        numeroEmpresa=body.numeroEmpresa,
        idUsuario=body.idUsuario,
    )
