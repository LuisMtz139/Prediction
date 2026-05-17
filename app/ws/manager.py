from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """Rastrea las conexiones WebSocket activas agrupadas por empresa."""

    def __init__(self):
        self.salas: dict[str, dict[str, WebSocket]] = defaultdict(dict)

    async def conectar(self, ws: WebSocket, idUsuario: str, idEmpresa: str) -> None:
        self.salas[idEmpresa][idUsuario] = ws

    def desconectar(self, idUsuario: str, idEmpresa: str) -> None:
        self.salas.get(idEmpresa, {}).pop(idUsuario, None)

    def usuarios_conectados(self, idEmpresa: str) -> list[str]:
        return list(self.salas.get(idEmpresa, {}).keys())


# Instancia global compartida por toda la aplicación
manager = ConnectionManager()
