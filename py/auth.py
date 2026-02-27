import bcrypt
import streamlit as st
from typing import Optional


ROLE_ADMIN = "ROLE_ADMIN"
ROLE_USER  = "ROLE_USER"

_AUTH_QUERY = """
    SELECT id, name, email, role, active
    FROM users
    WHERE email = %(email)s
      AND active = true
    LIMIT 1
"""

_PASSWORD_QUERY = """
    SELECT password_hash
    FROM users
    WHERE id = %(user_id)s
    LIMIT 1
"""


def authenticate_user(email: str, password: str) -> Optional[dict]:
    from db_connector import db

    try:
        df = db.execute_query(_AUTH_QUERY, {"email": email.strip().lower()})

        if df.empty:
            return None

        user = df.iloc[0].to_dict()

        df_pwd = db.execute_query(_PASSWORD_QUERY, {"user_id": user["id"]})
        if df_pwd.empty:
            return None

        password_hash = df_pwd.iloc[0]["password_hash"]

        if not _verify_password(password, password_hash):
            return None

        return {
            "id":    int(user["id"]),
            "name":  str(user["name"]),
            "email": str(user["email"]),
            "role":  str(user["role"]),
        }

    except Exception as e:
        st.error(f"Erro ao autenticar: {e}")
        return None


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            hashed.encode("utf-8")
        )
    except Exception:
        return False
    
    
def login(user: dict):
    st.session_state["authenticated"] = True
    st.session_state["user"] = user


def logout():
    """Limpa toda a sessão e força reavaliação do streamlit_app."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def is_logged_in() -> bool:
    return st.session_state.get("authenticated", False)


def get_current_user() -> Optional[dict]:
    return st.session_state.get("user", None)


def is_admin() -> bool:
    user = get_current_user()
    return user is not None and user.get("role") == ROLE_ADMIN


def get_user_id_filter() -> Optional[int]:
    if is_admin():
        return None
    user = get_current_user()
    return user["id"] if user else None


def require_auth():
    if not is_logged_in():
        st.error("Sessão expirada. Faça login novamente.")
        st.stop()