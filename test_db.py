from dotenv import load_dotenv
from social_media_bot.database.init_db import init_database
from social_media_bot.database.test_db import test_database, test_database_persistence
from cleanup_db import cleanup_database, cleanup_test_database
import time
import sqlite3
from sqlalchemy import create_engine, text
import logging

logger = logging.getLogger(__name__)

def main():
    load_dotenv()
    
    try:
        print("Initializing database...")
        engine, Session = init_database(create_test=True)
        print("Database initialized!")

        print("\nRunning database tests...")
        test_database()
        time.sleep(2)  # Wait between tests
        
        print("\nTesting database persistence...")
        test_database_persistence()
        
        print("\nAll tests completed!")
        
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        raise
    finally:
        try:
            # Close all connections
            if 'engine' in locals() and engine:
                engine.dispose()
            
            # Force cleanup
            with create_engine('sqlite:///data/test_social_media_bot.db').connect() as conn:
                conn.execute(text('PRAGMA journal_mode = DELETE'))
                conn.commit()
            
            time.sleep(1)
            cleanup_test_database()
        except Exception as e:
            print(f"Error during final cleanup: {str(e)}")

def cleanup_test_db():
    """Force cleanup database connections"""
    try:
        # For PostgreSQL, we just need to close connections
        if 'engine' in locals():
            engine.dispose()
        if 'db' in locals() and db:
            db.close()
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    main() 