from flask import (
    Flask, render_template, request, redirect, url_for, session, jsonify, flash
)
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
import requests # Needed for Google Places API
from datetime import timedelta
import openai # Assuming you use OpenAI for meal/recipe generation
from dotenv import load_dotenv # To load environment variables
import traceback # For debugging exceptions

# Load environment variables from .env file
load_dotenv()

from meal_suggestion import CreateMeal
from recipe_creation import CreateRecipe
from database import Database
from utils import format_recipe_for_display # format_history_for_display is no longer needed in app.py import

app = Flask(__name__)

# --- Secret Keys & JWT Configuration ---
# Flask Session secret key (used by session, flash messages)
# For production, load this from an environment variable for persistence across restarts:
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# JWT Secret Key (used by Flask-JWT-Extended)
# Crucial for production: Load this from an environment variable!
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'a-very-strong-default-jwt-secret-for-dev')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

jwt = JWTManager(app)

# --- API Keys (ensure these are in your .env file) ---
# Assuming these are used by your CreateMeal/CreateRecipe or directly in app.py now
openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # Define this globally if used across functions

# Database and Service Initialization
db = Database()
db.create_tables() # Ensure tables are created on app startup
meal_suggestion_service = CreateMeal()
recipe_creation_service = CreateRecipe()

# --- Routes ---

@app.route('/')
def index():
    # Clear any temporary recipe data from session when returning home
    session.pop('current_meal_idea', None)
    session.pop('user_inputs', None)
    session.pop('current_recipe_data', None)

    # Pass login status and username to the template
    user_logged_in = 'user_id' in session
    username = session.get('username')

    return render_template(
        'index.html',
        user_logged_in=user_logged_in,
        username=username
    )

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')

        try:
            user_id = db.create_user(username, email, password)
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('register.html')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html')

        user = db.get_user_by_username(username)
        if user and db.verify_password(user, password):
            access_token = create_access_token(identity=user['id'])
            session['access_token'] = access_token
            session['user_id'] = user['id'] # Store user_id in session for DB operations
            session['username'] = user['username'] # Store username for display

            flash('Logged in successfully!', 'success') # Added flash message here
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
            return render_template('login.html')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/create_recipe_page', methods=['GET', 'POST'])
