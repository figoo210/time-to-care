import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()


def create_connection(db_file):
    """Create a database connection to the SQLite database specified by db_file"""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"Connected to SQLite database: {db_file}")
    except sqlite3.Error as e:
        print(e)
    return conn


def setup_database(conn):
    """Create tables and setup initial configurations"""
    try:
        cursor = conn.cursor()

        # Create table
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS historical_wait_times (
                    hospital_id TEXT,
                    triage_code TEXT,
                    week_start DATE,
                    average_wait_time REAL
                )
            """
        )
        cursor.execute(
            """
                CREATE TABLE IF NOT EXISTS Symptoms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symptom_name TEXT NOT NULL,
                    specialization TEXT NOT NULL
                )
            """
        )

        conn.commit()
        print("Database setup completed.")
    except sqlite3.Error as e:
        print(e)


# function to use the database across the project with full setup
def get_connection():
    database = os.getenv("SQLITE_DB")
    conn = create_connection(database)
    setup_database(conn)
    return conn


# function to close the connection
def close_connection(conn):
    conn.close()
    print("Connection to SQLite database is closed.")


# function to insert general data into the database based on the table
def insert_data(conn, table, data):
    try:
        cursor = conn.cursor()
        placeholders = ", ".join(["?" for _ in range(len(data))])
        cursor.execute(f"INSERT INTO {table} VALUES ({placeholders})", data)
        conn.commit()
    except sqlite3.Error as e:
        print(e)


# function to fetch data from the database based on the table
def fetch_data(conn, table, query="*", conditions=None):
    try:
        cursor = conn.cursor()
        if conditions:
            cursor.execute(f"SELECT {query} FROM {table} {conditions}")
        else:
            cursor.execute(f"SELECT {query} FROM {table}")
        rows = cursor.fetchall()
        return rows
    except sqlite3.Error as e:
        print(e)
        return None
