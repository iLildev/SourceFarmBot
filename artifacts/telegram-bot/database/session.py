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
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
    connect_args=DB_CONNECT_ARGS,
)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── Versioned migrations ───────────────────────────────────────────────────────
# Each entry: (version_int, sql_statement)
# Never remove or reorder existing entries — only append new ones.
_MIGRATIONS: list[tuple[int, str]] = [
    (1,  "ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by    BIGINT    DEFAULT NULL"),
    (2,  "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen       TIMESTAMP DEFAULT NULL"),
    (3,  "ALTER TABLE users ADD COLUMN IF NOT EXISTS free_installs   INTEGER   DEFAULT 0"),
    (4,  "ALTER TABLE users ADD COLUMN IF NOT EXISTS discount_pct    INTEGER   DEFAULT 0"),
    (5,  "CREATE INDEX IF NOT EXISTS ix_users_referred_by ON users (referred_by)"),
    (6,  "CREATE INDEX IF NOT EXISTS ix_users_last_seen   ON users (last_seen)"),
    (7,  "ALTER TABLE bots ADD COLUMN IF NOT EXISTS username   VARCHAR(64) DEFAULT NULL"),
    (8,  "ALTER TABLE bots ADD COLUMN IF NOT EXISTS bot_config TEXT        DEFAULT NULL"),
    (9,  """CREATE TABLE IF NOT EXISTS rate_limit_blocks (
                user_id       BIGINT  PRIMARY KEY,
                blocked_until DOUBLE PRECISION NOT NULL
            )"""),
]


async def init_db() -> None:
    async with engine.begin() as conn:
        # Create all ORM-defined tables (safe — skips existing)
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

        # Bootstrap version-tracking table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version    INTEGER   PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT now()
            )
        """))

        result  = await conn.execute(text("SELECT version FROM schema_migrations"))
        applied = {row[0] for row in result.fetchall()}

        new_migrations = 0
        for version, sql in _MIGRATIONS:
            if version not in applied:
                await conn.execute(text(sql))
                await conn.execute(
                    text("INSERT INTO schema_migrations (version) VALUES (:v)"),
                    {"v": version},
                )
                new_migrations += 1

    if new_migrations:
        logger.info("Applied %d new migration(s).", new_migrations)
    logger.info("Database ready.")


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
