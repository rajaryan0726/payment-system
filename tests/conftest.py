import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.security import generate_client_credentials
from app.main import app
from app.models.base import Base, get_db
from app.models.client import ClientApplication, ClientCredential
from app.providers.base import PaymentProvider
from app.providers.factory import get_payment_provider
from app.models.payment import PaymentStatus

# In-memory SQLite engine for fast, isolated tests
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def registered_client_a(db_session: Session):
    client = ClientApplication(client_code="client-alpha", display_name="Client Alpha", status="ACTIVE")
    db_session.add(client)
    db_session.flush()

    key_id, secret, secret_hash = generate_client_credentials(is_test=True)
    cred = ClientCredential(
        client_application_id=client.id, key_id=key_id, secret_hash=secret_hash, status="ACTIVE"
    )
    db_session.add(cred)
    db_session.commit()
    db_session.refresh(client)
    return client, key_id, secret


@pytest.fixture
def registered_client_b(db_session: Session):
    client = ClientApplication(client_code="client-beta", display_name="Client Beta", status="ACTIVE")
    db_session.add(client)
    db_session.flush()

    key_id, secret, secret_hash = generate_client_credentials(is_test=True)
    cred = ClientCredential(
        client_application_id=client.id, key_id=key_id, secret_hash=secret_hash, status="ACTIVE"
    )
    db_session.add(cred)
    db_session.commit()
    db_session.refresh(client)
    return client, key_id, secret
