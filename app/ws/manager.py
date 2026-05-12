from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """
    Gestiona las conexiones WebSocket activas, agrupadas por empresa.

    Estructura interna:
        salas = {
            "idEmpresa_A": {
                "idUsuario_1": WebSocket,
                "idUsuario_2": WebSocket,
            },
            "idEmpresa_B": { ... }
        }
    """

    def __init__(self):
        # Dict[idEmpresa, Dict[idUsuario, WebSocket]]
        self.salas: dict[str, dict[str, WebSocket]] = defaultdict(dict)

    async def conectar(self, ws: WebSocket, idUsuario: str, idEmpresa: str) -> None:
        """Registra la conexión WebSocket en la sala de la empresa (ya debe estar aceptada)."""
        self.salas[idEmpresa][idUsuario] = ws

    def desconectar(self, idUsuario: str, idEmpresa: str) -> None:
        """Elimina la conexión del usuario de la sala."""
        empresa_sala = self.salas.get(idEmpresa, {})
        empresa_sala.pop(idUsuario, None)

    async def broadcast_empresa(self, idEmpresa: str, mensaje: dict) -> None:
        """
        Envía el mensaje a TODOS los usuarios conectados en la misma empresa.
        Si una conexión falla, la ignora y continúa con las demás.
        """
        conexiones = list(self.salas.get(idEmpresa, {}).items())
        for usuario_id, ws in conexiones:
            try:
                await ws.send_json(mensaje)
            except Exception:
                # Conexión caída — la limpiamos silenciosamente
                self.desconectar(usuario_id, idEmpresa)

    async def enviar_a_usuario(self, idUsuario: str, idEmpresa: str, mensaje: dict) -> bool:
        """
        Envía un mensaje privado a un usuario específico.
        Retorna True si el mensaje fue enviado, False si el usuario no está conectado.
        """
        ws = self.salas.get(idEmpresa, {}).get(idUsuario)
        if ws:
            try:
                await ws.send_json(mensaje)
                return True
            except Exception:
                self.desconectar(idUsuario, idEmpresa)
        return False

    def usuarios_conectados(self, idEmpresa: str) -> list[str]:
        """Retorna la lista de idUsuario actualmente conectados en una empresa."""
        return list(self.salas.get(idEmpresa, {}).keys())


# Instancia global compartida por toda la aplicación
manager = ConnectionManager()
