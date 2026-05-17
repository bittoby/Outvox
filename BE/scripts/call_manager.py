#!/usr/bin/env python3
"""
Call Manager - Simple script to manage outbound calling operations.
"""

import os
import sys
import time
import random
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Configuration
OUTBOUND_SERVICE_URL = os.getenv('OUTBOUND_SERVICE_URL', 'http://localhost:5100') # Nginx load balancer port
DB_SERVICE_URL = os.getenv('DB_SERVICE_URL', 'http://localhost:8000')  # Database service
INDIVIDUAL_AGENT_URLS = [f"http://localhost:{5101 + i}" for i in range(10)]  # Direct agent URLs

async def start_calling_session():
    """Start a calling session by making calls to available leads with proper agent stickiness."""
    # First, get a healthy agent to ensure stickiness
    healthy_agents = await get_healthy_agents()
    if not healthy_agents:
        print("No healthy agents available!")
        return {"status": "no_agents", "message": "No healthy agents available"}
    
    # Select agent using round-robin or least-busy logic
    selected_agent = select_best_agent(healthy_agents)
    print(f"Selected agent {selected_agent['agent_id']} for call")
    
    # Make call directly to the selected agent (bypassing load balancer)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{selected_agent['url']}/start-calling") as response:
                result = await response.json()
                result['selected_agent'] = selected_agent['agent_id']
                print(f"Call result from {selected_agent['agent_id']}: {result}")
                return result
        except Exception as e:
            print(f"Error starting call with agent {selected_agent['agent_id']}: {e}")
            return {"status": "error", "message": f"Failed to contact agent {selected_agent['agent_id']}", "error": str(e)}

async def get_agent_health():
    """Get health status of all outbound agents."""
    agent_status = []
    async with aiohttp.ClientSession() as session:
        for i, url in enumerate(INDIVIDUAL_AGENT_URLS, 1):
            try:
                async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        agent_status.append({
                            'agent_id': f'Agent{i}',  # Format: Agent1, Agent2, etc.
                            'url': url,
                            'status': 'healthy',
                            'data': data
                        })
                    else:
                        agent_status.append({
                            'agent_id': f'Agent{i}',  # Format: Agent1, Agent2, etc.
                            'url': url,
                            'status': 'unhealthy',
                            'error': f'HTTP {response.status}'
                        })
            except Exception as e:
                agent_status.append({
                    'agent_id': f'Agent{i}',  # Format: Agent1, Agent2, etc.
                    'url': url,
                    'status': 'unreachable',
                    'error': str(e)
                })
    
    return agent_status

async def get_healthy_agents():
    """Get list of healthy agents only."""
    all_agents = await get_agent_health()
    healthy_agents = [agent for agent in all_agents if agent['status'] == 'healthy']
    return healthy_agents

def select_best_agent(healthy_agents):
    """Select the least-frequently used agent for optimal load distribution."""
    if not healthy_agents:
        return None
    
    # Get current call frequency for each agent
    agent_frequencies = get_agent_call_frequencies(healthy_agents)
    
    # Find the agent(s) with the lowest call frequency
    min_frequency = min(agent_frequencies.values())
    least_used_agents = [agent_id for agent_id, freq in agent_frequencies.items() if freq == min_frequency]
    
    # If multiple agents have the same low frequency, pick randomly among them
    if len(least_used_agents) > 1:
        selected_agent_id = random.choice(least_used_agents)
        print(f"🎯 Agent selection: {len(least_used_agents)} agents tied with {min_frequency} calls, randomly selected {selected_agent_id}")
    else:
        selected_agent_id = least_used_agents[0]
        print(f"🎯 Agent selection: {selected_agent_id} has lowest frequency ({min_frequency} calls)")
    
    # Find the full agent object
    selected_agent = next(agent for agent in healthy_agents if agent['agent_id'] == selected_agent_id)
    
    # Increment the call counter for this agent
    increment_agent_call_count(selected_agent_id)
    
    print(f"🎯 Load distribution: {len(healthy_agents)} healthy agents, selected least-used agent {selected_agent_id}")
    return selected_agent

