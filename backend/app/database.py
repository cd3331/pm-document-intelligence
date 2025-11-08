"""
PostgreSQL Database Integration for PM Document Intelligence.

This module provides database utilities, connection management, and query helpers
for interacting with AWS RDS PostgreSQL database using SQLAlchemy.

Features:
- SQLAlchemy async engine with connection pooling
- Async context managers for database sessions
- Connection health checks with retries
- Query helper functions with SQL injection prevention
- Error handling and logging
- Transaction management

Usage:
    from app.database import execute_select, execute_insert

    # Select data
    users = await execute_select("users", match={"email": email})

    # Insert data
    user = await execute_insert("users", {"email": "user@example.com", "name": "John"})
"""

from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import (
    MetaData,
    Table,
    and_,
    delete,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.db.session import get_db, get_engine
from app.utils.exceptions import DatabaseError, RecordNotFoundError
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================================
# Global Metadata Cache
# ============================================================================

_metadata_cache: MetaData | None = None


async def get_metadata() -> MetaData:
    """
    Get or create metadata with table reflection.

    Returns:
        MetaData with reflected tables
    """
    global _metadata_cache

    if _metadata_cache is None:
        _metadata_cache = MetaData()
        engine = get_engine()

        # Reflect tables using async engine
        async with engine.begin() as conn:
            await conn.run_sync(_metadata_cache.reflect)

        logger.debug(f"Database metadata reflected: {len(_metadata_cache.tables)} tables")

    return _metadata_cache


def get_table(metadata: MetaData, table_name: str) -> Table:
    """
    Get table from metadata.

    Args:
        metadata: SQLAlchemy metadata
        table_name: Name of the table

    Returns:
        Table object

    Raises:
        DatabaseError: If table doesn't exist
    """
    if table_name not in metadata.tables:
        raise DatabaseError(
            message=f"Table '{table_name}' does not exist",
            details={"table": table_name},
        )

    return metadata.tables[table_name]


# ============================================================================
# Connection Health Check
# ============================================================================


@retry(
    retry=retry_if_exception_type(DatabaseError),
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
        async with get_db() as session:
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


# ============================================================================
# Query Helper Functions
# ============================================================================


async def execute_query(
    query: str,
    params: tuple | None = None,
    fetch_one: bool = False,
) -> list[dict[str, Any]] | dict[str, Any] | None:
    """
    Execute raw SQL query with parameterized values to prevent SQL injection.

    Args:
        query: SQL query with :param placeholders
        params: Query parameters as tuple
        fetch_one: If True, return single row

    Returns:
        Query results as list of dicts or single dict

    Raises:
        DatabaseError: If query execution fails

    Example:
        result = await execute_query(
            "SELECT * FROM users WHERE email = :param_0",
            ("user@example.com",)
        )
    """
    try:
        async with get_db() as session:
            # Convert positional params to named params
            if params:
                param_dict = {f"param_{i}": param for i, param in enumerate(params)}
                # Replace %s with :param_N for SQLAlchemy
                query_text = query
                for i in range(len(params)):
                    query_text = query_text.replace("%s", f":param_{i}", 1)
            else:
                query_text = query
                param_dict = {}

            result = await session.execute(text(query_text), param_dict)

            if fetch_one:
                row = result.fetchone()
                return dict(row._mapping) if row else None
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
    data: dict[str, Any],
    returning: str = "*",
) -> dict[str, Any]:
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
            {"email": "user@example.com", "full_name": "John Doe"}
        )
    """
    try:
        async with get_db() as session:
            metadata = await get_metadata()
            table_obj = get_table(metadata, table)

            stmt = insert(table_obj).values(**data).returning(table_obj)
            result = await session.execute(stmt)
            await session.commit()

            row = result.fetchone()
            if row:
                inserted_data = dict(row._mapping)
                logger.debug(f"Insert into {table} successful: {inserted_data.get('id', 'N/A')}")
                return inserted_data

            raise DatabaseError(
                message="Insert returned no data",
                details={"table": table},
            )

    except IntegrityError as e:
        logger.error(f"Insert integrity error: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to insert into {table}: integrity constraint violated",
            details={"error": str(e), "data": data},
        )
    except Exception as e:
        logger.error(f"Insert failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to insert into {table}",
            details={"error": str(e), "data": data},
        )


async def execute_update(
    table: str,
    data: dict[str, Any],
    match: dict[str, Any],
    returning: str = "*",
) -> dict[str, Any]:
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
        RecordNotFoundError: If no matching record found

    Example:
        user = await execute_update(
            "users",
            {"full_name": "Jane Doe"},
            {"id": user_id}
        )
    """
    try:
        async with get_db() as session:
            metadata = await get_metadata()
            table_obj = get_table(metadata, table)

            # Build WHERE conditions
            conditions = [table_obj.c[key] == value for key, value in match.items()]

            stmt = update(table_obj).where(and_(*conditions)).values(**data).returning(table_obj)

            result = await session.execute(stmt)
            await session.commit()

            row = result.fetchone()
            if row:
                updated_data = dict(row._mapping)
                logger.debug(f"Update in {table} successful")
                return updated_data

            raise RecordNotFoundError(
                message=f"No record found in {table}",
                details={"match": match},
            )

    except RecordNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Update failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to update {table}",
            details={"error": str(e), "match": match},
        )


