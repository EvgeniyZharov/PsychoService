import streamlit as st

st.set_page_config(page_title="Главное меню", page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")
# menu = ["Главная", "Сюжет", "Курсы", "Тесты", "Профиль"]
# choice = st.sidebar.radio("Навигация", menu)

st.title("📌 Добро пожаловать в психологический проект!")
st.write("Исследуйте свой внутренний мир, развивайтесь и проходите увлекательные тесты.")

if "current_page" not in st.session_state:
    st.session_state.current_page = "main"

# # --- Навигация ---
# if st.session_state.current_page == "courses":
#     st.write("📚 Страница курсов")
#     if st.button("🔙 Назад"):
#         st.session_state.current_page = "main"
#         st.rerun()
# else:
#     st.title("📌 Добро пожаловать!")
#     if st.button("📚 Перейти к курсам"):
#         st.session_state.current_page = "courses"
#         st.rerun()

st.subheader("Навигация по страницам:")
if st.button("Перейти к сюжету"):
    st.switch_page("pages/story.py")
if st.button("Перейти к курсам"):
    st.switch_page("pages/courses.py")
if st.button("Перейти к тестам"):
    st.switch_page("pages/tests.py")