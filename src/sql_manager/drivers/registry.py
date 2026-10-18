"""数据库驱动注册器

负责：
- 按类型注册/获取驱动类
- 统一创建驱动实例
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

from .base import BaseDriver


class DriverRegistry:
    """驱动注册表"""

    _registry: Dict[str, Type[BaseDriver]] = {}

    @classmethod
    def register(cls, db_type: str, driver_cls: Type[BaseDriver]) -> None:
        """注册驱动类"""
        cls._registry[db_type.lower()] = driver_cls

    @classmethod
    def get(cls, db_type: str) -> Optional[Type[BaseDriver]]:
        """获取驱动类"""
        return cls._registry.get(db_type.lower())

    @classmethod
    def create(cls, db_type: str, params: Dict[str, Any]) -> Optional[BaseDriver]:
        """创建驱动实例"""
        driver_cls = cls.get(db_type)
        if driver_cls is None:
            return None
        return driver_cls(params)

    @classmethod
    def list_types(cls) -> List[str]:
        """列出所有已注册的数据库类型"""
        return sorted(cls._registry.keys())


def register_driver(db_type: str):
    """装饰器：注册驱动类"""

    def _wrap(driver_cls: Type[BaseDriver]):
        DriverRegistry.register(db_type, driver_cls)
        return driver_cls

    return _wrap
