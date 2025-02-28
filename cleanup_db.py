import logging
from sqlalchemy import create_engine, text
from social_media_bot.database.models import Base
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_database():
    """Clean up database tables"""
    try:
        # Get database URLs
        main_db_url = os.getenv('DATABASE_URL')
        test_db_url = os.getenv('TEST_DATABASE_URL')
        
        # Clean main database
        if main_db_url:
            engine = create_engine(main_db_url)
            Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)
            engine.dispose()
            logger.info("Main database cleaned successfully")
            
        # Clean test database
        if test_db_url:
            test_engine = create_engine(test_db_url)
            Base.metadata.drop_all(test_engine)
            Base.metadata.create_all(test_engine)
            test_engine.dispose()
            logger.info("Test database cleaned successfully")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise

def cleanup_test_database():
    """Clean up test database"""
    try:
        test_db_url = os.getenv('TEST_DATABASE_URL')
        if test_db_url:
            engine = create_engine(test_db_url)
            Base.metadata.drop_all(engine)
            engine.dispose()
            logger.info("Test database cleaned successfully")
            
    except Exception as e:
        logger.error(f"Error cleaning test database: {str(e)}")
        raise

if __name__ == "__main__":
    cleanup_database() 