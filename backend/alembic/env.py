import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import create_engine
from alembic import context

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import your Base and settings
from app.core.database import Base
from app.core.config import settings

# Import your models (only the ones that exist)
from app.models import *

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Create sync database URL (replace asyncpg with psycopg2)
sync_url = settings.SQLALCHEMY_DATABASE_URI.replace(
    "postgresql+asyncpg://", 
    "postgresql+psycopg2://"
)
config.set_main_option("sqlalchemy.url", sync_url)

# Set target metadata
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode (synchronous)."""
    # Create sync engine
    connectable = create_engine(config.get_main_option("sqlalchemy.url"))
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()