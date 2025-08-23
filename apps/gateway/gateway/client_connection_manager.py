# apps/gateway/gateway/client_connection_manager.py
import time
from typing import Dict, Optional, Tuple

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from libs.utils.logging_setup import app_logger as logger


class ClientConnectionManager:
    """
    Управляет активными WebSocket-соединениями и временем их последней активности.
    """

    active_connections: Dict[str, Tuple[WebSocket, float]] = {}
    client_types: Dict[str, str] = {}

    def __init__(self):
        logger.info("✨ ClientConnectionManager инициализирован.")

    async def connect(
        self, websocket: WebSocket, client_id: str, client_type: str
    ) -> None:
        if client_id in self.active_connections:
            old_websocket, _ = self.active_connections[client_id]
            logger.warning(
                f"Существующее соединение для client_id {client_id} будет закрыто."
            )
            if old_websocket.client_state != WebSocketState.DISCONNECTED:
                try:
                    await old_websocket.close(
                        code=1000,
                        reason="New connection established for this client ID.",
                    )
                except RuntimeError:
                    pass

        self.active_connections[client_id] = (websocket, time.monotonic())
        self.client_types[client_id] = client_type
        logger.info(
            f"✅ Client ID {client_id} ({client_type}) подключен. Всего: {len(self.active_connections)}"
        )

    def disconnect(self, client_id: str) -> None:
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            if client_id in self.client_types:
                del self.client_types[client_id]
            logger.info(
                f"❌ Client ID {client_id} отключен. Всего: {len(self.active_connections)}"
            )

    def update_activity(self, client_id: str):
        if client_id in self.active_connections:
            websocket, _ = self.active_connections[client_id]
            self.active_connections[client_id] = (websocket, time.monotonic())

    async def send_message_to_client(self, client_id: str, message: str) -> bool:
        connection_data = self.active_connections.get(client_id)
        if not connection_data:
            logger.warning(f"Соединение для Client ID {client_id} не найдено.")
            return False

        websocket, _ = connection_data
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.send_text(message)
                return True
            except (WebSocketDisconnect, RuntimeError):
                self.disconnect(client_id)
                return False
        else:
            self.disconnect(client_id)
            return False

    # --- ВОССТАНОВЛЕННЫЙ МЕТОД ---
    async def send_message_to_client_type(self, client_type: str, message: str) -> int:
        """
        Отправляет текстовое сообщение всем клиентам определенного типа.
        Возвращает количество отправленных сообщений.
        """
        sent_count = 0
        disconnected_clients = []
        # Итерируем по копии, чтобы безопасно удалять элементы
        for client_id, (ws, _) in list(self.active_connections.items()):
            if self.client_types.get(client_id) == client_type:
                if ws.client_state != WebSocketState.DISCONNECTED:
                    try:
                        await ws.send_text(message)
                        sent_count += 1
                    except (WebSocketDisconnect, RuntimeError):
                        logger.warning(
                            f"Client ID {client_id} ({client_type}) отключен при попытке широковещательной отправки."
                        )
                        disconnected_clients.append(client_id)
                else:
                    disconnected_clients.append(client_id)

        for client_id in disconnected_clients:
            self.disconnect(client_id)

        return sent_count

    # --- КОНЕЦ ВОССТАНОВЛЕННОГО МЕТОДА ---

    def get_client_id_by_websocket(self, websocket: WebSocket) -> Optional[str]:
        for client_id, (ws, _) in self.active_connections.items():
            if ws == websocket:
                return client_id
        return None

    def get_client_type(self, client_id: str) -> Optional[str]:
        return self.client_types.get(client_id)
