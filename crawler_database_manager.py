import json
from copy import deepcopy
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Generator
import sqlite3

class CrawlerDatabaseManager:
    def __init__(self, db_path: str="crawler_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库和表结构"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS search_results (
                    url TEXT PRIMARY KEY NOT NULL,
                    keywords TEXT,
                    title TEXT,
                    site_name TEXT,
                    site_icon TEXT,
                    date TEXT,
                    snippet TEXT,
                    context TEXT,
                    CHECK (url LIKE 'http%')
                )
            ''')

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row  # 使查询结果支持字典访问
            yield conn
        finally:
            conn.close()

    def upsert(self, data: Dict[str, Any]) -> bool:
        """插入或更新记录（原子化操作）"""
        required_fields = {'url'}
        if not required_fields.issubset(data.keys()):
            raise ValueError(f"数据必须包含字段: {required_fields}")

        # 数据预处理
        processed = deepcopy(data)
        old_data = self.get(data['url'])
        if old_data:
            processed['keywords'] = list(set(old_data['keywords'] + data.get('keywords', [])))
        processed['keywords'] = json.dumps(processed.get('keywords', []))

        sql = '''
            INSERT INTO search_results (
                url, keywords, title, site_name, site_icon, date, snippet, context
            ) VALUES (:url, :keywords, :title, :site_name, :site_icon, :date, :snippet, :context)
            ON CONFLICT(url) DO UPDATE SET
                keywords = excluded.keywords,
                title = excluded.title,
                site_name = excluded.site_name,
                site_icon = excluded.site_icon,
                date = excluded.date,
                snippet = excluded.snippet,
                context = excluded.context
        '''
        try:
            with self._get_connection() as conn:
                conn.execute(sql, processed)
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"数据库操作失败: {e}")
            return False

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """根据 URL 获取记录"""
        sql = "SELECT * FROM search_results WHERE url = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(sql, (url,))
                row = cursor.fetchone()
                if row:
                    return self._row_to_dict(row)
                return None
        except sqlite3.Error as e:
            print(f"查询失败: {e}")
            return None

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将查询结果转换为字典并反序列化特殊字段"""
        data = dict(row)
        data['keywords'] = json.loads(data['keywords']) if data['keywords'] else []
        return data

    def batch_upsert(self, data_list: List[Dict[str, Any]]) -> int:
        """批量插入/更新（事务操作）"""
        success_count = 0
        try:
            with self._get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                for data in data_list:
                    if self.upsert(data):
                        success_count += 1
                conn.commit()
                return success_count
        except sqlite3.Error as e:
            print(f"Batch upsert failed: {e}")
            conn.rollback()
            return 0