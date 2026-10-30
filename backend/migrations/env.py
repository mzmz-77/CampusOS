"""Migrations receive an existing connection; no credential files are read."""
from alembic import context

config = context.config
connection = config.attributes.get('connection')
if connection is None:
    raise RuntimeError('Use python -m app.migrate to configure the project database.')
context.configure(connection=connection, transactional_ddl=True)
with context.begin_transaction():
    context.run_migrations()
