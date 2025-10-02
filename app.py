import pandas as pd
import streamlit as st
import calendar
import warnings
import hmac

from service.preprocess import *
from service.visualize import *
from service.database import connect_db

# WARNING: Hardcoded password (temporary as requested). For production, move to .streamlit/secrets.toml
HARDCODED_PASSWORD = "dpsp2024"


def check_password():
    """Returns True if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Compare against hardcoded password
        if hmac.compare_digest(st.session_state["password"], HARDCODED_PASSWORD):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    st.image(".static/Logo.png")
    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("Password salah")
    return False


def main():
    # Initial Web & Page Setup
    if not check_password():
        st.stop()
    set_page_settings()
    set_data_settings()
    warnings.filterwarnings("ignore")
    db = connect_db()

if __name__ == '__main__':
    main()