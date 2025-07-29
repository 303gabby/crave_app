from flask import (
    Flask, render_template, request, redirect, url_for, session, jsonify, flash
)
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os
from datetime import timedelta

from meal_suggestion import CreateMeal
from recipe_creation import CreateRecipe
from database import Database
from utils import format_recipe_for_display

app = Flask(__name__)

app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'a-very-strong-default-jwt-secret-for-dev')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

jwt = JWTManager(app)

# Database and Service Initialization
db = Database()
db.create_tables()
meal_suggestion_service = CreateMeal()
recipe_creation_service = CreateRecipe()

# --- Routes ---

@app.route('/')
def index():
    # Clear any temporary recipe data from session when returning home
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

        session.pop('current_recipe_data', None)
        return render_template('recipe_details.html',
                               meal_idea=new_meal_idea,
                               recipe=None,
                               user_inputs=user_inputs,
                               show_save_options=False)


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


if __name__ == '__main__':
    app.run(debug=True)