"""
Base Repository
Provides common database operations for all repositories.
"""

import os
import pyodbc
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()


class BaseRepository:
    """Base repository with common database operations."""
    
    def __init__(self):
        """Initialize repository with database configuration."""
        self.connection_string = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
            f"SERVER={os.getenv('SQLServer')};"
            f"DATABASE={os.getenv('SQLDatabase')};"
            f"UID={os.getenv('SQLUser')};"
            f"PWD={os.getenv('SQLPassword')}"
        )
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Ensures proper connection handling and cleanup.
        """
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(
        self,
        query: str,
        params: Tuple = None,
        fetch_one: bool = False,
        fetch_all: bool = False
    ) -> Any:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: Return single row
            fetch_all: Return all rows
            
        Returns:
            Query results or None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor
            finally:
                cursor.close()
    
    def execute_non_query(self, query: str, params: Tuple = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.rowcount
            finally:
                cursor.close()
    
    def execute_scalar(self, query: str, params: Tuple = None) -> Any:
        """
        Execute a query and return a single scalar value.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Single scalar value
        """
        row = self.execute_query(query, params, fetch_one=True)
        return row[0] if row else None
    
    def get_last_insert_id(self, conn) -> int:
        """
        Get the ID of the last inserted row.
        
        Args:
            conn: Active database connection
            
        Returns:
            Last inserted ID
        """
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT @@IDENTITY")
            result = cursor.fetchone()
            return int(result[0]) if result else None
        finally:
            cursor.close()
    
    def exists(self, query: str, params: Tuple = None) -> bool:
        """
        Check if a record exists.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            True if record exists, False otherwise
        """
        result = self.execute_query(query, params, fetch_one=True)
        return result is not None
    
    def count(self, query: str, params: Tuple = None) -> int:
        """
        Count records matching criteria.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of matching records
        """
        count_result = self.execute_scalar(query, params)
        return count_result or 0
    
    def paginate(
        self,
        query: str,
        params: List = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List, int]:
        """
        Execute paginated query.
        
        Args:
            query: SQL query string (without OFFSET/FETCH)
            params: Query parameters
            page: Page number (1-indexed)
            page_size: Items per page
            
        Returns:
            Tuple of (results, total_count)
        """
        if params is None:
            params = []
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Add pagination to query
        paginated_query = f"""
            {query}
            OFFSET ? ROWS
            FETCH NEXT ? ROWS ONLY
        """
        
        # Execute paginated query
        params_with_pagination = list(params) + [offset, page_size]
        results = self.execute_query(
            paginated_query,
            tuple(params_with_pagination),
            fetch_all=True
        )
        
        # Get total count (execute original query with COUNT)
        # Extract the main query part (before ORDER BY if present)
        count_query = query.split('ORDER BY')[0]
        count_query = f"SELECT COUNT(*) FROM ({count_query}) as total"
        total = self.execute_scalar(count_query, tuple(params) if params else None)
        
        return results, total or 0
    
    def bulk_insert(
        self,
        table: str,
        columns: List[str],
        values: List[Tuple]
    ) -> int:
        """
        Bulk insert multiple rows.
        
        Args:
            table: Table name
            columns: Column names
            values: List of value tuples
            
        Returns:
            Number of rows inserted
        """
        if not values:
            return 0
        
        placeholders = ', '.join(['?' for _ in columns])
        columns_str = ', '.join(columns)
        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, values)
                return cursor.rowcount
            finally:
                cursor.close()
    
    def bulk_update(
        self,
        table: str,
        set_clause: str,
        where_clause: str,
        values: List[Tuple]
    ) -> int:
        """
        Bulk update multiple rows.
        
        Args:
            table: Table name
            set_clause: SET clause with placeholders
            where_clause: WHERE clause with placeholders
            values: List of value tuples
            
        Returns:
            Number of rows updated
        """
        if not values:
            return 0
        
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, values)
                return cursor.rowcount
            finally:
                cursor.close()

