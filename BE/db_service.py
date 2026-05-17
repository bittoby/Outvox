#!/usr/bin/env python3
"""
Centralized Database Service for Outbound Calling System
This service handles ALL database operations for the entire system.
Voice agents communicate with this service via HTTP API.
"""

import os
import pyodbc
import asyncpg
import uvicorn
import aiohttp
import asyncio
import logging
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import routers
try:
    from routers import stores, campaigns, sms, phone_numbers, popup, leads, calls, templates, analytics, phone_validation, settings
    ROUTERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import routers: {e}")
    ROUTERS_AVAILABLE = False

# Import database schema initialization
from core.schema import create_outbound_tables_async

# Import models from models package (only what's needed for agent orchestration)
from models import CampaignRequest

# Database configuration (used for health check only)
DATABASE_BACKEND = os.getenv('DATABASE_BACKEND', 'sqlserver').lower()
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://outvox:outvox@localhost:5432/outvox')
SQL_SERVER = os.getenv('SQLServer')
SQL_USER = os.getenv('SQLUser')
SQL_PASSWORD = os.getenv('SQLPassword')
SQL_DATABASE = os.getenv('SQLDatabase')


def get_sqlserver_connection():
    """Get SQL Server connection (used for health check only)."""
    try:
        if not SQL_SERVER or not SQL_DATABASE:
            raise ValueError("SQLServer and SQLDatabase are required for DATABASE_BACKEND=sqlserver")
        # Use Windows Authentication for LocalDB
        if "localdb" in SQL_SERVER.lower():
            connection_string = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
                f"SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};"
                f"Trusted_Connection=yes;"
            )
        else:
            # Use SQL Server authentication for remote servers
            connection_string = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};TrustServerCertificate=yes;"
                f"SERVER={SQL_SERVER};"
                f"DATABASE={SQL_DATABASE};"
                f"UID={SQL_USER};"
                f"PWD={SQL_PASSWORD}"
            )
        return pyodbc.connect(connection_string)
    except Exception as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")


async def check_database_health():
    """Check the configured database backend without blocking the event loop."""
    if DATABASE_BACKEND in ("postgres", "postgresql"):
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.fetchval("SELECT 1")
        finally:
            await conn.close()
        return "postgres"

    if DATABASE_BACKEND in ("sqlserver", "mssql"):
        def _check_sqlserver():
            conn = get_sqlserver_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            finally:
                cursor.close()
                conn.close()

        await asyncio.to_thread(_check_sqlserver)
        return "sqlserver"

    raise HTTPException(
        status_code=500,
        detail=f"Unsupported DATABASE_BACKEND={DATABASE_BACKEND!r}",
    )

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting database service...")
    await create_outbound_tables_async()
    
    # Register the FastAPI app's event loop with WebSocket service for sync broadcasts
    try:
        import asyncio
        from services.websocket_service import set_app_event_loop
        loop = asyncio.get_running_loop()
        set_app_event_loop(loop)
        logger.info("✅ WebSocket service: App event loop registered")
    except Exception as e:
        logger.warning(f"⚠️  Failed to register event loop with WebSocket service: {e}")
    
    # Start all background workers
    try:
        from services.worker_manager import get_worker_manager
        worker_manager = get_worker_manager()
        await worker_manager.start_all_workers()
        logger.info("✅ All workers started successfully")
    except Exception as e:
        logger.error(f"❌ Failed to start workers: {e}")
        import traceback
        traceback.print_exc()
        # Continue even if workers fail
    
    yield
    
    # Shutdown
    try:
        from services.worker_manager import get_worker_manager
        worker_manager = get_worker_manager()
        await worker_manager.stop_all_workers()
        logger.info("✅ All workers stopped")
    except Exception as e:
        logger.error(f"❌ Error stopping workers: {e}")
    
    logger.info("🛑 Shutting down database service...")

