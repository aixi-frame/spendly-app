import pytest
from app import app as flask_app
from database.db import init_db, get_db
from database import queries
import sqlite3
import os

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-key'

    # Create a temporary database for testing
    import database.db as db
    db.DB_PATH = "test_spendly.db"
    init_db()

    with flask_app.test_client() as client:
        yield client

    # Cleanup
    if os.path.exists("test_spendly.db"):
        os.remove("test_spendly.db")

@pytest.fixture
def auth_client(client):
    # Create a test user
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Test User", "test@example.com", "hashed_password")
        )
        user_id = cursor.lastrowid
        conn.commit()

    # Log in the user
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    return client, user_id

def test_insert_expense_valid(auth_client):
    client, user_id = auth_client
    amount = 50.0
    category = "Food"
    date = "2026-03-20"
    description = "Lunch"

    expense_id = queries.insert_expense(user_id, amount, category, date, description)
    assert expense_id is not None

    with get_db() as conn:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        assert row is not None
        assert row["amount"] == amount
        assert row["category"] == category
        assert row["date"] == date
        assert row["description"] == description

def test_insert_expense_no_description(auth_client):
    client, user_id = auth_client
    amount = 25.0
    category = "Transport"
    date = "2026-03-21"
    description = ""

    expense_id = queries.insert_expense(user_id, amount, category, date, description)
    assert expense_id is not None

    with get_db() as conn:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        assert row["description"] is None

def test_add_expense_get_unauthenticated(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert "/login" in response.location

def test_add_expense_get_authenticated(auth_client):
    client, user_id = auth_client
    response = client.get("/expenses/add")
    assert response.status_code == 200
    assert b'amount' in response.data
    assert b'category' in response.data
    assert b'Food' in response.data
    assert b'Transport' in response.data
    assert b'Bills' in response.data
    assert b'Health' in response.data
    assert b'Entertainment' in response.data
    assert b'Shopping' in response.data
    assert b'Other' in response.data
    assert b'method="POST"' in response.data

def test_add_expense_post_unauthenticated(client):
    response = client.post("/expenses/add", data={})
    assert response.status_code == 302
    assert "/login" in response.location

def test_add_expense_post_valid(auth_client):
    client, user_id = auth_client
    data = {
        "amount": "50.0",
        "category": "Food",
        "date": "2026-03-20",
        "description": "Lunch"
    }
    response = client.post("/expenses/add", data=data, follow_redirects=False)
    assert response.status_code == 302
    assert "/profile" in response.location

    with get_db() as conn:
        row = conn.execute("SELECT * FROM expenses WHERE user_id = ? AND amount = ? AND category = ? AND date = ?",
                           (user_id, 50.0, "Food", "2026-03-20")).fetchone()
        assert row is not None

def test_add_expense_post_missing_amount(auth_client):
    client, user_id = auth_client
    data = {
        "amount": "",
        "category": "Food",
        "date": "2026-03-20",
        "description": "Lunch"
    }
    response = client.post("/expenses/add", data=data)
    assert response.status_code == 200
    assert b"Please enter a valid positive amount" in response.data

def test_add_expense_post_zero_amount(auth_client):
    client, user_id = auth_client
    data = {
        "amount": "0",
        "category": "Food",
        "date": "2026-03-20",
        "description": "Lunch"
    }
    response = client.post("/expenses/add", data=data)
    assert response.status_code == 200
    assert b"Please enter a valid positive amount" in response.data

def test_add_expense_post_invalid_category(auth_client):
    client, user_id = auth_client
    data = {
        "amount": "50.0",
        "category": "InvalidCat",
        "date": "2026-03-20",
        "description": "Lunch"
    }
    response = client.post("/expenses/add", data=data)
    assert response.status_code == 200
    assert b"Please select a valid category" in response.data

def test_add_expense_post_invalid_date(auth_client):
    client, user_id = auth_client
    data = {
        "amount": "50.0",
        "category": "Food",
        "date": "not-a-date",
        "description": "Lunch"
    }
    response = client.post("/expenses/add", data=data)
    assert response.status_code == 200
    assert b"Invalid date format" in response.data

def test_add_expense_post_no_description(auth_client):
    client, user_id = auth_client
    data = {
        "amount": "50.0",
        "category": "Food",
        "date": "2026-03-20",
        "description": ""
    }
    response = client.post("/expenses/add", data=data, follow_redirects=False)
    assert response.status_code == 302
    assert "/profile" in response.location

    with get_db() as conn:
        row = conn.execute("SELECT * FROM expenses WHERE user_id = ? AND amount = ? AND category = ? AND date = ?",
                           (user_id, 50.0, "Food", "2026-03-20")).fetchone()
        assert row is not None
        assert row["description"] is None
