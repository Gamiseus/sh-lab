import os
import logging
from sqlmodel import create_engine, SQLModel, Session, select
from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

# Create database engine
# echo=True logs all SQL queries — only enable in development
engine = create_engine(settings.DATABASE_URL, echo=os.getenv("SQL_ECHO", "").lower() == "true")

# Columns added after initial schema creation. create_all() never alters existing
# tables, so new columns are added here idempotently.
_COLUMN_MIGRATIONS = [
    "ALTER TABLE game ADD COLUMN IF NOT EXISTS achievements JSONB",
    "ALTER TABLE game ADD COLUMN IF NOT EXISTS steam_review_desc VARCHAR",
    "ALTER TABLE game ADD COLUMN IF NOT EXISTS steam_reviews_updated_at TIMESTAMP WITH TIME ZONE",
]

def _apply_column_migrations():
    from sqlalchemy import text
    with engine.begin() as conn:
        for stmt in _COLUMN_MIGRATIONS:
            try:
                conn.execute(text(stmt))
            except Exception as e:
                logger.warning(f"Column migration failed ({stmt}): {e}")

def init_db():
    """Create database tables and auto-initialize first-time setup / admin account."""
    from app import models
    from app.models.user import User
    from app.models.config import SystemConfig
    from app.core.security import hash_password, verify_password

    SQLModel.metadata.create_all(engine)
    _apply_column_migrations()

    if not settings.AUTO_CREATE_ADMIN:
        return

    with Session(engine) as session:
        # Check for existing admin
        admin = session.exec(select(User).where(User.is_admin == True)).first()
        target_user = session.exec(select(User).where(User.username == settings.ADMIN_USERNAME)).first()

        if not admin:
            if target_user:
                target_user.is_admin = True
                target_user.is_active = True
                target_user.password_hash = hash_password(settings.ADMIN_PASSWORD)
                session.add(target_user)
                logger.info(f"Promoted user '{settings.ADMIN_USERNAME}' to admin and set password from ADMIN_PASSWORD.")
            else:
                new_admin = User(
                    username=settings.ADMIN_USERNAME,
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                    email=settings.ADMIN_EMAIL,
                    display_name="Administrator",
                    is_admin=True,
                    is_active=True
                )
                session.add(new_admin)
                logger.info(f"Initialized first-time setup: created admin user '{settings.ADMIN_USERNAME}'.")
        else:
            # If the configured admin user exists and is an admin, ensure its password matches ADMIN_PASSWORD
            if target_user and target_user.is_admin:
                if not verify_password(settings.ADMIN_PASSWORD, target_user.password_hash):
                    target_user.password_hash = hash_password(settings.ADMIN_PASSWORD)
                    session.add(target_user)
                    logger.info(f"Synced admin '{settings.ADMIN_USERNAME}' password with ADMIN_PASSWORD setting.")
                if not target_user.is_active:
                    target_user.is_active = True
                    session.add(target_user)

        # Mark setup_complete in SystemConfig
        setup_cfg = session.get(SystemConfig, "setup_complete")
        if not setup_cfg:
            session.add(SystemConfig(
                key="setup_complete",
                value="true",
                value_type="bool",
                description="First-run setup completed"
            ))
        elif setup_cfg.value.lower() != "true":
            setup_cfg.value = "true"
            session.add(setup_cfg)

        # Seed Steam settings from environment variables if present
        if settings.STEAM_WEB_API_KEY:
            key_cfg = session.get(SystemConfig, "steam_api_key")
            if not key_cfg:
                session.add(SystemConfig(
                    key="steam_api_key",
                    value=settings.STEAM_WEB_API_KEY,
                    value_type="string",
                    description="Steam Web API Key",
                    is_secret=True
                ))
            elif not key_cfg.value:
                key_cfg.value = settings.STEAM_WEB_API_KEY
                session.add(key_cfg)

        if settings.STEAM_USERNAME:
            user_cfg = session.get(SystemConfig, "steam_username")
            if not user_cfg:
                session.add(SystemConfig(
                    key="steam_username",
                    value=settings.STEAM_USERNAME,
                    value_type="string",
                    description="Steam account username",
                    is_secret=False
                ))
            elif not user_cfg.value:
                user_cfg.value = settings.STEAM_USERNAME
                session.add(user_cfg)

        if settings.STEAM_PASSWORD:
            pass_cfg = session.get(SystemConfig, "steam_password")
            if not pass_cfg:
                session.add(SystemConfig(
                    key="steam_password",
                    value=settings.STEAM_PASSWORD,
                    value_type="string",
                    description="Steam account password",
                    is_secret=True
                ))
            elif not pass_cfg.value:
                pass_cfg.value = settings.STEAM_PASSWORD
                session.add(pass_cfg)

        session.commit()

def get_session():
    """Dependency to get a DB session"""
    with Session(engine) as session:
        yield session
