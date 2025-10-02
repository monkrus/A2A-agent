"""
Tests for production agent
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from agent_production import app
from database import Base, TaskRepository, CartMandateRepository, PaymentMandateRepository
from config import PRICING

# Test database
TEST_DATABASE_URL = "sqlite:///./test_agent.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test client
client = TestClient(app)


def setup_module():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)


def teardown_module():
    """Cleanup test database"""
    Base.metadata.drop_all(bind=engine)


def test_agent_discovery():
    """Test agent discovery endpoint"""
    response = client.get("/.well-known/agent.json")
    assert response.status_code == 200

    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "skills" in data
    assert "ap2" in data
    assert data["ap2"]["supported"] is True


def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "ap2_enabled" in data
    assert data["ap2_enabled"] is True


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert "agent" in data
    assert "services" in data
    assert len(data["services"]) > 0


def test_create_intent_mandate():
    """Test intent mandate creation"""
    payload = {
        "jsonrpc": "2.0",
        "method": "createIntentMandate",
        "params": {
            "description": "I need business analysis",
            "skillId": "business-analysis"
        },
        "id": "test-1"
    }

    response = client.post("/a2a", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "result" in data
    assert data["result"]["success"] is True
    assert "intent_mandate" in data["result"]


def test_create_cart_mandate():
    """Test cart mandate creation"""
    payload = {
        "jsonrpc": "2.0",
        "method": "createCartMandate",
        "params": {
            "skillId": "quick-consult",
            "taskDescription": "Help me with pricing strategy"
        },
        "id": "test-2"
    }

    response = client.post("/a2a", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "result" in data
    assert data["result"]["success"] is True
    assert "cart_id" in data["result"]
    assert "cart_mandate" in data["result"]


def test_submit_task_without_payment():
    """Test task submission without payment"""
    payload = {
        "jsonrpc": "2.0",
        "method": "submitTask",
        "params": {
            "skillId": "business-analysis",
            "message": {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": "Analyze my startup idea"
                    }
                ]
            }
        },
        "id": "test-3"
    }

    response = client.post("/a2a", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "result" in data
    assert data["result"]["status"] == "payment_required"
    assert "next_steps" in data["result"]


def test_invalid_skill():
    """Test with invalid skill ID"""
    payload = {
        "jsonrpc": "2.0",
        "method": "submitTask",
        "params": {
            "skillId": "invalid-skill",
            "message": {
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": "Test"
                    }
                ]
            }
        },
        "id": "test-4"
    }

    response = client.post("/a2a", json=payload)
    assert response.status_code != 200


def test_invalid_method():
    """Test with invalid method"""
    payload = {
        "jsonrpc": "2.0",
        "method": "invalidMethod",
        "params": {},
        "id": "test-5"
    }

    response = client.post("/a2a", json=payload)
    data = response.json()
    assert "error" in data


def test_get_task_status_not_found():
    """Test getting status of non-existent task"""
    payload = {
        "jsonrpc": "2.0",
        "method": "getTaskStatus",
        "params": {
            "taskId": "non-existent-task"
        },
        "id": "test-6"
    }

    response = client.post("/a2a", json=payload)
    assert response.status_code != 200


def test_database_task_repository():
    """Test task repository operations"""
    db = TestSessionLocal()
    repo = TaskRepository(db)

    # Create task
    task_data = {
        "id": "test-task-1",
        "skill_id": "business-analysis",
        "status": "pending",
        "price": 50.0,
        "currency": "USD",
        "payment_status": "pending"
    }

    task = repo.create(task_data)
    assert task.id == "test-task-1"
    assert task.status == "pending"

    # Get task
    retrieved_task = repo.get("test-task-1")
    assert retrieved_task is not None
    assert retrieved_task.skill_id == "business-analysis"

    # Update task
    updated_task = repo.update("test-task-1", {"status": "completed"})
    assert updated_task.status == "completed"

    db.close()


def test_all_pricing_skills():
    """Test that all pricing skills are valid"""
    for skill_id, details in PRICING.items():
        assert "price" in details
        assert "description" in details
        assert isinstance(details["price"], (int, float))
        assert isinstance(details["description"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
