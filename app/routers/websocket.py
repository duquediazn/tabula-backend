from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

router = APIRouter()


class ConnectionManager:
    """Esta clase guarda todas las conexiones activas en una lista.
    Cada vez que alguien se conecta al WebSocket, se añade a esta lista."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()  # .accept() es obligatorio para establecer la conexión con el cliente.
        self.active_connections.append(
            websocket
        )  # Después, lo guardamos en la lista de conexiones activas.

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(
            websocket
        )  # Si el cliente se desconecta (o se cae), lo quitamos de la lista.

    async def broadcast(self, message: str):
        """Este método envía un mensaje de texto a todos los clientes conectados."""
        for connection in self.active_connections:
            await connection.send_text(message)


# Instanciamos para poder usarla en cualquier parte del código
manager = ConnectionManager()


@router.websocket("/ws/movimientos")
async def websocket_endpoint(websocket: WebSocket):
    # Llamamos a manager.connect() para aceptar la conexión y guardarla.
    await manager.connect(websocket)

    try:
        # Mantenemos la conexión activa y viva con un bucle infinito.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        # Cuando el cliente se desconecta, lo removemos para no dejar conexiones zombis.
        manager.disconnect(websocket)
