"""Script de utilidad para crear la base de datos PostgreSQL local si no existe."""
from pathlib import Path

from decouple import config
import psycopg2
from psycopg2 import sql


def _normalize_env_value(value):
    if value is None:
        return value
    value = value.strip()
    for ch in ['"', "'", '«', '»', '“', '”', '‘', '’', '`']:
        value = value.strip(ch)
    return value


def main():
    db_name = _normalize_env_value(config('DB_NAME', default='facturacion'))
    db_user = _normalize_env_value(config('DB_USER', default='postgres'))
    db_password = _normalize_env_value(config('DB_PASSWORD', default='postgres'))
    db_host = _normalize_env_value(config('DB_HOST', default='localhost'))
    db_port = _normalize_env_value(config('DB_PORT', default='5432'))
    admin_db = _normalize_env_value(config('DB_ADMIN_DB', default='postgres'))

    print(f"Intentando conectar a PostgreSQL en {db_host}:{db_port} con usuario {db_user}...")
    conn = psycopg2.connect(dbname=admin_db, user=db_user, password=db_password, host=db_host, port=db_port)
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (db_name,))
        if cur.fetchone():
            print(f"La base de datos '{db_name}' ya existe.")
        else:
            print(f"Creando la base de datos '{db_name}'...")
            cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(db_name)))
            print('Base de datos creada con éxito.')

    conn.close()


if __name__ == '__main__':
    main()
