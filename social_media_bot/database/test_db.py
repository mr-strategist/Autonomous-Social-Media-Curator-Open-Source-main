import os
import time
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import hashlib
from .init_db import init_database
from .db_manager import DatabaseManager
from .models import Base, ContentSource, PostHistory, ContentMetrics, SafetyLog
from .utils import safe_remove_db_file
import sqlite3

logger = logging.getLogger(__name__)

def test_database():
    """Test basic database functionality"""
    engine = None
    db = None
    try:
        # Initialize test database
        test_db_url = os.getenv('TEST_DATABASE_URL')
        if not test_db_url:
            raise ValueError("Test database URL not found in environment")
            
        engine = create_engine(test_db_url)
        
        # Drop all tables and recreate them
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        logger.info("Database tables created successfully")
        
        # Initialize database manager
        db = DatabaseManager(database_url=test_db_url)
        
        # Test adding content source
        source_data = {
            'url': 'https://test.com/article',
            'title': 'Test Article',
            'source_type': 'test',
            'category': 'technology',
            'raw_content': 'Test content for hash generation',
            'created_at': datetime.utcnow()
        }
        
        # Generate content hash
        content_hash = hashlib.md5(
            source_data['raw_content'].encode()
        ).hexdigest()
        source_data['content_hash'] = content_hash
        
        # Add content source using session
        with db.Session() as session:
            try:
                new_source = ContentSource(**source_data)
                session.add(new_source)
                session.commit()
                source_id = new_source.id
                logger.info(f"Added content source with ID: {source_id}")
            except Exception as e:
                session.rollback()
                raise Exception(f"Failed to add content source: {str(e)}")
            
        logger.info("Database test completed successfully")
        
    finally:
        cleanup_test_db()
        if db:
            db.close()
        if engine:
            engine.dispose()

def test_database_persistence():
    """Test database persistence and recovery"""
    engine = None
    db = None
    verify_engine = None
    try:
        test_db_path = os.path.join(os.getcwd(), 'data', 'test_social_media_bot.db')
        test_db_url = f'sqlite:///{test_db_path}'
        
        # Create fresh test database
        engine = create_engine(test_db_url)
        
        # Ensure clean state
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        logger.info("Created fresh test database for persistence test")
        
        # Initialize database manager
        db = DatabaseManager(database_url=test_db_url)
        
        # Add test data
        source_data = {
            'url': 'https://test.com/persistence',
            'title': 'Persistence Test',
            'source_type': 'test',
            'category': 'technology',
            'raw_content': 'Test content for persistence',
            'created_at': datetime.utcnow()
        }
        
        # Generate content hash
        content_hash = hashlib.md5(
            source_data['raw_content'].encode()
        ).hexdigest()
        source_data['content_hash'] = content_hash
        
        # Add content source using session
        with db.Session() as session:
            try:
                new_source = ContentSource(**source_data)
                session.add(new_source)
                session.commit()
                source_id = new_source.id
                logger.info(f"Added test data with ID: {source_id}")
            except Exception as e:
                session.rollback()
                raise Exception(f"Failed to add test data: {str(e)}")
        
        # Close all connections before verification
        engine.dispose()
        
        # Create new connection for verification
        verify_engine = create_engine(test_db_url)
        VerifySession = sessionmaker(bind=verify_engine)
        
        # Verify data persistence
        with VerifySession() as session:
            try:
                source = session.query(ContentSource).first()
                if not source:
                    raise Exception("No data found in database")
                if source.title != 'Persistence Test':
                    raise Exception(f"Unexpected title: {source.title}")
                logger.info("Data persistence verified successfully")
            except Exception as e:
                raise Exception(f"Data persistence verification failed: {str(e)}")
            finally:
                verify_engine.dispose()
            
        logger.info("Database persistence test completed successfully")
        
    finally:
        cleanup_test_db()
        if verify_engine:
            verify_engine.dispose()
        if db:
            db.close()
        if engine:
            engine.dispose()

def cleanup_test_db():
    """Force cleanup database connections"""
    try:
        # Close any existing connections
        if os.path.exists('data/test_social_media_bot.db'):
            time.sleep(1)  # Wait for any pending operations
            os.remove('data/test_social_media_bot.db')
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

if __name__ == '__main__':
    # Run both tests
    logger.info("Running database functionality tests...")
    test_database()
    
    logger.info("\nRunning database persistence tests...")
    test_database_persistence() 