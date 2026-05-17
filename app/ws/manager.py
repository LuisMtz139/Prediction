import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """
    Gestiona las conexiones WebSocket activas y las colas de respuesta por usuario.

    Estructura interna:
        salas   = { idEmpresa: { idUsuario: WebSocket } }
        colas   = { idUsuario: asyncio.Queue }  — una por usuario activo
    """

    def __init__(self):
        self.salas: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        # Cola donde el endpoint REST deposita la respuesta para cada usuario
        self.colas: dict[str, asyncio.Queue] = {}

    async def conectar(self, ws: WebSocket, idUsuario: str, idEmpresa: str) -> None:
        self.salas[idEmpresa][idUsuario] = ws
        self.colas[idUsuario] = asyncio.Queue()

    def desconectar(self, idUsuario: str, idEmpresa: str) -> None:
        self.salas.get(idEmpresa, {}).pop(idUsuario, None)
        self.colas.pop(idUsuario, None)

    async def esperar_respuesta(self, idUsuario: str) -> str:
        """El WebSocket llama esto y queda bloqueado hasta que llegue una respuesta."""
        return await self.colas[idUsuario].get()

    async def entregar_respuesta(self, idUsuario: str, respuesta: str) -> bool:
        """El endpoint REST llama esto para enviar la respuesta al usuario conectado."""
        if idUsuario not in self.colas:
            return False
        await self.colas[idUsuario].put(respuesta)
        return True

    def usuarios_conectados(self, idEmpresa: str) -> list[str]:
        return list(self.salas.get(idEmpresa, {}).keys())

    def esta_conectado(self, idUsuario: str) -> bool:
        return idUsuario in self.colas


# Instancia global compartida por toda la aplicación
manager = ConnectionManager()
