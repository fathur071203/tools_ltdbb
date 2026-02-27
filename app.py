import pandas as pd
import streamlit as st
import calendar
import warnings
import hmac

from service.preprocess import *
from service.visualize import *
from service.database import connect_db


def _inject_login_css() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stAppViewContainer"] {
                background: radial-gradient(circle at 15% 15%, rgba(37, 99, 235, 0.18), transparent 35%),
                            radial-gradient(circle at 85% 10%, rgba(6, 182, 212, 0.18), transparent 40%),
                            linear-gradient(180deg, #f7fbff 0%, #edf6ff 60%, #f2fcff 100%);
            }
            .block-container {
                padding-top: 0.75rem;
                padding-bottom: 1rem;
                min-height: calc(100vh - 3.2rem);
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .block-container > div[data-testid="stVerticalBlock"] {
                width: min(860px, 94vw);
            }

            .login-hero {
                background: linear-gradient(125deg, #1d4ed8 0%, #2563eb 42%, #06b6d4 100%);
                border-radius: 16px;
                padding: 1.2rem 1.3rem;
                color: #ffffff;
                box-shadow: 0 14px 28px rgba(37, 99, 235, 0.24);
                border: 1px solid rgba(255, 255, 255, 0.24);
                margin-bottom: 1rem;
            }
            .login-hero-title {
                margin: 0;
                font-size: 1.52rem;
                font-weight: 760;
            }
            .login-hero-sub {
                margin-top: 0.25rem;
                font-size: 1.08rem;
                opacity: 0.96;
            }

            /* Card putih untuk logo agar selalu clear */
            [data-testid="stImage"] {
                background: #ffffff;
                border: 1px solid #dbeafe;
                border-radius: 12px;
                padding: 10px 12px;
                margin-bottom: 0.6rem;
                box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
            }

            [data-testid="stImage"] img {
                display: block;
                margin-left: auto;
                margin-right: auto;
            }

            [data-testid="stTextInput"] > div > div > input {
                border-radius: 12px;
                border: 1px solid #cfe6ff;
                background: #ffffff;
                box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
                min-height: 52px;
                font-size: 1.05rem;
            }

            [data-testid="stTextInput"] label p {
                font-size: 1.02rem;
                font-weight: 600;
            }

            @media (min-width: 1400px) {
                .login-hero-title {
                    font-size: 1.66rem;
                }
                .login-hero-sub {
                    font-size: 1.12rem;
                }
            }

            @media (max-width: 840px) {
                .block-container {
                    min-height: calc(100vh - 2.6rem);
                    padding-top: 0.4rem;
                }
                .login-hero {
                    padding: 1rem 1rem;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def check_password():
    """Returns True if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    _inject_login_css()

    st.markdown(
        """
        <div class="login-hero">
            <div class="login-hero-title">🔐 Tools Analisa Data LTDBB</div>
            <div class="login-hero-sub">Silakan masuk untuk melanjutkan ke dashboard analitik.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.image(".static/Logo.png", use_container_width=True)
    st.text_input(
        "Password",
        type="password",
        on_change=password_entered,
        key="password",
        placeholder="Masukkan password...",
    )
    st.caption("Tekan Enter setelah mengisi password.")
    if "password_correct" in st.session_state:
        st.error("Password salah")

    return False


def main():
    # Initial Web & Page Setup
    st.set_page_config(
        page_title="Tools Analisa Data LTDBB",
        page_icon=".static/favicon.png",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    if not check_password():
        st.stop()
    set_page_settings()
    set_data_settings()
    warnings.filterwarnings("ignore")


if __name__ == '__main__':
    main()