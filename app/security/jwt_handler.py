from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def crear_token(idUsuario: str, idEmpresa: str) -> str:
    """
    Genera un token JWT firmado con idUsuario e idEmpresa en el payload.
    El token expira según TOKEN_EXPIRE_HOURS configurado en .env
    """
    payload = {
        "sub": idUsuario,
        "empresa": idEmpresa,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def validar_token(token: str) -> dict:
    """
    Valida y decodifica un token JWT.
    Lanza jwt.ExpiredSignatureError si el token venció.
    Lanza jwt.InvalidTokenError si la firma es inválida.
    Retorna el payload (dict) si el token es válido.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
