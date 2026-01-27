import streamlit as st
import pandas as pd
from database import get_db, MealLog, UserProfile
from datetime import datetime

st.header("📊 Twój Dziennik Żywieniowy")

db = get_db()
user = db.query(UserProfile).first()
logs = pd.read_sql(db.query(MealLog).statement, db.bind)
db.close()

if logs.empty:
    st.info("Brak wpisów. Ugotuj coś i zapisz w zakładce **Przepisy**! :pot_of_food:")
else:
    logs['dt'] = pd.to_datetime(logs['date'])
    today = datetime.now().date()
    today_logs = logs[logs['dt'].dt.date == today]
    
    total_cal = today_logs['calories'].sum()
    target_cal = user.target_calories if user else 2000
    left_cal = target_cal - total_cal
    
    st.subheader(f"Dzisiejszy bilans ({today}) :calendar:")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Zjedzone :fire:", f"{int(total_cal)} kcal")
    c2.metric("Pozostało :sandwich:", f"{int(left_cal)} kcal")
    c3.metric("Cel :dart:", f"{target_cal} kcal")
    
    progress = min(total_cal / target_cal, 1.0)
    st.progress(progress)

    st.markdown("---")
    st.subheader(":scroll: Historia Posiłków")
    
    display_df = logs[['date', 'recipe_name', 'calories', 'protein', 'user_rating']].sort_values(by='date', ascending=False)
    
    st.dataframe(
        display_df,
        column_config={
            "date": "Data",
            "recipe_name": "Danie",
            "calories": "Kcal",
            "protein": "Białko (g)",
            "user_rating": st.column_config.NumberColumn("Ocena", format="%d ⭐")
        },
        # --- POPRAWKA TUTAJ ---
        width="stretch" 
    )
    # UWAGA: Jeśli Streamlit bardzo nalega na "stretch", wpisz: width=1000 (jako int) 
    # lub po prostu usuń ten argument całkowicie - tabela i tak będzie czytelna.