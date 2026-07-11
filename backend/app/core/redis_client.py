"""
Alakoro FiberSense - Redis Client
Async Redis Pub/Sub event bus.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RedisEventBus:
    """Event bus baseado em Redis Pub/Sub."""

    def __init__(self):
        self._redis: redis.Redis = None
        self._pubsub = None
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._listener_task = None

    async def connect(self):
        """Conecta ao Redis."""
        self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe("alakoro:events")
        self._running = True
        self._listener_task = asyncio.create_task(self._listen())
        logger.info("Redis event bus connected")

    async def disconnect(self):
        """Desconecta do Redis."""
        self._running = False
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        logger.info("Redis event bus disconnected")

    async def publish(self, channel: str, message: str):
        """Publica uma mensagem em um canal."""
        if self._redis:
            await self._redis.publish(f"alakoro:{channel}", message)

    async def subscribe(self, channel: str, handler: Callable):
        """Subscreve um handler para um canal."""
        full_channel = f"alakoro:{channel}"
        if full_channel not in self._handlers:
            self._handlers[full_channel] = []
            if self._pubsub:
                await self._pubsub.subscribe(full_channel)
        self._handlers[full_channel].append(handler)
        logger.info(f"Subscribed to {full_channel}")

    async def _listen(self):
        """Loop de escuta de mensagens."""
        while self._running:
            try:
                if self._pubsub:
                    message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message["type"] == "message":
                        channel = message["channel"]
                        data = message["data"]
                        handlers = self._handlers.get(channel, [])
                        for handler in handlers:
                            try:
                                await handler(data)
                            except Exception as e:
                                logger.error(f"Handler error: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Listener error: {e}")
                await asyncio.sleep(1)


# Global instance
event_bus = RedisEventBus()