# Global variables to track call stickiness and frequency
active_calls = {}  # {call_sid: agent_id} mapping
agent_call_counts = {}  # {agent_id: call_count} mapping for load balancing

def register_call_stickiness(call_sid: str, agent_id: str):
    """Register a call as being handled by a specific agent."""
    active_calls[call_sid] = agent_id
    print(f"🔗 Registered call stickiness: {call_sid} → {agent_id}")

def get_call_agent(call_sid: str) -> str:
    """Get the agent handling a specific call."""
    return active_calls.get(call_sid)

def unregister_call_stickiness(call_sid: str):
    """Remove call stickiness when call ends."""
    if call_sid in active_calls:
        agent_id = active_calls.pop(call_sid)
        print(f"🔗 Unregistered call stickiness: {call_sid} → {agent_id}")
        return agent_id
    return None

def get_agent_call_frequencies(healthy_agents):
    """Get current call frequencies for all healthy agents."""
    frequencies = {}
    
    for agent in healthy_agents:
        agent_id = agent['agent_id']
        # Initialize agent count if not exists
        if agent_id not in agent_call_counts:
            agent_call_counts[agent_id] = 0
        frequencies[agent_id] = agent_call_counts[agent_id]
    
    return frequencies

def increment_agent_call_count(agent_id: str):
    """Increment the call count for an agent."""
    if agent_id not in agent_call_counts:
        agent_call_counts[agent_id] = 0
    agent_call_counts[agent_id] += 1
    print(f"📊 Agent {agent_id} call count: {agent_call_counts[agent_id]}")


async def get_multiple_twilio_numbers(count: int):
    """Get multiple different Twilio numbers for parallel calling."""
    try:
        async with aiohttp.ClientSession() as session:
            # Get all available Twilio numbers
            async with session.get(f"{DB_SERVICE_URL}/api/analytics/stats") as response:
                if response.status == 200:
                    stats = await response.json()
                    all_numbers = stats.get('numbers', [])
                    
                    # Filter available numbers (not maxed out)
                    available_numbers = []
                    for num in all_numbers:
                        if num['daily_calls'] < 30:  # Daily limit
                            available_numbers.append({
                                'phone_number': num['phone'],
                                'daily_calls': num['daily_calls']
                            })
                    
                    print(f"📞 Found {len(available_numbers)} available Twilio numbers")
                    
                    # Sort by daily_calls (ascending) to get least used numbers first
                    available_numbers.sort(key=lambda x: x['daily_calls'])
                    
                    # Return up to 'count' numbers (least used first)
                    selected_numbers = available_numbers[:count]
                    for num in selected_numbers:
                        print(f"  📞 {num['phone_number']} (daily: {num['daily_calls']}/30)")
                    
                    return selected_numbers
                else:
                    print(f"❌ Error getting Twilio numbers: HTTP {response.status}")
                    return []
    except Exception as e:
        print(f"❌ Error getting multiple Twilio numbers: {e}")
        return []

