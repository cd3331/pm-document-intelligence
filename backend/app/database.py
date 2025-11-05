"""
Supabase Database Integration for PM Document Intelligence.

This module provides database utilities, connection management, and query helpers
for interacting with Supabase PostgreSQL database.

Features:
- Supabase client initialization with connection pooling
- Async context managers for database sessions
- Connection health checks with retries
- Query helper functions with SQL injection prevention
- Error handling and logging
- Transaction management

Usage:
    from app.database import get_supabase_client, execute_query

    # Get Supabase client
    supabase = get_supabase_client()

    # Execute query
    result = await execute_query(
        "SELECT * FROM users WHERE email = %s",
        (email,)
    )
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple, Union

from supabase import Client, create_client
from postgrest.exceptions import APIError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.db.session import get_db
from app.utils.exceptions import DatabaseError, RecordNotFoundError
from app.utils.logger import get_logger


logger = get_logger(__name__)


# ============================================================================
# Supabase Client Management
# ============================================================================

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client.

    Returns:
        Supabase client instance

    Raises:
        DatabaseError: If client creation fails
    """
    global _supabase_client

    if _supabase_client is None:
        try:
            _supabase_client = create_client(
                supabase_url=str(settings.supabase.supabase_url),
                supabase_key=settings.supabase.supabase_key,
            )

            logger.info(f"Supabase client initialized: {settings.supabase.supabase_url}")

        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to initialize database client",
                details={"error": str(e)},
            )

    return _supabase_client


def get_supabase_admin_client() -> Client:
    """
    Get Supabase admin client with service role key.

    Use this for operations that bypass Row Level Security.

    Returns:
        Supabase admin client instance

    Raises:
        DatabaseError: If client creation fails
    """
    try:
        admin_client = create_client(
            supabase_url=str(settings.supabase.supabase_url),
            supabase_key=settings.supabase.supabase_service_key,
        )

        logger.debug("Supabase admin client created")
        return admin_client

    except Exception as e:
        logger.error(f"Failed to create Supabase admin client: {e}", exc_info=True)
        raise DatabaseError(
            message="Failed to initialize admin database client",
            details={"error": str(e)},
        )


# ============================================================================
# Connection Health Check
# ============================================================================


