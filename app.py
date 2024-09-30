import pandas as pd
import streamlit as st
import calendar

from service.preprocess import *
from service.visualize import *

def main():
    # Initial Web & Page Setup
    set_page_settings()
    set_data_settings()

if __name__ == '__main__':
    main()