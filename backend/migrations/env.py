# migrations/env.py
import sys
import os
from pathlib import Path

backend_path = str(Path(__file__).parent.parent)
if backend_path not in sys.path:
    sys.path.append(backend_path)

from app import app
from models import db, Photo, Dataset, Model

from logging.config import fileConfig
from alembic import context
from dotenv import load_dotenv

load_dotenv()

# Конфигурация Alembic
config = context.config
fileConfig(config.config_file_name)

# Устанавливаем target_metadata
target_metadata = db.metadata

def get_url():
    """Получаем URL базы данных из переменных окружения"""
    return f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    with app.app_context():
        connectable = db.engine
        
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True
            )

            with context.begin_transaction():
                context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()