# FastAPI Application
app = FastAPI(
    title="Outvox — Database Service",
    version="0.1.0",
    lifespan=lifespan
)

# Setup global exception handlers
from core.error_handler import setup_exception_handlers
setup_exception_handlers(app)

# API-key authentication. Reads API_KEY and AUTH_EXEMPT_PREFIXES from the
# environment via config.security. See SECURITY.md.
from core.auth import install_api_key_auth
install_api_key_auth(app, service_name="db_service")

# CORS Configuration. Defaults to "*" for local development; restrict to your
# frontend's exact origin(s) in production via the CORS_ALLOWED_ORIGINS env
# var (comma-separated list).
_cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "*").strip()
_cors_origins = (
    ["*"] if _cors_origins_env in ("", "*")
    else [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers if available
if ROUTERS_AVAILABLE:
    app.include_router(leads.router)
    app.include_router(stores.router)
    app.include_router(campaigns.router)
    app.include_router(sms.router)
    app.include_router(phone_numbers.router)
    app.include_router(popup.router)
    app.include_router(calls.router)
    app.include_router(templates.router)
    app.include_router(analytics.router)
    app.include_router(phone_validation.router)
    app.include_router(settings.router)
    # Include WebSocket router
    try:
        from routers import websocket
        app.include_router(websocket.router)
        logger.info("✅ WebSocket router loaded successfully")
    except ImportError as e:
        logger.warning(f"⚠️ WebSocket router not available: {e}")
    logger.info("✅ All routers loaded successfully")
else:
    logger.warning("⚠️ Routers not available - some endpoints may not work")


# Legacy Twilio webhook redirect (for backwards compatibility)
# Twilio may still be configured to call /sms/twilio-sms instead of /api/sms/twilio-sms
@app.api_route("/sms/twilio-sms", methods=["GET", "POST"])
async def legacy_twilio_sms_webhook(request: Request):
    """Legacy redirect for Twilio SMS webhook. Forwards to /api/sms/twilio-sms."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/sms/twilio-sms", status_code=307)


@app.get("/", response_class=JSONResponse)
async def root():
    return {
        "service": "Outbound Database Service",
        "status": "healthy",
        "version": "0.1.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        backend = await check_database_health()
        
        return {
            "status": "healthy",
            "service": "database",
            "database_backend": backend,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database health check failed: {e}")


@app.post("/api/calls/start-call")
async def start_single_call(agent_id: Optional[str] = None):
    """Start a single outbound call through an available agent."""
    print(f"🚀 Start call request received (agent_id: {agent_id})")
    
    # Find an available agent
    agent_ports = list(range(5101, 5111))  # Agents on ports 5101-5110
    
    for port in agent_ports:
        try:
            async with aiohttp.ClientSession() as session:
                print(f"  Trying agent on port {port}...")
                
                # Try to start a call on this agent
                async with session.post(
                    f"http://localhost:{port}/start-calling",
                    json={"agent_id": agent_id} if agent_id else {},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"  ✅ Agent {port} response: {data}")
                        
                        # Check if the agent actually succeeded
                        if data.get("status") == "success" and data.get("call_sid"):
                            print(f"  ✅ Call successful! SID: {data.get('call_sid')}")
                            return {
                                "status": "success",
                                "agent_port": port,
                                "agent_id": data.get("agent_id"),
                                "call_sid": data.get("call_sid"),
                                "message": data.get("message", "Call initiated successfully")
                            }
                        else:
                            # Agent returned error or missing call_sid
                            print(f"  ⚠️  Agent {port} failed: {data.get('message', 'Unknown error')}")
                            continue
                    else:
                        print(f"  ❌ Agent {port} HTTP error: {response.status}")
                        
        except Exception as e:
            print(f"  ❌ Agent {port} exception: {e}")
            # Try next agent
            continue
    
    # No agents available or all failed
    print("❌ No agents could handle the call")
    raise HTTPException(status_code=503, detail="No available agents to handle the call")



@app.post("/api/calls/start-campaign")
async def start_campaign(request: CampaignRequest):
    """Start a parallel calling campaign across multiple agents."""
    call_count = request.call_count
    print(f"🚀 Campaign request: {call_count} calls")
    
    try:
        # Get healthy agents
        agent_ports = list(range(5101, 5111))
        healthy_agents = []
        
        async with aiohttp.ClientSession() as session:
            for port in agent_ports:
                try:
                    async with session.get(f"http://localhost:{port}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                        if response.status == 200:
                            healthy_agents.append({
                                'port': port,
                                'url': f"http://localhost:{port}",
                                'agent_id': f"Agent{port-5100}"  # Format: Agent1, Agent2, etc.
                            })
                except:
                    continue
        
        if not healthy_agents:
            print("❌ No healthy agents available")
            raise HTTPException(status_code=503, detail="No healthy agents available")
        
        print(f"✅ Found {len(healthy_agents)} healthy agents")
        
        # Get leads using LeadService
        from services.lead_service import get_lead_service
        lead_service = get_lead_service()
        leads_result = lead_service.get_multiple_leads(count=call_count)
        leads = leads_result.get('leads', [])
        
        if not leads:
            print("❌ No leads available")
            raise HTTPException(status_code=404, detail="No leads available for campaign")
        
        actual_count = min(call_count, len(leads))
        print(f"📋 Got {len(leads)} leads, will call {actual_count}")
        
        # Get available Twilio numbers using PhoneNumberService
        from services.phone_number_service import get_phone_number_service
        phone_service = get_phone_number_service()
        available_numbers_result = phone_service.get_available_numbers()
        
        twilio_numbers = []
        if available_numbers_result.get('available_numbers'):
            numbers = available_numbers_result['available_numbers'][:actual_count]
            twilio_numbers = [{'phone_number': n.get('phone_number')} for n in numbers]
        
        print(f"📱 Got {len(twilio_numbers)} Twilio numbers")
        
        if not twilio_numbers:
            raise HTTPException(status_code=404, detail="No Twilio numbers available")
        
        # Adjust count to min of leads and numbers
        actual_count = min(actual_count, len(twilio_numbers))
        
        # Create parallel tasks
        tasks = []
        async with aiohttp.ClientSession() as session:
            for i in range(actual_count):
                agent_index = i % len(healthy_agents)
                agent = healthy_agents[agent_index]
                lead = leads[i]
                twilio_num = twilio_numbers[i]
                
                # Call agent with pre-assigned data
                task = session.post(
                    f"{agent['url']}/start-calling-with-data",
                    json={
                        'lead': lead,
                        'twilio_number': twilio_num['phone_number']
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                )
                tasks.append(task)
                print(f"📞 Call {i+1}: {agent['agent_id']} → {lead['phone_number']} via {twilio_num['phone_number']}")
            
            print(f"🚀 Starting {len(tasks)} parallel calls...")
            
            # Execute all in parallel
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            results = []
            successful = 0
            failed = 0
            
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    failed += 1
                    results.append({
                        'call_number': i + 1,
                        'status': 'error',
                        'error': str(response)
                    })
                else:
                    try:
                        data = await response.json()
                        if data.get('status') == 'success':
                            successful += 1
                        else:
                            failed += 1
                        results.append({
                            'call_number': i + 1,
                            'status': data.get('status'),
                            'call_sid': data.get('call_sid'),
                            'agent_id': data.get('agent_id')
                        })
                    except:
                        failed += 1
                        results.append({
                            'call_number': i + 1,
                            'status': 'error',
                            'error': 'Failed to parse response'
                        })
        
        print(f"✅ Campaign complete: {successful} successful, {failed} failed")
        
        return {
            "status": "completed",
            "total_calls": actual_count,
            "successful": successful,
            "failed": failed,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Campaign error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Campaign failed: {e}")



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
