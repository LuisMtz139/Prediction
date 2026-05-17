from pydantic import BaseModel


class MensajeIn(BaseModel):
    """Estructura del mensaje que envía el cliente."""
    mensaje: str


class MensajeOut(BaseModel):
    """Estructura de la respuesta que recibe el usuario desde el servicio externo."""
    tipo: str        # "respuesta" | "error" | "sistema"
    mensaje: str     # contenido del mensaje
    timestamp: str   # fecha/hora UTC en ISO 8601
