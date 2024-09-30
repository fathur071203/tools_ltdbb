import pandas as pd
import streamlit as st
import calendar

from service.preprocess import *
from service.visualize import *

# Initial Page Setup
set_page_visuals()
st.text("Profile")