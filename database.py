import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self, db_name="crave.db"):
        """
        Initializes the Database class and ensures the necessary table exists.
        Connection objects are no longer stored as instance variables.
        """
        self.db_name = db_name
        self._create_table()

    @contextmanager
    def _get_connection(self):
        """
        A context manager to handle database connections.
        This will create a new connection for each operation, ensuring thread safety.
        It automatically handles commits, rollbacks, and closing the connection.
        """
        conn = sqlite3.connect(self.db_name)
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            if conn:
                conn.rollback()
          
        finally:
            if conn:
                conn.close()

    def _create_table(self):
        """Creates the 'users' and 'meals' tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS meals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        meal_idea TEXT NOT NULL,
                        user_inputs TEXT NOT NULL,
                        recipe_data TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
        except sqlite3.Error as e:
           
            print(f"Error creating table: {e}")

    def create_user(self, username, email, password):
        """Creates a new user account."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                password_hash = generate_password_hash(password)
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash)
                )
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                raise ValueError("Username already exists")
            elif "email" in str(e):
                raise ValueError("Email already exists")
            else:
                raise ValueError("User creation failed")
        except sqlite3.Error as e:
            print(f"Error creating user: {e}")
            raise ValueError("User creation failed")

    def get_user_by_username(self, username):
        """Retrieves a user by username."""
        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row["id"],
                        "username": row["username"],
                        "email": row["email"],
                        "password_hash": row["password_hash"],
                        "created_at": row["created_at"]
                    }
                return None
        except sqlite3.Error as e:
            print(f"Error retrieving user: {e}")
            return None

    def verify_password(self, user, password):
        """Verifies a user's password."""
        return check_password_hash(user["password_hash"], password)

    def save_meal(self, meal_idea, user_inputs, recipe_data, user_id):
        """Saves a meal and its associated data to the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                user_inputs_json = json.dumps(user_inputs)
                recipe_data_json = json.dumps(recipe_data)
                cursor.execute(
                    "INSERT INTO meals (user_id, meal_idea, user_inputs, recipe_data) VALUES (?, ?, ?, ?)",
                    (user_id, meal_idea, user_inputs_json, recipe_data_json)
                )
        except sqlite3.Error as e:
            print(f"Error saving meal: {e}")

    def meal_history(self, user_id):
        """Retrieves all past meals for a specific user from the database."""
        try:
            with self._get_connection() as conn:
               
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT meal_idea, user_inputs, recipe_data, timestamp FROM meals WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
                rows = cursor.fetchall()
                
              
                history = []
                for row in rows:
                    history.append({
                        "meal_idea": row["meal_idea"],
                        "user_inputs": json.loads(row["user_inputs"]),
                        "recipe_data": json.loads(row["recipe_data"]),
                        "timestamp": row["timestamp"]
                    })
                return history
        except sqlite3.Error as e:
            print(f"Error retrieving meal history: {e}")
            return []