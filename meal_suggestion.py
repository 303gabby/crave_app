import google.generativeai as genai
import os

class CreateMeal:
    def __init__(self):
      
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def create_meal(self, budget, mood, tools, time, dietary_restrictions, base_idea=None, variation_prompt=None):
        """
        Generates a tailored meal idea based on user inputs.
        """
        prompt = (
            f"As a culinary assistant for college students, suggest a personalized meal idea "
            f"considering the following:\n"
            f"- Budget: {budget}\n"
            f"- Mood: {mood}\n"
            f"- Kitchen tools available: {', '.join(tools)}\n"
            f"- Time: {time}\n"
            f"- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}\n"
        )
        # If the user wants a variation, we add that to the prompt
        if base_idea and variation_prompt:
            prompt += f"Based on '{base_idea}', suggest a variation that is '{variation_prompt}'.\n"

        prompt += "Please provide only the name of the meal, without any additional text or formatting."

        try:
            # Send the prompt to the AI and get a response
            response = self.model.generate_content(prompt)
            meal_idea = response.text.strip()
            return meal_idea
        except Exception as e:
            print(f"Error generating meal idea with Google GenAI: {e}")
            return None

    def create_whole_recipe(self, meal_idea, budget, tools, time, dietary_restrictions):
        """
        Generates a full recipe including ingredients, instructions, and cook time
        for a given meal idea, incorporating budget, tools, and dietary restrictions.
        """
        prompt_parts = [
            "You are a helpful culinary assistant for a college students who experience different situations. Generate a complete recipe.",
            f"The meal idea is: '{meal_idea}'.",
            f"The user's budget is: {budget}.",
            f"Available kitchen tools: {', '.join(tools) if tools else 'None specified'}.",
            f"The user wants to spend this amount of time in minutes: {time}.",
            f"Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None specified'}.",
            "Please provide the recipe in the following markdown format:",
            "```",
            " * Recipe Title: [Name of Meal] *",
            " Cook Time: [X] minutes",
            " Servings: [Y]",
            " Ingredients:",
            "- [Quantity] [Unit] [Ingredient 1]",
            "- [Quantity] [Unit] [Ingredient 2]",
            "- ...",
            "* Instructions:*",
            "1. [Step 1]",
            "2. [Step 2]",
            "3. ...",
            "```",
            "Ensure all sections are present and follow the markdown structure precisely."
        ]

        try:
            response2 = self.model.generate_content(prompt_parts)
            return response2.text.strip()
        except Exception as e:
            print(f"Error generating full recipe with GenAI: {e}")
            return None
