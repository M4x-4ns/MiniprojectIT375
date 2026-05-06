import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base

TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


from main import app, get_db  # noqa: E402
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app, follow_redirects=False)


def test_register_new_user():
    response = client.post("/auth/register", data={
        "username": "testuser",
        "email": "test@example.com",
        "password": "secret123",
    })
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def _register_and_login(username="alice", password="pass123"):
    client.post("/auth/register", data={
        "username": username,
        "email": f"{username}@test.com",
        "password": password,
    })
    resp = client.post("/auth/login", data={"username": username, "password": password})
    return resp.cookies


def test_dashboard_redirects_when_not_logged_in():
    response = client.get("/")
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_create_expense():
    cookies = _register_and_login()
    response = client.post("/expenses", data={
        "title": "ค่าข้าว",
        "amount": "150",
        "type": "expense",
        "category": "food",
        "date": "2026-05-06",
        "note": "",
    }, cookies=cookies)
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_delete_expense():
    cookies = _register_and_login()
    client.post("/expenses", data={
        "title": "เงินเดือน", "amount": "15000",
        "type": "income", "category": "salary",
        "date": "2026-05-01", "note": "",
    }, cookies=cookies)
    response = client.post("/expenses/1/delete", cookies=cookies)
    assert response.status_code == 303


def test_admin_users_blocked_for_regular_user():
    cookies = _register_and_login("bob", "pass123")
    response = client.get("/admin/users", cookies=cookies)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
