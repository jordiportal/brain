# ===========================================
# MCP Connections Repository
# ===========================================

import logging
from typing import Optional, List
from ..connection import get_db
from ..models import MCPConnection

logger = logging.getLogger(__name__)


class MCPConnectionRepository:
    """Repository for mcp_connections table."""
    
    @staticmethod
    async def get_all(active_only: bool = True) -> List[MCPConnection]:
        """Get all MCP connections."""
        db = get_db()
        
        query = "SELECT * FROM mcp_connections"
        if active_only:
            query += " WHERE is_active = true"
        query += " ORDER BY name"
        
        rows = await db.fetch_all(query)
        return [MCPConnectionRepository._row_to_connection(row) for row in rows]
    
    @staticmethod
    async def get_by_id(connection_id: int) -> Optional[MCPConnection]:
        """Get connection by ID."""
        db = get_db()
        
        query = "SELECT * FROM mcp_connections WHERE id = $1"
        row = await db.fetch_one(query, connection_id)
        
        if not row:
            return None
        
        return MCPConnectionRepository._row_to_connection(row)
    
    @staticmethod
    async def get_by_name(name: str) -> Optional[MCPConnection]:
        """Get connection by name."""
        db = get_db()
        
        query = "SELECT * FROM mcp_connections WHERE name = $1"
        row = await db.fetch_one(query, name)
        
        if not row:
            return None
        
        return MCPConnectionRepository._row_to_connection(row)
    
    @staticmethod
    async def get_by_slug(slug: str) -> Optional[MCPConnection]:
        """Get connection by slug."""
        db = get_db()
        
        query = "SELECT * FROM mcp_connections WHERE slug = $1"
        row = await db.fetch_one(query, slug)
        
        if not row:
            return None
        
        return MCPConnectionRepository._row_to_connection(row)
    
    @staticmethod
    def _row_to_connection(row) -> MCPConnection:
        """Convert database row to MCPConnection model."""
        config = row.get('config')
        args = row.get('args')
        env = row.get('env')
        tools = row.get('tools')
        
        return MCPConnection(
            id=row['id'],
            document_id=row.get('document_id'),
            name=row.get('name'),
            type=row.get('type'),
            command=row.get('command'),
            args=args if isinstance(args, list) else None,
            server_url=row.get('server_url'),
            env=env if isinstance(env, dict) else None,
            is_active=row.get('is_active', True),
            config=config if isinstance(config, dict) else None,
            description=row.get('description'),
            tools=tools if isinstance(tools, list) else None,
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            published_at=row.get('published_at'),
        )
