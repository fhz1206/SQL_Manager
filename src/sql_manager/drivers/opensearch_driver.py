"""OpenSearch 驱动（与 Elasticsearch API 兼容，单独注册以便明确支持）

调用 ElasticsearchDriver 的实现，OpenSearch 与 ES 7.x+ 客户端协议兼容。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .search_drivers import ElasticsearchDriver


class OpenSearchDriver(ElasticsearchDriver):
    """OpenSearch 驱动，复用 Elasticsearch 客户端实现"""

    pass