def create_recipe_page():
    if 'user_id' not in session:
        flash('Please login to create recipes.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        type_of_meal = request.form['type_of_meal']
        budget = request.form['budget']
        mood = request.form['mood']
        tools = [t.strip() for t in request.form['tools'].split(',') if t.strip()]
        time = request.form['time']
        # Fixed the NameError: 'd' was not defined, changed to 't'
        dietary_restrictions = [t.strip() for t in request.form['dietary_restrictions'].split(',') if t.strip()]

        user_inputs = {
            'type_of_meal': type_of_meal,
            'budget': budget,
            'mood': mood,
            'tools': tools,
            'time': time,
            'dietary_restrictions': dietary_restrictions
        }
        session['user_inputs'] = user_inputs

        # Corrected order for create_meal arguments: budget, mood, type_of_meal, tools, time, dietary_restrictions
        meal_idea = meal_suggestion_service.create_meal(
            budget, mood, type_of_meal, tools, time, dietary_restrictions
        )

        if not meal_idea:
            flash("Sorry, couldn't come up with a meal idea. Please try again with different preferences.", 'error')
            return render_template('create_recipe.html', user_inputs=user_inputs)

        session['current_meal_idea'] = meal_idea

        recipe_data = recipe_creation_service.req_recipe_details(
            meal_idea, type_of_meal, budget, tools, time, dietary_restrictions
        )

        if not recipe_data:
            flash("Couldn't find or generate a suitable recipe. Please try a different meal idea or adjust your preferences.", 'error')
            return render_template('create_recipe.html', user_inputs=user_inputs)

        # Store the raw recipe_data in session for optional saving later
        session['current_recipe_data'] = recipe_data

        # Render recipe_details.html with formatted data and show save options
        formatted_recipe = format_recipe_for_display(recipe_data)
        return render_template('recipe_details.html',
                               meal_idea=meal_idea,
                               recipe=formatted_recipe,
                               user_inputs=user_inputs,
                               show_save_options=True) # Flag to show save/discard buttons

    # For GET request or if initial POST has an error, pre-fill form if inputs exist
    return render_template('create_recipe.html', user_inputs=session.get('user_inputs', {}))


@app.route('/variation', methods=['POST'])
def variation():
    if 'user_id' not in session:
        flash('Please login to create variations.', 'warning')
        return redirect(url_for('login'))

    if 'user_inputs' not in session or 'current_meal_idea' not in session or 'current_recipe_data' not in session:
        flash("Session expired or missing data. Please start a new recipe.", 'error')
        return redirect(url_for('create_recipe_page'))

    user_inputs = session['user_inputs']
    base_idea = session['current_meal_idea'] # This is the base meal idea the variation was generated from
    original_recipe_data = session['current_recipe_data'] # Keep original recipe data if variation fails
    variation_prompt = request.form['variation_prompt']

    # Corrected order for create_meal arguments
    new_meal_idea = meal_suggestion_service.create_meal(
        user_inputs['budget'], user_inputs['mood'], user_inputs['type_of_meal'], user_inputs['tools'],
        user_inputs['time'], user_inputs['dietary_restrictions'],
        base_idea=base_idea, variation_prompt=variation_prompt
    )

    if not new_meal_idea:
        flash("Could not generate a variation idea. Please try again.", 'error')
        # Re-render recipe_details with original recipe if variation fails to generate a new idea
        formatted_recipe = format_recipe_for_display(original_recipe_data)
        return render_template('recipe_details.html',
                               meal_idea=base_idea, # Display the original meal idea if variation idea failed
                               recipe=formatted_recipe,
                               user_inputs=user_inputs,
                               show_save_options=True) # Still offer to save the original or try again


    session['current_meal_idea'] = new_meal_idea # Update current_meal_idea to the NEW variation idea

    variation_recipe_data = recipe_creation_service.req_recipe_details(
        new_meal_idea, user_inputs['type_of_meal'], user_inputs['budget'], user_inputs['tools'],
        user_inputs['time'], user_inputs['dietary_restrictions']
    )

    if variation_recipe_data:
        session['current_recipe_data'] = variation_recipe_data # Store new raw variation data
        formatted_recipe = format_recipe_for_display(variation_recipe_data)
        return render_template('recipe_details.html',
                               meal_idea=new_meal_idea, # Display the NEW variation meal idea
                               recipe=formatted_recipe,
                               user_inputs=user_inputs,
                               show_save_options=True) # Offer to save new variation
    else:
        flash(f"Could not find a recipe for the variation: '{new_meal_idea}'. Please try a different prompt.", 'error')
        # If new recipe details generation fails, show new meal idea but indicate no recipe details
        session.pop('current_recipe_data', None) # Clear it if no recipe found for this variation
        return render_template('recipe_details.html',
                               meal_idea=new_meal_idea, # Display the new meal idea that failed
                               recipe=None, # No recipe data to display
                               user_inputs=user_inputs,
                               show_save_options=False) # Don't offer to save if no recipe was found


@app.route('/save_current_recipe', methods=['POST'])
def save_current_recipe():
    if 'user_id' not in session:
        flash('Please login to save recipes.', 'warning')
        return redirect(url_for('login'))

    meal_idea = session.get('current_meal_idea')
    user_inputs = session.get('user_inputs')
    recipe_data = session.get('current_recipe_data') # This is the raw data from API

    if not all([meal_idea, user_inputs, recipe_data]):
        flash("No valid recipe data in session to save. Please generate a new one.", 'error')
        return redirect(url_for('create_recipe_page'))

    user_id = session['user_id'] # Get user_id from session

    try:
        db.save_meal(
            meal_idea=meal_idea,
            user_inputs=user_inputs,
            recipe_data=recipe_data, # Save the raw recipe_data
            user_id=user_id # Pass user_id to save_meal
        )
        flash("Recipe saved successfully!", 'success')
        # Clear session data after saving, as it's now in history
        session.pop('current_meal_idea', None)
        session.pop('user_inputs', None)
        session.pop('current_recipe_data', None)
    except ValueError as e: # Catch ValueError re-raised by database.py
        flash(f"Error saving recipe: {e}", 'error')
    except Exception as e:
        flash(f"An unexpected error occurred while saving: {e}", 'error')

    return redirect(url_for('view_history'))


@app.route('/discard_current_recipe', methods=['POST'])
def discard_current_recipe():
    # Clear temporary recipe data from session
    session.pop('current_meal_idea', None)
    session.pop('user_inputs', None)
    session.pop('current_recipe_data', None)
    flash("Recipe discarded.", 'info')
    return redirect(url_for('create_recipe_page'))


@app.route('/history')
def view_history():
    if 'user_id' not in session:
        flash('Please login to view history.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id'] # Get user ID from session
    history = db.meal_history(user_id) # Call with user_id

    # IMPORTANT: history_data is the variable passed to the template
    return render_template('history.html', history_data=history)


@app.route('/delete_meal/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    if 'user_id' not in session:
        flash('Please login to delete recipes.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id'] # Get user ID from session
    try:
        success = db.delete_meal(meal_id, user_id) # Pass user_id to delete_meal
        if success:
            flash(f'Recipe deleted successfully!', 'success')
        else:
            flash(f'Recipe not found or you do not have permission to delete it.', 'error')
    except ValueError as e: # Catch ValueError re-raised by database.py
        flash(f"Error deleting recipe: {e}", 'error')
    except Exception as e:
        flash(f"An unexpected error occurred while deleting: {e}", 'error')

    return redirect(url_for('view_history'))


# --- New Google Places API functions for Grocery Stores ---
def get_location_from_zip(zipcode, api_key):
    """Converts a ZIP code to latitude and longitude using Google Geocoding API."""
    geo_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={zipcode}&key={api_key}"
    try:
        geo_response = requests.get(geo_url).json()
        if geo_response["status"] == "OK":
            location = geo_response["results"][0]["geometry"]["location"]
            return f"{location['lat']},{location['lng']}"
        else:
            print(f"Geocoding API error for ZIP {zipcode}: {geo_response.get('error_message', geo_response['status'])}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Network error during geocoding: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"Unexpected JSON structure from geocoding API: {e}")
        return None


def find_grocery_stores(location, api_key):
    """Finds nearby grocery stores using Google Places API."""
    nearby_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    nearby_params = {
        "location": location,
        "radius": 5000, # 5000 meters = 5 km radius
        "type": "grocery_or_supermarket", # Use 'grocery_or_supermarket' for more specific results
        "key": api_key
    }

    try:
        response = requests.get(nearby_url, params=nearby_params)
        data = response.json()
        stores = []

        if data['status'] == 'OK':
            for place in data['results'][:5]:  # Limit to top 5 stores
                # Get more details for each place
                place_id = place['place_id']
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_params = {
                    "place_id": place_id,
                    "fields": "name,vicinity,opening_hours,url", # Added 'url' for link to map
                    "key": api_key
                }
                details_response = requests.get(details_url, params=details_params)
                details_data = details_response.json()

                if details_data['status'] == 'OK':
                    result = details_data['result']
                    hours = result.get('opening_hours', {}).get('weekday_text', ["Hours not available"])

                    stores.append({
                        "name": result.get("name", "Unknown Store"),
                        "address": result.get("vicinity", "No address available"),
                        "hours": hours,
                        "google_maps_url": result.get("url", "#") # Link to Google Maps
                    })
        else:
            print(f"Places API error: {data.get('error_message', data['status'])}")
        return stores
    except requests.exceptions.RequestException as e:
        print(f"Network error during Places API call: {e}")
        return []
    except (KeyError, IndexError) as e:
        print(f"Unexpected JSON structure from Places API: {e}")
        return []


@app.route('/grocery_near_me', methods=['POST'])
def grocery_near_me():
    if 'user_id' not in session:
        flash('Please login to use this feature.', 'warning')
        return redirect(url_for('login'))

    try:
        # Retrieve current recipe data from session to re-render recipe_details.html
        meal_idea = session.get('current_meal_idea')
        formatted_recipe = format_recipe_for_display(session.get('current_recipe_data'))
        user_inputs = session.get('user_inputs')

        zipcode = request.form.get('zipcode')
        if not zipcode:
            flash("Please provide a ZIP code.", 'error')
            return render_template('recipe_details.html',
                                   meal_idea=meal_idea,
                                   recipe=formatted_recipe,
                                   user_inputs=user_inputs,
                                   show_save_options=True) # Keep save options

        if not GOOGLE_API_KEY:
            flash("Google API Key is not configured. Cannot find grocery stores.", 'error')
            return render_template('recipe_details.html',
                                   meal_idea=meal_idea,
                                   recipe=formatted_recipe,
                                   user_inputs=user_inputs,
                                   show_save_options=True)

        location = get_location_from_zip(zipcode, GOOGLE_API_KEY)
        if not location:
            flash("Invalid ZIP code or geocoding failed. Please try again.", 'error')
            return render_template('recipe_details.html',
                                   meal_idea=meal_idea,
                                   recipe=formatted_recipe,
                                   user_inputs=user_inputs,
                                   show_save_options=True)

        stores = find_grocery_stores(location, GOOGLE_API_KEY)

        if not stores:
            flash(f"No grocery stores found near {zipcode}. Try a different ZIP code.", 'info')

        return render_template('recipe_details.html',
                               meal_idea=meal_idea,
                               recipe=formatted_recipe,
                               user_inputs=user_inputs,
                               show_save_options=True, # Keep save options
                               stores=stores,
                               zipcode=zipcode) # Pass zipcode back to pre-fill form

    except Exception as e:
        traceback.print_exc() # Print full traceback for debugging
        flash(f"An error occurred while finding grocery stores: {e}", 'error')
        # Re-render recipe_details with existing data
        return render_template('recipe_details.html',
                               meal_idea=session.get('current_meal_idea'),
                               recipe=format_recipe_for_display(session.get('current_recipe_data')),
                               user_inputs=session.get('user_inputs'),
                               show_save_options=True)


if __name__ == '__main__':
    app.run(debug=True)