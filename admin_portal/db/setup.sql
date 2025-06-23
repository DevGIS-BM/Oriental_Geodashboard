
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    email TEXT,
    password TEXT,
    role TEXT CHECK(role IN ('admin', 'editor', 'client')) NOT NULL
);
CREATE TABLE IF NOT EXISTS facilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    province TEXT,
    commune TEXT,
    type TEXT,
    name TEXT,
    latitude REAL,
    longitude REAL
);
