from flask import Flask, render_template, request, redirect, url_for, session
from meal_suggestion import CreateMeal
from recipe_creation import CreateRecipe
from database import Database
from utils import format_recipe_for_display, format_history_for_display
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)


db = Database()
meal_suggestion_service = CreateMeal()
recipe_creation_service = CreateRecipe()


@app.route('/')
def index():
   
    return render_template('index.html')

@app.route('/about')
def about():
   
    return render_template('about.html')

@app.route('/create_recipe_page', methods=['GET', 'POST'])
def create_recipe_page():
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
            recipe_data=recipe_data
        )

        formatted_recipe = format_recipe_for_display(recipe_data)
        return render_template('recipe_details.html', recipe=formatted_recipe, meal_idea=meal_idea)

    return render_template('create_recipe.html')

@app.route('/history')
def view_history():
    history = db.meal_history()
    formatted_history = format_history_for_display(history)
    return render_template('history.html', history_html=formatted_history)

@app.route('/variation', methods=['POST'])
def variation():
    
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
            recipe_data=variation_recipe_data
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
