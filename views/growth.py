import pandas as pd
import streamlit as st
import calendar

from service.preprocess import *
from service.visualize import *

# Initial Page Setup
set_page_visuals()
st.text(st.session_state['uploaded_file'])
import streamlit as st

import streamlit as st

# Row 1: One merged column (spans the full width)
col1 = st.columns(1)  # Create a single column spanning the entire width
with col1[0]:
    st.write("This is the first row with a merged column.")

# Row 2: Two separate columns
col2, col3 = st.columns(2)
with col2:
    st.write("This is the first column of the second row.")
with col3:
    st.write("This is the second column of the second row.")

