from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager

class PostgresDB:
    def __init__(self):
        self.app = None
        self.pool = None

    def init_app(self, app):
        self.app = app
        self.connect()

    def connect(self):
        with open("/run/secrets/db_passwd_back", "r") as f:
            password = f.read().strip()

        self.pool = SimpleConnectionPool(
            1, 20,
            user="backend_user",
            password=password,
            host="postgres",
            database="docker"
        )
        return self.pool

    @contextmanager
    def get_cursor(self):
        if self.pool is None:
            self.connect()
        con = self.pool.getconn()
        try:
            yield con.cursor()
            con.commit()
        finally:
            self.pool.putconn(con)
