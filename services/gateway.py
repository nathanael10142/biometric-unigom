"""
API Gateway Service - Meta-inspired microservices entry point
Handles routing, authentication, and request orchestration
"""

import logging
from typing import Dict, Any, Optional
import httpx
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
import asyncio
from datetime import datetime, timedelta

from app.config import settings
from app.core.auth import verify_token

logger = logging.getLogger("gateway")

# Service registry - Meta-style service discovery
SERVICE_REGISTRY = {
    "auth": {"url": "http://localhost:8001", "health": "/health"},
    "attendance": {"url": "http://localhost:8002", "health": "/health"},
    "employees": {"url": "http://localhost:8003", "health": "/health"},
    "dashboard": {"url": "http://localhost:8004", "health": "/health"},
    "notifications": {"url": "http://localhost:8005", "health": "/health"},
    "analytics": {"url": "http://localhost:8006", "health": "/health"},
}

class ServiceRegistry:
    """Meta-style service registry with health checking"""
    
    def __init__(self):
        self.services = SERVICE_REGISTRY.copy()
        self.health_status = {}
        self.last_health_check = {}
    
    async def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy"""
        if service_name not in self.services:
            return False
        
        service = self.services[service_name]
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service['url']}{service['health']}")
                is_healthy = response.status_code == 200
                self.health_status[service_name] = is_healthy
                self.last_health_check[service_name] = datetime.now()
                return is_healthy
        except Exception as e:
            logger.warning(f"Health check failed for {service_name}: {e}")
            self.health_status[service_name] = False
            return False
    
    async def get_healthy_service(self, service_name: str) -> Optional[str]:
        """Get a healthy service URL"""
        if service_name not in self.services:
            return None
        
        # Check if we need to refresh health status
        last_check = self.last_health_check.get(service_name)
        if not last_check or datetime.now() - last_check > timedelta(minutes=1):
            await self.check_service_health(service_name)
        
        if self.health_status.get(service_name, False):
            return self.services[service_name]["url"]
        
        return None
    
    async def route_request(self, service_name: str, path: str, method: str, 
                          headers: Dict[str, str], body: Optional[bytes] = None) -> Any:
        """Route request to appropriate service"""
        service_url = await self.get_healthy_service(service_name)
        if not service_url:
            raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable")
        
        url = f"{service_url}{path}"
        headers.pop("host", None)  # Remove host header
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=headers, content=body)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=headers, content=body)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise HTTPException(status_code=405, detail="Method not allowed")
                
                return response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Service timeout")
        except Exception as e:
            logger.error(f"Error routing to {service_name}: {e}")
            raise HTTPException(status_code=502, detail="Service error")

# Initialize service registry
service_registry = ServiceRegistry()
security = HTTPBearer()

# Create gateway app
gateway_app = FastAPI(
    title="UNIGOM API Gateway",
    description="Meta-inspired microservices gateway for UNIGOM Biométrie",
    version="2.0.0"
)

gateway_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@gateway_app.on_event("startup")
async def startup_event():
    """Initialize gateway and check service health"""
    logger.info("Starting UNIGOM API Gateway...")
    
    # Check all services health
    tasks = [service_registry.check_service_health(service) for service in SERVICE_REGISTRY]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("Gateway startup complete")

@gateway_app.get("/health")
async def gateway_health():
    """Gateway health check with service status"""
    return {
        "status": "healthy",
        "services": service_registry.health_status,
        "timestamp": datetime.now().isoformat()
    }

@gateway_app.get("/services")
async def list_services():
    """List all registered services and their status"""
    return {
        "services": {
            name: {
                "url": config["url"],
                "healthy": service_registry.health_status.get(name, False),
                "last_check": service_registry.last_health_check.get(name)?.isoformat()
            }
            for name, config in SERVICE_REGISTRY.items()
        }
    }

# Route handlers for different services
async def proxy_request(request: Request, service: str, path: str):
    """Generic request proxy to microservices"""
    # Verify authentication for protected routes
    if service != "auth" and not path.startswith("/health"):
        token = request.headers.get("authorization")
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Verify token with auth service
        try:
            await service_registry.route_request("auth", "/verify", "POST", 
                                               {"authorization": token})
        except:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get request body
    body = await request.body()
    headers = dict(request.headers)
    
    # Route to service
    return await service_registry.route_request(service, path, request.method, headers, body)

# Service routes
@gateway_app.api_route("/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def auth_proxy(request: Request, path: str):
    return await proxy_request(request, "auth", f"/{path}")

@gateway_app.api_route("/attendance/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def attendance_proxy(request: Request, path: str):
    return await proxy_request(request, "attendance", f"/{path}")

@gateway_app.api_route("/employees/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def employees_proxy(request: Request, path: str):
    return await proxy_request(request, "employees", f"/{path}")

@gateway_app.api_route("/dashboard/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def dashboard_proxy(request: Request, path: str):
    return await proxy_request(request, "dashboard", f"/{path}")

@gateway_app.api_route("/notifications/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def notifications_proxy(request: Request, path: str):
    return await proxy_request(request, "notifications", f"/{path}")

@gateway_app.api_route("/analytics/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def analytics_proxy(request: Request, path: str):
    return await proxy_request(request, "analytics", f"/{path}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(gateway_app, host="0.0.0.0", port=8000)
