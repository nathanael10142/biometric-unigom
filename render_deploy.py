#!/usr/bin/env python
"""
Render deployment script for UNIGOM Biometric System
Initializes database and runs migrations
"""

import os
import sys
import logging
from sqlalchemy import text, inspect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database tables and schema"""
    try:
        from app.database import local_engine
        from app.database import LocalBase
        from app.models.agent_cache import AgentCache
        from app.models.attendance import Attendance
        from app.models.scan_log import ScanLog
        from app.models.login_attempt import LoginAttempt
        from app.models.sync_cursor import SyncCursor
        
        logger.info("Creating database tables...")
        
        # Create all tables defined in LocalBase
        LocalBase.metadata.create_all(bind=local_engine)
        
        logger.info("✅ Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

def run_migrations():
    """Run Alembic migrations if available"""
    try:
        from alembic.config import Config
        from alembic.command import upgrade
        
        logger.info("Running Alembic migrations...")
        alembic_cfg = Config("alembic.ini")
        upgrade(alembic_cfg, "head")
        
        logger.info("✅ Migrations completed successfully")
        return True
        
    except ImportError:
        logger.warning("Alembic not available, skipping migrations")
        return True
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

def verify_connection():
    """Verify database connection"""
    try:
        from app.database import local_engine
        
        with local_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection verified")
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting UNIGOM deployment initialization...")
    
    # Verify connection first
    if not verify_connection():
        logger.error("Cannot connect to database. Check your DATABASE_URL.")
        sys.exit(1)
    
    # Initialize database
    if not init_database():
        logger.error("Database initialization failed")
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        logger.error("Migrations failed")
        sys.exit(1)
    
    logger.info("✅ Deployment initialization completed successfully!")
    sys.exit(0)
