"""
API Routers Package
Organized API routes by feature domain for better maintainability.
"""

from .leads import router as leads_router
from .stores import router as stores_router
from .calls import router as calls_router
from .campaigns import router as campaigns_router
from .sms import router as sms_router
from .phone_numbers import router as phone_numbers_router
from .popup import router as popup_router
from .templates import router as templates_router
from .analytics import router as analytics_router

__all__ = [
    "leads_router",
    "stores_router",
    "calls_router",
    "campaigns_router",
    "sms_router",
    "phone_numbers_router",
    "popup_router",
    "templates_router",
    "analytics_router",
]

# Router summary for documentation
ROUTER_INFO = {
    "leads_router": {
        "prefix": "/api/leads",
        "tags": ["leads"],
        "endpoints": 13,
        "description": "Lead management (CRUD, import, DNC)"
    },
    "stores_router": {
        "prefix": "/api/stores",
        "tags": ["stores"],
        "endpoints": 5,
        "description": "Store management and statistics"
    },
    "calls_router": {
        "prefix": "/api/calls",
        "tags": ["calls"],
        "endpoints": 5,
        "description": "Call history, results, and recordings"
    },
    "campaigns_router": {
        "prefix": "/api/campaigns",
        "tags": ["campaigns"],
        "endpoints": 6,
        "description": "SMS campaign management"
    },
    "sms_router": {
        "prefix": "/api/sms",
        "tags": ["sms"],
        "endpoints": 6,
        "description": "SMS conversations and photo submissions"
    },
    "phone_numbers_router": {
        "prefix": "/api/phone-numbers",
        "tags": ["phone_numbers"],
        "endpoints": 11,
        "description": "Phone number management and statistics"
    },
    "popup_router": {
        "prefix": "/api/popup",
        "tags": ["popup"],
        "endpoints": 3,
        "description": "Popup queue management"
    },
    "settings_router": {
        "prefix": "/api/settings",
        "tags": ["settings"],
        "endpoints": 5,
        "description": "AI provider and system settings"
    },
    "templates_router": {
        "prefix": "/api/templates",
        "tags": ["templates"],
        "endpoints": 4,
        "description": "SMS template management"
    },
    "analytics_router": {
        "prefix": "/api/analytics",
        "tags": ["analytics"],
        "endpoints": 5,
        "description": "Analytics and statistics"
    },
    "phone_validation_router": {
        "prefix": "/api/phone-validation",
        "tags": ["phone-validation"],
        "endpoints": 2,
        "description": "Phone number validation (Trestle)"
    }
}


def get_all_routers():
    """Get list of all routers for FastAPI app inclusion."""
    return [
        leads_router,
        stores_router,
        calls_router,
        campaigns_router,
        sms_router,
        phone_numbers_router,
        popup_router,
        templates_router,
        analytics_router,
    ]


def print_router_summary():
    """Print summary of all routers."""
    print("\n" + "="*70)
    print("API ROUTERS SUMMARY")
    print("="*70)
    
    total_endpoints = 0
    for router_name, info in ROUTER_INFO.items():
        print(f"\n{router_name}:")
        print(f"  Prefix: {info['prefix'] or '(none)'}")
        print(f"  Tags: {info['tags']}")
        print(f"  Endpoints: {info['endpoints']}")
        print(f"  Description: {info['description']}")
        total_endpoints += info['endpoints']
    
    print(f"\n{'='*70}")
    print(f"TOTAL: {len(ROUTER_INFO)} routers, {total_endpoints} endpoints")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Print summary when run directly
    print_router_summary()
