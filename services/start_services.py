#!/usr/bin/env python3
"""
Service Orchestrator - Meta-inspired microservices startup script
Manages the startup, health checking, and orchestration of all microservices
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Dict, List, Optional
import subprocess
import httpx
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("orchestrator")

# Service definitions with their startup commands and health endpoints
SERVICES = {
    "redis": {
        "command": ["redis-server"],
        "port": 6379,
        "health_url": None,
        "startup_timeout": 10,
        "description": "Redis Cache & Message Queue"
    },
    "mysql-auth": {
        "command": ["mysqld", "--datadir=/var/lib/mysql"],
        "port": 3306,
        "health_url": None,
        "startup_timeout": 30,
        "description": "MySQL Auth Database"
    },
    "mysql-dashboard": {
        "command": ["mysqld", "--datadir=/var/lib/mysql"],
        "port": 3307,
        "health_url": None,
        "startup_timeout": 30,
        "description": "MySQL Dashboard Database"
    },
    "auth-service": {
        "command": ["python", "-m", "services.auth_service"],
        "port": 8001,
        "health_url": "http://localhost:8001/health",
        "startup_timeout": 20,
        "description": "Authentication Service"
    },
    "dashboard-service": {
        "command": ["python", "-m", "services.dashboard_service"],
        "port": 8004,
        "health_url": "http://localhost:8004/health",
        "startup_timeout": 20,
        "description": "Dashboard Analytics Service"
    },
    "attendance-service": {
        "command": ["python", "-m", "services.attendance_service"],
        "port": 8002,
        "health_url": "http://localhost:8002/health",
        "startup_timeout": 20,
        "description": "Attendance Service"
    },
    "employees-service": {
        "command": ["python", "-m", "services.employees_service"],
        "port": 8003,
        "health_url": "http://localhost:8003/health",
        "startup_timeout": 20,
        "description": "Employees Service"
    },
    "notifications-service": {
        "command": ["python", "-m", "services.notifications_service"],
        "port": 8005,
        "health_url": "http://localhost:8005/health",
        "startup_timeout": 20,
        "description": "Notifications Service"
    },
    "analytics-service": {
        "command": ["python", "-m", "services.analytics_service"],
        "port": 8006,
        "health_url": "http://localhost:8006/health",
        "startup_timeout": 20,
        "description": "Analytics Service"
    },
    "realtime-service": {
        "command": ["python", "-m", "services.realtime_service"],
        "port": 8007,
        "health_url": "http://localhost:8007/health",
        "startup_timeout": 20,
        "description": "Real-time WebSocket Service"
    },
    "gateway": {
        "command": ["python", "-m", "services.gateway"],
        "port": 8000,
        "health_url": "http://localhost:8000/health",
        "startup_timeout": 20,
        "description": "API Gateway"
    }
}

# Service startup order (dependencies first)
STARTUP_ORDER = [
    "redis",
    "mysql-auth",
    "mysql-dashboard",
    "auth-service",
    "dashboard-service",
    "attendance-service",
    "employees-service",
    "notifications-service",
    "analytics-service",
    "realtime-service",
    "gateway"
]

class ServiceManager:
    """Meta-style service manager for microservices orchestration"""
    
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.health_status: Dict[str, bool] = {}
        self.startup_times: Dict[str, datetime] = {}
        self.running = True
        self.shutdown_event = asyncio.Event()
    
    async def start_service(self, service_name: str) -> bool:
        """Start a single service"""
        if service_name not in SERVICES:
            logger.error(f"Unknown service: {service_name}")
            return False
        
        service_config = SERVICES[service_name]
        
        logger.info(f"Starting {service_name}: {service_config['description']}")
        
        try:
            # Start the service process
            process = subprocess.Popen(
                service_config["command"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[service_name] = process
            self.startup_times[service_name] = datetime.now()
            
            # Wait for service to be ready
            if service_config["health_url"]:
                await self.wait_for_service_health(service_name, service_config)
            
            logger.info(f"✅ {service_name} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start {service_name}: {e}")
            return False
    
    async def wait_for_service_health(self, service_name: str, service_config: Dict):
        """Wait for service to become healthy"""
        timeout = service_config["startup_timeout"]
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                try:
                    response = await client.get(service_config["health_url"], timeout=5)
                    if response.status_code == 200:
                        self.health_status[service_name] = True
                        return
                except:
                    pass
                
                await asyncio.sleep(1)
            
            raise TimeoutError(f"Service {service_name} did not become healthy within {timeout} seconds")
    
    async def start_all_services(self) -> bool:
        """Start all services in dependency order"""
        logger.info("🚀 Starting UNIGOM Microservices Platform")
        logger.info("=" * 60)
        
        for service_name in STARTUP_ORDER:
            if not self.running:
                break
            
            success = await self.start_service(service_name)
            if not success:
                logger.error(f"Failed to start {service_name}, stopping...")
                await self.stop_all_services()
                return False
            
            # Small delay between services
            await asyncio.sleep(2)
        
        logger.info("=" * 60)
        logger.info("✅ All services started successfully!")
        await self.print_service_status()
        
        return True
    
    async def stop_service(self, service_name: str):
        """Stop a single service"""
        if service_name in self.processes:
            process = self.processes[service_name]
            logger.info(f"Stopping {service_name}...")
            
            try:
                process.terminate()
                await asyncio.sleep(5)
                
                if process.poll() is None:
                    process.kill()
                
                del self.processes[service_name]
                logger.info(f"✅ {service_name} stopped")
                
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {e}")
    
    async def stop_all_services(self):
        """Stop all services"""
        logger.info("🛑 Stopping all services...")
        
        # Stop in reverse order
        for service_name in reversed(STARTUP_ORDER):
            await self.stop_service(service_name)
        
        logger.info("✅ All services stopped")
    
    async def health_check_loop(self):
        """Continuous health checking of services"""
        while self.running:
            try:
                async with httpx.AsyncClient() as client:
                    for service_name, service_config in SERVICES.items():
                        if service_config["health_url"] and service_name in self.processes:
                            try:
                                response = await client.get(service_config["health_url"], timeout=5)
                                self.health_status[service_name] = response.status_code == 200
                            except:
                                self.health_status[service_name] = False
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(10)
    
    async def print_service_status(self):
        """Print current service status"""
        logger.info("\n📊 Service Status:")
        logger.info("-" * 40)
        
        for service_name in STARTUP_ORDER:
            status = "🟢 Healthy" if self.health_status.get(service_name, False) else "🔴 Unhealthy"
            uptime = ""
            
            if service_name in self.startup_times:
                uptime_duration = datetime.now() - self.startup_times[service_name]
                uptime = f" (Uptime: {uptime_duration})"
            
            logger.info(f"{service_name:20} {status:15} {uptime}")
        
        logger.info("-" * 40)
    
    async def monitor_services(self):
        """Monitor services and handle failures"""
        while self.running:
            await asyncio.sleep(60)  # Check every minute
            
            for service_name, service_config in SERVICES.items():
                if service_name in self.processes and not self.health_status.get(service_name, False):
                    logger.warning(f"⚠️  Service {service_name} is unhealthy")
                    
                    # Attempt to restart the service
                    logger.info(f"Restarting {service_name}...")
                    await self.stop_service(service_name)
                    await asyncio.sleep(5)
                    await self.start_service(service_name)

async def main():
    """Main orchestration function"""
    manager = ServiceManager()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        manager.running = False
        asyncio.create_task(manager.stop_all_services())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start all services
        if await manager.start_all_services():
            # Start health monitoring
            health_task = asyncio.create_task(manager.health_check_loop())
            monitor_task = asyncio.create_task(manager.monitor_services())
            
            # Wait for shutdown signal
            await manager.shutdown_event.wait()
            
            # Cancel background tasks
            health_task.cancel()
            monitor_task.cancel()
            
            # Stop all services
            await manager.stop_all_services()
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
    finally:
        await manager.stop_all_services()

if __name__ == "__main__":
    asyncio.run(main())
