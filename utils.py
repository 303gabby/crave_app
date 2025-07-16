def format_recipe_for_display(recipe_data):
    """
    Formats the detailed recipe information for display in HTML.
    Returns an HTML string or a dictionary of formatted parts.
    """
    if not recipe_data:
        return "No recipe data to display."

    ingredients_html = "<ul>"
    if 'extendedIngredients' in recipe_data:
        for ingredient in recipe_data['extendedIngredients']:
            amount = ingredient.get('amount', '')
            unit = ingredient.get('unit', '')
            name = ingredient.get('originalName', '')
            ingredients_html += f"<li>{amount} {unit} {name}</li>"
    else:
        ingredients_html += "<li>No ingredients listed.</li>"
    ingredients_html += "</ul>"

    instructions_html = "<ol>"
    if 'instructions' in recipe_data and recipe_data['instructions']:
        # Assuming instructions are line-separated steps from GenAI or Tasty
        steps = recipe_data['instructions'].split('\n')
        for step in steps:
            if step.strip(): # Avoid empty list items
                instructions_html += f"<li>{step.strip()}</li>"
    elif 'analyzedInstructions' in recipe_data and recipe_data['analyzedInstructions']:
        for instruction_set in recipe_data['analyzedInstructions']:
            for step in instruction_set.get('steps', []):
                instructions_html += f"<li>Step {step.get('number')}: {step.get('step')}</li>"
    else:
        instructions_html += "<li>No instructions available.</li>"
    instructions_html += "</ol>"

    nutrition_html = "<ul>"
    if 'nutrition' in recipe_data and 'nutrients' in recipe_data['nutrition']:
        for nutrient in recipe_data['nutrition']['nutrients']:
            if nutrient['name'] in ['Calories', 'Protein', 'Fat', 'Carbohydrates'] or nutrient['name'] == 'Summary':
                nutrition_html += f"<li>{nutrient['name']}: {nutrient['amount']}{nutrient['unit']}</li>"
    else:
        nutrition_html += "<li>Nutritional information not available.</li>"
    nutrition_html += "</ul>"

    return {
        'title': recipe_data.get('title', 'N/A'),
        'servings': recipe_data.get('servings', 'N/A'),
        'readyInMinutes': recipe_data.get('readyInMinutes', 'N/A'),
        'sourceUrl': recipe_data.get('sourceUrl', 'N/A'),
        'image': recipe_data.get('image', None),
        'ingredients_html': ingredients_html,
        'instructions_html': instructions_html,
        'nutrition_html': nutrition_html
    }

def format_history_for_display(history):
    """
    Formats the recipe history for display in HTML.
    """
    if not history:
        return "No past meals found."

    history_html = ""
    for i, meal in enumerate(history):
        history_html += f"<div class='history-entry'>"
        history_html += f"<h3>Meal {i+1} (Cooked on: {meal['timestamp']})</h3>"
        history_html += f"<p><strong>Meal Idea:</strong> {meal['meal_idea']}</p>"
        history_html += f"<p><strong>Your Inputs:</strong></p>"
        history_html += "<ul>"
        for key, value in meal['user_inputs'].items():
            if isinstance(value, list):
                history_html += f"<li>{key.replace('_', ' ').title()}: {', '.join(value)}</li>"
            else:
                history_html += f"<li>{key.replace('_', ' ').title()}: {value}</li>"
        history_html += "</ul>"
        history_html += f"<p><strong>Recipe Name:</strong> {meal['recipe_data'].get('title', 'N/A')}</p>"
        history_html += "</div><hr>"
    return history_html