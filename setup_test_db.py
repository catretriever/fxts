#!/usr/bin/env python3
"""
setup_test_db.py - FXTS test database setup runner

Reads setup_test_db.sql and executes it against the configured MySQL/MariaDB
instance to create the FXDB schema and load sample data.

Configuration (in priority order):
  1. Environment variables: FXDB_HOST, FXDB_USER, FXDB_PASSWD, FXDB_NAME
  2. config.ini [database] section
  3. Built-in defaults:  host=localhost, db=FXDB, user/passwd from CLI prompt

Usage:
  python3 setup_test_db.py [--host HOST] [--user USER] [--passwd PASSWD]
  python3 setup_test_db.py --verify   # verify tables and row counts only
  python3 setup_test_db.py --help
"""

import argparse
import configparser
import getpass
import os
import sys


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _load_ini():
    cfg = configparser.ConfigParser()
    cfg_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    cfg.read(cfg_path)
    return cfg


def _resolve(env_key, ini_cfg, section, key, fallback):
    return (
        os.environ.get(env_key)
        or ini_cfg.get(section, key, fallback=None)
        or fallback
    )


def build_config(args):
    ini = _load_ini()
    host   = args.host   or _resolve('FXDB_HOST',   ini, 'database', 'host',   'localhost')
    user   = args.user   or _resolve('FXDB_USER',   ini, 'database', 'user',   '')
    passwd = args.passwd or _resolve('FXDB_PASSWD', ini, 'database', 'passwd', '')
    db     = args.db     or _resolve('FXDB_NAME',   ini, 'database', 'db',     'FXDB')

    if not user:
        user = input('MySQL user: ').strip()
    if not passwd:
        passwd = getpass.getpass('MySQL password: ')

    return {'host': host, 'user': user, 'passwd': passwd, 'db': db}


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

VERIFY_QUERY = """
SELECT 'FXCross'           AS tbl, COUNT(*) AS rows FROM FXCross
UNION ALL SELECT 'HourlyData',         COUNT(*) FROM HourlyData
UNION ALL SELECT 'TEngine',            COUNT(*) FROM TEngine
UNION ALL SELECT 'MAP_Pfo_TEngine',    COUNT(*) FROM MAP_Pfo_TEngine
UNION ALL SELECT 'MAP_TEngine_SigGen', COUNT(*) FROM MAP_TEngine_SigGen
UNION ALL SELECT 'SigGenTP',           COUNT(*) FROM SigGenTP
UNION ALL SELECT 'fx_table',           COUNT(*) FROM fx_table
UNION ALL SELECT 'fx_data',            COUNT(*) FROM fx_data
UNION ALL SELECT 'tf_engines',         COUNT(*) FROM tf_engines
"""


def connect(cfg):
    try:
        import pymysql
        import pymysql.cursors
    except ImportError:
        sys.exit("Error: PyMySQL is not installed.  Run:  pip install PyMySQL")

    print(f"Connecting to {cfg['host']} as {cfg['user']} ...")
    conn = pymysql.connect(
        host=cfg['host'],
        user=cfg['user'],
        passwd=cfg['passwd'],
        cursorclass=pymysql.cursors.DictCursor,
    )
    print("Connected.")
    return conn


def run_sql_file(conn, sql_path):
    """Split setup_test_db.sql on semicolons and execute each statement."""
    with open(sql_path, 'r') as fh:
        content = fh.read()

    # Strip comment lines and split on ';'
    statements = [
        stmt.strip()
        for stmt in content.split(';')
        if stmt.strip() and not stmt.strip().startswith('--')
    ]

    with conn.cursor() as cur:
        for stmt in statements:
            # Skip pure-comment blocks that slipped through
            lines = [l for l in stmt.splitlines() if not l.strip().startswith('--')]
            clean = '\n'.join(lines).strip()
            if not clean:
                continue
            try:
                cur.execute(clean)
                conn.commit()
            except Exception as exc:
                print(f"  [WARN] {exc!r}")
                print(f"        Statement: {clean[:120]} ...")
                conn.rollback()


def verify(conn, db_name):
    with conn.cursor() as cur:
        cur.execute(f"USE {db_name}")
        cur.execute(VERIFY_QUERY)
        rows = cur.fetchall()

    print(f"\n{'Table':<25} {'Rows':>6}")
    print('-' * 33)
    for row in rows:
        print(f"{row['tbl']:<25} {row['rows']:>6}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Set up FXTS test database')
    parser.add_argument('--host',   default='', help='MySQL host (default: localhost)')
    parser.add_argument('--user',   default='', help='MySQL user')
    parser.add_argument('--passwd', default='', help='MySQL password')
    parser.add_argument('--db',     default='', help='Database name (default: FXDB)')
    parser.add_argument('--verify', action='store_true',
                        help='Only verify table row counts, do not recreate schema')
    args = parser.parse_args()

    cfg = build_config(args)
    conn = connect(cfg)

    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'setup_test_db.sql')

    if args.verify:
        print(f"\nVerifying database '{cfg['db']}' ...")
        verify(conn, cfg['db'])
    else:
        print(f"\nRunning {sql_path} ...")
        run_sql_file(conn, sql_path)
        print("Schema and sample data applied.")
        verify(conn, cfg['db'])

    conn.close()
    print("Done.")


if __name__ == '__main__':
    main()
