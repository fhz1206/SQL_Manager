"""全局配置模块

本模块定义了应用程序的全局配置,包括:
- 基础路径配置(图标、样式文件等)
- 业务常量配置(分页大小、提示阈值等)
- 性能优化配置
"""

import os

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, 'icon.ico')
CSS_PATH = os.path.join(BASE_DIR, 'style.css')

# 业务常量配置
TABLE_PAGE_SIZE = 1000  # 表数据默认每页加载行数
SQL_RESULT_PROMPT_THRESHOLD = 1000  # SQL查询结果超过该行数时弹出加载提示

# 性能优化配置
USE_PRAGMA_WAL = True  # 启用WAL模式提高并发性能
USE_PRAGMA_JOURNAL_MODE = "WAL"  # 设置日志模式为WAL
USE_PRAGMA_SYNCHRONOUS = "NORMAL"  # 降低同步级别提高性能
USE_PRAGMA_TEMP_STORE = "MEMORY"  # 临时表使用内存
USE_PRAGMA_MMAP_SIZE = 268435456  # 256MB内存映射
SQL_TIMEOUT = 30  # SQL查询超时时间(秒)
MAX_CONCURRENT_QUERIES = 3  # 最大并发查询数