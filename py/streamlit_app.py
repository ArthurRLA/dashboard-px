import streamlit as st
from config_loader import config
from auth import is_logged_in

settings = config.get_settings()
ui_config = settings.get('ui', {})

st.set_page_config(
    page_title=ui_config.get('titulo', 'Dashboard PowerX'),
    page_icon=ui_config.get('icone_pagina', '📊'),
    layout=ui_config.get('layout', 'wide')
)

login      = st.Page("pages/login.py",      title="Login",      icon="🔑")
vendas     = st.Page("pages/vendas.py",     title="Vendas",     icon="📊")
incentivos = st.Page("pages/incentivos.py", title="Incentivos", icon="🏆")

if is_logged_in():
    pg = st.navigation([vendas, incentivos])
else:
    pg = st.navigation([login])

pg.run()