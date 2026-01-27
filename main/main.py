import streamlit as st

# 1. Konfiguracja strony
# Tutaj shortcodes działają, ale dla spójności dajemy emoji
st.set_page_config(
    page_title="NoWaste Chef",
    page_icon="👨‍🍳",
    layout="wide"
)

# 2. Definicja stron
# UWAGA: Tutaj MUSZĄ być znaki emoji (np. 🏠), a nie kody (:house:)

p_home = st.Page(
    "views/home_page.py", 
    title="Start", 
    icon="🏠",  # Było :house:
    default=True
)

p_profile = st.Page(
    "views/user_profile_page.py", 
    title="Mój Profil", 
    icon="👤"   # Było :bust_in_silhouette:
)

p_analyze = st.Page(
    "views/fridge_analyze_page.py", 
    title="Skaner Lodówki", 
    icon="📸"   # Było :camera:
)

p_recipes = st.Page(
    "views/recipe_page.py", 
    title="Przepisy i Zakupy", 
    icon="🍳"   # Było :fried_egg:
)

p_journal = st.Page(
    "views/journal_page.py", 
    title="Dziennik Kalorii", 
    icon="📊"   # Było :bar_chart:
)

# 3. Budowanie Menu
pg = st.navigation({
    "Główne": [p_home],
    "Narzędzia AI": [p_analyze, p_recipes],
    "Twoje Dane": [p_journal, p_profile]
})

# 4. Uruchomienie
pg.run()