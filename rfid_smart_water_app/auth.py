import streamlit as st
from database import get_user_by_username


def login_form():
    st.subheader("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        user = get_user_by_username(username.strip())
        if user and user["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = user
            st.success(f"Welcome, {user['name']}!")
            st.rerun()
        else:
            st.error("Invalid username or password.")


def logout():
    st.session_state["logged_in"] = False
    st.session_state["current_user"] = None
