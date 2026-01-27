from main.database import UserProfile, MealLog

def test_create_user_defaults(test_db):
    """Sprawdza czy użytkownik tworzy się z domyślnymi wartościami."""
    # GIVEN
    user = UserProfile(name="Test User")
    
    # WHEN
    test_db.add(user)
    test_db.commit()
    
    # THEN
    saved_user = test_db.query(UserProfile).first()
    assert saved_user.name == "Test User"
    assert saved_user.weight == 70.0  # Domyślna waga z database.py
    assert saved_user.goal == "maintenance"
    assert saved_user.target_calories == 2000 # Domyślna wartość przed przeliczeniem

def test_calculate_calories_weight_loss_male(test_db):
    """
    Testuje obliczenia dla: Mężczyzna, Redukcja, Mała aktywność.
    Weryfikuje wzór Mifflin-St Jeor + deficyt.
    """
    # GIVEN
    user = UserProfile(
        name="Adam",
        weight=100.0,
        height=180.0,
        age=30,
        gender="Male",
        activity_level="sedentary", # Mnożnik 1.2
        goal="weight_loss"          # -400 kcal
    )
    
    # WHEN
    user.calculate_and_update_targets()
    test_db.add(user)
    test_db.commit()
    
    # THEN
    # Ręczne wyliczenie:
    # BMR = (10*100) + (6.25*180) - (5*30) + 5 
    # BMR = 1000 + 1125 - 150 + 5 = 1980
    # TDEE = 1980 * 1.2 = 2376
    # Cel = 2376 - 400 = 1976 kcal
    
    assert user.target_calories == 1976
    
    # Makro dla sedentary: P:25%, F:35%, C:40%
    # Białko = (1976 * 0.25) / 4 = 123g
    assert user.target_protein == 123 

def test_calculate_calories_muscle_gain_female(test_db):
    """
    Testuje obliczenia dla: Kobieta, Masa, Duża aktywność.
    """
    # GIVEN
    user = UserProfile(
        name="Ewa",
        weight=60.0,
        height=165.0,
        age=25,
        gender="Female",
        activity_level="active", # Mnożnik 1.55
        goal="muscle_gain"       # +300 kcal
    )
    
    # WHEN
    user.calculate_and_update_targets()
    test_db.add(user)
    test_db.commit()
    
    # THEN
    # Ręczne wyliczenie:
    # BMR = (10*60) + (6.25*165) - (5*25) - 161
    # BMR = 600 + 1031.25 - 125 - 161 = 1345.25
    # TDEE = 1345.25 * 1.55 = 2085.13
    # Cel = 2085 + 300 = 2385 kcal
    
    # Dopuszczamy margines błędu +/- 1 kcal ze względu na zaokrąglenia float
    assert 2384 <= user.target_calories <= 2386

def test_meal_log_creation(test_db):
    """Sprawdza czy można zapisać i odczytać posiłek."""
    # GIVEN
    meal = MealLog(
        recipe_name="Jajecznica",
        calories=350.5,
        protein=20.0,
        fat=25.0,
        carbs=5.0,
        user_rating=9,
        user_notes="Pyszne!"
    )
    
    # WHEN
    test_db.add(meal)
    test_db.commit()
    
    # THEN
    saved_meal = test_db.query(MealLog).first()
    assert saved_meal.recipe_name == "Jajecznica"
    assert saved_meal.calories == 350.5
    assert saved_meal.date is not None # Data powinna się wygenerować automatycznie