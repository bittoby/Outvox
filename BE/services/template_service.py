"""
Template Service
Business logic for SMS template management.
"""

from typing import Dict, Any
from repositories.template_repository import TemplateRepository
from core.exceptions import ResourceNotFoundError, ValidationError


class TemplateService:
    """Service for template business logic."""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'TemplateService':
        """Get singleton instance of TemplateService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize service with repository."""
        self.repository = TemplateRepository()
    
    def get_all_templates(self) -> Dict[str, Any]:
        """
        Get all SMS templates.
        
        Returns:
            Dict with templates list and count
        """
        templates = self.repository.get_all()
        
        return {
            "success": True,
            "templates": templates,
            "total_count": len(templates)
        }
    
    def get_template(self, template_id: int) -> Dict[str, Any]:
        """
        Get template by ID.
        
        Args:
            template_id: Template ID
            
        Returns:
            Dict with template details
            
        Raises:
            ResourceNotFoundError: If template not found
        """
        template = self.repository.get_by_id(template_id)
        
        if not template:
            raise ResourceNotFoundError("Template", template_id)
        
        return {
            "success": True,
            "template": template
        }
    
    def create_template(self, template_text: str) -> Dict[str, Any]:
        """
        Create a new SMS template.
        
        Args:
            template_text: Template text with placeholders
            
        Returns:
            Dict with created template
            
        Raises:
            ValidationError: If template is invalid
        """
        # Validate template text
        if not template_text or not template_text.strip():
            raise ValidationError("Template text is required")
        
        if len(template_text.strip()) < 10:
            raise ValidationError("Template text too short (min 10 characters)")
        
        if len(template_text.strip()) > 500:
            raise ValidationError("Template text too long (max 500 characters)")
        
        # Check for STOP instruction (TCPA compliance)
        if 'STOP' not in template_text.upper():
            raise ValidationError("Template must include 'STOP' opt-out instruction for TCPA compliance")
        
        template_id = self.repository.create(template_text.strip())
        
        return {
            "success": True,
            "template_id": template_id,
            "template_text": template_text.strip(),
            "usage_count": 0,
            "message": "Template created successfully"
        }
    
    def update_template(self, template_id: int, template_text: str) -> Dict[str, Any]:
        """
        Update an existing template.
        
        Args:
            template_id: Template ID
            template_text: Updated template text
            
        Returns:
            Dict with updated template
            
        Raises:
            ResourceNotFoundError: If template not found
            ValidationError: If template is invalid
        """
        # Verify template exists
        if not self.repository.get_by_id(template_id):
            raise ResourceNotFoundError("Template", template_id)
        
        # Validate template text
        if not template_text or not template_text.strip():
            raise ValidationError("Template text is required")
        
        if len(template_text.strip()) < 10:
            raise ValidationError("Template text too short (min 10 characters)")
        
        if 'STOP' not in template_text.upper():
            raise ValidationError("Template must include 'STOP' opt-out instruction")
        
        success = self.repository.update(template_id, template_text.strip())
        
        if not success:
            raise ResourceNotFoundError("Template", template_id)
        
        # Get updated template
        updated_template = self.repository.get_by_id(template_id)
        
        return {
            "success": True,
            "template": updated_template,
            "message": "Template updated successfully"
        }
    
    def increment_usage(self, template_id: int) -> Dict[str, Any]:
        """
        Increment usage counter for a template.
        
        Args:
            template_id: Template ID
            
        Returns:
            Dict with updated usage count
            
        Raises:
            ResourceNotFoundError: If template not found
        """
        if not self.repository.get_by_id(template_id):
            raise ResourceNotFoundError("Template", template_id)
        
        success = self.repository.increment_usage(template_id)
        
        if not success:
            raise ResourceNotFoundError("Template", template_id)
        
        usage_count = self.repository.get_usage_count(template_id)
        
        return {
            "success": True,
            "template_id": template_id,
            "usage_count": usage_count or 0,
            "message": "Usage count incremented"
        }
    
    def count_templates(self) -> int:
        """
        Count total SMS templates.
        
        Returns:
            Total number of templates
        """
        return self.repository.count_templates()


def get_template_service() -> TemplateService:
    """Get singleton instance of TemplateService."""
    return TemplateService.get_instance()

