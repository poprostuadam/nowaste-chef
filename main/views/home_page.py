import streamlit as st
import pandas as pd
from database import init_db, get_db, UserProfile, MealLog

init_db()

if 'fridge_ingredients' not in st.session_state:
    st.session_state['fridge_ingredients'] = []

# --- WIDOK GŁÓWNY ---
st.title("👨‍🍳 Witaj w NoWaste Chef!")
st.subheader("Twój osobisty asystent Zero Waste ♻️")

st.markdown("""
### Co chcesz dzisiaj zrobić? :thinking:

1. **:bust_in_silhouette: Ustaw Profil** (menu po lewej) – abyśmy znali Twój cel kaloryczny.
2. **:camera: Zeskanuj Lodówkę** – AI rozpozna składniki ze zdjęcia.
3. **:fried_egg: Znajdź Przepis** – wygenerujemy pomysły na obiad z tego, co masz.
4. **:bar_chart: Sprawdź Dziennik** – kontroluj kalorie i makroskładniki.

---
:point_left: *Wybierz zakładkę z menu bocznego, aby zacząć!*
""")

# --- SEKCJA DEWELOPERA ---
st.divider()
with st.expander(":hammer_and_wrench: Strefa Dewelopera (Baza Danych i Stan)"):
    st.warning("To widok techniczny. Tutaj podglądasz 'wnętrzności' aplikacji.")

    st.subheader("📦 Pamięć podręczna (Session State)")
    st.write(st.session_state)

    st.markdown("---")
    st.subheader("🗄️ Baza Danych SQL (nowaste.db)")
    
    if st.button("🔄 Odśwież dane z bazy"):
        st.rerun()

    try:
        db = get_db()
        
        st.markdown("**Tabela: UserProfile**")
        users_query = db.query(UserProfile).statement
        df_users = pd.read_sql(users_query, db.bind)
        
        if not df_users.empty:
            # --- POPRAWKA ---
            st.dataframe(df_users, width="stretch")
        else:
            st.info("Tabela UserProfile jest pusta.")

        st.markdown("**Tabela: MealLog**")
        logs_query = db.query(MealLog).statement
        df_logs = pd.read_sql(logs_query, db.bind)
        
        if not df_logs.empty:
            # --- POPRAWKA ---
            st.dataframe(df_logs, width="stretch")
        else:
            st.info("Tabela MealLog jest pusta.")
            
        db.close()

    except Exception as e:
        st.error(f"Błąd odczytu bazy: {e}")