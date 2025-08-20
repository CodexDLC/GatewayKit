# game_server/app_gateway/gateway/client_connection_manager.py


from typing import Dict, Optional

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from libs.utils.logging_setup import app_logger as logger


class ClientConnectionManager:
    """
    Универсальный менеджер для управления всеми активными WebSocket-соединениями.
    Хранит ссылки на WebSocket-соединения, индексированные по-уникальному client_id.
    """

    # Словарь для хранения активных соединений: {client_id: WebSocket}
    active_connections: Dict[str, WebSocket] = {}
    # Словарь для хранения типов клиентов: {client_id: client_type}
    client_types: Dict[str, str] = {}

    def __init__(self):
        logger.info("✨ ClientConnectionManager инициализирован.")

    async def connect(
        self, websocket: WebSocket, client_id: str, client_type: str
    ) -> None:
        """
        Регистрирует новое WebSocket-соединение.
        """
        # Если соединение с таким client_id уже существует, закроем старое
        if client_id in self.active_connections:
            old_websocket = self.active_connections[client_id]
            logger.warning(
                f"Существующее соединение для client_id {client_id} будет закрыто перед установкой нового."
            )
            # Попытаемся корректно закрыть старое соединение, если оно еще активно
            if (
                old_websocket.client_state != WebSocketState.DISCONNECTED
            ):  # <--- ИЗМЕНЕНО
                try:
                    await old_websocket.close(
                        code=1000,
                        reason="New connection established for this client ID.",
                    )
                except (
                    RuntimeError
                ):  # Может произойти, если соединение уже в процессе закрытия
                    pass

        self.active_connections[client_id] = websocket
        self.client_types[client_id] = client_type
        logger.info(
            f"✅ Client ID {client_id} ({client_type}) подключен. Всего активных: {len(self.active_connections)}"
        )

    def disconnect(self, client_id: str) -> None:
        """
        Удаляет соединение по client_id.
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.client_types[client_id]
            logger.info(
                f"❌ Client ID {client_id} отключен. Всего активных: {len(self.active_connections)}"
            )
        else:
            logger.warning(f"Попытка отключить неизвестный client_id: {client_id}")

    async def send_message_to_client(self, client_id: str, message: str) -> bool:
        """
        Отправляет текстовое сообщение конкретному клиенту по его client_id.
        Возвращает True в случае успеха, False иначе.
        """
        websocket = self.active_connections.get(client_id)
        if (
            websocket and websocket.client_state != WebSocketState.DISCONNECTED
        ):  # <--- ИЗМЕНЕНО
            try:
                await websocket.send_text(message)
                return True
            except WebSocketDisconnect:
                logger.warning(
                    f"Client ID {client_id} уже отключен при попытке отправить сообщение."
                )
                self.disconnect(client_id)  # Удаляем, так как соединение закрыто
                return False
            except Exception as e:
                logger.error(
                    f"Ошибка отправки сообщения Client ID {client_id}: {e}",
                    exc_info=True,
                )
                return False
        else:
            logger.warning(
                f"WebSocket-соединение для Client ID {client_id} не найдено или закрыто."
            )
            self.disconnect(client_id)  # Удаляем, если соединение неактивно
            return False

    async def send_message_to_client_type(self, client_type: str, message: str) -> int:
        """
        Отправляет текстовое сообщение всем клиентам определенного типа.
        Возвращает количество отправленных сообщений.
        """
        sent_count = 0
        disconnected_clients = []
        for client_id, ws in list(
            self.active_connections.items()
        ):  # Итерируем по копии
            if self.client_types.get(client_id) == client_type:
                if ws.client_state != WebSocketState.DISCONNECTED:  # <--- ИЗМЕНЕНО
                    try:
                        await ws.send_text(message)
                        sent_count += 1
                    except WebSocketDisconnect:
                        logger.warning(
                            f"Client ID {client_id} ({client_type}) отключен при попытке отправить сообщение."
                        )
                        disconnected_clients.append(client_id)
                    except Exception as e:
                        logger.error(
                            f"Ошибка отправки сообщения Client ID {client_id} ({client_type}): {e}",
                            exc_info=True,
                        )
                else:
                    disconnected_clients.append(client_id)

        for client_id in disconnected_clients:
            self.disconnect(client_id)  # Удаляем отключенные соединения

        return sent_count

    def get_client_id_by_websocket(self, websocket: WebSocket) -> Optional[str]:
        """
        Возвращает client_id по объекту WebSocket.
        """
        for client_id, ws in self.active_connections.items():
            if ws == websocket:
                return client_id
        return None

    def get_client_type(self, client_id: str) -> Optional[str]:
        """
        Возвращает тип клиента по его client_id.
        """
        return self.client_types.get(client_id)
