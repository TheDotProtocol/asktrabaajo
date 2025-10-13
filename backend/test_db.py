import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from api.models.database import create_tables
    print("✅ Database module imported successfully")
    
    create_tables()
    print("✅ Database tables created successfully")
    
    print("✅ Backend setup is working!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc() 