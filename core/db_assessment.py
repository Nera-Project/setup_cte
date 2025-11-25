# core/db_assessment.py
import os
from typing import List, Dict

import pymysql
import psycopg2
from psycopg2.extras import DictCursor

from core.env_loader import load_env, get_env
from core.logger import get_logger
from utils.command import run_shell

logger = get_logger(__name__)


class DatabaseAssessment:
    """
    - Load DB config dari .env
    - Connect ke DB (MySQL/MariaDB/PostgreSQL)
    - Deteksi Directory path for Encryption dari metadata DB
    - Deteksi tabel & kolom PII berdasarkan nama kolom (PII_COLUMNS)
    - Hitung total record PII per kolom
    - Deteksi proses yang menggunakan path (lsof)
    """

    def __init__(self, pii_columns: List[str] = None, env_path: str = ".env"):
        self.env_path = env_path
        self.config: Dict[str, str] = {}
        self.pii_columns: List[str] = pii_columns or []
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

        # PII_COLUMNS di .env (comma separated)
        pii_env = get_env("PII_COLUMNS", "")
        if pii_env:
            cols = [c.strip() for c in pii_env.split(",") if c.strip()]
            # Simpan dalam lowercase untuk mempermudah compare
            self.pii_columns = [c.lower() for c in cols]

        logger.info(
            "DB config loaded: type=%s host=%s db=%s pii_columns=%s",
            self.config["db_type"],
            self.config["host"],
            self.config["database"],
            ",".join(self.pii_columns) if self.pii_columns else "(none)",
        )

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
                # untuk pymysql DictCursor, row = {"Variable_name": "...", "Value": "..."}
                datadir = row.get("Value") or row.get("value")

            # 2) coba information_schema.FILES (jika ada)
            try:
                cur.execute(
                    """
                    SELECT FILE_NAME
                    FROM information_schema.FILES
                    WHERE TABLE_SCHEMA = %s
                      AND FILE_NAME IS NOT NULL
                    LIMIT 1;
                    """,
                    (db_name,),
                )
                frow = cur.fetchone()
                if frow:
                    file_path = frow.get("FILE_NAME") or frow.get("file_name")
            except Exception as e:
                logger.warning("information_schema.FILES not available or error: %s", e)

        if file_path:
            encrypt_path = os.path.dirname(file_path)
            logger.info("Detected encryption path from FILE_NAME: %s", encrypt_path)
            return encrypt_path

        if datadir:
            encrypt_path = os.path.join(datadir, db_name)
            logger.info("Detected encryption path from datadir: %s", encrypt_path)
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
            logger.info("Detected encryption path for PostgreSQL: %s", encrypt_path)
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
    # PII discovery (MySQL/MariaDB)
    # ==============================
    def _find_pii_columns_mysql(self, conn) -> Dict[str, List[Dict[str, str]]]:
        """
        Cari table & kolom yang nama kolomnya ada di self.pii_columns
        return: {table_name: [ {column, type}, ... ], ...}
        """
        if not self.pii_columns:
            return {}

        db_name = self.config["database"]
        placeholders = ", ".join(["%s"] * len(self.pii_columns))

        sql = f"""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
        FROM information_schema.columns
        WHERE table_schema = %s
          AND LOWER(COLUMN_NAME) IN ({placeholders})
        """

        params = [db_name] + self.pii_columns

        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        result: Dict[str, List[Dict[str, str]]] = {}
        for r in rows:
            table = r["TABLE_NAME"]
            col = r["COLUMN_NAME"]
            dtype = r["DATA_TYPE"]
            result.setdefault(table, []).append({"column": col, "type": dtype})

        return result

    def _count_pii_records_mysql(self, conn, pii_map: Dict[str, List[Dict[str, str]]]):
        """
        Hitung total record per kolom PII (simple COUNT).
        pii_map: {table: [{column, type}, ...]}
        """
        summary = []
        with conn.cursor() as cur:
            for table, cols in pii_map.items():
                for col_info in cols:
                    col = col_info["column"]
                    q = f"SELECT COUNT({col}) AS cnt FROM `{table}`"
                    try:
                        cur.execute(q)
                        row = cur.fetchone()
                        cnt = row["cnt"] if row else 0
                    except Exception as e:
                        logger.error("Failed counting %s.%s: %s", table, col, e)
                        cnt = "Error"
                    summary.append(
                        {
                            "table": table,
                            "column": col,
                            "count": cnt,
                            "type": col_info["type"],
                        }
                    )
        return summary

    # ==============================
    # PII discovery (PostgreSQL)
    # ==============================
    def _find_pii_columns_postgres(self, conn) -> Dict[str, List[Dict[str, str]]]:
        if not self.pii_columns:
            return {}

        db_name = self.config["database"]
        placeholders = ", ".join(["%s"] * len(self.pii_columns))

        # di Postgres, informasi kolom ada di information_schema.columns
        sql = f"""
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_catalog = %s
          AND LOWER(column_name) IN ({placeholders})
        """

        params = [db_name] + self.pii_columns
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        result: Dict[str, List[Dict[str, str]]] = {}
        for r in rows:
            table = r["table_name"]
            col = r["column_name"]
            dtype = r["data_type"]
            result.setdefault(table, []).append({"column": col, "type": dtype})

        return result

    def _count_pii_records_postgres(self, conn, pii_map: Dict[str, List[Dict[str, str]]]):
        summary = []
        with conn.cursor() as cur:
            for table, cols in pii_map.items():
                for col_info in cols:
                    col = col_info["column"]
                    q = f'SELECT COUNT("{col}") AS cnt FROM "{table}"'
                    try:
                        cur.execute(q)
                        row = cur.fetchone()
                        cnt = row["cnt"] if row else 0
                    except Exception as e:
                        logger.error("Failed counting %s.%s: %s", table, col, e)
                        cnt = "Error"
                    summary.append(
                        {
                            "table": table,
                            "column": col,
                            "count": cnt,
                            "type": col_info["type"],
                        }
                    )
        return summary

    # ==============================
    # fuser helper
    # ==============================
    def _get_path_users_once(self, path: str):
        """
        Return list of 'PID(user)' yang menggunakan path tersebut via fuser.
        - fuser -u <path> -> output berisi pid(user)
        Contoh: '/var/lib/mysql/perusahaan_db: 758514(mysql)'
        NOTE:
          - fuser exit code:
              0 = ada proses
              1 = tidak ada proses
          - Jadi kita TIDAK boleh pakai check=True.
        """
        try:
            # Pakai check=False supaya non-zero exit code tidak dilempar sebagai exception
            cmd = f"fuser -u {path}"
            output = run_shell(cmd, check=False, capture_output=True) or ""
            output = output.strip()

            if not output:
                return []

            users = set()
            for line in output.splitlines():
                # contoh line: "/var/lib/mysql/perusahaan_db: 758514(mysql) 758600(mysql)"
                if ":" in line:
                    _, pids_part = line.split(":", 1)
                else:
                    pids_part = line

                for token in pids_part.split():
                    token = token.strip()
                    if not token:
                        continue
                    # token biasanya format '758514(mysql)'
                    users.add(token)

            return sorted(users)

        except Exception as e:
            logger.error("Failed to run fuser on %s: %s", path, e)
            return []


    def _get_path_users_deep(self, path: str):
        """
        Cek path & parent directory (satu level di atas) pakai fuser -u
        """
        path = path.rstrip("/")
        paths_to_check = set()
        if path:
            paths_to_check.add(path)
            parent = os.path.dirname(path)
            if parent and parent != path:
                paths_to_check.add(parent)

        users = set()
        for p in paths_to_check:
            for u in self._get_path_users_once(p):
                users.add(u)

        return sorted(users)

    # ==============================
    # Main run()
    # ==============================
    def run(self) -> Dict[str, str]:
        """
        Output:
        {
          "Directory path for Encryption": "...",
          "Database Name": "...",
          "List Column have PII": "...",
          "Character Data per PII Column": "...",
          "Total PII Record": "...",
          "Who users used the path": "..."
        }
        """
        conn = None
        try:
            conn = self.get_connection()
            db_type = self.config["db_type"]

            encrypt_path = self.detect_encrypt_path(conn)
            result: Dict[str, str] = {
                "Directory path for Encryption": encrypt_path,
                "Database Name": self.config["database"],
            }

            pii_map = {}
            pii_summary = []

            # PII detection per engine
            if db_type in ("mysql", "mariadb"):
                pii_map = self._find_pii_columns_mysql(conn)
                pii_summary = self._count_pii_records_mysql(conn, pii_map)
            elif db_type in ("postgres", "postgresql"):
                pii_map = self._find_pii_columns_postgres(conn)
                pii_summary = self._count_pii_records_postgres(conn, pii_map)

            # mapping ke format yang kamu mau di tabel
            if pii_map:
                # List table + kolom PII
                pii_str = []
                for table, cols in pii_map.items():
                    col_names = ", ".join(c["column"] for c in cols)
                    pii_str.append(f"{table}: {col_names}")
                result["List Column have PII"] = "; ".join(pii_str)

                # Tipe data per kolom PII
                char_detail = []
                for table, cols in pii_map.items():
                    for c in cols:
                        char_detail.append(f"{table}.{c['column']}: {c['type']}")
                result["Character Data per PII Column"] = ", ".join(char_detail)

            if pii_summary:
                cnt_str = []
                for s in pii_summary:
                    cnt_str.append(f"{s['table']}.{s['column']}={s['count']}")
                result["Total PII Record"] = ", ".join(cnt_str)

            # lsof path
            if encrypt_path and encrypt_path != "Unknown":
                users = self._get_path_users_deep(encrypt_path)
                result["Who users used the path"] = (
                    ", ".join(users) if users else "No open files detected"
                )

            return result

        finally:
            if conn:
                conn.close()
