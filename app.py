# ==============================================================================
# AETHERIUM PROJECT — STABLE & FIXED VERSION
# ==============================================================================

from google import genai
import os
import streamlit as st
import urllib.parse
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==============================================================================
# --- SECTION 0: SESSION STATE INITIALIZATION (CRITICAL) ---
# ==============================================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "token" not in st.session_state:
    st.session_state.token = None

# ==============================================================================
# --- SECTION 1: APP CONFIGURATION ---
# ==============================================================================
st.set_page_config(
    page_title="Aetherium Project",
    page_icon="Δ",
    layout="wide"
)

# ==============================================================================
# --- SECTION 1.1: GLOBAL CSS ---
# ==============================================================================
def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;600&family=Michroma&display=swap');
        body, h1, h2, h3, h4, h5, h6, p, span, div {
            font-family: 'Inter', sans-serif !important;
            color: white !important;
        }
        .stApp::before {
            content: ""; position: fixed; inset: 0;
            background: linear-gradient(rgba(0,0,0,.4), rgba(0,0,0,.4)),
                        url("https://images.unsplash.com/photo-1663104192417-6804188a9a8e");
            background-size: cover;
            filter: blur(18px);
            z-index: -1;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

inject_css()

# ==============================================================================
# --- SECTION 2: CONSTANTS ---
# ==============================================================================
TYPE_MAPPING = {
    "Ride": "Cycling", "GravelRide": "Cycling", "VirtualRide": "Cycling",
    "Run": "Running", "TrailRun": "Running", "Treadmill": "Running",
    "Walk": "Running/Walking", "Hike": "Running/Walking",
    "WeightTraining": "Strength", "Yoga": "Mobility", "Pilates": "Mobility"
}

# ==============================================================================
# --- SECTION 3: HELPERS ---
# ==============================================================================
def clean_text(text):
    return "".join(c for c in str(text) if c.isalnum() or c in " -_")

def infer_primary_sport(activities):
    load_by_sport = {}
    for a in activities:
        sport = TYPE_MAPPING.get(a.get("type"), "Other")
        load = a.get("icu_training_load") or 0
        load_by_sport[sport] = load_by_sport.get(sport, 0) + load
    return max(load_by_sport, key=load_by_sport.get) if load_by_sport else "General Fitness"

# ==============================================================================
# --- SECTION 4: AUTH ---
# ==============================================================================
def show_login_screen():
    params = {
        "client_id": st.secrets["INTERVALS_CLIENT_ID"],
        "redirect_uri": st.secrets["REDIRECT_URI"],
        "response_type": "code",
        "scope": "ACTIVITY:READ,WELLNESS:READ"
    }
    auth_url = f"https://intervals.icu/oauth/authorize?{urllib.parse.urlencode(params)}"
    st.markdown("## 🚀 Connect to Intervals.icu")
    st.link_button("Authorize", auth_url, use_container_width=True)

def get_access_token(code):
    r = requests.post(
        "https://intervals.icu/api/oauth/token",
        data={
            "client_id": st.secrets["INTERVALS_CLIENT_ID"],
            "client_secret": st.secrets["INTERVALS_CLIENT_SECRET"],
            "code": code,
            "redirect_uri": st.secrets["REDIRECT_URI"],
            "grant_type": "authorization_code",
        },
        timeout=10
    )
    return r.json() if r.ok else {}

# ==============================================================================
# --- SECTION 5: DATA FETCH ---
# ==============================================================================
@st.cache_data(ttl=300)
def fetch_data(token):
    headers = {"Authorization": f"Bearer {token}"}
    base = "https://intervals.icu/api/v1/athlete/0/activities"

    all_activities = []
    page = 1
    per_page = 100

    while True:
        r = requests.get(
            base,
            headers=headers,
            params={"page": page, "limit": per_page},
            timeout=10
        )

        if not r.ok:
            break

        data = r.json()

        # Intervals returns a list here
        if not isinstance(data, list) or not data:
            break

        all_activities.extend(data)
        page += 1

    wellness = requests.get(
        "https://intervals.icu/api/v1/athlete/0/wellness",
        headers=headers,
        timeout=10
    ).json()

    return all_activities, wellness


# ==============================================================================
# --- SECTION 6: OAUTH CALLBACK HANDLING ---
# ==============================================================================
if "code" in st.query_params and not st.session_state.authenticated:
    token_response = get_access_token(st.query_params["code"])

    if "access_token" in token_response:
        st.session_state.token = token_response["access_token"]
        st.session_state.authenticated = True
        st.query_params.clear()
        st.rerun()

# ==============================================================================
# --- SECTION 7: AUTH GUARD ---
# ==============================================================================
if not st.session_state.authenticated or not st.session_state.token:
    show_login_screen()
    st.stop()

# ==============================================================================
# --- SECTION 8: LOAD DATA (DEFINITIVE SAFE VERSION) ---
# ==============================================================================
act_json, well_json = fetch_data(st.session_state.token)

st.write("DEBUG — act_json output:", act_json)
st.stop()
act_list, well_json = fetch_data(st.session_state.token)

if not act_list:
    st.error("No activities found in Intervals.icu account")
    st.stop()

df = pd.DataFrame(act_list)


# 🔒 ABSOLUTE GUARD — THIS STOPS YOUR ERROR FOREVER
import pandas as pd
if isinstance(df.columns, pd.RangeIndex):
    st.error("Invalid activity structure (no column names)")
    st.stop()

# Resolve date column
# Show all columns for debugging
st.write("DEBUG — DataFrame columns:", list(df.columns))

# Attempt to auto-detect date column
DATE_COLUMNS = ["start_date_local", "start_date", "start_time", "date", "start"]

date_col = next((c for c in DATE_COLUMNS if c in df.columns), None)

if date_col is None:
    st.error(
        "No recognized date column found in activity data. "
        "Please check the DEBUG output for available columns."
    )
    st.stop()  # Stop execution safely

# Convert the selected column to datetime
df["activity_date"] = pd.to_datetime(df[date_col], errors="coerce")
df = df.dropna(subset=["activity_date"]).sort_values("activity_date")



def estimate_load(row):
    if pd.notna(row.get("icu_training_load")):
        return row["icu_training_load"]
    if pd.notna(row.get("suffer_score")):
        return row["suffer_score"]
    if pd.notna(row.get("moving_time")):
        return (row["moving_time"] / 3600) * 50
    return 0

df["TSS"] = df.apply(estimate_load, axis=1)
daily = df.set_index("activity_date")["TSS"].resample("D").sum()

ctl = daily.ewm(span=42, adjust=False).mean()
atl = daily.ewm(span=7, adjust=False).mean()
tsb = ctl - atl

current_fitness = ctl.iloc[-1]
current_fatigue = atl.iloc[-1]
current_form = tsb.iloc[-1]

# ==============================================================================
# --- SECTION 9: DASHBOARD ---
# ==============================================================================
st.markdown("## ⚡ Training Status")

if current_form > 10:
    status, color = "PRIME", "#4CAF50"
elif -10 <= current_form <= 10:
    status, color = "PRODUCTIVE", "#FFC107"
else:
    status, color = "FATIGUED", "#FF5252"

st.markdown(
    f"""
    <div style="border-left:4px solid {color}; padding:15px; background:rgba(255,255,255,.05)">
    <b style="color:{color}">{status}</b><br>
    Form (TSB): {int(current_form)}
    </div>
    """,
    unsafe_allow_html=True
)

m1, m2, m3 = st.columns(3)
m1.metric("Fitness (CTL)", int(current_fitness))
m2.metric("Fatigue (ATL)", int(current_fatigue))
m3.metric("Form (TSB)", int(current_form))

# ==============================================================================
# --- SECTION 10: AI WORKOUT ---
# ==============================================================================
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

st.markdown("---")
st.markdown("## 🤖 AI Workout Generator")

sport = infer_primary_sport(act_json)
goal = st.selectbox("Goal", ["Base", "Threshold", "VO2", "Recovery"])
time_avail = st.slider("Time (min)", 30, 120, 60, step=15)

if st.button("Generate Workout", use_container_width=True):
    if not client:
        st.error("Missing Gemini API key")
    else:
        recent = df.sort_values("activity_date", ascending=False).head(3)
        history = "\n".join(
            f"- {r.activity_date.date()} {clean_text(r.name)}"
            for r in recent.itertuples()
        )

        prompt = f"""
Act as an elite {sport} coach.

Sport: {sport}
Goal: {goal}
Time: {time_avail} min
Form: {int(current_form)}

Recent Training:
{history}

FORMAT STRICTLY:
**Workout Name**
**Warm Up**
**Main Set**
**Cool Down**
**Coach's Logic**
"""

        res = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt
        )
        st.markdown(res.text)

# ==============================================================================
# --- SECTION 11: LOAD CHART ---
# ==============================================================================
df_daily = pd.DataFrame({"CTL": ctl, "ATL": atl, "TSB": tsb})

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_daily.index, y=df_daily["CTL"], name="CTL"))
fig.add_trace(go.Scatter(x=df_daily.index, y=df_daily["ATL"], name="ATL"))
fig.add_trace(go.Scatter(x=df_daily.index, y=df_daily["TSB"], name="TSB"))

fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="white"),
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)
