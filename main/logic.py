import os
import requests
import json
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Literal
from dotenv import load_dotenv

from database import get_db, MealLog

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


class IdentifiedItem(BaseModel):
    name_en_clean: str = Field(
        description="ONLY the core ingredient keyword in English "
                    "(e.g. 'eggs', 'milk', 'chicken breast'). "
                    "NO packaging, brands, or containers."
    )
    name_pl: str = Field(
        description="Ingredient name in Polish (for UI)."
    )
    quantity_estimated: Optional[str] = Field(
        description="Estimated quantity in Polish (e.g. '2 sztuki', 'ok. 200g'). "
                    "Use null if not possible."
    )
    confidence_level: Literal["high", "medium", "low"] = Field(
        description="Confidence level of visual recognition."
    )
    needs_clarification: bool = Field(
        description="True if the ingredient is ambiguous or unclear."
    )
    is_staple: bool = Field(
        description="True if ingredient is a basic kitchen staple "
                    "(spices, oils, sauces, sugar, flour, etc.)."
    )

class FridgeAnalysis(BaseModel):
    identified_items: List[IdentifiedItem]
    clarification_questions: List[str] = Field(
        description="Questions for the user if something is unclear in polish"
        )
    ready_to_search: bool = Field(
        description="True ONLY if no clarification is needed and "
                    "core ingredients are confidently identified."
    )

class RecipeSearchPlan(BaseModel):
    ingredients: list[str]
    reason: str 

class SearchPlans(BaseModel):
    plans: list[RecipeSearchPlan]

def analyze_fridge_process(image_path: str):
    """
    Initial fridge analysis using GPT vision.
    Returns FridgeAnalysis or None on error.
    """
    if not OPENAI_API_KEY:
        print("Błąd: Brak klucza OpenAI.")
        return None
    
    try:

        with open(image_path, "rb") as f:
            file_res = client.files.create(
                file=f,
                purpose="vision"
            )

        system_prompt = """
        Jesteś inteligentnym asystentem kulinarnym analizującym zdjęcie lodówki lub blatu.

        TWOJE ZADANIE:
        1. Zidentyfikuj wszystkie widoczne produkty spożywcze.
        2. Każdy produkt opisz jako osobny obiekt.

        ZASADY NAZW:
        - Pole `name_en_clean` MUSI zawierać WYŁĄCZNIE główny składnik kulinarny po angielsku
        (np. 'eggs', 'milk', 'chicken breast', 'bell pepper').
        - NIGDY nie dodawaj informacji o opakowaniu, marce ani formie
        ('carton', 'jar', 'package').
        - `name_en` może być bardziej opisowe, ale zgodne z tym samym składnikiem.
        - `name_pl` ma być przyjazne dla użytkownika.

        STAPLES (POMIJANE PRZY WYSZUKIWANIU PRZEPISÓW):
        Oznacz `is_staple = true` dla produktów, które:
        - są przyprawami (sól, pieprz, papryka, oregano, curry)
        - są olejami lub tłuszczami (olej, oliwa, masło)
        - są sosami (ketchup, musztarda, majonez, sos sojowy)
        - są słodzikami (cukier, miód, syrop klonowy)
        - są produktami technicznymi (mąka, drożdże, proszek do pieczenia)

        ILOŚĆ:
        - Podaj realistyczne oszacowanie ilości po polsku.
        - Jeśli to niemożliwe, użyj null.

        PEWNOŚĆ I PYTANIA:
        - Jeśli nie masz pewności, ustaw confidence_level na 'medium' lub 'low'.
        - Jeśli produkt jest niejednoznaczny (np. zawartość słoika),
        ustaw needs_clarification = true i dodaj pytanie po polsku.

        WARUNEK GOTOWOŚCI:
        - ready_to_search = true TYLKO jeśli:
        • brak otwartych pytań
        • kluczowe składniki mają confidence 'high' lub 'medium'
        """

        user_prompt = "Zidentyfikuj produkty spożywcze widoczne na zdjęciu."

        msg = [
            {"role": "developer", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_prompt},
                    {"type": "input_image", "file_id": file_res.id},
                ],
            }
        ]

        try:
            response = client.responses.parse(
                model="gpt-5-mini",
                input=msg,
                text_format=FridgeAnalysis
            )

            return response.output_parsed, file_res.id

        except Exception as e:
            print(f"[ERROR] Fridge analysis failed ({analyze_fridge_process.__name__}): {e}")
            return None, None
    except Exception as e:
        print(f"API error ({analyze_fridge_process.__name__}): {e}")
        return None, None
    
