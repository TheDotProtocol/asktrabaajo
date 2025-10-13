import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.models.database import Base, get_db
from main import app
import json

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

class TestAPI:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        # Create test user
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "testpass123",
            "role": "employer"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "features" in data

    def test_jobs_endpoints(self):
        """Test job-related endpoints"""
        # Create a job
        job_data = {
            "title": "Software Engineer",
            "description": "We are looking for a talented software engineer",
            "requirements": {"skills": ["Python", "JavaScript"]},
            "salary_range": {"min": 80000, "max": 120000},
            "location": "San Francisco",
            "remote_allowed": True,
            "job_type": "full_time"
        }
        
        response = client.post("/api/jobs/", json=job_data, headers=self.headers)
        assert response.status_code == 201
        job_id = response.json()["id"]
        
        # Get jobs
        response = client.get("/api/jobs/", headers=self.headers)
        assert response.status_code == 200
        assert len(response.json()) > 0
        
        # Get specific job
        response = client.get(f"/api/jobs/{job_id}", headers=self.headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Software Engineer"

    def test_profile_endpoints(self):
        """Test profile-related endpoints"""
        # Create profile
        profile_data = {
            "phone": "+1234567890",
            "location": "New York",
            "bio": "Experienced professional",
            "skills": {"Python": "Advanced", "JavaScript": "Intermediate"}
        }
        
        response = client.post("/api/users/profile", json=profile_data, headers=self.headers)
        assert response.status_code == 200
        
        # Get profile
        response = client.get("/api/users/profile", headers=self.headers)
        assert response.status_code == 200
        assert response.json()["phone"] == "+1234567890"

    def test_assessment_endpoints(self):
        """Test assessment-related endpoints"""
        # Get questions
        response = client.get("/api/tests/questions", headers=self.headers)
        assert response.status_code == 200
        questions = response.json()
        assert len(questions) > 0
        
        # Submit test
        answers = {str(q["id"]): "option_a" for q in questions}
        test_data = {"answers": answers}
        
        response = client.post("/api/tests/submit", json=test_data, headers=self.headers)
        assert response.status_code == 200
        result = response.json()
        assert "score" in result

    def test_notifications_endpoints(self):
        """Test notification endpoints"""
        # Get notifications
        response = client.get("/api/notifications/", headers=self.headers)
        assert response.status_code == 200
        
        # Get unread count
        response = client.get("/api/notifications/unread-count", headers=self.headers)
        assert response.status_code == 200
        assert "unread_count" in response.json()

    def test_documents_endpoints(self):
        """Test document endpoints"""
        # Get supported document types
        response = client.get("/api/documents/types/supported", headers=self.headers)
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_compliance_endpoints(self):
        """Test compliance endpoints"""
        # Get supported compliance types
        response = client.get("/api/compliance/types/supported", headers=self.headers)
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_currencies_endpoints(self):
        """Test currency endpoints"""
        # Get supported currencies
        response = client.get("/api/currencies/supported/list", headers=self.headers)
        assert response.status_code == 200
        currencies = response.json()
        assert len(currencies) > 0
        
        # Test currency conversion
        conversion_data = {
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "EUR"
        }
        response = client.post("/api/currencies/convert", json=conversion_data, headers=self.headers)
        assert response.status_code == 200
        result = response.json()
        assert "converted_amount" in result

    def test_ai_endpoints(self):
        """Test AI endpoints"""
        # Test AI suggestions
        response = client.get("/api/ai/suggestions", headers=self.headers)
        assert response.status_code == 200
        
        # Test AI scoring
        scoring_data = {
            "question": "What is your experience with Python?",
            "answer": "I have 5 years of experience with Python",
            "context": "Software engineering position"
        }
        response = client.post("/api/ai/score", json=scoring_data, headers=self.headers)
        assert response.status_code == 200
        result = response.json()
        assert "score" in result

    def test_dashboard_stats(self):
        """Test dashboard statistics"""
        response = client.get("/api/users/dashboard-stats", headers=self.headers)
        assert response.status_code == 200
        stats = response.json()
        assert "jobs" in stats
        assert "applications" in stats
        assert "interviews" in stats
        assert "assessments" in stats

    def test_protected_endpoints_without_token(self):
        """Test protected endpoints without authentication"""
        endpoints = [
            "/api/users/profile",
            "/api/jobs/",
            "/api/tests/questions",
            "/api/notifications/",
            "/api/documents/types/supported",
            "/api/compliance/types/supported",
            "/api/currencies/supported/list",
            "/api/ai/suggestions"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401

    def test_invalid_endpoints(self):
        """Test invalid endpoints"""
        response = client.get("/api/invalid-endpoint")
        assert response.status_code == 404

    def test_cors_headers(self):
        """Test CORS headers"""
        response = client.options("/api/auth/register")
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_rate_limiting(self):
        """Test rate limiting (basic implementation)"""
        # Make multiple requests to test rate limiting
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_error_handling(self):
        """Test error handling"""
        # Test with invalid JSON
        response = client.post("/api/auth/register", data="invalid json")
        assert response.status_code == 422
        
        # Test with missing required fields
        response = client.post("/api/auth/register", json={"email": "test@example.com"})
        assert response.status_code == 422 