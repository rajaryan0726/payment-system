from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.client import ClientApplication, ClientCredential


class ClientRepository:
    @staticmethod
    def get_by_code(db: Session, client_code: str) -> Optional[ClientApplication]:
        return db.query(ClientApplication).filter(ClientApplication.client_code == client_code).first()

    @staticmethod
    def get_by_id(db: Session, client_id: str) -> Optional[ClientApplication]:
        return db.query(ClientApplication).filter(ClientApplication.id == client_id).first()

    @staticmethod
    def get_credential_by_key_id(db: Session, key_id: str) -> Optional[ClientCredential]:
        return db.query(ClientCredential).filter(ClientCredential.key_id == key_id).first()

    @staticmethod
    def create_client(db: Session, client_code: str, display_name: str) -> ClientApplication:
        client = ClientApplication(client_code=client_code, display_name=display_name, status="ACTIVE")
        db.add(client)
        db.commit()
        db.refresh(client)
        return client

    @staticmethod
    def create_credential(
        db: Session, client_id: str, key_id: str, secret_hash: str
    ) -> ClientCredential:
        cred = ClientCredential(
            client_application_id=client_id,
            key_id=key_id,
            secret_hash=secret_hash,
            status="ACTIVE",
        )
        db.add(cred)
        db.commit()
        db.refresh(cred)
        return cred

    @staticmethod
    def update_last_used(db: Session, credential_id: str) -> None:
        db.query(ClientCredential).filter(ClientCredential.id == credential_id).update(
            {"last_used_at": datetime.now(timezone.utc)}
        )
        db.commit()
