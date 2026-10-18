"""数据库分片管理器

功能：
- 设置单分片最大存储行数（shard_size）
- 基于范围（range）或哈希（hash）的分片策略
- 自动将表数据切分为多个分片，每个分片映射到具体节点
- 支持跨分片查询聚合
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import hashlib
import threading


@dataclass
class Shard:
    shard_id: str
    group_id: str
    node_id: str
    table_name: str
    shard_strategy: str  # "range" | "hash"
    row_count: int = 0
    range_start: Optional[Any] = None
    range_end: Optional[Any] = None
    hash_mod: Optional[int] = None
    hash_remainder: Optional[int] = None
    created_at: float = field(default_factory=lambda: __import__("time").time())


class ShardManager:
    """分片管理器

    负责维护分片元数据、计算数据落入哪个分片、提供跨分片聚合接口。
    """

    def __init__(self, default_shard_size: int = 1_000_000):
        self.default_shard_size = default_shard_size
        self._shards: Dict[str, Shard] = {}          # shard_id -> Shard
        self._table_shards: Dict[str, List[str]] = {}  # table_name -> [shard_id, ...]
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # 分片元数据
    # ------------------------------------------------------------------
    def create_shard(
        self,
        shard_id: str,
        group_id: str,
        node_id: str,
        table_name: str,
        strategy: str = "range",
        shard_size: Optional[int] = None,
        range_start: Optional[Any] = None,
        range_end: Optional[Any] = None,
        hash_mod: Optional[int] = None,
        hash_remainder: Optional[int] = None,
    ) -> Shard:
        with self._lock:
            shard = Shard(
                shard_id=shard_id,
                group_id=group_id,
                node_id=node_id,
                table_name=table_name,
                shard_strategy=strategy,
                range_start=range_start,
                range_end=range_end,
                hash_mod=hash_mod,
                hash_remainder=hash_remainder,
            )
            self._shards[shard_id] = shard
            self._table_shards.setdefault(table_name, []).append(shard_id)
        return shard

    def get_shard(self, shard_id: str) -> Optional[Shard]:
        with self._lock:
            return self._shards.get(shard_id)

    def list_shards(self, table_name: Optional[str] = None) -> List[Shard]:
        with self._lock:
            if table_name:
                ids = self._table_shards.get(table_name, [])
                return [self._shards[sid] for sid in ids if sid in self._shards]
            return list(self._shards.values())

    def get_shards_for_table(self, table_name: str) -> List[Shard]:
        return self.list_shards(table_name)

    def update_row_count(self, shard_id: str, count: int) -> None:
        with self._lock:
            if shard_id in self._shards:
                self._shards[shard_id].row_count = count

    def remove_shard(self, shard_id: str) -> None:
        with self._lock:
            shard = self._shards.pop(shard_id, None)
            if shard:
                ids = self._table_shards.get(shard.table_name, [])
                if shard_id in ids:
                    ids.remove(shard_id)

    # ------------------------------------------------------------------
    # 分片路由：计算数据落入哪个分片
    # ------------------------------------------------------------------
    def locate_shard(self, table_name: str, shard_key: Any,
                     strategy: str = "hash") -> Optional[Shard]:
        """根据分片键定位数据所在分片"""
        shards = self.get_shards_for_table(table_name)
        if not shards:
            return None

        if strategy == "range":
            for shard in shards:
                if shard.shard_strategy != "range":
                    continue
                if shard.range_start is not None and shard_key < shard.range_start:
                    continue
                if shard.range_end is not None and shard_key >= shard.range_end:
                    continue
                return shard
            # 落空则返回第一个 range 分片（兜底）
            range_shards = [s for s in shards if s.shard_strategy == "range"]
            return range_shards[0] if range_shards else shards[0]

        # hash：对 shard_key 做稳定哈希，取模后匹配
        if strategy == "hash":
            key_bytes = str(shard_key).encode("utf-8")
            digest = int(hashlib.md5(key_bytes).hexdigest(), 16)
            for shard in shards:
                if shard.shard_strategy != "hash":
                    continue
                if shard.hash_mod is None or shard.hash_remainder is None:
                    continue
                if digest % shard.hash_mod == shard.hash_remainder:
                    return shard
            # 兜底：返回第一个 hash 分片
            hash_shards = [s for s in shards if s.shard_strategy == "hash"]
            return hash_shards[0] if hash_shards else shards[0]

        return shards[0]

    def auto_shard_table(
        self,
        table_name: str,
        group_id: str,
        node_ids: List[str],
        total_rows: int,
        shard_size: Optional[int] = None,
        strategy: str = "range",
    ) -> List[Shard]:
        """自动为表切分分片。

        Args:
            table_name: 表名
            group_id: 所属数据库组
            node_ids: 可用节点列表（分片会轮询分布到这些节点）
            total_rows: 表总行数
            shard_size: 单分片最大行数，默认使用 default_shard_size
            strategy: 分片策略 "range" 或 "hash"
        """
        size = shard_size or self.default_shard_size
        shard_count = max(1, (total_rows + size - 1) // size)
        created: List[Shard] = []

        # 移除旧分片
        for sid in list(self._table_shards.get(table_name, [])):
            self.remove_shard(sid)

        for i in range(shard_count):
            shard_id = f"{table_name}_shard_{i+1}"
            node_id = node_ids[i % len(node_ids)]
            if strategy == "range":
                start = i * size
                end = min((i + 1) * size, total_rows)
                self.create_shard(
                    shard_id=shard_id,
                    group_id=group_id,
                    node_id=node_id,
                    table_name=table_name,
                    strategy="range",
                    range_start=start,
                    range_end=end,
                )
            else:
                self.create_shard(
                    shard_id=shard_id,
                    group_id=group_id,
                    node_id=node_id,
                    table_name=table_name,
                    strategy="hash",
                    hash_mod=shard_count,
                    hash_remainder=i,
                )
            created.append(self._shards[shard_id])
        return created
