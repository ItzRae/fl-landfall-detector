import pandas as pd
import streamlit as st

DATA_PATH = "output/florida_hurricane_landfalls.csv"

st.set_page_config(
    page_title="Florida Hurricane Landfalls",
    layout="wide",
)

st.title("KCC - Florida Hurricane Landfalls")

df = pd.read_csv(
    DATA_PATH,
    parse_dates=["landfall_datetime"],
)

st.metric(
    "Detected landfalls",
    len(df),
)

st.dataframe(
    df,
    use_container_width=True,
)

