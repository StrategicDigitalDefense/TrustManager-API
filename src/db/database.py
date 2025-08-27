from flask import g
from flask_sqlalchemy import SQLAlchemy
import sqlite3

db = SQLAlchemy()

DATABASE = 'certificates.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    #with open('schema.sql') as f:
    #    db.executescript(f.read())
    create_certificates_table()
    db.commit()
    return db

def create_certificates_table():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS CERTIFICATES (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            issuer TEXT NOT NULL,
            valid_from TEXT NOT NULL,
            valid_to TEXT NOT NULL,
            pem TEXT NOT NULL,
            serial TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            uploaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_changed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            trusted BOOLEAN NOT NULL DEFAULT 0
        )
    ''')
    db.commit()