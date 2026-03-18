import os
from dotenv import load_dotenv
load_dotenv()
import streamlit as st

# HOST = os.getenv("HOST")
# PORT = os.getenv("PORT")
# DATABASE = os.getenv("DATABASE")
# USER = os.getenv("USER")
# PASSWORD = os.getenv("PASSWORD")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

HOST = st.secrets["HOST"]
PORT = st.secrets["PORT"]
DATABASE = st.secrets["DATABASE"]
USER =  st.secrets["USER"]
PASSWORD = st.secrets["PASSWORD"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]