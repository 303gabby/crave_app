# Crave Web Application

## Overview
Crave helps college students cook delicious, affordable meals based on their budget, mood, tools, time, and diet. Powered by the OpenAI, Tasty and Google Places APIs, if we can't find a suitable recipe, we'll create an AI-generated one. Bon appétit!

---

## Live Application

Crave is currently deployed and accessible live on Render:
**https://crave-app-jvkm.onrender.com/**

---

## Key Features

### Personalized Recipe Generation
Crave allows users to input several preferences to get personalized meal suggestions:

* **Budget:** Choose from predefined budget ranges (e.g., $5, $10, $30).
* **Type of Meal:** Specify if you're looking for breakfast, lunch, or dinner.
* **Diet Type:** Accommodates various dietary preferences (e.g., vegetarian, gluten-free, etc.).
* **Kitchen Tools:** Select available tools (e.g., stovetop, microwave only, fridge, etc.) to ensure practical recipe suggestions.
* **Time for Cooking:** Filter recipes based on preparation time (e.g., under 10 mins, 10–50 mins, etc.).

### User Accounts & Management
* **Personalized Accounts:** Users can register and log in to save their preferences and track their recipes across sessions.
* **Save Feature:** Users have full control over their recipe history. They can choose to save newly generated recipes or remove them from their history.

### Utility Features
* **Grocery Store Finder:** Missing an ingredient? Users can enter their ZIP code to see a list of nearby grocery stores along with their operating hours.

---

## Target Audience

This website is specifically aimed at college students, offering practical and affordable meal solutions tailored to their needs.

---

## Technologies Used

* **Backend:** Python (Flask framework)
* **Frontend:** HTML, CSS, JavaScript (Jinja2 for templating)
* **Database:** SQLite
* **APIs:** OpenAI API, Tasty API, Google Places API

---

## Setup and Installation (for local development)

To get Crave up and running on your local machine for development:

1.  **Clone the repository:**
    ```bash
    git clone
    cd crave_app-2
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  
    # For Windows Command Prompt: venv\Scripts\activate
    # For Windows PowerShell: venv\Scripts\Activate.ps1
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up API Keys:**
    Create a `.env` file in the root of your project and add your API keys:
    ```
    OPENAI_API_KEY
    TASTY_API_KEY
    GOOGLE_API_KEY 
    ```

5.  **Run the application:**
    ```bash
    flask run
    ```
    The application should now be accessible at `http://127.0.0.1:5000/` in your web browser. The `crave.db` database file will be automatically created and tables set up on the first run if it doesn't exist.

---

## Usage

Once the application is running (either locally or on Render):

* Navigate to the application's URL.
* You can register a new account or log in if you already have one.
* After, from the homepage, navigate to **"Create a New Recipe"** to input your preferences and generate a personalized meal.
* Use **"View Recipe History"** to see all your saved recipes.
* On a recipe details page, you can utilize the **"Grocery Store Finder"** by entering your ZIP code to find nearby stores.

---

