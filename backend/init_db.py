from sqlmodel import SQLModel, create_engine, Session, text
from backend.config import settings
from backend.models import user, material, segment, job, push_record
import subprocess
import sys

def init_db():
    engine = create_engine(settings.DATABASE_URL)
    
    # 1. Create all tables if they don't exist
    # SQLModel's create_all is idempotent (won't error if table exists)
    print("Creating tables (if not exists)...")
    SQLModel.metadata.create_all(engine)
    
    # 2. Check if alembic_version table exists
    with Session(engine) as session:
        result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"))
        exists = result.fetchone()
    
    if not exists:
        print("Alembic version table missing. Stamping to head...")
        # Stamp the database to the latest migration version
        try:
            subprocess.run(["alembic", "stamp", "head"], check=True)
            print("Successfully stamped to head.")
        except Exception as e:
            print(f"Error stamping to head: {e}")
            # If stamp fails, maybe alembic isn't in path, but usually it is in the container
    else:
        print("Alembic version table exists. Running migrations...")
        try:
            subprocess.run(["alembic", "upgrade", "head"], check=True)
            print("Successfully upgraded to head.")
        except Exception as e:
            print(f"Error upgrading database: {e}")

if __name__ == "__main__":
    init_db()
