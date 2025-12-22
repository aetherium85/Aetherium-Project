import streamlit as st

st.set_page_config(page_title="Privacy Policy", layout="wide")

st.title("📄 Privacy Policy")
st.caption("Last Updated: December 22, 2025")

st.markdown("""
### 1. Data Collection
This application accesses your Intervals.icu data via their official API. We only collect:
* **Activity Data**: Workout types, dates, and load metrics.
* **Wellness Data**: CTL, ATL, and TSB scores.

### 2. Data Usage
Data is used solely to generate your personal fitness dashboard. **We do not store your data** on any permanent database; it resides in temporary session memory and is cleared when you close your browser tab.

### 3. Third-Party Sharing
We never sell, share, or trade your fitness data with third parties.

### 4. Revoking Access
You can disconnect this app at any time by revoking the API key or OAuth permission within your [Intervals.icu Settings](https://intervals.icu/settings).

### 5. Attribution
Charts may include data from Garmin devices.
""")

if st.button("⬅️ Back to Dashboard"):
    st.switch_page("app.py")