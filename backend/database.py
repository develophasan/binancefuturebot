import aiosqlite
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / 'data.sqlite'

async def init_db():
    """Initialize SQLite database and create tables if they don't exist"""
    # Ensure data directory exists if we put it in one, but it's just root for now.
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                user_id TEXT PRIMARY KEY,
                data TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                status TEXT,
                opened_at TEXT,
                closed_at TEXT,
                data TEXT
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS ai_decisions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                created_at TEXT,
                data TEXT
            )
        ''')
        await db.commit()
        logger.info("✅ SQLite Database initialized")

class AsyncSQLiteCollection:
    def __init__(self, db_path, table_name):
        self.db_path = db_path
        self.table_name = table_name

    async def _execute(self, query, params=()):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor

    async def _fetch_one(self, query, params=()):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                if row:
                    data = json.loads(row['data'])
                    return data
                return None

    async def _fetch_all(self, query, params=()):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                results = []
                for row in rows:
                    results.append(json.loads(row['data']))
                return results

    # Mock MongoDB methods
    async def find_one(self, filter_query, projection=None):
        where_clauses = []
        params = []
        for key, value in filter_query.items():
            if key in ('user_id', 'id', 'status'):
                where_clauses.append(f"{key} = ?")
                params.append(value)
            else:
                # Basic JSON extraction for other fields
                where_clauses.append(f"json_extract(data, '$.\"' || ? || '\"') = ?")
                params.extend([key, value])
        
        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT data FROM {self.table_name} WHERE {where_str} LIMIT 1"
        return await self._fetch_one(query, tuple(params))

    def find(self, filter_query=None, projection=None):
        return MockCursor(self, filter_query)

    async def insert_one(self, document):
        if self.table_name == 'settings':
            user_id = document.get('user_id', 'default_user')
            query = f"INSERT INTO {self.table_name} (user_id, data) VALUES (?, ?)"
            await self._execute(query, (user_id, json.dumps(document)))
        elif self.table_name == 'positions':
            doc_id = document.get('id')
            user_id = document.get('user_id', 'default_user')
            status = document.get('status', 'OPEN')
            opened_at = document.get('opened_at')
            closed_at = document.get('closed_at')
            query = f"INSERT INTO {self.table_name} (id, user_id, status, opened_at, closed_at, data) VALUES (?, ?, ?, ?, ?, ?)"
            await self._execute(query, (doc_id, user_id, status, opened_at, closed_at, json.dumps(document)))
        elif self.table_name == 'ai_decisions':
            doc_id = document.get('id')
            if not doc_id:
                 import uuid
                 doc_id = str(uuid.uuid4())
                 document['id'] = doc_id
            user_id = document.get('user_id', 'default_user')
            created_at = document.get('created_at')
            query = f"INSERT INTO {self.table_name} (id, user_id, created_at, data) VALUES (?, ?, ?, ?)"
            await self._execute(query, (doc_id, user_id, created_at, json.dumps(document)))

    async def update_one(self, filter_query, update_operation, upsert=False):
        # Extremely simplified update support
        existing = await self.find_one(filter_query)
        if existing:
            set_ops = update_operation.get('$set', {})
            for k, v in set_ops.items():
                existing[k] = v
            
            if self.table_name == 'settings':
                query = "UPDATE settings SET data = ? WHERE user_id = ?"
                await self._execute(query, (json.dumps(existing), existing.get('user_id', 'default_user')))
            elif self.table_name == 'positions':
                query = "UPDATE positions SET status = ?, closed_at = ?, data = ? WHERE id = ?"
                await self._execute(query, (
                    existing.get('status'),
                    existing.get('closed_at'),
                    json.dumps(existing),
                    existing.get('id')
                ))
        elif upsert:
            document = filter_query.copy()
            if '$set' in update_operation:
                document.update(update_operation['$set'])
            await self.insert_one(document)

    async def count_documents(self, filter_query):
        where_clauses = []
        params = []
        for key, value in filter_query.items():
            if key in ('user_id', 'id', 'status'):
                where_clauses.append(f"{key} = ?")
                params.append(value)
            elif isinstance(value, dict) and '$gte' in value:
                # Handle opened_at >= date
                if key in ('opened_at', 'closed_at'):
                    where_clauses.append(f"{key} >= ?")
                    params.append(value['$gte'])
        
        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE {where_str}"
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, tuple(params)) as cursor:
                row = await cursor.fetchone()
                return row['count'] if row else 0


class MockCursor:
    def __init__(self, collection, filter_query):
        self.collection = collection
        self.filter_query = filter_query or {}
        self._sort = None
        self._limit = None

    def sort(self, key, direction):
        self._sort = (key, direction)
        return self

    def limit(self, limit_val):
        self._limit = limit_val
        return self

    async def to_list(self, length):
        where_clauses = []
        params = []
        for key, value in self.filter_query.items():
            if key in ('user_id', 'id', 'status'):
                where_clauses.append(f"{key} = ?")
                params.append(value)
            elif isinstance(value, dict) and '$gte' in value:
                if key in ('opened_at', 'closed_at', 'created_at'):
                    where_clauses.append(f"{key} >= ?")
                    params.append(value['$gte'])
        
        where_str = " AND ".join(where_clauses) if where_clauses else "1=1"
        query = f"SELECT data FROM {self.collection.table_name} WHERE {where_str}"
        
        if self._sort:
            # We assume sorting by created_at desc mostly
             query += f" ORDER BY {self._sort[0]} {'DESC' if self._sort[1] == -1 else 'ASC'}"
        
        if self._limit or length:
             lim = self._limit or length
             query += f" LIMIT {lim}"

        return await self.collection._fetch_all(query, tuple(params))

class AsyncSQLiteDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self._collections = {}

    def __getattr__(self, name):
        if name not in self._collections:
            self._collections[name] = AsyncSQLiteCollection(self.db_path, name)
        return self._collections[name]

# Global DB instance 
sqlite_db = AsyncSQLiteDatabase(DB_PATH)
