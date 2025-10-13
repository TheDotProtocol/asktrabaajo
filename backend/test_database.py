import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.models.database import engine, Base, User, Profile, TestResult, Job, Application, Interview, Payment, AuditLog

def test_database():
    try:
        print("Testing database connection...")
        
        # Test connection
        with engine.connect() as connection:
            print("✅ Database connection successful!")
            
        # Create tables
        print("Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        
        # Verify tables exist
        with engine.connect() as connection:
            result = connection.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [row[0] for row in result]
            print(f"✅ Tables found: {tables}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database() 