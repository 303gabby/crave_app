from flask import (
    Flask, render_template, request, redirect, url_for, session, jsonify, flash
)
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
import requests 
from datetime import timedelta
import openai 
from dotenv import load_dotenv 
import traceback 


load_dotenv()

from meal_suggestion import CreateMeal
from recipe_creation import CreateRecipe
from database import Database
from utils import format_recipe_for_display 

app = Flask(__name__)

# --- Secret Keys & JWT Configuration ---

app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))


app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'a-very-strong-default-jwt-secret-for-dev')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

jwt = JWTManager(app)

openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 

db = Database()
db.create_tables() 
meal_suggestion_service = CreateMeal()
recipe_creation_service = CreateRecipe()

# --- Routes ---

@app.route('/')
def index():

    session.pop('current_meal_idea', None)
    session.pop('user_inputs', None)
    session.pop('current_recipe_data', None)

  
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
            session['user_id'] = user['id'] 
            session['username'] = user['username'] 

            
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

        session['current_recipe_data'] = recipe_data

        formatted_recipe = format_recipe_for_display(recipe_data)
        return render_template('recipe_details.html',
                               meal_idea=meal_idea,
                               recipe=formatted_recipe,
                               user_inputs=user_inputs,
                               show_save_options=True) 

   
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
    base_idea = session['current_meal_idea'] 
    original_recipe_data = session['current_recipe_data'] 
    variation_prompt = request.form['variation_prompt']

    # Corrected order for create_meal arguments
    new_meal_idea = meal_suggestion_service.create_meal(
        user_inputs['budget'], user_inputs['mood'], user_inputs['type_of_meal'], user_inputs['tools'],
        user_inputs['time'], user_inputs['dietary_restrictions'],
        base_idea=base_idea, variation_prompt=variation_prompt
    )

    if not new_meal_idea:
        flash("Could not generate a variation idea. Please try again.", 'error')

        formatted_recipe = format_recipe_for_display(original_recipe_data)
        return render_template('recipe_details.html',
                               meal_idea=base_idea, 
                               recipe=formatted_recipe,
                               user_inputs=user_inputs,
                               show_save_options=True) 


    session['current_meal_idea'] = new_meal_idea

    variation_recipe_data = recipe_creation_service.req_recipe_details(
        new_meal_idea, user_inputs['type_of_meal'], user_inputs['budget'], user_inputs['tools'],
        user_inputs['time'], user_inputs['dietary_restrictions']
    )

    if variation_recipe_data:
        session['current_recipe_data'] = variation_recipe_data 
        formatted_recipe = format_recipe_for_display(variation_recipe_data)
        return render_template('recipe_details.html',
                               meal_idea=new_meal_idea, 
                               recipe=formatted_recipe,
                               user_inputs=user_inputs,
                               show_save_options=True) 
    else:
        flash(f"Could not find a recipe for the variation: '{new_meal_idea}'. Please try a different prompt.", 'error')
       
        session.pop('current_recipe_data', None) # Clear it if no recipe found for this variation
        return render_template('recipe_details.html',
                               meal_idea=new_meal_idea, 
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
    recipe_data = session.get('current_recipe_data') 

    if not all([meal_idea, user_inputs, recipe_data]):
        flash("No valid recipe data in session to save. Please generate a new one.", 'error')
        return redirect(url_for('create_recipe_page'))

    user_id = session['user_id'] 

    try:
        db.save_meal(
            meal_idea=meal_idea,
            user_inputs=user_inputs,
            recipe_data=recipe_data, 
            user_id=user_id 
        )
        flash("Recipe saved successfully!", 'success')
     
        session.pop('current_meal_idea', None)
        session.pop('user_inputs', None)
        session.pop('current_recipe_data', None)
    except ValueError as e: 
        flash(f"Error saving recipe: {e}", 'error')
    except Exception as e:
        flash(f"An unexpected error occurred while saving: {e}", 'error')

    return redirect(url_for('view_history'))


@app.route('/discard_current_recipe', methods=['POST'])
def discard_current_recipe():

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

    user_id = session['user_id'] 
    history = db.meal_history(user_id) 


    return render_template('history.html', history_data=history)


@app.route('/delete_meal/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    if 'user_id' not in session:
        flash('Please login to delete recipes.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    try:
        success = db.delete_meal(meal_id, user_id)
        if success:
            flash(f'Recipe deleted successfully!', 'success')
        else:
            flash(f'Recipe not found or you do not have permission to delete it.', 'error')
    except ValueError as e: 
        flash(f"Error deleting recipe: {e}", 'error')
    except Exception as e:
        flash(f"An unexpected error occurred while deleting: {e}", 'error')

    return redirect(url_for('view_history'))



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
        "radius": 5000, 
        "type": "grocery_or_supermarket", 
        "key": api_key
    }

    try:
        response = requests.get(nearby_url, params=nearby_params)
        data = response.json()
        stores = []

        if data['status'] == 'OK':
            for place in data['results'][:5]: 
               
                place_id = place['place_id']
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_params = {
                    "place_id": place_id,
                    "fields": "name,vicinity,opening_hours,url", 
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
                        "google_maps_url": result.get("url", "#") 
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
                                   show_save_options=True) 

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
                               show_save_options=True, 
                               stores=stores,
                               zipcode=zipcode) 

    except Exception as e:
        traceback.print_exc()
        flash(f"An error occurred while finding grocery stores: {e}", 'error')
   
        return render_template('recipe_details.html',
                               meal_idea=session.get('current_meal_idea'),
                               recipe=format_recipe_for_display(session.get('current_recipe_data')),
                               user_inputs=session.get('user_inputs'),
                               show_save_options=True)


if __name__ == '__main__':
    app.run(debug=True)