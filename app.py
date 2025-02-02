from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import json

app = Flask(__name__)

GEMINI_API_KEY = "AIzaSyDSeG1cvRKbmrcOardxtuRkigjq9RQ-UBI"

def configure_gemini():
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    return model

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_recipe_suggestions', methods=['POST'])
def get_recipe_suggestions():
    ingredients = request.form.get('ingredients')
    filter_option = request.form.get('filter_option', 'None')

    if not ingredients:
        return jsonify({"error": "No ingredients provided"}), 400

    try:
        model = configure_gemini()
        
        # Enhanced filter conditions with medical precision
        filter_conditions = {
            "None": "",
            "Allergies": "Exclude all recipes containing common allergens (nuts, dairy, gluten, eggs, soy, shellfish, fish).",
            "Diabetic": """
                Only include recipes that meet these criteria:
                - Less than 45g of carbohydrates per serving
                - Low glycemic index ingredients (GI < 55 )
                - No added sugars or sweeteners
                - High in fiber (minimum 3g per serving)
                - Balanced with protein and healthy fats
                - Portion controlled (specify serving size)
                Focus on recipes using whole grains, lean proteins, and non-starchy vegetables.
                Display all of the nutritional benefits for diabetic people of this recipe.
                
            """,
            "Cholesterol": """
                Only include recipes that meet these criteria:
                - Less than 200mg cholesterol per serving
                - No trans fats
                - Limited saturated fats (less than 5g per serving)
                - No full-fat dairy products
                - Minimal use of oils (prefer olive oil if needed)
                - Rich in soluble fiber
                - Include heart-healthy ingredients like:
                  * Lean proteins (skinless poultry, fish)
                  * Whole grains
                  * Legumes
                  * Fresh vegetables and fruits
                Avoid or minimize:
                - Red meat
                - Egg yolks
                - Butter and margarine
                - Fried foods
                Display all of the nutritional benefits of this recipe for cholestrol patients.
            """
        }
        
        filter_text = filter_conditions.get(filter_option, "")
        
        prompt = f"""
        Given these ingredients: {ingredients}
        Create 6-8 recipes that can be made with these ingredients.
        {filter_text}
        
        Only include recipes where the main ingredients are available in the provided list.
        Additional common ingredients (salt, pepper, oil, etc.) can be assumed to be available.

        You must return the response in this exact JSON format:
        {{
            "recipes": [
                {{
                    "id": 1,
                    "name": "Recipe Name",
                    "description": "Brief 1-2 sentence description including key health benefits for the selected dietary restriction",
                    "difficulty": "Easy/Medium/Hard",
                    "time": "Total time in minutes"
                }},
                ... more recipes
            ]
        }}

        Ensure each recipe in the JSON:
        - Has a unique numeric id
        - Includes a descriptive name
        - Has a brief description mentioning health benefits
        - Specifies difficulty as either "Easy", "Medium", or "Hard"
        - Includes total time in minutes as a number

        The response must be valid JSON and match this format exactly.
        """

        response = model.generate_content(prompt)
        
        try:
            response_text = response.text
            start_idx = response_text.find('{')
            end_idx = response_text.rindex('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                recipes = json.loads(json_str)
            else:
                recipes = json.loads(response_text)
                
            if not isinstance(recipes, dict) or "recipes" not in recipes:
                return jsonify({"error": "Invalid response format from AI"}), 500
            
            return jsonify(recipes)
        except json.JSONDecodeError:
            return jsonify({"error": "Failed to parse recipe suggestions"}), 500
    except Exception as e:
        return jsonify({"error": f"Error generating recipes: {str(e)}"}), 500

@app.route('/get_full_recipe', methods=['POST'])
def get_full_recipe():
    recipe_name = request.form.get('recipe_name')
    ingredients = request.form.get('ingredients')
    filter_option = request.form.get('filter_option', 'None')

    if not recipe_name or not ingredients:
        return jsonify({"error": "Recipe name or ingredients not provided"}), 400

    try:
        model = configure_gemini()
        
        # Add specific health information based on filter
        health_info = ""
        if filter_option == "Diabetic":
            health_info = """
            Include per serving:
            - Total carbohydrates (g)
            - Fiber content (g)
            - Net carbs
            - Glycemic load estimate
            - Protein content
            Add tips for blood sugar management with this meal.
            """
        elif filter_option == "Cholesterol":
            health_info = """
            Include per serving:
            - Cholesterol content (mg)
            - Saturated fat content (g)
            - Fiber content (g)
            - Heart-healthy benefits of ingredients used
            Add tips for cholesterol management with this meal.
            """
            
        prompt = f"""
        Create a detailed recipe for "{recipe_name}" using these ingredients: {ingredients}.
        Format the response as HTML with proper semantic tags.
        Include:
        - Recipe name as h2
        - Preparation time
        - Cooking time
        - Difficulty level
        - Serving size and number of servings
        - Ingredients list (ul/li)
        - Step-by-step instructions (ol/li)
        - Tips or variations
        - Complete nutritional information per serving
        {health_info}
        """

        response = model.generate_content(prompt)
        return jsonify({"recipe": response.text})
    except Exception as e:
        return jsonify({"error": f"Error generating recipe: {str(e)}"}), 500

if __name__ == '__main__':
    app.debug = True
    app.run(port=5000)