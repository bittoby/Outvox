"""
Worker Manager
Automatically starts all background workers when the application starts.

Workers:
1. Batch Executor - Executes pending SMS batches (runs continuously)
2. Reset Phone Stats - Resets hourly/daily counters (scheduled)
3. Daily Reporter - Generates daily reports (scheduled)
4. Safe Call Popup Creator - Creates popup cards for safe calling (scheduled)
"""

import asyncio
import logging
import threading
from datetime import datetime, time, timedelta
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Worker imports are lazy-loaded to avoid import errors if ODBC is not available


class WorkerManager:
    """
    Manages all background workers for the application.
    
    Automatically starts:
    - Batch Executor (continuous daemon)
    - Reset Phone Stats (hourly/daily)
    - Daily Reporter (daily at 11:59 PM)
    - Safe Call Popup Creator (every hour)
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'WorkerManager':
        """Get singleton instance of WorkerManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the worker manager."""
        self.batch_executor: Optional[Any] = None  # BatchExecutorWorker (lazy loaded)
        self.scheduler_tasks: list = []
        self.is_running = False
    
    async def start_all_workers(self):
        """
        Start all background workers.
        
        This should be called when the application starts (e.g., in FastAPI startup event).
        """
        if self.is_running:
            logger.warning("Workers are already running")
            return
        
        logger.info("🚀 Starting all background workers...")
        
        try:
            # Start batch executor in daemon mode (continuous)
            await self._start_batch_executor()
            
            # Start scheduled workers
            await self._start_scheduled_workers()
            
            self.is_running = True
            logger.info("✅ All workers started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start workers: {e}")
            import traceback
            traceback.print_exc()
    
    async def _start_batch_executor(self):
        """Start the batch executor worker in daemon mode."""
        try:
            logger.info("📦 Starting Batch Executor Worker...")
            # Lazy import to avoid import errors if ODBC is not available
            from workers.batch_executor import BatchExecutorWorker
            self.batch_executor = BatchExecutorWorker()
            
            # Start in background task (non-blocking)
            asyncio.create_task(self.batch_executor.run_daemon())
            
            logger.info("✅ Batch Executor Worker started (daemon mode)")
        except ImportError as e:
            logger.warning(f"⚠️  Batch Executor Worker not available (ODBC not installed): {e}")
            logger.warning("   Workers require ODBC drivers. Skipping worker startup.")
            self.batch_executor = None
        except Exception as e:
            logger.error(f"❌ Failed to start Batch Executor: {e}")
            # Don't raise - allow app to continue without workers
            self.batch_executor = None
    
    async def _start_scheduled_workers(self):
        """Start scheduled workers using asyncio tasks."""
        try:
            logger.info("⏰ Starting scheduled workers...")
            
            # 1. Reset Phone Stats - Hourly (runs every hour)
            task1 = asyncio.create_task(self._schedule_hourly_reset())
            self.scheduler_tasks.append(task1)
            
            # 2. Reset Phone Stats - Daily (runs at midnight)
            task2 = asyncio.create_task(self._schedule_daily_reset())
            self.scheduler_tasks.append(task2)
            
            # 3. Daily Reporter - Daily at 11:59 PM
            task3 = asyncio.create_task(self._schedule_daily_reporter())
            self.scheduler_tasks.append(task3)
            
            # 4. Safe Call Popup Creator - Every hour
            task4 = asyncio.create_task(self._schedule_safe_call_popup_creator())
            self.scheduler_tasks.append(task4)
            
            logger.info("✅ Scheduled workers started:")
            logger.info("   - Reset Phone Stats: Hourly (at :00) and Daily (midnight)")
            logger.info("   - Daily Reporter: Daily at 11:59 PM")
            logger.info("   - Safe Call Popup Creator: Every hour")
            
        except Exception as e:
            logger.error(f"❌ Failed to start scheduled workers: {e}")
            raise
    
    async def _schedule_hourly_reset(self):
        """Schedule hourly phone stats reset."""
        while self.is_running:
            try:
                now = datetime.now()
                # Calculate next hour (at :00)
                next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
                wait_seconds = (next_hour - now).total_seconds()
                
                logger.info(f"⏰ Hourly reset scheduled for {next_hour.strftime('%H:%M:%S')} (waiting {wait_seconds:.0f} seconds)")
                await asyncio.sleep(wait_seconds)
                
                # Lazy import to avoid import errors if ODBC is not available
                try:
                    from workers.reset_phone_stats import reset_hourly
                    # Run reset in thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, reset_hourly)
                except ImportError as e:
                    logger.warning(f"⚠️  Reset phone stats worker not available: {e}")
                    break  # Exit loop if worker not available
                
            except Exception as e:
                logger.error(f"❌ Hourly phone stats reset failed: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def _schedule_daily_reset(self):
        """Schedule daily phone stats reset (at midnight)."""
        while self.is_running:
            try:
                now = datetime.now()
                # Calculate next midnight
                next_midnight = (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
                wait_seconds = (next_midnight - now).total_seconds()
                
                logger.info(f"⏰ Daily reset scheduled for {next_midnight.strftime('%Y-%m-%d %H:%M:%S')} (waiting {wait_seconds:.0f} seconds)")
                await asyncio.sleep(wait_seconds)
                
                # Lazy import to avoid import errors if ODBC is not available
                try:
                    from workers.reset_phone_stats import reset_daily
                    # Run reset in thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, reset_daily)
                except ImportError as e:
                    logger.warning(f"⚠️  Reset phone stats worker not available: {e}")
                    break  # Exit loop if worker not available
                
            except Exception as e:
                logger.error(f"❌ Daily phone stats reset failed: {e}")
                await asyncio.sleep(86400)  # Wait 24 hours before retry
    
    async def _schedule_daily_reporter(self):
        """Schedule daily reporter (at 11:59 PM)."""
        while self.is_running:
            try:
                now = datetime.now()
                # Calculate next 11:59 PM
                target_time = time(23, 59, 0)
                next_report = now.replace(hour=target_time.hour, minute=target_time.minute, second=0, microsecond=0)
                if next_report <= now:
                    next_report += timedelta(days=1)
                wait_seconds = (next_report - now).total_seconds()
                
                logger.info(f"⏰ Daily reporter scheduled for {next_report.strftime('%Y-%m-%d %H:%M:%S')} (waiting {wait_seconds:.0f} seconds)")
                await asyncio.sleep(wait_seconds)
                
                # Lazy import to avoid import errors if ODBC is not available
                try:
                    from workers.daily_reporter import DailyReporter
                    # Run reporter in thread pool
                    loop = asyncio.get_event_loop()
                    reporter = DailyReporter()
                    # Generate report for today (no email, just generate)
                    await loop.run_in_executor(None, lambda: reporter.generate_report())
                except ImportError as e:
                    logger.warning(f"⚠️  Daily reporter worker not available: {e}")
                    break  # Exit loop if worker not available
                
            except Exception as e:
                logger.error(f"❌ Daily reporter failed: {e}")
                await asyncio.sleep(86400)  # Wait 24 hours before retry
    
    async def _schedule_safe_call_popup_creator(self):
        """Schedule safe call popup creator (every hour)."""
        while self.is_running:
            try:
                now = datetime.now()
                # Calculate next hour (at :00)
                next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
                wait_seconds = (next_hour - now).total_seconds()
                
                await asyncio.sleep(wait_seconds)
                
                # Lazy import to avoid import errors if ODBC is not available
                try:
                    from workers.safe_call_popup_creator import process_safe_call_leads
                    # Run in thread pool
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, process_safe_call_leads)
                except ImportError as e:
                    logger.warning(f"⚠️  Safe call popup creator worker not available: {e}")
                    break  # Exit loop if worker not available
                
            except Exception as e:
                logger.error(f"❌ Safe call popup creator failed: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retry
    
    async def stop_all_workers(self):
        """Stop all workers gracefully."""
        logger.info("🛑 Stopping all workers...")
        
        try:
            # Stop batch executor
            if self.batch_executor:
                self.batch_executor.stop()
            
            # Cancel scheduler tasks
            for task in self.scheduler_tasks:
                task.cancel()
            
            # Wait for tasks to complete cancellation
            if self.scheduler_tasks:
                await asyncio.gather(*self.scheduler_tasks, return_exceptions=True)
            
            self.is_running = False
            logger.info("✅ All workers stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping workers: {e}")


def get_worker_manager() -> WorkerManager:
    """Get singleton instance of WorkerManager."""
    return WorkerManager.get_instance()

