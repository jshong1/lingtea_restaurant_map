import streamlit as st
import pandas as pd

df = pd.DataFrame({
    'Name': ['A', 'B', 'C'],
    'Score': [1, 2, 3]
})

event = st.dataframe(df, on_select="rerun", selection_mode="single-row")
st.write(event)
