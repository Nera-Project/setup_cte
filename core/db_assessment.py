# core/db_assessment.py
import os
from typing import List, Dict

import pymysql
import psycopg2
from psycopg2.extras import DictCursor
from core.env_loader import load_env, get_env

from core.logger import get_logger

logger = get_logger(__name__)


class DatabaseAssessment:
    """
    - Load DB config from .env
    - Connect ke DB (MySQL/MariaDB/PostgreSQL)
    - Deteksi Directory path for Encryption dari metadata DB
    - (PII detection bisa ditambah di sini nanti)
    """

    def __init__(self, pii_columns: List[str] = None, env_path: str = ".env"):
        self.env_path = env_path
        self.config = {}
        self.pii_columns = pii_columns or []
        self._load_env()

    # ==============================
    # Load .env
    # ==============================
    def _load_env(self):
        load_env(self.env_path)

        self.config = {
            "db_type": get_env("DB_TYPE", "").lower(),
            "host": get_env("DB_HOST"),
            "port": int(get_env("DB_PORT", "0")) or None,
            "user": get_env("DB_USER"),
            "password": get_env("DB_PASSWORD"),
            "database": get_env("DB_NAME"),
        }

        ...
        pii_env = get_env("PII_COLUMNS", "")
        ...

    # ==============================
    # Connection
    # ==============================
    def _connect_mysql(self):
        logger.info("Connecting to MySQL/MariaDB...")
        conn = pymysql.connect(
            host=self.config["host"],
            port=self.config["port"] or 3306,
            user=self.config["user"],
            password=self.config["password"],
            database=self.config["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        return conn

    def _connect_postgres(self):
        logger.info("Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            host=self.config["host"],
            port=self.config["port"] or 5432,
            user=self.config["user"],
            password=self.config["password"],
            dbname=self.config["database"],
            cursor_factory=DictCursor,
        )
        return conn

    def get_connection(self):
        db_type = self.config["db_type"]
        if db_type in ("mysql", "mariadb"):
            return self._connect_mysql()
        elif db_type in ("postgres", "postgresql"):
            return self._connect_postgres()
        raise RuntimeError(f"Unsupported DB_TYPE: {db_type}")

    # ==============================
    # Detect encrypt path: MySQL/MariaDB
    # ==============================
    def _detect_encrypt_path_mysql(self, conn) -> str:
        db_name = self.config["database"]
        datadir = None
        file_path = None

        with conn.cursor() as cur:
            # 1) datadir
            cur.execute("SHOW VARIABLES LIKE 'datadir';")
            row = cur.fetchone()
            if row:
                datadir = row.get("Value")

            # 2) coba information_schema.FILES
            try:
                cur.execute("""
                    SELECT FILE_NAME
                    FROM information_schema.FILES
                    WHERE TABLE_SCHEMA = %s
                      AND FILE_NAME IS NOT NULL
                    LIMIT 1;
                """, (db_name,))
                frow = cur.fetchone()
                if frow:
                    file_path = frow.get("FILE_NAME")
            except Exception as e:
                logger.warning(f"information_schema.FILES not available or error: {e}")

        if file_path:
            # contoh: /data/mysqldata/cbhrm/users.ibd -> parent dir
            encrypt_path = os.path.dirname(file_path)
            logger.info(f"Detected encryption path from FILE_NAME: {encrypt_path}")
            return encrypt_path

        if datadir:
            encrypt_path = os.path.join(datadir, db_name)
            logger.info(f"Detected encryption path from datadir: {encrypt_path}")
            return encrypt_path

        logger.warning("Failed to detect encryption path for MySQL/MariaDB.")
        return "Unknown"

    # ==============================
    # Detect encrypt path: PostgreSQL
    # ==============================
    def _detect_encrypt_path_postgres(self, conn) -> str:
        db_name = self.config["database"]
        data_directory = None
        db_oid = None

        with conn.cursor() as cur:
            cur.execute("SHOW data_directory;")
            row = cur.fetchone()
            if row:
                data_directory = row[0]

            cur.execute("SELECT oid FROM pg_database WHERE datname = %s;", (db_name,))
            row = cur.fetchone()
            if row:
                db_oid = row[0]

        if data_directory and db_oid:
            encrypt_path = os.path.join(data_directory, "base", str(db_oid))
            logger.info(f"Detected encryption path for PostgreSQL: {encrypt_path}")
            return encrypt_path

        logger.warning("Failed to detect encryption path for PostgreSQL.")
        return "Unknown"

    def detect_encrypt_path(self, conn) -> str:
        db_type = self.config["db_type"]
        if db_type in ("mysql", "mariadb"):
            return self._detect_encrypt_path_mysql(conn)
        elif db_type in ("postgres", "postgresql"):
            return self._detect_encrypt_path_postgres(conn)
        return "Unknown"

    # ==============================
    # Main run()
    # ==============================
    def run(self) -> Dict[str, str]:
        """
        Minimal output:
        {
          "Directory path for Encryption": "...",
          "Database Name": "..."
        }
        Nanti bisa ditambah PII info.
        """
        conn = None
        try:
            conn = self.get_connection()
            encrypt_path = self.detect_encrypt_path(conn)

            result = {
                "Directory path for Encryption": encrypt_path,
                "Database Name": self.config["database"],
            }

            # TODO: di sini nanti tambah PII analysis
            return result

        finally:
            if conn:
                conn.close()
