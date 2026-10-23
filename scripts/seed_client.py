import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.security import generate_client_credentials
from app.models.base import SessionLocal
from app.repositories.client_repo import ClientRepository


def seed_client(client_code: str, display_name: str):
    db = SessionLocal()
    try:
        existing = ClientRepository.get_by_code(db, client_code)
        if existing:
            print(f"[INFO] Client '{client_code}' already exists with ID: {existing.id}")
            return existing

        client = ClientRepository.create_client(db, client_code=client_code, display_name=display_name)
        key_id, plaintext_secret, secret_hash = generate_client_credentials(is_test=True)
        ClientRepository.create_credential(db, client_id=client.id, key_id=key_id, secret_hash=secret_hash)

        print("\n=======================================================")
        print(f"  CLIENT APPLICATION REGISTERED: {display_name}")
        print("=======================================================")
        print(f"Client ID:       {client.id}")
        print(f"Client Code:     {client.client_code}")
        print(f"API Key ID:      {key_id}")
        print(f"API Secret:      {plaintext_secret}")
        print("=======================================================")
        print("IMPORTANT: Store API Secret safely; it will not be displayed again.\n")
        return client
    finally:
        db.close()


if __name__ == "__main__":
    code = sys.argv[1] if len(sys.argv) > 1 else "aiaic-farm-to-retail"
    name = sys.argv[2] if len(sys.argv) > 2 else "AIAIC Farm to Retail"
    seed_client(code, name)