def refine_analysis_process(
    file_id: str,
    previous_analysis: FridgeAnalysis,
    user_answers: str
) -> Optional[FridgeAnalysis]:
    """
    Refinement loop: updates analysis based on user answers.
    """

    if not file_id:
        print("No file id!")
        return None
    
    system_prompt = """
    Jesteś inteligentnym asystentem kulinarnym.

    Użytkownik odpowiedział na Twoje pytania dotyczące poprzedniej analizy zdjęcia.

    ZASADY:
    - Zachowaj wszystkie poprawnie zidentyfikowane składniki.
    - Popraw lub uzupełnij TYLKO elementy, które były niejasne.
    - Nie dodawaj nowych produktów, jeśli nie wynikają z obrazu lub odpowiedzi użytkownika.

    NAZWY:
    - `name_en_clean` MUSI pozostać czystą nazwą składnika (bez opakowań).
    - Staples oznacz jako `is_staple = true`.

    CEL:
    - Zwróć kompletny obiekt typu FridgeAnalysis.
    - Jeśli wszystkie kluczowe składniki są już jasne,
    ustaw ready_to_search = true.
    """

    # Konwertujemy poprzedni obiekt Pydantic na JSON string
    prev_json = previous_analysis.model_dump_json()

    user_content = (
        f"Poprzednia analiza (JSON):\n{prev_json}\n\n"
        f"Odpowiedzi użytkownika:\n{user_answers}\n\n"
        "Zaktualizuj analizę."
    )

    msg = [
        {"role": "developer", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": user_content},
                {"type": "input_image", "file_id": file_id},
            ],
        }
    ]

    try:
        response = client.responses.parse(
            model="gpt-5-mini",
            input=msg,
            text_format=FridgeAnalysis
        )

        return response.output_parsed

    except Exception as e:
        print(f"[ERROR] Refinement failed ({refine_analysis_process.__name__}): {e}")
        return None
    
def plan_recipes_with_ai(ingredients: List[str], user_profile=None) -> Optional[SearchPlans]:
    """
    Generuje 3 pomysły na dania na podstawie składników, uwzględniając profil użytkownika.
    Złożona logika z notebooka: unikanie powtórzeń, limity składników, restrykcje.
    """
    
    # 1. Budowanie kontekstu profilu (Cel + Restrykcje)
    if user_profile:
        # Pobieramy dane z obiektu bazy danych (SQLAlchemy)
        goal = getattr(user_profile, 'goal', 'maintenance')
        restrictions = getattr(user_profile, 'dietary_restrictions', '') or "brak"
        profile_text = f"Goal: {goal}, Dietary Restrictions: {restrictions}"
    else:
        profile_text = "Goal: maintenance, Restrictions: None"

    # 2. Rozbudowany Prompt (Systemowy)
    system_prompt = f"""
    You are a culinary expert.
    From the provided ingredients, create 3 reasonable ingredient sets
    (each max 4 ingredients) that could realistically form a tasty dish.

    RULES:
    - Ignore spices, oils, sauces, water, flour etc. (assume user has staples).
    - Prefer protein + carb + vegetable combinations.
    - Do NOT try to use all ingredients at once.
    - For each set try to use DIFFERENT ingredients if possible.
    - Provide a short 'reason' in Polish describing the dish idea (e.g. 'Jajecznica z warzywami').

    CRITICAL CONSTRAINTS:
    - Ingredient overlap between sets must be minimal.
    - Each set must represent a DIFFERENT type of dish (e.g. breakfast, lunch, dinner).
    - STRICTLY RESPECT DIETARY RESTRICTIONS: {profile_text}
    """

    try:
        response = client.responses.parse(
            model="gpt-4o",  # Używamy gpt-4o lub gpt-4o-mini
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps({"ingredients": ingredients})}
            ],
            text_format=SearchPlans,
            temperature=0.85 #
        )
        return response.output_parsed
    except Exception as e:
        print(f"ERROR AI ({plan_recipes_with_ai.__name__})): {e}")
        return None

def get_nutrient(rec, name) -> float:
    for n in rec.get("nutrition", {}).get("nutrients", []):
        if n.get("name") == name: return n.get("amount", 0)
    return 0

