import pytest
import os
import tempfile

# Add the project root to the path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import create_app
from models.customer import db as _db

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    app = create_app('testing')

    # Create a temporary directory for uploads
    upload_dir = app.config['UPLOAD_DIR']
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    with app.app_context():
        _db.create_all()

    yield app

    with app.app_context():
        _db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def db(app):
    """
    Fixture for providing a database session for each test function.
    This will roll back any changes made during the test.
    """
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()

        _db.session.begin_nested()

        yield _db

        transaction.rollback()
        connection.close()
        _db.session.remove()
