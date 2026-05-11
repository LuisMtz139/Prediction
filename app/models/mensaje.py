from pydantic import BaseModel


class MensajeIn(BaseModel):
    """Estructura del mensaje que envía el cliente."""
    mensaje: str


class MensajeOut(BaseModel):
    """Estructura del mensaje que se emite a todos los conectados."""
    de: str          # idUsuario del remitente
    idEmpresa: str   # empresa a la que pertenece la sala
    mensaje: str     # contenido del mensaje
    timestamp: str   # fecha/hora UTC en ISO 8601
