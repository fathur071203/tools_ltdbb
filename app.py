import pandas as pd
import streamlit as st
import calendar
import warnings

from service.preprocess import *
from service.visualize import *
from service.database import connect_db

def main():
    # Initial Web & Page Setup
    set_page_settings()
    set_data_settings()
    warnings.filterwarnings("ignore")
    db = connect_db()

if __name__ == '__main__':
    main()