async def get_multiple_leads(count: int):
    """Get multiple different leads for parallel calling."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DB_SERVICE_URL}/api/leads/multiple", 
                                 params={'count': count}) as response:
                if response.status == 200:
                    data = await response.json()
                    leads = data.get('leads', [])
                    
                    print(f"📋 Got {len(leads)} different leads:")
                    for i, lead in enumerate(leads):
                        print(f"  📋 Lead {i+1}: {lead['name']} - {lead['phone_number']}")
                    
                    return leads
                else:
                    print(f"❌ Error getting multiple leads: HTTP {response.status}")
                    return []
    except Exception as e:
        print(f"❌ Error getting multiple leads: {e}")
        return []

async def send_consent_sms(lead_id: int, message: Optional[str] = None, force: bool = False):
    """Send SMS consent request to a specific lead."""
    payload = {"force": force}
    if message:
        payload["message"] = message
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{DB_SERVICE_URL}/api/leads/{lead_id}/request-consent",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                data = await response.json()
                if response.status == 200:
                    print(f"✅ Consent SMS sent to lead {lead_id} ({data.get('phone_number')})")
                else:
                    print(f"❌ Failed to send consent SMS: HTTP {response.status} - {data}")
    except Exception as e:
        print(f"❌ Error sending consent SMS: {e}")

async def send_consent_batch(limit: int = 100, message: Optional[str] = None, force: bool = False):
    """Send SMS consent requests to a batch of unverified leads."""
    payload = {"limit": limit, "force": force}
    if message:
        payload["message"] = message
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{DB_SERVICE_URL}/api/leads/request-consent-batch",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                data = await response.json()
                if response.status == 200:
                    print(f"✅ Consent SMS requested for {data.get('requested', 0)} leads")
                    for result in data.get("results", []):
                        if result.get("status") == "sent":
                            print(f"   → Lead {result['lead_id']}: sent to {result.get('phone_number')}")
                        else:
                            print(f"   → Lead {result.get('lead_id')}: {result.get('status')} ({result.get('error')})")
                else:
                    print(f"❌ Failed to run consent batch: HTTP {response.status} - {data}")
    except Exception as e:
        print(f"❌ Error sending consent batch: {e}")

async def make_single_parallel_call(agent: dict, lead: dict, twilio_number: dict, call_number: int):
    """Make a single call with pre-assigned agent, lead, and Twilio number."""
    agent_id = agent['agent_id']
    agent_url = agent['url']
    
    try:
        # Make call directly to agent with pre-assigned data
        async with aiohttp.ClientSession() as session:
            call_data = {
                'lead': lead,
                'twilio_number': twilio_number['phone_number']
            }
            
            async with session.post(f"{agent_url}/start-calling-with-data", 
                                  json=call_data, 
                                  timeout=aiohttp.ClientTimeout(total=30)) as response:
                result = await response.json()
                
                # Track this call for load balancing
                increment_agent_call_count(agent_id)
                
                # Add metadata
                result['call_number'] = call_number
                result['agent_id'] = agent_id
                result['twilio_number'] = twilio_number['phone_number']
                result['lead_phone'] = lead['phone_number']
                
                return result
                
    except Exception as e:
        print(f"❌ {agent_id}-Call{call_number}: Connection error - {e}")
        return {
            'call_number': call_number,
            'agent_id': agent_id,
            'status': 'error',
            'error': str(e),
            'twilio_number': twilio_number['phone_number'],
            'lead_phone': lead['phone_number']
        }

async def start_parallel_calling(max_calls: int = 10):
    """Start TRUE PARALLEL calling across multiple agents with DIFFERENT Twilio numbers."""
    healthy_agents = await get_healthy_agents()
    
    if not healthy_agents:
        print("No healthy agents available!")
        return []
    
    print(f"🚀 Found {len(healthy_agents)} healthy agents for PARALLEL calling")
    print(f"🎯 Target: {max_calls} calls using up to {len(healthy_agents)} agents simultaneously")
    
    # PRE-ALLOCATE Twilio numbers for parallel calls
    print(f"📞 PRE-ALLOCATING Twilio numbers for parallel execution...")
    twilio_numbers = await get_multiple_twilio_numbers(max_calls)
    
    if len(twilio_numbers) < max_calls:
        print(f"⚠️  Only {len(twilio_numbers)} Twilio numbers available, adjusting to {len(twilio_numbers)} calls")
        max_calls = len(twilio_numbers)
    
    if max_calls == 0:
        print("❌ No Twilio numbers available!")
        return []
    
    # PRE-FETCH leads for parallel calls
    print(f"📋 PRE-FETCHING leads for parallel execution...")
    leads = await get_multiple_leads(max_calls)
    
    if len(leads) < max_calls:
        print(f"⚠️  Only {len(leads)} leads available, adjusting to {len(leads)} calls")
        max_calls = len(leads)
    
    if max_calls == 0:
        print("❌ No leads available!")
        return []
    
    # Show current load distribution before starting
    print("📊 Current load distribution:")
    frequencies = get_agent_call_frequencies(healthy_agents)
    if frequencies:
        for agent_id, count in frequencies.items():
            print(f"  {agent_id}: {count} calls")
    else:
        print("  No previous calls recorded")
    
    # Determine how many agents to use (up to available agents or max_calls)
    agents_to_use = min(len(healthy_agents), max_calls)
    selected_agents = healthy_agents[:agents_to_use]
    
    print(f"🔥 PARALLEL EXECUTION: Using {agents_to_use} agents simultaneously")
    print(f"📞 Twilio numbers allocated: {[num['phone_number'] for num in twilio_numbers[:max_calls]]}")
    print(f"📋 Leads allocated: {[lead['name'] + ' (' + lead['phone_number'] + ')' for lead in leads[:max_calls]]}")
    
    # Create parallel tasks with PRE-ASSIGNED leads and numbers
    tasks = []
    for i in range(max_calls):
        agent_index = i % agents_to_use
        agent = selected_agents[agent_index]
        lead = leads[i]
        twilio_number = twilio_numbers[i]
        
        task = make_single_parallel_call(agent, lead, twilio_number, i + 1)
        tasks.append(task)
        print(f"📞 Call {i+1}: {agent['agent_id']} → {lead['phone_number']} via {twilio_number['phone_number']}")
    
    print(f"\n🚀 Starting {len(tasks)} PARALLEL calls with DIFFERENT numbers...")
    
    # Execute all calls in parallel
    start_time = datetime.now()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = datetime.now()
    
    # Process results
    total_calls = 0
    successful_calls = 0
    all_results = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ Call {i+1}: ERROR - {result}")
            error_result = {
                'call_number': i + 1,
                'status': 'error',
                'error': str(result)
            }
            all_results.append(error_result)
        else:
            all_results.append(result)
            total_calls += 1
            if result.get('status') == 'success':
                successful_calls += 1
                print(f"✅ Call {i+1}: SUCCESS - {result.get('call_sid')} via {result.get('twilio_number')}")
            else:
                print(f"❌ Call {i+1}: FAILED - {result.get('message', 'Unknown error')}")
    
    # Show final statistics
    duration = (end_time - start_time).total_seconds()
    print(f"\n🏁 PARALLEL CALLING COMPLETED in {duration:.2f} seconds")
    print(f"📊 Results: {successful_calls}/{max_calls} successful calls")
    print(f"⚡ Throughput: {max_calls/duration:.2f} calls/second")
    
    # Show Twilio number usage
    print(f"\n📞 Twilio Number Usage:")
    for i, twilio_num in enumerate(twilio_numbers[:max_calls]):
        result = all_results[i] if i < len(all_results) else {}
        status = "✅ SUCCESS" if result.get('status') == 'success' else "❌ FAILED"
        print(f"  {twilio_num['phone_number']}: {status}")
    
    return all_results


async def get_call_stats():
    """Get statistics from database service."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DB_SERVICE_URL}/api/analytics/stats") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error getting stats: HTTP {response.status}")
                    return None
    except Exception as e:
        print(f"Error getting stats: {e}")
        return None

