# main/tests/test_logic.py

import pytest
from unittest.mock import patch, MagicMock, mock_open
# Uwaga: importujemy z kropką jeśli uruchamiamy jako moduł, lub bez jeśli z folderu
from main.logic import (
    analyze_fridge_process,
    plan_recipes_with_ai,
    fetch_spoonacular_recipes,
    generate_shopping_list,
    save_meal_to_db,
    IdentifiedItem,
    FridgeAnalysis,
    SearchPlans,
    RecipeSearchPlan
)

# --- 1. Testy Logiki ---
def test_generate_shopping_list():
    recipe = {"extendedIngredients": [{"nameClean": "chicken"}, {"nameClean": "salt"}]}
    fridge = ["chicken"]
    have, missing = generate_shopping_list(recipe, fridge)
    assert len(have) == 2  # Chicken + Salt (staple)
    assert len(missing) == 0

# --- 2. Testy AI ---

@patch("main.logic.client")
def test_analyze_fridge_process_success(mock_client):
    """Sprawdza czy analiza zwraca wynik i ID pliku."""
    
    mock_analysis = FridgeAnalysis(
        identified_items=[], clarification_questions=[], ready_to_search=True
    )
    mock_client.files.create.return_value.id = "file_123"
    mock_client.responses.parse.return_value.output_parsed = mock_analysis

    # POPRAWKA: Mockujemy open TYLKO tutaj, żeby nie zepsuć load_dotenv
    with patch("builtins.open", new_callable=mock_open, read_data=b"img_data"):
        result, file_id = analyze_fridge_process("fake.jpg")

    assert result == mock_analysis
    assert file_id == "file_123"

@patch("main.logic.client")
def test_plan_recipes_with_ai_constraints(mock_client):
    """Sprawdza czy restrykcje usera trafiają do promptu."""
    
    mock_profile = MagicMock()
    mock_profile.goal = "muscle_gain"
    
    mock_plans = SearchPlans(plans=[RecipeSearchPlan(ingredients=["egg"], reason="Food")])
    mock_client.responses.parse.return_value.output_parsed = mock_plans

    plan_recipes_with_ai(["egg"], mock_profile)

    # Sprawdzamy prompt
    call_args = mock_client.responses.parse.call_args
    sent_messages = call_args[1]['input']
    system_prompt = sent_messages[0]['content']
    assert "muscle_gain" in system_prompt

# --- 3. Testy Bazy Danych ---

def test_save_meal_to_db_success(test_db):
    """
    Testuje zapis używając PRAWDZIWEJ (w pamięci) bazy danych z conftest.py.
    """
    
    # POPRAWKA: Podmieniamy get_db w logic.py, aby zwracało naszą bazę testową
    # zamiast tworzyć nową sesję do pliku nowaste.db
    with patch("main.logic.get_db", return_value=test_db):
        
        recipe = {
            "title": "Test Pasta",
            "nutrition": {"nutrients": [{"name": "Calories", "amount": 400}]}
        }

        result = save_meal_to_db(recipe, rating=10, notes="Ok")

        assert result is True
        
        # Sprawdzamy w bazie czy faktycznie siedzi
        from main.database import MealLog
        saved = test_db.query(MealLog).first()
        assert saved is not None
        assert saved.recipe_name == "Test Pasta"