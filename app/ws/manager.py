import asyncio
from collections import defaultdict

from fastapi import WebSocket


class ConnectionManager:
    """
    Gestiona conexiones WebSocket y colas de respuesta por usuario.

    Clave interna: "{numeroCelular}-{numeroEmpresa}"
    """

    def __init__(self):
        self.salas: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self.colas: dict[str, asyncio.Queue] = {}

    def _clave(self, numeroCelular: str, numeroEmpresa: str) -> str:
        return f"{numeroCelular}-{numeroEmpresa}"

    async def conectar(self, ws: WebSocket, numeroCelular: str, numeroEmpresa: str) -> None:
        self.salas[numeroEmpresa][numeroCelular] = ws
        self.colas[self._clave(numeroCelular, numeroEmpresa)] = asyncio.Queue()

    def desconectar(self, numeroCelular: str, numeroEmpresa: str) -> None:
        self.salas.get(numeroEmpresa, {}).pop(numeroCelular, None)
        self.colas.pop(self._clave(numeroCelular, numeroEmpresa), None)

    def esta_conectado(self, numeroCelular: str, numeroEmpresa: str) -> bool:
        return self._clave(numeroCelular, numeroEmpresa) in self.colas

    async def esperar_respuesta(self, numeroCelular: str, numeroEmpresa: str) -> str:
        return await self.colas[self._clave(numeroCelular, numeroEmpresa)].get()

    async def entregar_respuesta(self, numeroCelular: str, numeroEmpresa: str, respuesta: str) -> bool:
        clave = self._clave(numeroCelular, numeroEmpresa)
        if clave not in self.colas:
            return False
        await self.colas[clave].put(respuesta)
        return True

    def usuarios_conectados(self, numeroEmpresa: str) -> list[str]:
        return list(self.salas.get(numeroEmpresa, {}).keys())


manager = ConnectionManager()
