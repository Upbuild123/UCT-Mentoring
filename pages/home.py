import streamlit as st
import base64, os

logo_path = os.path.join(os.path.dirname(__file__), "..", "assets", "upbuild_logo.png")
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.markdown(
        f'<img src="data:image/png;base64,{b64}" style="height:60px; margin-bottom:24px;">',
        unsafe_allow_html=True,
    )

st.title("Welcome to Upbuild Mentoring")
st.markdown(
    "<p style='font-size:17px; color:#7a5fa0; margin-top:-8px;'>Coaching assessment and development program</p>",
    unsafe_allow_html=True,
)
