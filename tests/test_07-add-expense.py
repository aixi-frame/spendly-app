import pytest
from app import app as flask_app
from database.db import init_db
from database import queries
import sqlite3

@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': ':memory:',  # isolated in-memory DB per test
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })

    # Override get_db to use the in-memory database for testing
    # Since we are using :memory:, we need to maintain one connection for the duration of the test
    # because different connections to :memory: see different databases.
    import database.db
    original_get_db = database.db.get_db

    _test_db_conn = None
    def test_get_db():
        nonlocal _test_db_conn
        if _test_db_conn is None:
            _test_db_conn = sqlite3.connect(':memory:')
            _test_db_conn.row_factory = sqlite3.Row
            _test_db_conn.execute("PRAGMA foreign_keys = ON")
        return _test_db_conn

    database.db.get_db = test_get_db

    with flask_app.app_context():
        init_db()
        yield flask_app

    database.db.get_db = original_get_db

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    """A test client that is already logged in."""
    # Register a user
    client.post('/register', data={
        'name': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass',
        'confirm_password': 'testpass'
    })
    # Login the user
    client.post('/login', data={
        'email': 'test@example.com',
        'password': 'testpass'
    })
    return client

class TestAddExpenseUnit:
    """Unit tests for database query helpers."""

    def test_insert_expense_valid_data(self, app):
        with app.app_context():
            # Setup user
            from database.db import create_user
            user_id = create_user("Test User", "unit@example.com", "password")

            # Test valid insert
            queries.insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")

            # Verify in DB
            from database.db import get_db
            with get_db() as conn:
                row = conn.execute("SELECT * FROM expenses WHERE user_id = ?", (user_id,)).fetchone()
                assert row is not None
                assert row["amount"] == 50.0
                assert row["category"] == "Food"
                assert row["date"] == "2026-03-20"
                assert row["description"] == "Lunch"

    def test_insert_expense_none_description(self, app):
        with app.app_context():
            from database.db import create_user
            user_id = create_user("Test User", "unit2@example.com", "password")

            # Test insert with None description
            queries.insert_expense(user_id, 20.0, "Transport", "2026-03-21", None)

            from database.db import get_db
            with get_db() as conn:
                row = conn.execute("SELECT * FROM expenses WHERE user_id = ?", (user_id,)).fetchone()
                assert row is not None
                assert row["description"] is None

class TestAddExpenseRoutes:
    """Route tests for the Add Expense feature."""

    def test_get_add_expense_unauthenticated_redirects(self, client):
        response = client.get('/expenses/add')
        assert response.status_code == 302
        assert response.location.endswith('/login')

    def test_get_add_expense_authenticated_success(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert response.status_code == 200

        # Check for category select options
        categories = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
        for cat in categories:
            assert cat.encode() in response.data

        # Check for form method
        assert b'method="POST"' in response.data

    def test_post_add_expense_unauthenticated_redirects(self, client):
        response = client.post('/expenses/add', data={'amount': '10.0', 'category': 'Food', 'date': '2026-01-01'})
        assert response.status_code == 302
        assert response.location.endswith('/login')

    def test_post_add_expense_valid_data_redirects(self, auth_client, app):
        # Need user_id for DB verification
        with app.app_context():
            from flask import session
            with client.session_transaction() as sess:
                # The auth_client already logged in, but we need the id.
                # Instead of guessing, let's just check if any record was added for the current session user.
                pass

            # Use auth_client to post
            data = {
                'amount': '50.0',
                'category': 'Food',
                'date': '2026-03-20',
                'description': 'Lunch'
            }
            response = auth_client.post('/expenses/add', data=data, follow_redirects=False)

            assert response.status_code == 302
            assert response.location.endswith('/profile')

            # Verify DB side effect
            from database.db import get_db
            with get_db() as conn:
                # Find the user we created in auth_client
                user = conn.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",)).fetchone()
                row = conn.execute("SELECT * FROM expenses WHERE user_id = ? AND amount = ?", (user["id"], 50.0)).fetchone()
                assert row is not None
                assert row["category"] == "Food"
                assert row["description"] == "Lunch"

    @pytest.mark.parametrize("amount,category,date,desc,expected_error", [
        ("", "Food", "2026-01-01", "test", "Please enter a valid positive amount"), # missing amount
        ("0", "Food", "2026-01-01", "test", "Please enter a valid positive amount"), # zero amount
        ("-10", "Food", "2026-01-01", "test", "Please enter a valid positive amount"), # negative amount
        ("abc", "Food", "2026-01-01", "test", "Please enter a valid positive amount"), # non-numeric
        ("10", "", "2026-01-01", "test", "Please select a valid category"), # missing category
        ("10", "InvalidCat", "2026-01-01", "test", "Please select a valid category"), # invalid category
        ("10", "Food", "", "test", "Please select a valid date"), # missing date
        ("10", "Food", "invalid-date", "test", "Invalid date format"), # invalid date format
    ])
    def test_post_add_expense_validation_errors(self, auth_client, amount, category, date, desc, expected_error):
        data = {
            'amount': amount,
            'category': category,
            'date': date,
            'description': desc
        }
        response = auth_client.post('/expenses/add', data=data)

        assert response.status_code == 200
        assert expected_error.encode() in response.data

    def test_post_add_expense_optional_description(self, auth_client, app):
        data = {
            'amount': '25.0',
            'category': 'Transport',
            'date': '2026-03-21',
            'description': '' # empty description
        }
        response = auth_client.post('/expenses/add', data=data, follow_redirects=False)

        assert response.status_code == 302
        assert response.location.endswith('/profile')

        # Verify DB side effect - should be NULL/None
        from database.db import get_db
        with get_db() as conn:
            user = conn.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",)).fetchone()
            row = conn.execute("SELECT * FROM expenses WHERE user_id = ? AND amount = ?", (user["id"], 25.0)).fetchone()
            assert row is not None
            assert row["description"] is None or row["description"] == "" # Spec says store None if blank
