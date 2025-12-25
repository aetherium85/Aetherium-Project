import streamlit.components.v1 as components
import urllib.parse
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURATION (MUST BE FIRST) ---
st.set_page_config(page_title="Yearly Fitness Dashboard", layout="wide")

pretty_labels = {
    "ctl": "Fitness (CTL)",
    "atl": "Fatigue (ATL)",
    "tsb": "Form (TSB)",
    "date": "Date",
    "value": "Score"
}

TYPE_MAPPING = {
    "Ride": "Cycling", "GravelRide": "Cycling", "VirtualRide": "Cycling", 
    "EBikeRide": "Cycling", "MountainBikeRide": "Cycling", "Velomobile": "Cycling",
    "Handcycle": "Cycling", "TrackCycling": "Cycling",
    "Run": "Running", "TrailRun": "Running", "VirtualRun": "Running", 
    "Treadmill": "Running", "Walk": "Running/Walking", "Hike": "Running/Walking",
    "Swim": "Swimming", "OpenWaterSwim": "Swimming", "Rowing": "Water Sports", 
    "WeightTraining": "Strength", "Yoga": "Mobility", "Pilates": "Mobility"
}

# --- 2. THE FINAL CSS FIX ---
st.markdown(
    """
    <style>
    /* Target the main container and the blurred overlay Streamlit uses */
    .stApp, .stMainBlockContainer, [data-testid="stAppViewBlockContainer"] {
        background: linear-gradient(rgba(135,135,135,0.7), rgba(135,135,135,0.7)), 
                    url("https://images.unsplash.com/photo-1754980004850-3c93f91c6052") !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
        background-repeat: no-repeat !important;
    }

    /* Glassmorphism for containers */
    div[data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {
        background-color: rgba(135,135,135, 0.5) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 15px !important;
        padding: 20px !important;
        border: 1px solid rgba(135,135,135, 0.1) !important;
    }

    /* Force all text to white */
    h1, h2, h3, p, span, label, .stMetric label, [data-testid="stMetricValue"] {
        color: white !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 3. FUNCTION DEFINITIONS (Defining everything BEFORE calling them) ---

def show_login_screen():
    st.title("❤️ Fitness Command Center")
    st.write("Securely sync your 2025 performance data.")
    auth_url = f"https://intervals.icu/oauth/authorize?{urllib.parse.urlencode({
        'client_id': st.secrets['INTERVALS_CLIENT_ID'],
        'redirect_uri': st.secrets['REDIRECT_URI'],
        'response_type': 'code',
        'scope': 'ACTIVITY:READ,WELLNESS:READ'
    })}"
    st.link_button("🚀 Connect with Intervals.icu", auth_url, type="primary")

def get_access_token(auth_code):
    token_url = "https://intervals.icu/api/oauth/token"
    payload = {
        "client_id": st.secrets["INTERVALS_CLIENT_ID"],
        "client_secret": st.secrets["INTERVALS_CLIENT_SECRET"],
        "code": auth_code,
        "redirect_uri": st.secrets["REDIRECT_URI"],
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=payload)
    return response.json() if response.status_code == 200 else {}

def get_ytd_data():
    if "token_data" not in st.session_state or st.session_state.token_data is None:
        return None, None, None
    token = st.session_state.token_data.get('access_token')
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://intervals.icu/api/v1/athlete/0" 
    first_day = datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    params = {'oldest': first_day, 'newest': today}
    try:
        well_res = requests.get(f"{base_url}/wellness", headers=headers, params=params)
        act_res = requests.get(f"{base_url}/activities", headers=headers, params=params)
        ath_res = requests.get(base_url, headers=headers)
        return well_res.json(), act_res.json(), ath_res.json()
    except Exception as e:
        st.error(f"Fetch failed: {e}")
        return None, None, None

def create_gauge(value, title, color_steps, min_val, max_val):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'size': 18, 'color': 'white'}},
        number={'font': {'color': 'white'}},
        gauge={'axis': {'range': [min_val, max_val], 'tickcolor': "white"},
               'bar': {'color': "rgba(255,255,255,0.3)"}, 'steps': color_steps}
    ))
    fig.update_layout(height=220, margin=dict(l=30, r=30, t=50, b=20),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

# --- 4. SESSION LOGIC & AUTHENTICATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

query_params = st.query_params
if "code" in query_params and not st.session_state.authenticated:
    token_response = get_access_token(query_params["code"])
    if "access_token" in token_response:
        st.session_state.authenticated = True
        st.session_state.token_data = token_response
        st.query_params.clear()
        st.rerun()

# --- 5. MAIN PAGE ROUTING ---
if not st.session_state.authenticated:
    show_login_screen()
    st.stop()

# --- 6. DASHBOARD (Only runs if authenticated) ---
st.success("✅ Connection Active!")
well_json, act_json, ath_json = get_ytd_data()

# --- MAIN DASHBOARD ---
if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

well_json, act_json, ath_json = get_ytd_data()

# --- WELLNESS SECTION ---
if well_json is not None:
    df = pd.DataFrame([well_json]) if isinstance(well_json, dict) else pd.DataFrame(well_json)

    if not df.empty:
        # 1. Standardize date column
        date_col = next((c for c in ['timestamp', 'id', 'date'] if c in df.columns), None)
        if date_col:
            df = df.rename(columns={date_col: 'date'})
            df['date'] = pd.to_datetime(df['date'])

        # 2. Safety Check: Ensure the required columns exist (Fixes the ValueError)
        required_cols = ['ctl', 'atl', 'tsb']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0.0

        # 3. Handle Form (TSB) calculation if missing
        if (df['tsb'] == 0).all() and 'ctl' in df.columns and 'atl' in df.columns:
             df['tsb'] = df['ctl'] - df['atl']

        # --- 4. DISPLAY GAUGES ---
        st.subheader("⚡ Current Training Status")
        latest = df.iloc[-1]
        g1, g2, g3 = st.columns(3)

        # Call the create_gauge function for each metric
        g1.plotly_chart(create_gauge(
            latest.get('ctl', 0), "Fitness (CTL)", 
            [{'range': [0, 100], 'color': "#70C4B0"}], 0, 100
        ), use_container_width=True)
        
        g2.plotly_chart(create_gauge(
            latest.get('atl', 0), "Fatigue (ATL)", 
            [{'range': [0, 120], 'color': "#E16C45"}], 0, 120
        ), use_container_width=True)
        
        form_steps = [
            {'range': [-60, -30], 'color': "#E16C45"}, 
            {'range': [-30, -10], 'color': "#4BD4B0"}, 
            {'range': [-10, 10], 'color': "#D4AA57"}, 
            {'range': [10, 60], 'color': "#E16C45"}
        ]
        g3.plotly_chart(create_gauge(
            latest.get('tsb', 0), "Form (TSB)", 
            form_steps, -60, 60
        ), use_container_width=True)

        # --- 5. YEARLY AREA CHART ---
        st.divider()
        st.subheader("📈 Yearly Training Load Progression")
        fig = px.area(df, x='date', y=['ctl', 'atl', 'tsb'], labels=pretty_labels)
        fig.for_each_trace(lambda t: t.update(name = pretty_labels.get(t.name, t.name)))
        fig.update_traces(stackgroup=None, fill='tozeroy', opacity=1,
    hovertemplate="<b>%{fullData.name} Score:</b> %{y:.1f}<extra></extra>"
)
        fig.update_layout(hovermode="x unified",hoverlabel=dict(bgcolor="white", font_size=14),
    xaxis=dict(
        hoverformat="%b %d, %Y",
        gridcolor="rgba(255, 255, 255, 0.1)",
        zerolinecolor="rgba(255, 255, 255, 0.3)",
        tickfont=dict(color="white", size=12),  # Labels like "Jan 2025"
        title=dict(text="Date", font=dict(color="white", size=14)) # Proper Title syntax
    ),
    # Y-Axis visibility settings
    yaxis=dict(
        gridcolor="rgba(255, 255, 255, 0.1)",
        zerolinecolor="rgba(255, 255, 255, 0.3)",
        tickfont=dict(color="white", size=12),  # Scores
        title=dict(text="Score", font=dict(color="white", size=14)) # Proper Title syntax
    ),
    # Background transparency
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    # Global font fallback
    font=dict(color="white")
)

    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Could not load wellness data.")

# --- ACTIVITIES SECTION ---
st.divider()
st.subheader("📅 Monthly Performance Summary")
if act_json:
    df_act = pd.DataFrame(act_json)
    df_act['category'] = df_act['type'].map(lambda x: TYPE_MAPPING.get(x, x))
    
    # Metrics with Glass Background
    df_act['date_dt'] = pd.to_datetime(df_act['start_date_local'])
    df_act['Month'] = df_act['date_dt'].dt.strftime('%B %Y')
    
    monthly = df_act.groupby('Month').agg({'id':'count', 'icu_training_load':'sum'}).reset_index()
    
    m1, m2 = st.columns(2)
    m1.metric("Avg. Monthly Sessions", f"{monthly['id'].mean():.1f}")
    m2.metric("Avg. Monthly Load", f"{monthly['icu_training_load'].mean():.0f}")
    
    st.dataframe(monthly, use_container_width=True, hide_index=True)