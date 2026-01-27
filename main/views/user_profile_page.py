import streamlit as st
from database import get_db, UserProfile

st.header(":bust_in_silhouette: Twój Profil Dietetyczny")
st.write("Uzupełnij dane, abyśmy mogli obliczyć Twoje zapotrzebowanie! :memo:")

db = get_db()
user = db.query(UserProfile).first()

if not user:
    user = UserProfile(name="")

with st.form("profile_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Dane podstawowe :id:")
        name = st.text_input("Imię", value=user.name, placeholder="Np. Marek")
        weight = st.number_input("Waga (kg) :balance_scale:", value=user.weight)
        height = st.number_input("Wzrost (cm) :straight_ruler:", value=user.height)
        
    with col2:
        st.subheader("Szczegóły :clipboard:")
        age = st.number_input("Wiek :birthday:", value=user.age, step=1)
        gender = st.selectbox("Płeć :wc:", ["Male", "Female"], index=0 if user.gender=="Male" else 1)
        activity = st.selectbox(
            "Aktywność fizyczna :running_man:", 
            ["sedentary", "moderate", "active", "very_active"],
            index=0
        )
    
    st.markdown("---")
    goal = st.selectbox(
        "Twój Cel :dart:", 
        ["weight_loss", "maintenance", "muscle_gain"],
        index=1
    )
    restrictions = st.text_area("Alergie / Czego nie lubisz? :no_entry_sign:", value=user.dietary_restrictions)
    
    submitted = st.form_submit_button(":floppy_disk: Zapisz Profil")

if submitted:
    if not user.id:
        db.add(user)
    
    user.name = name
    user.weight = weight
    user.height = height
    user.age = age
    user.gender = gender
    user.activity_level = activity
    user.goal = goal
    user.dietary_restrictions = restrictions
    
    user.calculate_and_update_targets()
    
    db.commit()
    st.success(f"Profil zaktualizowany! Twój cel dzienny: **{user.target_calories} kcal** :fire:")
    st.balloons()

db.close()

