import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from api.models.database import DATABASE_URL

def debug_database():
    print(f"Database URL: {DATABASE_URL}")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        print("✅ Engine created successfully")
        
        # Test connection
        with engine.connect() as connection:
            print("✅ Connection successful")
            
            # Check if we can query
            result = connection.execute(text("SELECT 1"))
            print("✅ Query test successful")
            
            # Check existing tables
            result = connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
            tables = [row[0] for row in result]
            print(f"Current tables: {tables}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_database() 