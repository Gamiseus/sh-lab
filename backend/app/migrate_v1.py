from sqlalchemy import text
from app.core.db import engine

def migrate():
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE game ADD COLUMN IF NOT EXISTS igdb_id INTEGER;"))
        conn.execute(text("ALTER TABLE game ADD COLUMN IF NOT EXISTS summary TEXT;"))
        conn.execute(text("ALTER TABLE game ADD COLUMN IF NOT EXISTS rating FLOAT;"))
        conn.execute(text("ALTER TABLE game ADD COLUMN IF NOT EXISTS cover_url TEXT;"))
        conn.execute(text("ALTER TABLE game ADD COLUMN IF NOT EXISTS background_url TEXT;"))
        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
