from sqlalchemy import create_engine, text
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from parent directory (project root)
env_path = Path(__file__).parent.parent / '.env'
print(f"Loading .env from: {env_path}")
print(f".env exists: {env_path.exists()}")
load_dotenv(dotenv_path=env_path)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Debug prints
print(f"DB_HOST: {DB_HOST}")
print(f"DB_PORT: {DB_PORT}")
print(f"DB_NAME: {DB_NAME}")
print(f"DB_USER: {DB_USER}")
print(f"DB_PASSWORD: {'*' * len(DB_PASSWORD) if DB_PASSWORD else 'None'}")

if DB_PASSWORD:
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)

def test_db():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("DB Connected:", result.fetchone())

if __name__ == "__main__":
    test_db()