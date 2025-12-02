import logging
from logging.config import fileConfig

from flask import current_app
from alembic import context

# Alembic Config object
config = context.config

# Setup logging from alembic.ini
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


# --------------------------------------------------------
# GET SQLALCHEMY ENGINE (support for SQLAlchemy 1.4 + 2.0)
# --------------------------------------------------------
def get_engine():
    """Unified engine getter for Flask-SQLAlchemy <3 and >=3."""
    try:
        # Flask-SQLAlchemy < 3
        return current_app.extensions['migrate'].db.get_engine()
    except Exception:
        # Flask-SQLAlchemy 3+
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace("%", "%%")
    except Exception:
        return str(get_engine().url).replace("%", "%%")


# Inject the DB URL from Flask config
config.set_main_option("sqlalchemy.url", get_engine_url())

target_db = current_app.extensions['migrate'].db


# --------------------------------------------------------
# Target metadata from Flask-Migrate
# --------------------------------------------------------
def get_metadata():
    """Support Flask-Migrate metadatas API."""
    if hasattr(target_db, "metadatas"):
        return target_db.metadatas[None]
    return target_db.metadata


# --------------------------------------------------------
# OFFLINE MODE
# --------------------------------------------------------
def run_migrations_offline():
    """Run migrations without engine (offline mode)."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# --------------------------------------------------------
# ONLINE MODE
# --------------------------------------------------------
def run_migrations_online():
    """Run migrations with engine (online mode)."""

    # Prevent empty migrations
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    conf_args = current_app.extensions["migrate"].configure_args

    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            compare_type=True,       # detect type changes automatically
            compare_server_default=True,
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


# --------------------------------------------------------
# MODE SWITCH
# --------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
