from sqlalchemy import text
from app.core.db import engine

def migrate_tags():
    print("Migrating news_posts tags column...")
    with engine.connect() as conn:
        # Add tags column as ARRAY of TEXT
        conn.execute(text("ALTER TABLE news_posts ADD COLUMN IF NOT EXISTS tags TEXT[];"))
        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_tags()
