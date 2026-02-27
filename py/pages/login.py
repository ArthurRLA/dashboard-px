import streamlit as st
from auth import authenticate_user, login, is_logged_in

if is_logged_in():
    st.rerun()

_, col_center, _ = st.columns([1, 2, 1])

with col_center:
    st.title("Dashboard PowerX")
    st.subheader("Acesse sua conta")
    st.markdown("---")

    with st.form("form_login", clear_on_submit=False):
        email     = st.text_input("E-mail", placeholder="seu@email.com")
        password  = st.text_input("Senha", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Preencha e-mail e senha.")
        else:
            with st.spinner("Verificando"):
                user = authenticate_user(email, password)

            if user:
                login(user)
                st.rerun()  
            else:
                st.error("E-mail e/ou senha inválidos.")