async def add_lead(phone_number: str, name: str = None, Address: str = None, City: str = None, County: str = None, State: str = None, Zip: str = None, priority: int = 1):
    """Add a new lead via database service."""
    try:
        lead_data = {
            "phone_number": phone_number,
            "name": name,
            "Address": Address,
            "City": City,
            "County": County,
            "State": State,
            "Zip": Zip,
            "priority": priority
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{DB_SERVICE_URL}/api/leads", json=lead_data) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ {result['message']}")
                else:
                    error = await response.json()
                    print(f"❌ Error: {error.get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Error adding lead: {e}")

async def mark_lead_dnc(phone_number: str):
    """Mark a lead as Do Not Call via database service."""
    try:
        dnc_data = {
            "phone_number": phone_number,
            "agent_id": "MANAGER"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{DB_SERVICE_URL}/api/leads/mark-dnc", json=dnc_data) as response:
                if response.status == 200:
                    result = await response.json()
                    print(result['message'])
                else:
                    error = await response.json()
                    print(f"Error marking DNC: {error.get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"Error marking DNC: {e}")


async def run_smart_campaign(target_calls: int = None):
    """Run an intelligent campaign that automatically uses all available agents and leads."""
    print("🧠 Starting SMART CAMPAIGN - Auto-optimized for maximum efficiency")
    
    # Get system status
    healthy_agents = await get_healthy_agents()
    if not healthy_agents:
        print("❌ No healthy agents available!")
        return []
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DB_SERVICE_URL}/api/analytics/stats") as response:
                if response.status == 200:
                    stats = await response.json()
                    available_leads = stats.get('pending_leads', 0)
                    
                    if available_leads == 0:
                        print("❌ No leads available for calling!")
                        return []
                    
                    # Smart decision making
                    if target_calls is None:
                        # Auto-optimize: use all available leads up to agent capacity
                        optimal_calls = min(available_leads, len(healthy_agents) * 3)  # 3 calls per agent max
                        print(f"🧠 Auto-optimization: {available_leads} leads, {len(healthy_agents)} agents")
                        print(f"🎯 Optimal target: {optimal_calls} calls")
                    else:
                        optimal_calls = min(target_calls, available_leads)
                        print(f"🎯 Target: {optimal_calls} calls (limited by available leads: {available_leads})")
                    
                    print(f"⚡ Using {len(healthy_agents)} agents in parallel")
                    print(f"📊 Expected throughput: ~{optimal_calls/max(1, optimal_calls/len(healthy_agents)):.1f} calls/agent")
                    
                    # Execute the optimized campaign
                    return await start_parallel_calling(optimal_calls)
                else:
                    print(f"❌ Error getting system stats: HTTP {response.status}")
                    return []
    except Exception as e:
        print(f"❌ Error in smart campaign: {e}")
        return []

def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("🚀 OUTBOUND CALLING SYSTEM")
        print("=" * 50)
        print("ESSENTIAL COMMANDS:")
        print("  python call_manager.py stats              - Show call statistics")
        print("  python call_manager.py health             - Check agent health")
        print("  python call_manager.py single-call        - Make one call")
        print("  python call_manager.py campaign <count>   - Run parallel campaign")
        print("")
        print("LEAD MANAGEMENT:")
        print("  python call_manager.py add-lead <phone> [name] [address] [city] [state] [zip] [priority]")
        print("  python call_manager.py add-lead <phone> [name] [shop] [priority]  # Simple format")
        print("  python call_manager.py mark-dnc <phone>             # Mark number as DNC")
        print("  python call_manager.py send-consent <lead_id> [--force] [custom message]")
        print("  python call_manager.py consent-batch [limit] [--force] [custom message]")
        print("")
        print("💡 TIP: Use 'campaign' for best performance!")
        return
    
    command = sys.argv[1]
    
    if command == "stats":
        async def show_stats():
            stats = await get_call_stats()
            if stats:
                print("\n=== OUTBOUND CALLING STATS ===")
                print(f"Today's Calls: {stats['total_calls']}")
                print(f"  Interested: {stats['interested']}")
                print(f"  Not Interested: {stats['not_interested']}")
                print(f"  DNC Requests: {stats['dnc']}")
                print(f"  Callbacks: {stats['callback']}")
                print(f"Pending Leads: {stats['pending_leads']}")
                print("\nTwilio Numbers:")
                for num in stats['numbers']:
                    last_call = num['last_call'] if num['last_call'] else 'Never'
                    status = "Active" if num['is_active'] else "Inactive"
                    print(f"  {num['phone']} (Agent {num['agent_id']}, {status}) - {num['daily_calls']}/30 calls, last: {last_call}")
            else:
                print("Failed to get statistics")
        
        asyncio.run(show_stats())
    
    elif command == "add-lead":
        if len(sys.argv) < 3:
            print("Usage: python call_manager.py add-lead <phone> [name] [address] [city] [state] [zip] [priority]")
            print("       python call_manager.py add-lead <phone> [name] [shop] [priority]  # Simple format")
            return
        
        phone = sys.argv[2]
        name = sys.argv[3] if len(sys.argv) > 3 else None
        
        # Check if this is the simple format (4 args: phone, name, shop, priority)
        if len(sys.argv) == 5:
            # Simple format: phone, name, shop, priority
            shop = sys.argv[4]
            priority = 1
            asyncio.run(add_lead(phone, name, None, None, None, None, None, priority))
        elif len(sys.argv) >= 4:
            # Full format: phone, name, address, city, state, zip, priority
            address = sys.argv[4] if len(sys.argv) > 4 else None
            city = sys.argv[5] if len(sys.argv) > 5 else None
            state = sys.argv[6] if len(sys.argv) > 6 else None
            zip_code = sys.argv[7] if len(sys.argv) > 7 else None
            priority = int(sys.argv[8]) if len(sys.argv) > 8 else 1
            
            asyncio.run(add_lead(phone, name, address, city, None, state, zip_code, priority))
        else:
            # Just phone number
            asyncio.run(add_lead(phone))
    
    elif command == "mark-dnc":
        if len(sys.argv) < 3:
            print("Usage: python call_manager.py mark-dnc <phone>")
            return
        
        phone = sys.argv[2]
        asyncio.run(mark_lead_dnc(phone))
    
    elif command == "send-consent":
        if len(sys.argv) < 3:
            print("Usage: python call_manager.py send-consent <lead_id> [--force] [custom message]")
            return
        
        lead_id = int(sys.argv[2])
        args = sys.argv[3:]
        force = False
        if "--force" in args:
            force = True
            args.remove("--force")
        message = " ".join(args) if args else None
        asyncio.run(send_consent_sms(lead_id, message=message, force=force))
    
    elif command == "consent-batch":
        args = sys.argv[2:]
        limit = 100
        force = False
        message_tokens = []
        
        for arg in args:
            if arg.isdigit() and limit == 100:
                limit = int(arg)
            elif arg == "--force":
                force = True
            else:
                message_tokens.append(arg)
        
        message = " ".join(message_tokens) if message_tokens else None
        asyncio.run(send_consent_batch(limit=limit, message=message, force=force))
    
    elif command == "single-call":
        asyncio.run(start_calling_session())
    
    elif command == "campaign":
        if len(sys.argv) < 3:
            print("Usage: python call_manager.py campaign <count>")
            return
        
        count = int(sys.argv[2])
        asyncio.run(run_smart_campaign(count))
    
    elif command == "health":
        async def check_health():
            agents = await get_agent_health()
            print("\n=== OUTBOUND AGENT HEALTH ===")
            healthy_count = 0
            for agent in agents:
                status = agent['status']
                if status == 'healthy':
                    healthy_count += 1
                    print(f"✓ {agent['agent_id']}: {status} - {agent['data'].get('timestamp', 'Unknown time')}")
                else:
                    print(f"✗ {agent['agent_id']}: {status} - {agent.get('error', 'No error info')}")
            
            print(f"\nSummary: {healthy_count}/{len(agents)} agents healthy")
            
            # Check load balancer
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{OUTBOUND_SERVICE_URL}/health") as response:
                        if response.status == 200:
                            print("✓ Load balancer: healthy")
                        else:
                            print(f"✗ Load balancer: HTTP {response.status}")
            except Exception as e:
                print(f"✗ Load balancer: {e}")
        
        asyncio.run(check_health())
    
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
