import os, threading, pymysql
from pymysql.cursors import DictCursor

_tls = threading.local()

def _env(name, default=None):
    return os.environ.get(name, default)

def _mysql_params():
    host = _env("MYSQL_HOST", "127.0.0.1")
    port = int(_env("MYSQL_PORT", "3306"))
    user = _env("MYSQL_USER")
    password = _env("MYSQL_PASSWORD")
    db = _env("MYSQL_DB")
    charset = _env("MYSQL_CHARSET", "utf8mb4")
    if not user or not password or not db:
        raise RuntimeError("MYSQL_* env not loaded (user/password/db missing). Check /www/wwwroot/wecom_ops/.env is loaded.")
    return dict(host=host, port=port, user=user, password=password,
                database=db, charset=charset, cursorclass=DictCursor,
                autocommit=True)

def get_mysql_conn():
    params = _mysql_params()
    conn = getattr(_tls, "conn", None)
    if conn:
        try:
            conn.ping(reconnect=True)
            return conn
        except Exception:
            conn = None
    _tls.conn = pymysql.connect(**params)
    return _tls.conn


# --- compat alias for legacy code ---
try:
    get_conn
except NameError:
    get_conn = get_mysql_conn
