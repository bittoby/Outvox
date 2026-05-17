"""
Template Router
API endpoints for SMS template management.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from services.template_service import TemplateService, get_template_service
from core.exceptions import ResourceNotFoundError, ValidationError

router = APIRouter(prefix="/api/templates", tags=["templates"])


def get_service() -> TemplateService:
    """Dependency to get TemplateService instance."""
    return get_template_service()


@router.get("", summary="Get all templates")
async def get_all_templates(
    service: TemplateService = Depends(get_service)
) -> Dict[str, Any]:
    """Get all SMS templates."""
    return service.get_all_templates()


@router.get("/{template_id}", summary="Get template by ID")
async def get_template(
    template_id: int,
    service: TemplateService = Depends(get_service)
) -> Dict[str, Any]:
    """Get a specific template by ID."""
    try:
        return service.get_template(template_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", summary="Create new template")
async def create_template(
    request: Dict[str, Any],
    service: TemplateService = Depends(get_service)
) -> Dict[str, Any]:
    """Create a new SMS template."""
    template_text = request.get("template_text")
    if not template_text:
        raise HTTPException(status_code=400, detail="template_text is required")
    
    try:
        return service.create_template(template_text)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{template_id}", summary="Update template")
async def update_template(
    template_id: int,
    request: Dict[str, Any],
    service: TemplateService = Depends(get_service)
) -> Dict[str, Any]:
    """Update an existing template."""
    template_text = request.get("template_text")
    if not template_text:
        raise HTTPException(status_code=400, detail="template_text is required")
    
    try:
        return service.update_template(template_id, template_text)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/increment-usage", summary="Increment template usage")
async def increment_template_usage(
    template_id: int,
    service: TemplateService = Depends(get_service)
) -> Dict[str, Any]:
    """Increment usage counter for a template."""
    try:
        return service.increment_usage(template_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

