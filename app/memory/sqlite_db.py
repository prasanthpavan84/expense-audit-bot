import sqlite3
from pathlib import Path

from app.core.config_manager import config


class SQLiteDatabase:
    """Manages the SQLite database connection and schema initialization."""

    _instance = None
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            db_path = config.database_path

            # Handle directory creation for file-based databases
            if db_path != ":memory:":
                db_file = Path(db_path)
                db_file.parent.mkdir(parents=True, exist_ok=True)

            self._connection = sqlite3.connect(db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self.initialize_schema()
        return self._connection

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None

    def initialize_schema(self):
        """Creates tables if they do not exist."""
        cursor = self._connection.cursor()

        # 1. Audits table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audits (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                status TEXT,
                decision TEXT,
                reasoning TEXT,
                total_amount REAL,
                currency TEXT,
                policy_version TEXT,
                workflow_version TEXT,
                prompt_version TEXT,
                model_version TEXT,
                created_at TEXT
            )
        """)

        # 2. Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id TEXT,
                correlation_id TEXT,
                agent TEXT,
                event_type TEXT,
                payload TEXT,
                timestamp TEXT
            )
        """)

        # 3. Checkpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                audit_id TEXT PRIMARY KEY,
                correlation_id TEXT,
                last_completed_step TEXT,
                state_data TEXT,
                updated_at TEXT
            )
        """)

        self._connection.commit()


# Expose a global database instance
db = SQLiteDatabase()
