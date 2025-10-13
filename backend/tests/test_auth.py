import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models.database import Base, get_db
from main import app
import os

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def setup_module():
    Base.metadata.create_all(bind=engine)

def teardown_module():
    Base.metadata.drop_all(bind=engine)

class TestAuth:
    def test_register_user(self):
        """Test user registration"""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "testpass123",
            "role": "jobseeker"
        })
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_user(self):
        """Test user login"""
        # First register a user
        client.post("/api/auth/register", json={
            "email": "login@example.com",
            "password": "testpass123",
            "role": "employer"
        })
        
        # Then login
        response = client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "testpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_invalid_login(self):
        """Test invalid login credentials"""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_get_current_user(self):
        """Test getting current user with valid token"""
        # Register and login
        register_response = client.post("/api/auth/register", json={
            "email": "current@example.com",
            "password": "testpass123",
            "role": "consultant"
        })
        token = register_response.json()["access_token"]
        
        # Get current user
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "current@example.com"

    def test_invalid_token(self):
        """Test accessing protected endpoint with invalid token"""
        response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid_token"})
        assert response.status_code == 401

    def test_register_duplicate_email(self):
        """Test registering with duplicate email"""
        # Register first user
        client.post("/api/auth/register", json={
            "email": "duplicate@example.com",
            "password": "testpass123",
            "role": "jobseeker"
        })
        
        # Try to register with same email
        response = client.post("/api/auth/register", json={
            "email": "duplicate@example.com",
            "password": "testpass123",
            "role": "employer"
        })
        assert response.status_code == 400

    def test_invalid_role(self):
        """Test registering with invalid role"""
        response = client.post("/api/auth/register", json={
            "email": "invalid@example.com",
            "password": "testpass123",
            "role": "invalid_role"
        })
        assert response.status_code == 400

    def test_password_validation(self):
        """Test password validation"""
        response = client.post("/api/auth/register", json={
            "email": "short@example.com",
            "password": "123",
            "role": "jobseeker"
        })
        assert response.status_code == 400 