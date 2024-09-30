# app/services/global_listener.py

import asyncio
from abc import ABC, abstractmethod
from uuid import UUID
from typing import Any, Dict, List, Set
import logging

logger = logging.getLogger(__name__)


class IGlobalListener(ABC):
    @abstractmethod
    async def subscribe(self, job_id: UUID) -> asyncio.Queue:
        """
        Subscribe to updates for a specific job.

        :param job_id: UUID of the job to subscribe to.
        :return: An asyncio.Queue instance where updates will be published.
        """
        pass

    @abstractmethod
    async def unsubscribe(self, job_id: UUID, queue: asyncio.Queue) -> None:
        """
        Unsubscribe from updates for a specific job.

        :param job_id: UUID of the job to unsubscribe from.
        :param queue: The asyncio.Queue instance to remove from subscribers.
        """
        pass

    @abstractmethod
    async def publish_update(self, job_id: UUID, update_data: Dict[str, Any]) -> None:
        """
        Publish an update to all subscribers of a specific job.

        :param job_id: UUID of the job to publish the update to.
        :param update_data: A dictionary containing update information.
        """
        pass


class GlobalListener(IGlobalListener):
    """
    Manages global subscribers for different job IDs and facilitates publishing updates to them.
    """

    def __init__(self):
        self.subscribers: Dict[UUID, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)

    async def subscribe(self, job_id: UUID, maxsize: int = 100) -> asyncio.Queue:
        """
        Subscribe to updates for a specific job ID.

        Args:
            job_id (UUID): The job ID to subscribe to.
            maxsize (int): Maximum size of the subscriber's queue.

        Returns:
            asyncio.Queue: The queue through which updates will be received.
        """
        async with self._lock:
            if job_id not in self.subscribers:
                self.subscribers[job_id] = set()
            queue = asyncio.Queue(maxsize=maxsize)
            self.subscribers[job_id].add(queue)
            self.logger.info(
                f"New subscriber added for job_id: {job_id}. Total subscribers: {len(self.subscribers[job_id])}"
            )
            return queue

    async def unsubscribe(self, job_id: UUID, queue: asyncio.Queue):
        """
        Unsubscribe from updates for a specific job ID.

        Args:
            job_id (UUID): The job ID to unsubscribe from.
            queue (asyncio.Queue): The subscriber's queue to remove.
        """
        async with self._lock:
            if job_id in self.subscribers:
                self.subscribers[job_id].discard(queue)
                self.logger.info(
                    f"Subscriber removed for job_id: {job_id}. Remaining subscribers: {len(self.subscribers[job_id])}"
                )
                if not self.subscribers[job_id]:
                    del self.subscribers[job_id]
                    self.logger.info(f"No more subscribers for job_id: {job_id}. Removed from subscribers list.")

    async def publish_update(self, job_id: UUID, update: Any, timeout: float = 1.0):
        """
        Publish an update to all subscribers of a specific job ID.

        Args:
            job_id (UUID): The job ID to publish the update to.
            update (Any): The update data.
            timeout (float): Timeout for each subscriber's queue.
        """
        async with self._lock:
            subscribers = self.subscribers.get(job_id, set()).copy()

        if subscribers:
            self.logger.info(f"Publishing update for job_id: {job_id}. Update: {update}")
            tasks = [self._publish_to_queue(queue, update, timeout) for queue in subscribers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_publishes = sum(1 for r in results if r is True)
            self.logger.info(
                f"Update published to {successful_publishes}/{len(subscribers)} subscribers for job_id: {job_id}"
            )
        else:
            self.logger.warning(f"No subscribers found for job_id: {job_id}. Update not published.")

    async def _publish_to_queue(self, queue: asyncio.Queue, update: Any, timeout: float) -> bool:
        """
        Helper method to publish an update to a single subscriber's queue.

        Args:
            queue (asyncio.Queue): The subscriber's queue.
            update (Any): The update data.
            timeout (float): Timeout for the queue operation.

        Returns:
            bool: True if the update was successfully published, False otherwise.
        """
        try:
            await asyncio.wait_for(queue.put(update), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            self.logger.warning("Timeout occurred while publishing update to a subscriber.")
            return False
        except asyncio.QueueFull:
            self.logger.warning("Subscriber queue is full. Dropping update.")
            return False


def get_global_listener() -> IGlobalListener:
    """
    Dependency provider for the GlobalListener.
    Ensures a singleton instance is used throughout the application.
    """
    if not hasattr(get_global_listener, "instance"):
        get_global_listener.instance = GlobalListener()
    return get_global_listener.instance
