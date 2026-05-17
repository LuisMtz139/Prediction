from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.ws.manager import manager

router = APIRouter(prefix="/chat", tags=["Chat"])

CHAT_LOG = Path("chat_log.txt")


class MensajeWebhook(BaseModel):
    idUsuario: str = ""
    idEmpresa: str = ""
    mensaje: str
    historial: list[dict] = []


def _escribir(linea: str) -> None:
    with open(CHAT_LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


@router.post(
    "/responder",
    summary="Webhook — recibe mensaje del usuario y devuelve la respuesta",
)
async def responder(body: MensajeWebhook):
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Guardar el mensaje del usuario
    _escribir(f"[{ahora}] {body.idUsuario} → bot: {body.mensaje}")

    # Respuesta de prueba — reemplaza esto con tu lógica real
    respuesta = f"Hola {body.idUsuario}, recibí tu mensaje: '{body.mensaje}'"

    # Guardar la respuesta
    _escribir(f"[{ahora}] bot → {body.idUsuario}: {respuesta}")
    _escribir("")  # línea en blanco entre turnos

    # Devolver la misma estructura que llegó + responseBot: True
    return {
        "idUsuario": body.idUsuario,
        "idEmpresa": body.idEmpresa,
        "mensaje": respuesta,
        "responseBot": True,
        "historial": body.historial,
    }


@router.get(
    "/historial",
    summary="Leer el historial del chat_log.txt estructurado por turnos",
)
def ver_historial():
    if not CHAT_LOG.exists():
        return {"turnos": []}

    turnos = []
    turno_actual: dict | None = None

    for linea in CHAT_LOG.read_text(encoding="utf-8").splitlines():
        if not linea.strip():
            if turno_actual:
                turnos.append(turno_actual)
                turno_actual = None
            continue

        # Formato: [2026-05-16 21:50:35] 1 → bot: Hola
        try:
            hora = linea[1:20]
            resto = linea[22:]
            de, _, mensaje = resto.partition(": ")
            remitente, _, _ = de.partition(" → ")

            entrada = {"hora": hora, "de": remitente.strip(), "mensaje": mensaje.strip()}

            if remitente.strip() == "bot":
                if turno_actual:
                    turno_actual["bot"] = entrada
            else:
                turno_actual = {"usuario": entrada, "bot": None}
        except Exception:
            continue

    if turno_actual:
        turnos.append(turno_actual)

    return {"total_turnos": len(turnos), "turnos": turnos}


@router.delete(
    "/historial",
    summary="Borrar el chat_log.txt",
)
def borrar_historial():
    if CHAT_LOG.exists():
        CHAT_LOG.unlink()
    return {"ok": True}


@router.get(
    "/conectados",
    summary="Ver usuarios conectados por empresa",
)
def usuarios_conectados(idEmpresa: str):
    usuarios = manager.usuarios_conectados(idEmpresa)
    return {"idEmpresa": idEmpresa, "usuarios": usuarios, "total": len(usuarios)}
