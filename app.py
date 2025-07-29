from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from meal_suggestion import CreateMeal
from recipe_creation import CreateRecipe
from database import Database
from utils import format_recipe_for_display, format_history_for_display
import os
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-string')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

jwt = JWTManager(app)


db = Database()
meal_suggestion_service = CreateMeal()
recipe_creation_service = CreateRecipe()


@app.route('/')
def index():
   
    return render_template('index.html')

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
            flash('All fields are required')
            return render_template('register.html')
        
        try:
            user_id = db.create_user(username, email, password)
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        except ValueError as e:
            flash(str(e))
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Username and password are required')
            return render_template('login.html')
        
        user = db.get_user_by_username(username)
        if user and db.verify_password(user, password):
            access_token = create_access_token(identity=user['id'])
            session['access_token'] = access_token
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/create_recipe_page', methods=['GET', 'POST'])
def create_recipe_page():
    if 'user_id' not in session:
        flash('Please login to create recipes')
        return redirect(url_for('login'))
    if request.method == 'POST':
        # Get user inputs from the form
        type_of_meal = request.form['type_of_meal']
        budget = request.form['budget']
        mood = request.form['mood']
        tools = [t.strip() for t in request.form['tools'].split(',') if t.strip()]
        time = request.form['time']
        dietary_restrictions = [d.strip() for d in request.form['dietary_restrictions'].split(',') if d.strip()]

        session['user_inputs'] = {
            'type_of_meal': type_of_meal,
            'budget': budget,
            'mood': mood,
            'tools': tools,
            'time': time,
            'dietary_restrictions': dietary_restrictions
        }

        meal_idea = meal_suggestion_service.create_meal(
            type_of_meal,budget, mood, tools, time, dietary_restrictions
        )

        if not meal_idea:
            
            return render_template('create_recipe.html', error_message="Sorry, couldn't come up with a meal idea. Please try again with different preferences.")

        session['current_meal_idea'] = meal_idea

        recipe_data = recipe_creation_service.req_recipe_details(
            meal_idea, type_of_meal, budget, tools, time, dietary_restrictions
        )

        if not recipe_data:
            
            return render_template('create_recipe.html', error_message="Couldn't find or generate a suitable recipe. Please try a different meal idea or adjust your preferences.")

        db.save_meal(
            meal_idea=meal_idea,
            user_inputs=session['user_inputs'],
            recipe_data=recipe_data,
            user_id=session['user_id']
        )

        formatted_recipe = format_recipe_for_display(recipe_data)
        return render_template('recipe_details.html', recipe=formatted_recipe, meal_idea=meal_idea)

    return render_template('create_recipe.html')

@app.route('/history')
def view_history():
    if 'user_id' not in session:
        flash('Please login to view history')
        return redirect(url_for('login'))
    
    history = db.meal_history(session['user_id'])
    formatted_history = format_history_for_display(history)
    return render_template('history.html', history_html=formatted_history)

@app.route('/variation', methods=['POST'])
def variation():
    if 'user_id' not in session:
        flash('Please login to create variations')
        return redirect(url_for('login'))
    
    if 'user_inputs' not in session or 'current_meal_idea' not in session:
        return redirect(url_for('create_recipe_page'))

    user_inputs = session['user_inputs']
    base_idea = session['current_meal_idea']
    variation_prompt = request.form['variation_prompt']

    new_meal_idea = meal_suggestion_service.create_meal(
        user_inputs['type_of_meal'],user_inputs['budget'], user_inputs['mood'], user_inputs['tools'],
        user_inputs['time'], user_inputs['dietary_restrictions'],
        base_idea=base_idea, variation_prompt=variation_prompt
    )

    if not new_meal_idea:
        return render_template(
            'recipe_details.html',
            recipe=format_recipe_for_display(recipe_creation_service.req_recipe_details(base_idea, **user_inputs)),
            error_message="Could not generate a variation. Please try again."
        )

    session['current_meal_idea'] = new_meal_idea

    variation_recipe_data = recipe_creation_service.req_recipe_details(
        new_meal_idea, user_inputs['type_of_meal'],user_inputs['budget'], user_inputs['tools'],
        user_inputs['time'], user_inputs['dietary_restrictions']
    )

    if variation_recipe_data:
        db.save_meal(
            meal_idea=new_meal_idea,
            user_inputs=user_inputs,
            recipe_data=variation_recipe_data,
            user_id=session['user_id']
        )
        formatted_recipe = format_recipe_for_display(variation_recipe_data)
        return render_template('recipe_details.html', recipe=formatted_recipe, meal_idea=new_meal_idea)
    else:
        return render_template(
            'recipe_details.html',
            recipe=format_recipe_for_display(recipe_creation_service.req_recipe_details(base_idea, **user_inputs)),
            error_message="Could not find a recipe for this variation."
        )

if __name__ == '__main__':
    app.run(debug=True)