def fetch_spoonacular_recipes(plans: SearchPlans, user_profile):
    """
    Zaawansowane pobieranie przepisów:
    1. findByIngredients (szukanie po składnikach)
    2. informationBulk (szczegóły + makro)
    3. Filtrowanie (kalorie, białko, cel użytkownika)
    """
    results_list = []
    
    find_params = {
        "apiKey": SPOONACULAR_API_KEY,
        "number": 5,
        "ranking": 2,
        "ignorePantry": True
    }

    api_limit_reached = False

    for i, plan in enumerate(plans.plans):
        if api_limit_reached: break
        
        # Spoonacular najlepiej działa z max 4 składnikami w zapytaniu
        safe_ings = plan.ingredients[:4]
        plan.ingredients = safe_ings
        
        current_find_params = find_params.copy()
        current_find_params['ingredients'] = ",".join(safe_ings)
        
        try:
            # Etap 1: Szukanie ID przepisów
            r_find = requests.get("https://api.spoonacular.com/recipes/findByIngredients", params=current_find_params)
            r_find.raise_for_status()
            find_data = r_find.json()
            if not find_data: continue

            recipe_ids = [str(item['id']) for item in find_data]
            ids_string = ",".join(recipe_ids)
            
            # Etap 2: Pobieranie szczegółów (Bulk)
            bulk_params = {
                "apiKey": SPOONACULAR_API_KEY,
                "ids": ids_string,
                "includeNutrition": True
            }
            
            r_bulk = requests.get("https://api.spoonacular.com/recipes/informationBulk", params=bulk_params)
            r_bulk.raise_for_status()
            bulk_data = r_bulk.json()
            
            valid_recipes = []
            for recipe in bulk_data:
                # Odrzucamy przepisy bez instrukcji
                if not recipe.get('analyzedInstructions') and not recipe.get('instructions'):
                    continue

                cal = get_nutrient(recipe, "Calories")
                prot = get_nutrient(recipe, "Protein")
                
                # Filtrowanie pod cel użytkownika
                if user_profile:
                    if user_profile.goal == 'muscle_gain' and prot < 20: continue
                    elif user_profile.goal == 'weight_loss' and cal > 800: continue

                valid_recipes.append(recipe)
            
            if valid_recipes:
                # Zwracamy krotkę (Plan, Lista pasujących przepisów)
                # Ograniczamy do 2 najlepszych wyników na plan
                results_list.append((plan, valid_recipes[:2]))

        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [402, 429]:
                print(f"[{fetch_spoonacular_recipes.__name__}] LIMIT API PRZEKROCZONY (Kod {e.response.status_code})")
                api_limit_reached = True
            else:
                print(f"[{fetch_spoonacular_recipes.__name__}] Błąd HTTP: {e}")

        except Exception as e:
            print(f"[{fetch_spoonacular_recipes.__name__}] Błąd API: {e}")
            
    return results_list

def generate_shopping_list(recipe: dict, fridge_ingredients: List[str]) -> tuple[List[str], List[str]]:
    """
    Porównuje składniki przepisu z zawartością lodówki.
    Zwraca dwie listy: (posiadane, brakujące).
    """
    have_items = []
    missing_items = []
    
    # 1. Normalizacja listy z lodówki (małe litery)
    # fridge_ingredients to lista nazw (str), np. ['jajka', 'mleko']
    fridge_clean_names = {item.lower() for item in fridge_ingredients}
            
    # 2. Definicja produktów bazowych (zakładamy, że user je ma)
    pantry_staples = {
        'salt', 'pepper', 'black pepper', 'white pepper', 
        'water', 'oil', 'olive oil', 'vegetable oil', 
        'sugar', 'flour', 'butter', 'garlic'
    }
    
    # 3. Iterujemy po składnikach przepisu
    # Spoonacular zwraca listę 'extendedIngredients'
    ingredients = recipe.get('extendedIngredients', [])
    
    for ing in ingredients:
        # nameClean to czysta nazwa (np. "garlic"), name to czasem "cloves of garlic"
        ing_name = (ing.get('nameClean') or ing.get('name', '')).lower()
        original_string = ing.get('original', ing_name) # Np. "2 cloves of garlic"
        
        is_present = False
        
        # A. Czy to staple?
        if ing_name in pantry_staples:
            is_present = True
        else:
            # B. Czy jest w lodówce? 
            # Sprawdzamy czy "chicken" jest w "chicken breast" albo odwrotnie
            for f_item in fridge_clean_names:
                if f_item in ing_name or ing_name in f_item:
                    is_present = True
                    break
        
        if is_present:
            have_items.append(original_string)
        else:
            missing_items.append(original_string)
            
    return have_items, missing_items

def save_meal_to_db(recipe: dict, rating: int, notes: str) -> bool:
    """
    Zapisuje wybrany przepis do historii posiłków (tabela MealLog).
    Pobiera makroskładniki używając funkcji pomocniczej get_nutrient.
    """
    db = get_db()  # Otwieramy nową sesję
    
    try:
        # Tworzymy obiekt (wiersz)
        new_log = MealLog(
            recipe_name=recipe.get('title', 'Nieznane danie'),
            recipe_url=recipe.get('sourceUrl', ''),
            image_url=recipe.get('image', ''),
            
            calories=get_nutrient(recipe, "Calories"),
            protein=get_nutrient(recipe, "Protein"),
            fat=get_nutrient(recipe, "Fat"),
            carbs=get_nutrient(recipe, "Carbohydrates"),
            
            user_rating=rating,
            user_notes=notes
        )
        
        db.add(new_log)
        db.commit()      # Zatwierdzamy transakcję
        print(f"[{save_meal_to_db.__name__}] Zapisano posiłek: {new_log.recipe_name}")
        return True
        
    except Exception as e:
        db.rollback()    # Cofamy zmiany w razie błędu
        print(f"[{save_meal_to_db.__name__}] Błąd zapisu do bazy: {e}")
        return False
        
    finally:
        db.close()       # Zamykamy sesję (ważne!)