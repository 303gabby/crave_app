import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_name="crave.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_table()

    def _connect(self):
        """Establishes a connection to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")

    def _create_table(self):
        """Creates the 'meals' table if it doesn't exist."""
        if self.conn:
            try:
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS meals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        meal_idea TEXT NOT NULL,
                        user_inputs TEXT NOT NULL,
                        recipe_data TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                self.conn.commit()
            except sqlite3.Error as e:
                print(f"Error creating table: {e}")
        else:
            print("Database connection not established. Cannot create table.")

    def save_meal(self, meal_idea, user_inputs, recipe_data):
        """Saves a meal and its associated data to the database."""
        if self.conn:
            try:
                user_inputs_json = json.dumps(user_inputs)
                recipe_data_json = json.dumps(recipe_data)
                self.cursor.execute(
                    "INSERT INTO meals (meal_idea, user_inputs, recipe_data) VALUES (?, ?, ?)",
                    (meal_idea, user_inputs_json, recipe_data_json)
                )
                self.conn.commit()
            except sqlite3.Error as e:
                print(f"Error saving meal: {e}")
        else:
            print("Database connection not established. Cannot save meal.")

    def meal_history(self):
        """Retrieves all past meals from the database."""
        if self.conn:
            try:
                self.cursor.execute("SELECT meal_idea, user_inputs, recipe_data, timestamp FROM meals ORDER BY timestamp DESC")
                rows = self.cursor.fetchall()
                history = []
                for row in rows:
                    history.append({
                        "meal_idea": row[0],
                        "user_inputs": json.loads(row[1]),
                        "recipe_data": json.loads(row[2]),
                        "timestamp": row[3]
                    })
                return history
            except sqlite3.Error as e:
                print(f"Error retrieving meal history: {e}")
                return []
        else:
            print("Database connection not established. Cannot retrieve history.")
            return []

    def close(self):
        """Closes the database connection."""
        if self.conn:
            self.conn.close()