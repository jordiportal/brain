# ===========================================
# MCP Connections Repository
# ===========================================

import json
import logging
from typing import Any, Optional, List
from ..connection import get_db
from ..models import MCPConnection

logger = logging.getLogger(__name__)


def _parse_json(value: Any, expected_type: type = dict):
    """Parse a value that may be a JSON string or already the target Python type."""
    if isinstance(value, expected_type):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, expected_type):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    return None


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
        config = _parse_json(row.get('config'), dict)
        args = _parse_json(row.get('args'), list)
        env = _parse_json(row.get('env'), dict)
        tools = _parse_json(row.get('tools'), list)
        
        return MCPConnection(
            id=row['id'],
            document_id=row.get('document_id'),
            name=row.get('name'),
            type=row.get('type'),
            command=row.get('command'),
            args=args,
            server_url=row.get('server_url'),
            env=env,
            is_active=row.get('is_active', True),
            config=config,
            description=row.get('description'),
            tools=tools,
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            published_at=row.get('published_at'),
        )
