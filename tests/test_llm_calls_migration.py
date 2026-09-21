"""Exercise the new migration against a disposable old-schema database."""
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_usage_backfill_and_downgrade():
    path = Path(__file__).parents[1] / "alembic/versions/e62c91a740bd_move_usage_to_llm_calls.py"
    spec = importlib.util.spec_from_file_location("usage_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with sa.create_engine("sqlite://").begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.exec_driver_sql("CREATE TABLE conversations (id CHAR(32) PRIMARY KEY, model_type TEXT)")
        connection.exec_driver_sql("""CREATE TABLE messages (
            id CHAR(32) PRIMARY KEY, conversation_id CHAR(32),
            prompt_tokens INTEGER, response_tokens INTEGER, total_tokens INTEGER,
            input_cost NUMERIC, output_cost NUMERIC, total_cost NUMERIC,
            is_success BOOLEAN, created_at DATETIME, ttft FLOAT, total_time FLOAT)
        """)
        connection.exec_driver_sql("INSERT INTO conversations VALUES ('c', 'old-model')")
        connection.exec_driver_sql("""INSERT INTO messages VALUES
            ('m', 'c', 309, 75, 384, 0.00004635, 0.000045, 0.00009135, 1, '2026-09-21', 0.1, 0.3),
            ('unknown', 'c', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '2026-09-21', NULL, NULL)
        """)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            row = connection.exec_driver_sql("SELECT * FROM llm_calls").mappings().one()
            assert row["message_id"] == 'm'
            assert row["conversation_id"] == 'c'
            assert row["total_tokens"] == 384
            assert abs(row["total_cost"] - 0.00009135) < 1e-12
            assert row["provider"] is None
            assert row["purpose"] == 'legacy_answer'
            assert "total_cost" not in {c["name"] for c in sa.inspect(connection).get_columns("messages")}
            assert connection.exec_driver_sql("SELECT ttft FROM messages WHERE id='m'").scalar() == 0.1
            migration.downgrade()
            assert connection.exec_driver_sql("SELECT total_tokens FROM messages WHERE id='m'").scalar() == 384
            migration.upgrade()
            connection.exec_driver_sql("DELETE FROM messages WHERE id='m'")
            assert connection.exec_driver_sql("SELECT message_id FROM llm_calls").scalar() is None
            connection.exec_driver_sql("DELETE FROM conversations WHERE id='c'")
            assert connection.exec_driver_sql("SELECT conversation_id FROM llm_calls").scalar() is None
            assert connection.exec_driver_sql("SELECT COUNT(*) FROM llm_calls").scalar() == 1
