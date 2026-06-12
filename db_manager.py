"""数据库连接管理模块

支持多种数据库类型:
- SQLite (本地文件)
- MySQL (网络数据库)
- PostgreSQL (网络数据库)
"""

import sqlite3
import json
from typing import Optional, Dict, Any, Union
from PyQt6.QtWidgets import QMessageBox

# 尝试导入数据库驱动
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import psycopg2
    import psycopg2.extras
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False


class DatabaseConnection:
    """数据库连接管理类

    支持多种数据库类型的连接和管理
    """
    def __init__(self, db_type: str, connection_params: Dict[str, Any]):
        """
        初始化数据库连接

        Args:
            db_type: 数据库类型 ('sqlite', 'mysql', 'postgres')
            connection_params: 连接参数
        """
        self.db_type = db_type.lower()
        self.connection_params = connection_params
        self.conn = None
        self.cursor = None

        # 验证数据库类型和依赖
        if self.db_type == 'sqlite':
            self._validate_sqlite_params()
        elif self.db_type == 'mysql':
            if not MYSQL_AVAILABLE:
                raise ImportError("MySQL驱动未安装，请安装pymysql: pip install pymysql")
            self._validate_mysql_params()
        elif self.db_type == 'postgres':
            if not POSTGRES_AVAILABLE:
                raise ImportError("PostgreSQL驱动未安装，请安装psycopg2: pip install psycopg2-binary")
            self._validate_postgres_params()
        else:
            raise ValueError(f"不支持的数据库类型: {self.db_type}")

    def _validate_sqlite_params(self):
        """验证SQLite连接参数"""
        if 'database' not in self.connection_params:
            raise ValueError("SQLite连接缺少'database'参数")

    def _validate_mysql_params(self):
        """验证MySQL连接参数"""
        required_params = ['host', 'user', 'password', 'database']
        for param in required_params:
            if param not in self.connection_params:
                raise ValueError(f"MySQL连接缺少'{param}'参数")

    def _validate_postgres_params(self):
        """验证PostgreSQL连接参数"""
        required_params = ['host', 'user', 'password', 'database']
        for param in required_params:
            if param not in self.connection_params:
                raise ValueError(f"PostgreSQL连接缺少'{param}'参数")

    def connect(self) -> bool:
        """连接到数据库

        Returns:
            bool: 连接是否成功
        """
        try:
            if self.db_type == 'sqlite':
                self.conn = sqlite3.connect(
                    self.connection_params['database'],
                    timeout=self.connection_params.get('timeout', 30)
                )
            elif self.db_type == 'mysql':
                self.conn = pymysql.connect(
                    host=self.connection_params['host'],
                    user=self.connection_params['user'],
                    password=self.connection_params['password'],
                    database=self.connection_params['database'],
                    port=self.connection_params.get('port', 3306),
                    charset=self.connection_params.get('charset', 'utf8mb4'),
                    cursorclass=pymysql.cursors.DictCursor
                )
            elif self.db_type == 'postgres':
                self.conn = psycopg2.connect(
                    host=self.connection_params['host'],
                    user=self.connection_params['user'],
                    password=self.connection_params['password'],
                    database=self.connection_params['database'],
                    port=self.connection_params.get('port', 5432),
                    cursor_factory=psycopg2.extras.DictCursor
                )

            # 创建游标
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            print(f"数据库连接失败: {str(e)}")
            return False

    def disconnect(self):
        """断开数据库连接"""
        if self.cursor:
            self.cursor.close()
            self.cursor = None

        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, sql: str, params: Optional[tuple] = None) -> bool:
        """执行SQL语句

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            bool: 执行是否成功
        """
        try:
            if params:
                self.cursor.execute(sql, params)
            else:
                self.cursor.execute(sql)
            return True
        except Exception as e:
            print(f"SQL执行失败: {str(e)}")
            return False

    def fetchall(self) -> list:
        """获取所有查询结果

        Returns:
            list: 查询结果列表
        """
        try:
            return self.cursor.fetchall()
        except Exception as e:
            print(f"获取查询结果失败: {str(e)}")
            return []

    def fetchone(self) -> Optional[Dict[str, Any]]:
        """获取单条查询结果

        Returns:
            dict: 查询结果字典
        """
        try:
            return self.cursor.fetchone()
        except Exception as e:
            print(f"获取查询结果失败: {str(e)}")
            return None

    def commit(self):
        """提交事务"""
        if self.conn:
            self.conn.commit()

    def rollback(self):
        """回滚事务"""
        if self.conn:
            self.conn.rollback()

    def get_tables(self) -> list:
        """获取数据库中的所有表名

        Returns:
            list: 表名列表
        """
        try:
            if self.db_type == 'sqlite':
                self.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            elif self.db_type == 'mysql':
                self.execute("SHOW TABLES")
            elif self.db_type == 'postgres':
                self.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")

            tables = self.fetchall()
            # 处理不同数据库返回的格式
            if self.db_type == 'mysql':
                return [list(t.values())[0] for t in tables]
            elif self.db_type == 'postgres':
                return [t['tablename'] for t in tables]
            else:
                return [t[0] for t in tables]
        except Exception as e:
            print(f"获取表列表失败: {str(e)}")
            return []

    def get_table_info(self, table_name: str) -> list:
        """获取表结构信息

        Args:
            table_name: 表名

        Returns:
            list: 表结构信息列表
        """
        try:
            if self.db_type == 'sqlite':
                self.execute(f"PRAGMA table_info('{table_name}')")
            elif self.db_type == 'mysql':
                self.execute(f"DESCRIBE {table_name}")
            elif self.db_type == 'postgres':
                self.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                """)

            return self.fetchall()
        except Exception as e:
            print(f"获取表结构信息失败: {str(e)}")
            return []

    def get_db_info(self) -> Dict[str, Any]:
        """获取数据库信息

        Returns:
            dict: 数据库信息字典
        """
        try:
            info = {
                'type': self.db_type,
                'tables': self.get_tables()
            }

            if self.db_type == 'mysql':
                self.execute("SELECT VERSION() as version")
                version = self.fetchone()
                info['version'] = version['version'] if version else 'Unknown'
            elif self.db_type == 'postgres':
                self.execute("SELECT VERSION() as version")
                version = self.fetchone()
                info['version'] = version['version'] if version else 'Unknown'
            elif self.db_type == 'sqlite':
                info['version'] = sqlite3.sqlite_version

            return info
        except Exception as e:
            print(f"获取数据库信息失败: {str(e)}")
            return {'type': self.db_type, 'tables': []}

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


def test_connection(db_type: str, connection_params: Dict[str, Any]) -> Dict[str, Any]:
    """测试数据库连接

    Args:
        db_type: 数据库类型
        connection_params: 连接参数

    Returns:
        dict: 连接测试结果
    """
    result = {
        'success': False,
        'message': '',
        'db_info': None
    }

    try:
        with DatabaseConnection(db_type, connection_params) as db:
            if db.connect():
                result['success'] = True
                result['message'] = '连接成功'
                result['db_info'] = db.get_db_info()
            else:
                result['message'] = '连接失败，请检查连接参数'
    except Exception as e:
        result['message'] = f"连接错误: {str(e)}"

    return result
