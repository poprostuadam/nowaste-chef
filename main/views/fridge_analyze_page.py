import streamlit as st
import os
from logic import analyze_fridge_process, refine_analysis_process

st.header(":camera: Skaner Zawartości Lodówki")
st.info("Zrób zdjęcie wnętrza lodówki lub blatu kuchennego z produktami! :camera_flash:")

uploaded_file = st.file_uploader("Wgraj zdjęcie tutaj :inbox_tray:", type=['jpg', 'png', 'jpeg'])

if 'analysis_data' not in st.session_state:
    st.session_state['analysis_data'] = None
if 'file_id' not in st.session_state:
    st.session_state['file_id'] = None

if uploaded_file:
    st.image(uploaded_file, caption="Twoje zdjęcie", width=400)
    
    if st.button(":mag: Analizuj zdjęcie (AI)"):
        with st.spinner(":robot: AI analizuje składniki... Może to chwilę potrwać!"):
            with open("temp_img.jpg", "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            result, file_id = analyze_fridge_process("temp_img.jpg")
            
            if result:
                st.session_state['analysis_data'] = result
                st.session_state['file_id'] = file_id
                if os.path.exists("temp_img.jpg"): os.remove("temp_img.jpg")
                st.success("Analiza zakończona! :white_check_mark:")
            else:
                st.error("Wystąpił błąd analizy. Sprawdź klucze API. :warning:")
                if os.path.exists("temp_img.jpg"): os.remove("temp_img.jpg")

analysis = st.session_state['analysis_data']

if analysis:
    st.divider()
    st.subheader("🧐 Wyniki Analizy")
    
    # Pytania wyjaśniające
    if analysis.clarification_questions:
        st.warning(":warning: AI ma pytania:")
        for q in analysis.clarification_questions:
            st.write(f":question: {q}")
            
        answer = st.text_input("Twoja odpowiedź:")
        if st.button("📩 Wyślij wyjaśnienie"):
            with st.spinner("AI myśli... :thinking:"):
                new_result = refine_analysis_process(st.session_state['file_id'], analysis, answer)
                if new_result:
                    st.session_state['analysis_data'] = new_result
                    st.rerun()

    # Wyniki
    col1, col2 = st.columns(2)
    valid_items = [i for i in analysis.identified_items if not i.is_staple]
    staples = [i for i in analysis.identified_items if i.is_staple]
    
    with col1:
        st.success(f":tomato: Główne Składniki ({len(valid_items)})")
        for item in valid_items:
            st.write(f"• **{item.name_pl}** _({item.quantity_estimated or '?'})_")
            
    with col2:
        st.info(f":canned_food: Spiżarnia/Bazowe ({len(staples)})")
        st.write(", ".join([i.name_pl for i in staples]))

    st.divider()
    if st.button(":rocket: Zatwierdź i idź do Przepisów"):
        final_list = [i.name_en_clean for i in valid_items]
        st.session_state['fridge_ingredients'] = final_list
        st.success(f"Zapisano {len(final_list)} składników! Przejdź do zakładki **Przepisy** :fast_forward:")