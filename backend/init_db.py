from api.models.database import create_tables, engine

if __name__ == "__main__":
    print("Creating database tables...")
    create_tables()
    print("Database tables created successfully!") 