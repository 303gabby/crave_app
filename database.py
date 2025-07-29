import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Database:
    def __init__(self, db_name="crave.db"):
        """
        Initializes the Database class and ensures the necessary tables exist.
        """
        self.db_name = db_name
        # Call the public method to create tables when the Database object is initialized
        self.create_tables()

    @contextmanager
    def _get_connection(self, autocommit=True):
        """
        A context manager to handle database connections.
        It automatically handles commits, rollbacks, and closing the connection.
        It also sets row_factory to sqlite3.Row for dictionary-like access.
        """
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row # Allows accessing columns by name (e.g., row['id'])
        try:
            yield conn
            if autocommit:
                conn.commit()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise # Re-raise the exception to be caught by the calling function/route
        finally:
            if conn:
                conn.close()

    def create_tables(self):
        """
        Creates the 'users' and 'meals' tables if they don't exist.
        Includes robust error handling to immediately show issues during table creation.
        """
        try:
            with self._get_connection() as conn: # autocommit=True by default here
                cursor = conn.cursor()

                # 1. Create 'users' table (must be created before 'meals' due to foreign key)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 2. Create 'meals' table
                # IMPORTANT: Added 'user_id INTEGER NOT NULL,' column definition here
                # Added ON DELETE CASCADE for better integrity when a user is deleted
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS meals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL, -- This column must be explicitly defined
                        meal_idea TEXT NOT NULL,
                        user_inputs TEXT NOT NULL,
                        recipe_data TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                """)
                print("Database: Tables 'users' and 'meals' successfully created (or already existed).")
        except sqlite3.Error as e:
            print(f"*** FATAL DATABASE ERROR: Failed to create tables: {e} ***")
            # Re-raise the error to prevent the application from starting if tables aren't created
            raise

    def create_user(self, username, email, password):
        """Creates a new user account with a hashed password."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Use pbkdf2:sha256 method for password hashing for stronger security
                password_hash = generate_password_hash(password, method='pbkdf2:sha256')
                cursor.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, password_hash)
                )
                return cursor.lastrowid # Returns the ID of the newly created user
        except sqlite3.IntegrityError as e:
            # Provide more specific error messages for common integrity violations
            if "username" in str(e).lower():
                raise ValueError("Username already exists. Please choose a different username.")
            elif "email" in str(e).lower():
                raise ValueError("Email address already registered. Please use a different email or login.")
            else:
                raise ValueError(f"User creation failed due to data integrity issue: {e}")
        except sqlite3.Error as e:
            print(f"Error creating user '{username}': {e}")
            raise ValueError(f"User creation failed due to database error: {e}")

    def get_user_by_username(self, username):
        """Retrieves a user's details by their username."""
        try:
            with self._get_connection() as conn:
                # row_factory is already set in _get_connection, no need to set again here
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if row:
                    return dict(row) # Return as a dictionary for consistent access
                return None # Return None if user not found
        except sqlite3.Error as e:
            print(f"Error retrieving user '{username}': {e}")
            return None # Return None on database error

    def verify_password(self, user, password):
        """Verifies a user's plain-text password against their stored hash."""
        # Ensure 'user' object and 'password_hash' key exist before attempting verification
        if user and "password_hash" in user:
            return check_password_hash(user["password_hash"], password)
        return False # Return False if user or hash is missing (e.g., user not found)

    def save_meal(self, meal_idea, user_inputs, recipe_data, user_id):
        """
        Saves a meal and its associated data to the database, linked to a specific user.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                user_inputs_json = json.dumps(user_inputs)
                recipe_data_json = json.dumps(recipe_data)
                # Ensure user_id is included in the INSERT statement
                cursor.execute(
                    "INSERT INTO meals (user_id, meal_idea, user_inputs, recipe_data) VALUES (?, ?, ?, ?)",
                    (user_id, meal_idea, user_inputs_json, recipe_data_json)
                )
        except sqlite3.Error as e:
            print(f"Error saving meal '{meal_idea}' for user {user_id}: {e}")
            raise ValueError(f"Failed to save meal: {e}") # Re-raise for app.py to catch

    def delete_meal(self, meal_id, user_id):
        """
        Deletes a meal from the database by its ID, ensuring it belongs to the specified user.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Delete only if the meal_id matches AND it belongs to the user_id for security
                cursor.execute("DELETE FROM meals WHERE id = ? AND user_id = ?", (meal_id, user_id))
                if cursor.rowcount > 0:
                    print(f"Meal ID {meal_id} deleted successfully by user {user_id}.")
                    return True # Indicate successful deletion
                else:
                    print(f"Meal ID {meal_id} not found or does not belong to user {user_id}.")
                    return False # Indicate no meal found or unauthorized deletion
        except sqlite3.Error as e:
            print(f"Error deleting meal ID {meal_id} for user {user_id}: {e}")
            raise ValueError(f"Failed to delete meal: {e}") # Re-raise for app.py to catch

    def meal_history(self, user_id):
        """
        Retrieves all past meals for a specific user from the database.
        Returns a list of dictionaries, including 'id' for deletion functionality on the frontend.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Select 'id' and filter by 'user_id' to get only the current user's history
                cursor.execute(
                    "SELECT id, meal_idea, user_inputs, recipe_data, timestamp FROM meals WHERE user_id = ? ORDER BY timestamp DESC",
                    (user_id,)
                )
                rows = cursor.fetchall() # Fetches all matching rows

                history = []
                for row in rows:
                    parsed_row = dict(row) # Convert sqlite3.Row object to a standard dictionary
                    # Parse JSON strings back into Python objects (dictionaries/lists)
                    parsed_row["user_inputs"] = json.loads(parsed_row["user_inputs"])
                    parsed_row["recipe_data"] = json.loads(parsed_row["recipe_data"])
                    history.append(parsed_row)
                return history
        except sqlite3.Error as e:
            print(f"Error retrieving meal history for user {user_id}: {e}")
            return [] # Return an empty list on database error