from openai import OpenAI
import os

class CreateMeal:
    def __init__(self):
       
        self.client = OpenAI(api_key="") 
        
       
        self.model_name = 'gpt-4o-mini' 

    def create_meal(self, budget, mood,type_of_meal, tools, time, dietary_restrictions, base_idea=None, variation_prompt=None):
        """
        Generates a tailored meal idea based on user inputs using OpenAI API.
        """
        prompt = (
            f"As a culinary assistant for college students, suggest a personalized meal idea "
            f"considering the following:\n"
            f"- Budget: {budget}\n"
            f"- Type of Meal: {type_of_meal}\n"
            f"- Mood: {mood}\n"
            f"- Kitchen tools available: {', '.join(tools)}\n"
            f"- Time: {time}\n"
            f"- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}\n"
        )
       
        if base_idea and variation_prompt:
            prompt += f"Based on '{base_idea}', suggest a variation that is the same meal as '{base_idea}' but with the '{variation_prompt}' alteration.\n"

        prompt += "Please provide only the name of the meal, without any additional text or formatting."

        messages = [
            {"role": "system", "content": "You are a helpful culinary assistant for college students."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=50,
                temperature=0.7
            )
            meal_idea = response.choices[0].message.content.strip()
            return meal_idea
        except Exception as e:
            print(f"Error generating meal idea with OpenAI: {e}")
            return None

    def create_whole_recipe(self, meal_idea, type_of_meal, budget, tools, time, dietary_restrictions):
        """
        Generates a full recipe including ingredients, instructions, and cook time
        for a given meal idea, incorporating budget, tools, and dietary restrictions,
        using OpenAI API.
        """
        prompt_parts = [
            "You are a helpful culinary assistant for a college students who experience different situations. Generate a complete recipe.",
            f"The meal idea is: '{meal_idea}'.",
            f"The type of meal is: '{type_of_meal}'.",
            f"The user's budget is: {budget}.",
            f"Available kitchen tools: {', '.join(tools) if tools else 'None specified'}.",
            f"The user wants to spend this amount of time in minutes: {time}.",
            f"Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None specified'}.",
            "Please provide the recipe in the following markdown format:",
            "```",
            " ~ Recipe Title: [Name of Meal] ~",
            " Cook Time: [X] minutes",
            " Servings: [Y]",
            " Ingredients:",
            "- [Quantity] [Unit] [Ingredient 1]",
            "- [Quantity] [Unit] [Ingredient 2]",
            "- ...",
            "~ Instructions:~",
            "1. [Step 1]",
            "2. [Step 2]",
            "3. ...",
            "```",
            "Ensure all sections are present and follow the markdown structure precisely."
        ]
        
        messages = [
            {"role": "system", "content": "You are a helpful culinary assistant."},
            {"role": "user", "content": "\n".join(prompt_parts)}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error generating full recipe with OpenAI: {e}")
            return None

# Example Usage
if __name__ == "__main__":
    
    meal_generator = CreateMeal()

   
    budget = "low"
    type_of_meal = "lunch",
    mood = "tired"
    tools = ["microwave", "fork"]
    time = "10 minutes"
    dietary_restrictions = ["vegetarian"]
    
    print("Attempting to generate meal idea...")
    meal_idea = meal_generator.create_meal(type_of_meal,budget, mood, tools, time, dietary_restrictions)
    if meal_idea:
        print(f"Generated Meal Idea: {meal_idea}\n")
    else:
        print("Failed to generate meal idea.")

    # Test create_whole_recipe
    if meal_idea:
        print("Attempting to generate full recipe...")
        recipe = meal_generator.create_whole_recipe(meal_idea,type_of_meal, budget, tools, time, dietary_restrictions)
        if recipe:
            print(f"Generated Recipe:\n{recipe}")
        else:
            print("Failed to generate full recipe.")
    else:
        print("Skipping recipe generation as meal idea was not generated.")

    # Test with variation
    base_idea = "Instant Noodles"
    variation_prompt = "more gourmet with available tools"
    
    print("\nAttempting to generate variation meal idea...")
    variation_meal_idea = meal_generator.create_meal(
        type_of_meal,budget, mood, tools, time, dietary_restrictions, base_idea=base_idea, variation_prompt=variation_prompt
    )
    if variation_meal_idea:
        print(f"Generated Variation Meal Idea: {variation_meal_idea}")
    else:
        print("Failed to generate variation meal idea.")
