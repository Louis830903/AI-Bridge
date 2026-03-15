"""
Card 发布器

提供 Agent Card 的发布功能，支持：
- 本地发布（私有部署）
- 远程发布（公共/私有 Registry）
- 发布/取消发布/更新操作
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
import asyncio
import json
import logging

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    import aiofiles
    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False

from .agent_card import AgentCardExtended

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    card_id: str
    registry_url: str
    error: Optional[str] = None
    published_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "card_id": self.card_id,
            "registry_url": self.registry_url,
            "error": self.error,
            "published_at": self.published_at,
        }


class CardPublisher(ABC):
    """Card 发布器抽象基类"""
    
    @abstractmethod
    async def publish(self, card: AgentCardExtended) -> PublishResult:
        """发布 Card
        
        Args:
            card: 要发布的 Agent Card
            
        Returns:
            发布结果
        """
        pass
    
    @abstractmethod
    async def unpublish(self, card_id: str) -> bool:
        """取消发布
        
        Args:
            card_id: Card ID
            
        Returns:
            是否成功
        """
        pass
    
    @abstractmethod
    async def update(self, card: AgentCardExtended) -> PublishResult:
        """更新 Card
        
        Args:
            card: 要更新的 Agent Card
            
        Returns:
            更新结果
        """
        pass
    
    @abstractmethod
    async def get(self, card_id: str) -> Optional[AgentCardExtended]:
        """获取 Card
        
        Args:
            card_id: Card ID
            
        Returns:
            Agent Card 或 None
        """
        pass


class LocalCardPublisher(CardPublisher):
    """本地 Card 发布器（用于私有部署）
    
    支持内存存储和文件持久化
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        persist: bool = False
    ):
        """
        Args:
            storage_path: 持久化存储路径
            persist: 是否持久化到文件
        """
        self._storage_path = Path(storage_path) if storage_path else Path(".aibridge/cards")
        self._persist = persist
        self._cards: Dict[str, AgentCardExtended] = {}
        self._lock = asyncio.Lock()
        
        if self._persist:
            self._storage_path.mkdir(parents=True, exist_ok=True)
    
    async def publish(self, card: AgentCardExtended) -> PublishResult:
        """发布 Card 到本地"""
        async with self._lock:
            # 更新时间戳
            card.metadata.updated_at = datetime.utcnow()
            if card.id not in self._cards:
                card.metadata.created_at = datetime.utcnow()
            
            self._cards[card.id] = card
            
            # 持久化
            if self._persist:
                await self._save_card(card)
            
            logger.info(f"Published card locally: {card.id}")
            
            return PublishResult(
                success=True,
                card_id=card.id,
                registry_url=f"local://{self._storage_path}",
                published_at=card.metadata.updated_at.isoformat()
            )
    
    async def unpublish(self, card_id: str) -> bool:
        """取消发布"""
        async with self._lock:
            if card_id in self._cards:
                del self._cards[card_id]
                
                # 删除持久化文件
                if self._persist:
                    await self._delete_card_file(card_id)
                
                logger.info(f"Unpublished card: {card_id}")
                return True
            return False
    
    async def update(self, card: AgentCardExtended) -> PublishResult:
        """更新 Card"""
        return await self.publish(card)
    
    async def get(self, card_id: str) -> Optional[AgentCardExtended]:
        """获取 Card"""
        return self._cards.get(card_id)
    
    def get_all(self) -> List[AgentCardExtended]:
        """获取所有 Cards"""
        return list(self._cards.values())
    
    async def load_from_disk(self) -> int:
        """从磁盘加载所有 Cards
        
        Returns:
            加载的 Card 数量
        """
        if not self._persist or not self._storage_path.exists():
            return 0
        
        count = 0
        for file_path in self._storage_path.glob("*.json"):
            try:
                card = await self._load_card(file_path)
                if card:
                    self._cards[card.id] = card
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to load card from {file_path}: {e}")
        
        logger.info(f"Loaded {count} cards from disk")
        return count
    
    async def _save_card(self, card: AgentCardExtended) -> None:
        """保存 Card 到文件"""
        file_path = self._storage_path / f"{card.id}.json"
        content = json.dumps(card.to_dict(), indent=2, ensure_ascii=False)
        
        if HAS_AIOFILES:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
        else:
            file_path.write_text(content, encoding="utf-8")
    
    async def _load_card(self, file_path: Path) -> Optional[AgentCardExtended]:
        """从文件加载 Card"""
        try:
            if HAS_AIOFILES:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    content = await f.read()
            else:
                content = file_path.read_text(encoding="utf-8")
            
            data = json.loads(content)
            return AgentCardExtended.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load card from {file_path}: {e}")
            return None
    
    async def _delete_card_file(self, card_id: str) -> None:
        """删除 Card 文件"""
        file_path = self._storage_path / f"{card_id}.json"
        if file_path.exists():
            file_path.unlink()


