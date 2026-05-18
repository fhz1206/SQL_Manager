import os

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, 'icon.ico')
CSS_PATH = os.path.join(BASE_DIR, 'style.css')

# 业务常量配置
TABLE_PAGE_SIZE = 1000  # 表数据默认每页加载行数
SQL_RESULT_PROMPT_THRESHOLD = 1000  # SQL查询结果超过该行数时弹出加载提示