@retry(
    retry=retry_if_exception_type((DatabaseError, APIError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)
async def check_database_connection() -> bool:
    """
    Check database connectivity with retries.

    Returns:
        True if connection is healthy, False otherwise

    Raises:
        DatabaseError: If connection check fails after retries
    """
    try:
        # Use SQLAlchemy session to test connection
        async with get_db() as session:
            from sqlalchemy import text

            result = await session.execute(text("SELECT 1"))
            result.scalar_one()

        logger.debug("Database connection healthy")
        return True

    except Exception as e:
        logger.error(f"Database connection check failed: {e}", exc_info=True)
        raise DatabaseError(
            message="Database connection check failed",
            details={"error": str(e)},
        )


async def test_supabase_connection() -> bool:
    """
    Test Supabase connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        supabase = get_supabase_client()

        # Try to query a public table or use auth endpoint
        # This is a lightweight check
        response = supabase.table("users").select("id").limit(1).execute()

        logger.debug("Supabase connection test successful")
        return True

    except Exception as e:
        logger.warning(f"Supabase connection test failed: {e}")
        return False


# ============================================================================
# Query Helper Functions
# ============================================================================


async def execute_query(
    query: str,
    params: Optional[Tuple] = None,
    fetch_one: bool = False,
) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
    """
    Execute SQL query with parameterized values to prevent SQL injection.

    Args:
        query: SQL query with %s placeholders
        params: Query parameters
        fetch_one: If True, return single row

    Returns:
        Query results as list of dicts or single dict

    Raises:
        DatabaseError: If query execution fails

    Example:
        result = await execute_query(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )
    """
    try:
        async with get_db() as session:
            from sqlalchemy import text

            # Convert params to dict for SQLAlchemy
            if params:
                # Replace %s with :param_N for SQLAlchemy
                param_dict = {f"param_{i}": param for i, param in enumerate(params)}
                query_text = query
                for i in range(len(params)):
                    query_text = query_text.replace("%s", f":param_{i}", 1)
            else:
                query_text = query
                param_dict = {}

            result = await session.execute(text(query_text), param_dict)

            if fetch_one:
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
                return None
            else:
                rows = result.fetchall()
                return [dict(row._mapping) for row in rows]

    except Exception as e:
        logger.error(
            f"Query execution failed: {e}",
            extra={"query": query, "params": params},
            exc_info=True,
        )
        raise DatabaseError(
            message="Failed to execute query",
            details={"query": query, "error": str(e)},
        )


async def execute_insert(
    table: str,
    data: Dict[str, Any],
    returning: str = "*",
) -> Dict[str, Any]:
    """
    Insert data into table and return the inserted row.

    Args:
        table: Table name
        data: Data to insert
        returning: Columns to return (default: all)

    Returns:
        Inserted row data

    Raises:
        DatabaseError: If insert fails

    Example:
        user = await execute_insert(
            "users",
            {"email": "user@example.com", "name": "John Doe"}
        )
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table(table).insert(data).execute()

        if response.data:
            logger.debug(f"Insert into {table} successful")
            return response.data[0] if isinstance(response.data, list) else response.data

        raise DatabaseError(
            message="Insert returned no data",
            details={"table": table},
        )

    except APIError as e:
        logger.error(f"Insert failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to insert into {table}",
            details={"error": str(e), "data": data},
        )


async def execute_update(
    table: str,
    data: Dict[str, Any],
    match: Dict[str, Any],
    returning: str = "*",
) -> Dict[str, Any]:
    """
    Update data in table.

    Args:
        table: Table name
        data: Data to update
        match: Match conditions (WHERE clause)
        returning: Columns to return

    Returns:
        Updated row data

    Raises:
        DatabaseError: If update fails

    Example:
        user = await execute_update(
            "users",
            {"name": "Jane Doe"},
            {"id": user_id}
        )
    """
    try:
        supabase = get_supabase_client()

        # Build query with match conditions
        query = supabase.table(table).update(data)

        for key, value in match.items():
            query = query.eq(key, value)

        response = query.execute()

        if response.data:
            logger.debug(f"Update in {table} successful")
            return response.data[0] if isinstance(response.data, list) else response.data

        raise RecordNotFoundError(
            message=f"No record found in {table}",
            details={"match": match},
        )

    except APIError as e:
        logger.error(f"Update failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to update {table}",
            details={"error": str(e), "match": match},
        )


async def execute_delete(
    table: str,
    match: Dict[str, Any],
) -> bool:
    """
    Delete data from table.

    Args:
        table: Table name
        match: Match conditions (WHERE clause)

    Returns:
        True if successful

    Raises:
        DatabaseError: If delete fails

    Example:
        success = await execute_delete("users", {"id": user_id})
    """
    try:
        supabase = get_supabase_client()

        # Build query with match conditions
        query = supabase.table(table).delete()

        for key, value in match.items():
            query = query.eq(key, value)

        response = query.execute()

        logger.debug(f"Delete from {table} successful")
        return True

    except APIError as e:
        logger.error(f"Delete failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to delete from {table}",
            details={"error": str(e), "match": match},
        )


async def execute_select(
    table: str,
    columns: str = "*",
    match: Optional[Dict[str, Any]] = None,
    order: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Select data from table.

    Args:
        table: Table name
        columns: Columns to select
        match: Match conditions
        order: Order by clause
        limit: Limit results
        offset: Offset results

    Returns:
        List of matching rows

    Raises:
        DatabaseError: If select fails

    Example:
        users = await execute_select(
            "users",
            columns="id,email,name",
            match={"organization_id": org_id},
            order="created_at.desc",
            limit=10
        )
    """
    try:
        supabase = get_supabase_client()

        # Build query
        query = supabase.table(table).select(columns)

        # Add match conditions
        if match:
            for key, value in match.items():
                query = query.eq(key, value)

        # Add order
        if order:
            query = query.order(order)

        # Add limit
        if limit:
            query = query.limit(limit)

        # Add offset
        if offset:
            query = query.offset(offset)

        response = query.execute()

        logger.debug(f"Select from {table} successful")
        return response.data if response.data else []

    except APIError as e:
        logger.error(f"Select failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to select from {table}",
            details={"error": str(e)},
        )


async def execute_count(
    table: str,
    match: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Count rows in table.

    Args:
        table: Table name
        match: Match conditions

    Returns:
        Row count

    Raises:
        DatabaseError: If count fails
    """
    try:
        supabase = get_supabase_client()

        # Build query
        query = supabase.table(table).select("*", count="exact")

        # Add match conditions
        if match:
            for key, value in match.items():
                query = query.eq(key, value)

        response = query.execute()

        count = response.count if hasattr(response, "count") else 0
        logger.debug(f"Count from {table}: {count}")
        return count

    except APIError as e:
        logger.error(f"Count failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to count {table}",
            details={"error": str(e)},
        )


# ============================================================================
# Transaction Management
# ============================================================================


@asynccontextmanager
async def transaction():
    """
    Context manager for database transactions.

    Usage:
        async with transaction() as session:
            # Perform operations
            await session.execute(...)
            # Auto-commit on success, rollback on exception
    """
    async with get_db() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ============================================================================
# Batch Operations
# ============================================================================


async def batch_insert(
    table: str,
    data_list: List[Dict[str, Any]],
    chunk_size: int = 100,
) -> List[Dict[str, Any]]:
    """
    Insert multiple rows in batches.

    Args:
        table: Table name
        data_list: List of data dictionaries to insert
        chunk_size: Number of rows per batch

    Returns:
        List of inserted rows

    Raises:
        DatabaseError: If batch insert fails
    """
    try:
        supabase = get_supabase_client()
        all_results = []

        # Process in chunks
        for i in range(0, len(data_list), chunk_size):
            chunk = data_list[i : i + chunk_size]

            response = supabase.table(table).insert(chunk).execute()

            if response.data:
                all_results.extend(response.data)

            logger.debug(f"Batch insert into {table}: {len(chunk)} rows")

        logger.info(f"Batch insert into {table} completed: {len(all_results)} total rows")
        return all_results

    except APIError as e:
        logger.error(f"Batch insert failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to batch insert into {table}",
            details={"error": str(e), "count": len(data_list)},
        )


# ============================================================================
# Advanced Query Helpers
# ============================================================================


async def search_full_text(
    table: str,
    column: str,
    search_term: str,
    columns: str = "*",
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Perform full-text search.

    Args:
        table: Table name
        column: Column to search
        search_term: Search term
        columns: Columns to return
        limit: Result limit

    Returns:
        Matching rows

    Raises:
        DatabaseError: If search fails
    """
    try:
        supabase = get_supabase_client()

        response = (
            supabase.table(table)
            .select(columns)
            .text_search(column, search_term)
            .limit(limit)
            .execute()
        )

        logger.debug(f"Full-text search in {table}.{column}: {len(response.data)} results")
        return response.data if response.data else []

    except APIError as e:
        logger.error(f"Full-text search failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to search {table}",
            details={"error": str(e), "search_term": search_term},
        )


async def upsert_data(
    table: str,
    data: Union[Dict[str, Any], List[Dict[str, Any]]],
    on_conflict: str = "id",
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Upsert data (insert or update on conflict).

    Args:
        table: Table name
        data: Data to upsert
        on_conflict: Conflict column(s)

    Returns:
        Upserted row(s)

    Raises:
        DatabaseError: If upsert fails
    """
    try:
        supabase = get_supabase_client()

        response = supabase.table(table).upsert(data, on_conflict=on_conflict).execute()

        logger.debug(f"Upsert into {table} successful")
        return response.data

    except APIError as e:
        logger.error(f"Upsert failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to upsert into {table}",
            details={"error": str(e)},
        )


# ============================================================================
# Utility Functions
# ============================================================================


def sanitize_table_name(table_name: str) -> str:
    """
    Sanitize table name to prevent SQL injection.

    Args:
        table_name: Table name to sanitize

    Returns:
        Sanitized table name

    Raises:
        ValueError: If table name is invalid
    """
    # Only allow alphanumeric and underscores
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name}")

    return table_name


def build_filter_query(
    base_query: Any,
    filters: Dict[str, Any],
) -> Any:
    """
    Build query with multiple filters.

    Args:
        base_query: Base Supabase query
        filters: Filter conditions

    Returns:
        Query with filters applied
    """
    query = base_query

    for key, value in filters.items():
        if value is not None:
            if isinstance(value, list):
                query = query.in_(key, value)
            else:
                query = query.eq(key, value)

    return query
