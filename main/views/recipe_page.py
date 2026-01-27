import streamlit as st
import time
from database import get_db, UserProfile
from logic import plan_recipes_with_ai, fetch_spoonacular_recipes, generate_shopping_list, save_meal_to_db

# --- FUNKCJA OKNA DIALOGOWEGO (POP-UP) ---
@st.dialog("🍽️ Jak Ci smakowało?")
def rate_and_save_meal(recipe):
    st.write(f"Danie: **{recipe['title']}**")
    
    # Link do przepisu w oknie (dla wygody)
    st.markdown(f"🔗 [Otwórz przepis w przeglądarce]({recipe['sourceUrl']})")
    
    st.divider()
    
    # Formularz oceny
    with st.form("rating_form"):
        rating = st.slider("Twoja ocena (1-10) ⭐", min_value=1, max_value=10, value=5)
        notes = st.text_area("Notatki (opcjonalnie)", placeholder="Np. dodałem więcej papryki, bardzo sycące...")
        
        # Przycisk zatwierdzający wewnątrz formularza
        submitted = st.form_submit_button("💾 Zapisz w Dzienniku")
        
        if submitted:
            if save_meal_to_db(recipe, rating, notes):
                st.success("Zapisano pomyślnie!")
                st.toast("Posiłek dodany do dziennika! ✅", icon="✅")
                st.session_state['fridge_ingredients'] = []
                
                # 2. Czyścimy stare wyniki wyszukiwania (żeby nie wisiały nieaktualne przepisy)
                if 'search_results' in st.session_state:
                    del st.session_state['search_results']
                
                # Krótkie opóźnienie, żeby użytkownik zobaczył sukces przed przeładowaniem
                time.sleep(1)
                st.rerun()
            else:
                st.error("Wystąpił błąd podczas zapisu do bazy.")

# --- GŁÓWNY WIDOK STRONY ---
st.header("🍳 Generuj Przepisy")
st.write("Co ugotować z tego, co masz? 🗑️ ➡️ 🍲")

ingredients = st.session_state.get('fridge_ingredients', [])

if not ingredients:
    st.warning("Twoja wirtualna lodówka jest pusta! 😲 Użyj najpierw **Skanera**.")
else:
    st.success(f"✅ Dostępne składniki: **{', '.join(ingredients)}**")

    if st.button("🎲 Wymyśl Pyszne Dania (AI)"):
        with st.spinner("🕵️‍♀️ Analizuję składniki i szukam przepisów..."):
            db = get_db()
            user = db.query(UserProfile).first()
            db.close()
            
            plans = plan_recipes_with_ai(ingredients, user)
            
            if plans:
                st.session_state['search_results'] = fetch_spoonacular_recipes(plans, user)
            else:
                st.error("AI nie mogło wymyślić planu. Spróbuj ponownie. 😢")

    if 'search_results' in st.session_state:
        results = st.session_state['search_results']
        
        if not results:
            st.warning("Mamy plan, ale API nie znalazło pasujących przepisów. 🤷‍♂️")
            
        # Wyświetlanie wyników
        for plan_idx, (plan, recipes) in enumerate(results):
            st.markdown("---")
            st.subheader(f"💡 Pomysł: {plan.reason}")
            
            cols = st.columns(len(recipes))
            for idx, recipe in enumerate(recipes):
                with cols[idx]:
                    # Obrazek
                    if recipe.get('image'):
                        st.image(recipe['image'], use_container_width=True)
                    
                    # Tytuł
                    st.markdown(f"### {recipe['title']}")
                    
                    # Makro
                    nutrients = {n['name']: n['amount'] for n in recipe['nutrition']['nutrients']}
                    cal = int(nutrients.get('Calories', 0))
                    prot = int(nutrients.get('Protein', 0))
                    
                    st.write(f"🔥 **{cal} kcal** | 🥩 **{prot}g białka**")
                    
                    # Link do przepisu (zewnętrzny)
                    st.markdown(f"🔗 [Zobacz pełny przepis]({recipe['sourceUrl']})")

                    # Lista Zakupów (rozwijana)
                    with st.expander("🛒 Lista Zakupów"):
                        have, missing = generate_shopping_list(recipe, ingredients)
                        if missing:
                            st.error(f"Kup: {', '.join(missing)}")
                        else:
                            st.success("Masz wszystko! 🎉")
                        st.write(f"Masz: {', '.join(have)}")

                    # PRZYCISK AKCJI
                    unique_key = f"btn_{recipe['id']}_plan{plan_idx}"
                    
                    # Teraz przycisk nie zapisuje od razu, tylko otwiera okno dialogowe
                    if st.button("🍽️ Zjadłem to (Oceń)", key=unique_key):
                        rate_and_save_meal(recipe)