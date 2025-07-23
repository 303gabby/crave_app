import requests
import os
import json
from meal_suggestion import CreateMeal

class CreateRecipe:
    def __init__(self):

    

        self.base_url = f"https://{self.api_host}"

        self.headers = {
            "X-RapidAPI-Host": self.api_host,
            "X-RapidAPI-Key": self.api_key
        }

        self.meal_suggestion = CreateMeal()

    def req_recipe_details(self, meal_idea, budget, tools, time, dietary_restrictions):
        """
        Fetches recipe details from Tasty API based on the meal idea and user preferences.
        If Tasty API fails or returns no results, it falls back to GenAI.
        """
        search_url = f"https://{self.api_host}/recipes/list"
        search_params = {
            "from": "0",
            "size": "1",
            "q": meal_idea
        }

        print(f"Searching Tasty for: '{meal_idea}'")

        tasty_recipe = None
        try:
            response = requests.get(search_url, headers=self.headers, params=search_params)
            response.raise_for_status()
            data = response.json()

            if data and data.get('results'):
                first_result = data['results'][0]
                recipe_id = first_result.get('id')
                recipe_name = first_result.get('name')

                if recipe_id:
                    print(f"Found recipe: '{recipe_name}' (ID: {recipe_id}). Fetching details from Tasty...")
                    tasty_recipe = self._req_recipe_by_id(recipe_id)
                else:
                    print("No ID found for the first recipe result from Tasty.")
            else:
                print(f"No suitable recipes found on Tasty for '{meal_idea}'.")

        except requests.exceptions.RequestException as e:
            if e.response is not None:
                print(f"Error fetching recipe from Tasty API: {e.response.status_code} - {e.response.text}")
            else:
                print(f"Error fetching recipe from Tasty API: {e}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response from Tasty API: {e}. Raw response: {response.text if 'response' in locals() else 'No response object.'}")

        if tasty_recipe:
            return tasty_recipe
        else:
            print("Will Generate a recipe based on your needs!")
            genai_recipe_text = self.meal_suggestion.create_whole_recipe(
                meal_idea, budget, tools, time, dietary_restrictions
            )

            if genai_recipe_text:
                print("AI-generated recipe received. Parsing...")
                ai_recipe = self._loop_genai_recipe(genai_recipe_text)
                return ai_recipe
            else:
                print("Failed to generate a full recipe from AI.")
                return None

    def _req_recipe_by_id(self, recipe_id):
        """
        Fetches detailed recipe information for a given recipe ID from Tasty API.
        """
        detail_url = f"https://{self.api_host}/recipes/get-more-info"
        detail_params = {
            "id": str(recipe_id)
        }

        try:
            response = requests.get(detail_url, headers=self.headers, params=detail_params)
            response.raise_for_status()
            recipe_data = response.json()

            if recipe_data:
                return self._loop_tasty_recipe(recipe_data)
            else:
                print(f"No detailed information found for recipe ID: {recipe_id}")
                return None
        except requests.exceptions.RequestException as e:
            if e.response is not None:
                print(f"Error fetching detailed recipe by ID from Tasty API: {e.response.status_code} - {e.response.text}")
            else:
                print(f"Error fetching detailed recipe by ID from Tasty API: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response from Tasty API for ID {recipe_id}: {e}. Raw response: {response.text if 'response' in locals() else 'No response object.'}")
            return None

    def _loop_tasty_recipe(self, tasty_data):
        """
        Parses the raw JSON data from Tasty API into a consistent dictionary format for Crave.
        """
        looped_recipe = {
            'title': tasty_data.get('name', 'N/A'),
            'servings': tasty_data.get('num_servings', 'N/A'),
            'readyInMinutes': tasty_data.get('total_time_minutes', 'N/A'),
            'sourceUrl': tasty_data.get('canonical_url', 'N/A'),
            'image': tasty_data.get('thumbnail_url', None),
            'extendedIngredients': [],
            'instructions': '',
        }

        # Ingredients parsing
        if 'sections' in tasty_data:
            for section in tasty_data['sections']:
                if 'components' in section:
                    for component in section['components']:
                        ingredient_name = component.get('raw_text', '')
                        if ingredient_name:
                            looped_recipe['extendedIngredients'].append({
                                'originalName': ingredient_name,
                                'amount': '',
                                'unit': ''
                            })

        # Instructions parsing
        if 'instructions' in tasty_data:
            steps_list = []
            for i, instruction_step in enumerate(tasty_data['instructions']):
                display_text = instruction_step.get('display_text', '').strip()
                if display_text:
                    steps_list.append(f"Step {i+1}: {display_text}")
            looped_recipe['instructions'] = "\n".join(steps_list)
        else:
            looped_recipe['instructions'] = "No detailed instructions available."

        return looped_recipe

    def _loop_genai_recipe(self, genai_text):
        """
        Parses the markdown-formatted text response from GenAI into a dictionary
        consistent with the expected recipe structure for Crave.
        """
        looped_ai_recipe = {
            'title': 'AI Generated Recipe',
            'servings': 'N/A',
            'readyInMinutes': 'N/A',
            'sourceUrl': 'AI Generated',
            'extendedIngredients': [],
            'instructions': '',
            'nutrition': {'nutrients': []}
        }

        lines = genai_text.split('\n')
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Identify sections based on common headings
            if line.startswith("* Recipe Title:"):
                try:
                    looped_ai_recipe['title'] = line.replace("* Recipe Title:", "").replace("*", "").strip()
                except IndexError:
                    pass
                current_section = 'title'
            elif line.startswith("Cook Time:"):
                time_str = line.replace("Cook Time:", "").strip()
                if "minutes" in time_str.lower():
                    try:
                        looped_ai_recipe['readyInMinutes'] = int(time_str.lower().replace("minutes", "").strip())
                    except ValueError:
                        looped_ai_recipe['readyInMinutes'] = time_str
                else:
                    looped_ai_recipe['readyInMinutes'] = time_str
                current_section = 'cook_time'
            elif line.startswith("Servings:"):
                looped_ai_recipe['servings'] = line.replace("Servings:", "").strip()
                current_section = 'servings'
            elif line.startswith("Nutritonal Facts:"):
                nutrition_summary = line.replace("Nutritonal Facts:", "").strip()
                if nutrition_summary and nutrition_summary != '[Z]':
                    looped_ai_recipe['nutrition']['nutrients'].append({
                        'name': 'Summary',
                        'amount': nutrition_summary,
                        'unit': ''
                    })
                current_section = 'nutrition'
            elif line.startswith("Ingredients:"):
                current_section = 'ingredients'
            elif line.startswith("* Instructions:*"):
                current_section = 'instructions'
            elif line.startswith("1."):
                if current_section != 'instructions':
                    looped_ai_recipe['instructions'] += line + "\n"
                    current_section = 'instructions'
                else:
                    looped_ai_recipe['instructions'] += line + "\n"
            else:
                if current_section == 'ingredients' and line.startswith('- '):
                    looped_ai_recipe['extendedIngredients'].append({
                        'originalName': line[2:].strip(),
                        'amount': '',
                        'unit': ''
                    })
                elif current_section == 'instructions':
                    looped_ai_recipe['instructions'] += line + "\n"

        looped_ai_recipe['instructions'] = looped_ai_recipe['instructions'].strip()
        return looped_ai_recipe
