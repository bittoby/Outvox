"""
Template Repository
Handles all database operations for SMS templates.
"""

from typing import Optional, List, Dict, Any
from .base import BaseRepository


class TemplateRepository(BaseRepository):
    """Repository for template data access."""
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all SMS templates."""
        query = """
            SELECT 
                template_id,
                template_content,
                usage_count,
                created_at
            FROM sms_templates
            WHERE is_active = 1
            ORDER BY template_id
        """
        rows = self.execute_query(query, fetch_all=True)
        
        templates = []
        for row in rows:
            templates.append({
                'template_id': row[0],
                'template_text': row[1],  # Keep 'template_text' key for compatibility
                'usage_count': row[2] or 0,
                'created_at': row[3].isoformat() if row[3] else None
            })
        
        return templates
    
    def get_by_id(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Get template by ID."""
        query = """
            SELECT 
                template_id,
                template_content,
                usage_count,
                created_at
            FROM sms_templates
            WHERE template_id = ?
        """
        row = self.execute_query(query, (template_id,), fetch_one=True)
        
        if not row:
            return None
        
        return {
            'template_id': row[0],
            'template_text': row[1],  # Keep 'template_text' key for compatibility
            'usage_count': row[2] or 0,
            'created_at': row[3].isoformat() if row[3] else None
        }
    
    def create(self, template_text: str) -> int:
        """Create a new template."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO sms_templates (template_name, template_content, usage_count, is_active)
                    VALUES (?, ?, 0, 1)
                """, ('Default Template', template_text))
                conn.commit()
                return self.get_last_insert_id(conn)
            finally:
                cursor.close()
    
    def update(self, template_id: int, template_text: str) -> bool:
        """Update an existing template."""
        query = """
            UPDATE sms_templates 
            SET template_content = ?, updated_at = GETDATE()
            WHERE template_id = ?
        """
        rows_affected = self.execute_non_query(query, (template_text, template_id))
        return rows_affected > 0
    
    def increment_usage(self, template_id: int) -> bool:
        """Increment usage count for a template."""
        query = """
            UPDATE sms_templates
            SET usage_count = usage_count + 1
            WHERE template_id = ?
        """
        rows_affected = self.execute_non_query(query, (template_id,))
        return rows_affected > 0
    
    def get_usage_count(self, template_id: int) -> Optional[int]:
        """Get usage count for a template."""
        query = "SELECT usage_count FROM sms_templates WHERE template_id = ?"
        result = self.execute_scalar(query, (template_id,))
        return result
    
    def count_templates(self) -> int:
        """Count total active SMS templates."""
        query = "SELECT COUNT(*) FROM sms_templates WHERE is_active = 1"
        try:
            result = self.execute_scalar(query)
            return int(result) if result is not None else 0
        except Exception as e:
            print(f"Error counting templates: {e}")
            return 0

