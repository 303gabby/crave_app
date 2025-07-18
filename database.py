import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime

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
        """Creates the 'meals' table if it doesn't exist."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS meals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        meal_idea TEXT NOT NULL,
                        user_inputs TEXT NOT NULL,
                        recipe_data TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        except sqlite3.Error as e:
           
            print(f"Error creating table: {e}")

    def save_meal(self, meal_idea, user_inputs, recipe_data):
        """Saves a meal and its associated data to the database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                user_inputs_json = json.dumps(user_inputs)
                recipe_data_json = json.dumps(recipe_data)
                cursor.execute(
                    "INSERT INTO meals (meal_idea, user_inputs, recipe_data) VALUES (?, ?, ?)",
                    (meal_idea, user_inputs_json, recipe_data_json)
                )
        except sqlite3.Error as e:
            print(f"Error saving meal: {e}")

    def meal_history(self):
        """Retrieves all past meals from the database."""
        try:
            with self._get_connection() as conn:
               
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT meal_idea, user_inputs, recipe_data, timestamp FROM meals ORDER BY timestamp DESC")
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