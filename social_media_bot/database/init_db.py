import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from .models import Base, Post

logger = logging.getLogger(__name__)

def init_database(create_test: bool = False) -> tuple:
    """Initialize database and return engine and session factory"""
    try:
        # Determine database URL
        if create_test:
            database_url = os.getenv('TEST_DATABASE_URL')
        else:
            database_url = os.getenv('DATABASE_URL')
            
        if not database_url:
            raise ValueError("Database URL not found in environment variables")
        
        logger.info(f"Initializing database at: {database_url}")
        
        # Create engine with PostgreSQL-specific settings
        engine = create_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,
            echo=False
        )
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        # Create session factory
        Session = sessionmaker(bind=engine)
        
        return engine, Session
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def init_db(database_url: str):
    """Initialize database"""
    try:
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)  # This will create the new Post table
        logger.info(f"Initialized database at: {database_url}")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False