class RemoteCardPublisher(CardPublisher):
    """远程 Registry 发布器
    
    支持向远程 Agent Registry 发布 Card
    """
    
    def __init__(
        self,
        registry_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        retry_attempts: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Args:
            registry_url: Registry 服务地址
            api_key: API 密钥（可选）
            timeout: 请求超时时间
            retry_attempts: 重试次数
            retry_delay: 重试间隔
        """
        if not HAS_AIOHTTP:
            raise ImportError("aiohttp is required for RemoteCardPublisher. Install with: pip install aiohttp")
        
        self._registry_url = registry_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._retry_attempts = retry_attempts
        self._retry_delay = retry_delay
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AI-Bridge/5.0",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers
    
    async def _request_with_retry(
        self,
        method: str,
        url: str,
        json_data: Dict[str, Any] = None
    ) -> tuple[int, Optional[Dict[str, Any]], Optional[str]]:
        """带重试的请求
        
        Returns:
            (status_code, response_data, error_message)
        """
        last_error = None
        
        for attempt in range(self._retry_attempts):
            try:
                async with aiohttp.ClientSession() as session:
                    request_kwargs = {
                        "headers": self._get_headers(),
                        "timeout": aiohttp.ClientTimeout(total=self._timeout),
                    }
                    if json_data:
                        request_kwargs["json"] = json_data
                    
                    async with session.request(method, url, **request_kwargs) as resp:
                        status = resp.status
                        try:
                            data = await resp.json()
                        except Exception:
                            data = None
                        
                        if status < 500:  # 非服务器错误，不重试
                            return status, data, None
                        
                        last_error = f"HTTP {status}"
                        
            except asyncio.TimeoutError:
                last_error = "Request timeout"
            except aiohttp.ClientError as e:
                last_error = str(e)
            except Exception as e:
                last_error = str(e)
            
            if attempt < self._retry_attempts - 1:
                await asyncio.sleep(self._retry_delay * (attempt + 1))
        
        return 0, None, last_error
    
    async def publish(self, card: AgentCardExtended) -> PublishResult:
        """发布 Card 到远程 Registry"""
        url = f"{self._registry_url}/agents"
        card_data = card.to_dict()
        
        status, data, error = await self._request_with_retry("POST", url, card_data)
        
        if status in (200, 201):
            logger.info(f"Published card to {self._registry_url}: {card.id}")
            return PublishResult(
                success=True,
                card_id=card.id,
                registry_url=self._registry_url,
                published_at=data.get("published_at") if data else None
            )
        else:
            error_msg = error or (data.get("error") if data else f"HTTP {status}")
            logger.warning(f"Failed to publish card {card.id}: {error_msg}")
            return PublishResult(
                success=False,
                card_id=card.id,
                registry_url=self._registry_url,
                error=error_msg
            )
    
    async def unpublish(self, card_id: str) -> bool:
        """取消发布"""
        url = f"{self._registry_url}/agents/{card_id}"
        
        status, _, error = await self._request_with_retry("DELETE", url)
        
        if status in (200, 204):
            logger.info(f"Unpublished card from {self._registry_url}: {card_id}")
            return True
        else:
            logger.warning(f"Failed to unpublish card {card_id}: {error or f'HTTP {status}'}")
            return False
    
    async def update(self, card: AgentCardExtended) -> PublishResult:
        """更新 Card"""
        url = f"{self._registry_url}/agents/{card.id}"
        card_data = card.to_dict()
        
        status, data, error = await self._request_with_retry("PUT", url, card_data)
        
        if status == 200:
            logger.info(f"Updated card in {self._registry_url}: {card.id}")
            return PublishResult(
                success=True,
                card_id=card.id,
                registry_url=self._registry_url,
                published_at=data.get("updated_at") if data else None
            )
        else:
            error_msg = error or (data.get("error") if data else f"HTTP {status}")
            logger.warning(f"Failed to update card {card.id}: {error_msg}")
            return PublishResult(
                success=False,
                card_id=card.id,
                registry_url=self._registry_url,
                error=error_msg
            )
    
    async def get(self, card_id: str) -> Optional[AgentCardExtended]:
        """获取 Card"""
        url = f"{self._registry_url}/agents/{card_id}"
        
        status, data, error = await self._request_with_retry("GET", url)
        
        if status == 200 and data:
            return AgentCardExtended.from_dict(data)
        return None


class MultiRegistryPublisher(CardPublisher):
    """多 Registry 发布器
    
    支持同时发布到多个 Registry
    """
    
    def __init__(self, publishers: List[CardPublisher] = None):
        """
        Args:
            publishers: 发布器列表
        """
        self._publishers: List[CardPublisher] = publishers or []
    
    def add_publisher(self, publisher: CardPublisher) -> None:
        """添加发布器"""
        self._publishers.append(publisher)
    
    def remove_publisher(self, publisher: CardPublisher) -> None:
        """移除发布器"""
        if publisher in self._publishers:
            self._publishers.remove(publisher)
    
    async def publish(self, card: AgentCardExtended) -> PublishResult:
        """发布到所有 Registry
        
        返回第一个成功的结果，或最后一个失败的结果
        """
        if not self._publishers:
            return PublishResult(
                success=False,
                card_id=card.id,
                registry_url="none",
                error="No publishers configured"
            )
        
        # 并发发布
        tasks = [p.publish(card) for p in self._publishers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_results = []
        failure_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failure_results.append(PublishResult(
                    success=False,
                    card_id=card.id,
                    registry_url="unknown",
                    error=str(result)
                ))
            elif result.success:
                success_results.append(result)
            else:
                failure_results.append(result)
        
        if success_results:
            # 返回第一个成功结果，但记录所有结果
            logger.info(
                f"Published card {card.id} to {len(success_results)}/{len(self._publishers)} registries"
            )
            return success_results[0]
        else:
            return failure_results[-1] if failure_results else PublishResult(
                success=False,
                card_id=card.id,
                registry_url="unknown",
                error="All publishers failed"
            )
    
    async def unpublish(self, card_id: str) -> bool:
        """从所有 Registry 取消发布"""
        if not self._publishers:
            return False
        
        tasks = [p.unpublish(card_id) for p in self._publishers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Unpublished card {card_id} from {success_count}/{len(self._publishers)} registries")
        
        return success_count > 0
    
    async def update(self, card: AgentCardExtended) -> PublishResult:
        """更新所有 Registry 中的 Card"""
        return await self.publish(card)
    
    async def get(self, card_id: str) -> Optional[AgentCardExtended]:
        """从第一个可用的 Registry 获取 Card"""
        for publisher in self._publishers:
            card = await publisher.get(card_id)
            if card:
                return card
        return None
