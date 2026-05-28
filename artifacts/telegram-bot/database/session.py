import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import DATABASE_URL, DB_CONNECT_ARGS
from database.models import Base

logger = logging.getLogger(__name__)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=DB_CONNECT_ARGS,
)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        # Create all new tables (skips existing ones)
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        # Idempotent column migrations for existing tables
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by    BIGINT    DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen       TIMESTAMP DEFAULT NULL",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS free_installs   INTEGER   DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS discount_pct    INTEGER   DEFAULT 0",
            "CREATE INDEX IF NOT EXISTS ix_users_referred_by ON users (referred_by)",
            "CREATE INDEX IF NOT EXISTS ix_users_last_seen   ON users (last_seen)",
            "ALTER TABLE bots ADD COLUMN IF NOT EXISTS username   VARCHAR(64) DEFAULT NULL",
            "ALTER TABLE bots ADD COLUMN IF NOT EXISTS bot_config TEXT        DEFAULT NULL",
        ]
        for sql in migrations:
            await conn.execute(text(sql))

    logger.info("Database tables created / verified.")


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
