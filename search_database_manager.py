import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Generator
from contextlib import contextmanager
import sqlite3


class SearchDatabaseManager:
    def __init__(self, db_path: str="search_cache.db", outdated_days: int=3):
        self.db_path = db_path
        self.outdated_days = outdated_days
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS search_cache (
                    original_query TEXT NOT NULL,
                    num_results INTEGER NOT NULL,
                    results_json TEXT,
                    created_time TIMESTAMP,
                    PRIMARY KEY (original_query, num_results)
                )
            ''')
            conn.commit()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row  # 使查询结果支持字典访问
            yield conn
        finally:
            conn.close()

    def get(self, original_query: str, num_results: int) -> Optional[Dict]:
        """获取有效缓存结果（3天内）"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute('''
                    SELECT results_json, created_time 
                    FROM search_cache 
                    WHERE original_query = ? AND num_results = ?
                ''', (original_query, num_results))
                
                if row := cursor.fetchone():
                    cache_time = datetime.fromisoformat(row["created_time"])
                    if (datetime.now() - cache_time) <= timedelta(days=self.outdated_days):
                        return json.loads(row["results_json"])
        except sqlite3.Error as e:
            print(f"Query error: {e}")
        return None
    
    def upsert(self, original_query: str, num_results: int, results: Dict) -> bool:
        """原子化插入/更新单条记录"""
        try:
            with self._get_connection() as conn:
                # 使用 REPLACE INTO 语句实现插入或更新：完全覆盖旧记录且不关心自增主键的变化
                # conn.execute('''
                #     INSERT OR REPLACE INTO search_cache 
                #     VALUES (?, ?, ?, ?)
                # ''', (
                #     original_query,
                #     num_results,
                #     json.dumps(results),
                #     datetime.now().isoformat()
                # ))
                # 使用 ON CONFLICT 语句实现插入或更新：只更新指定字段，不覆盖所有字段
                conn.execute('''
                    INSERT INTO search_cache (
                        original_query, num_results, results_json, created_time
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(original_query, num_results) DO UPDATE SET
                        results_json = excluded.results_json,
                        created_time = excluded.created_time
                ''', (
                    original_query,
                    num_results,
                    json.dumps(results),
                    datetime.now().isoformat()
                ))
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Upsert error: {e}")
            return False

    def batch_upsert(self, data_list: List[Dict]) -> int:
        """批量插入/更新记录（事务操作）"""
        success_count = 0
        try:
            with self._get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                for data in data_list:
                    if self.upsert(**data):
                        success_count += 1
                conn.commit()
                return success_count
        except sqlite3.Error as e:
            print(f"Batch upsert failed: {e}")
            conn.rollback()
            return 0