# ===========================================
# Database Connection Pool
# ===========================================

import os
import asyncpg
import logging
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class Database:
    """Singleton database connection pool manager."""
    
    _instance: Optional["Database"] = None
    _pool: Optional[asyncpg.Pool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("Database not initialized. Call await db.connect() first.")
        return self._pool
    
    async def connect(self):
        """Initialize the connection pool."""
        if self._pool is not None:
            return
            
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            # Build from individual components
            host = os.getenv("DATABASE_HOST", "localhost")
            port = os.getenv("DATABASE_PORT", "5432")
            name = os.getenv("DATABASE_NAME", "brain_db")
            user = os.getenv("DATABASE_USER", "brain")
            password = os.getenv("DATABASE_PASSWORD", "brain_secret")
            database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        
        logger.info(f"Connecting to database...")
        
        self._pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        
        logger.info("Database connection pool established")
    
    async def disconnect(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Database connection pool closed")
    
    async def fetch_one(self, query: str, *args):
        """Fetch a single row."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch_all(self, query: str, *args):
        """Fetch all rows."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def execute(self, query: str, *args):
        """Execute a query."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def executemany(self, query: str, args_list):
        """Execute a query multiple times."""
        async with self.pool.acquire() as conn:
            return await conn.executemany(query, args_list)


# Global database instance
_db: Optional[Database] = None


def get_db() -> Database:
    """Get the global database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db


@asynccontextmanager
async def get_connection():
    """Context manager for getting a database connection."""
    db = get_db()
    async with db.pool.acquire() as conn:
        yield conn