async def execute_delete(
    table: str,
    match: dict[str, Any],
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
        async with get_db() as session:
            metadata = await get_metadata()
            table_obj = get_table(metadata, table)

            # Build WHERE conditions
            conditions = [table_obj.c[key] == value for key, value in match.items()]

            stmt = delete(table_obj).where(and_(*conditions))
            await session.execute(stmt)
            await session.commit()

            logger.debug(f"Delete from {table} successful")
            return True

    except Exception as e:
        logger.error(f"Delete failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to delete from {table}",
            details={"error": str(e), "match": match},
        )


async def execute_select(
    table: str,
    columns: str = "*",
    match: dict[str, Any] | None = None,
    order: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict[str, Any]]:
    """
    Select data from table.

    Args:
        table: Table name
        columns: Columns to select (comma-separated or "*")
        match: Match conditions
        order: Order by clause (e.g., "created_at.desc" or "name")
        limit: Limit results
        offset: Offset results

    Returns:
        List of matching rows

    Raises:
        DatabaseError: If select fails

    Example:
        users = await execute_select(
            "users",
            columns="id,email,full_name",
            match={"is_active": True},
            order="created_at.desc",
            limit=10
        )
    """
    try:
        async with get_db() as session:
            metadata = await get_metadata()
            table_obj = get_table(metadata, table)

            # Build SELECT columns
            if columns == "*":
                stmt = select(table_obj)
            else:
                col_list = [table_obj.c[col.strip()] for col in columns.split(",")]
                stmt = select(*col_list)

            # Add WHERE conditions
            if match:
                conditions = [table_obj.c[key] == value for key, value in match.items()]
                stmt = stmt.where(and_(*conditions))

            # Add ORDER BY
            if order:
                # Handle Supabase-style ordering (e.g., "created_at.desc")
                if "." in order:
                    col_name, direction = order.split(".")
                    order_col = table_obj.c[col_name]
                    stmt = stmt.order_by(
                        order_col.desc() if direction == "desc" else order_col.asc()
                    )
                else:
                    stmt = stmt.order_by(table_obj.c[order])

            # Add LIMIT
            if limit:
                stmt = stmt.limit(limit)

            # Add OFFSET
            if offset:
                stmt = stmt.offset(offset)

            result = await session.execute(stmt)
            rows = result.fetchall()

            data = [dict(row._mapping) for row in rows]
            logger.debug(f"Select from {table} returned {len(data)} rows")
            return data

    except Exception as e:
        logger.error(f"Select failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to select from {table}",
            details={"error": str(e)},
        )


async def execute_count(
    table: str,
    match: dict[str, Any] | None = None,
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
        async with get_db() as session:
            metadata = await get_metadata()
            table_obj = get_table(metadata, table)

            stmt = select(func.count()).select_from(table_obj)

            # Add WHERE conditions
            if match:
                conditions = [table_obj.c[key] == value for key, value in match.items()]
                stmt = stmt.where(and_(*conditions))

            result = await session.execute(stmt)
            count = result.scalar_one()

            logger.debug(f"Count from {table}: {count}")
            return count

    except Exception as e:
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
    data_list: list[dict[str, Any]],
    chunk_size: int = 100,
) -> list[dict[str, Any]]:
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
        async with get_db() as session:
            metadata = await get_metadata()
            table_obj = get_table(metadata, table)

            all_results = []

            # Process in chunks
            for i in range(0, len(data_list), chunk_size):
                chunk = data_list[i : i + chunk_size]

                stmt = insert(table_obj).values(chunk).returning(table_obj)
                result = await session.execute(stmt)

                rows = result.fetchall()
                all_results.extend([dict(row._mapping) for row in rows])

                logger.debug(f"Batch insert into {table}: {len(chunk)} rows")

            await session.commit()

            logger.info(f"Batch insert into {table} completed: {len(all_results)} total rows")
            return all_results

    except Exception as e:
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
) -> list[dict[str, Any]]:
    """
    Perform full-text search using PostgreSQL ILIKE.

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
        async with get_db() as session:
            metadata = await get_metadata()
            table_obj = get_table(metadata, table)

            # Build SELECT columns
            if columns == "*":
                stmt = select(table_obj)
            else:
                col_list = [table_obj.c[col.strip()] for col in columns.split(",")]
                stmt = select(*col_list)

            # Add ILIKE search condition
            search_pattern = f"%{search_term}%"
            stmt = stmt.where(table_obj.c[column].ilike(search_pattern))
            stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            rows = result.fetchall()

            data = [dict(row._mapping) for row in rows]
            logger.debug(f"Full-text search in {table}.{column}: {len(data)} results")
            return data

    except Exception as e:
        logger.error(f"Full-text search failed: {e}", exc_info=True)
        raise DatabaseError(
            message=f"Failed to search {table}",
            details={"error": str(e), "search_term": search_term},
        )


async def upsert_data(
    table: str,
    data: dict[str, Any] | list[dict[str, Any]],
    on_conflict: str = "id",
) -> dict[str, Any] | list[dict[str, Any]]:
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
        async with get_db() as session:
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            metadata = await get_metadata(session)
            table_obj = get_table(metadata, table)

            is_list = isinstance(data, list)
            data_list = data if is_list else [data]

            stmt = pg_insert(table_obj).values(data_list)

            # Get all columns except the conflict column for update
            update_cols = {
                col.name: stmt.excluded[col.name]
                for col in table_obj.columns
                if col.name != on_conflict
            }

            stmt = stmt.on_conflict_do_update(
                index_elements=[on_conflict],
                set_=update_cols,
            ).returning(table_obj)

            result = await session.execute(stmt)
            await session.commit()

            rows = result.fetchall()
            results = [dict(row._mapping) for row in rows]

            logger.debug(f"Upsert into {table} successful: {len(results)} rows")
            return results if is_list else results[0]

    except Exception as e:
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


def build_filter_conditions(
    table_obj: Table,
    filters: dict[str, Any],
) -> list:
    """
    Build WHERE conditions from filters.

    Args:
        table_obj: SQLAlchemy Table object
        filters: Filter conditions

    Returns:
        List of SQLAlchemy conditions
    """
    conditions = []

    for key, value in filters.items():
        if value is not None:
            if isinstance(value, list):
                conditions.append(table_obj.c[key].in_(value))
            else:
                conditions.append(table_obj.c[key] == value)

    return conditions
