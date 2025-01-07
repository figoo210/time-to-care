import streamlit as st


def set_page_config():
    st.set_page_config(
        page_title="Time To Care Dashboard",
        page_icon=":bar_chart:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown("<style> footer {visibility: hidden;} </style>", unsafe_allow_html=True)
