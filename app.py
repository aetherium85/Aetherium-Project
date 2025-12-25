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

# --- 2. THE FINAL CSS FIX (Background + Elegant Typography + Icon Fix) ---
st.markdown(
    """
    <style>
    /* 1. IMPORT ELEGANT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400&display=swap');

    /* 2. BACKGROUND LAYER */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.4)), 
                    url("https://images.unsplash.com/photo-1619359209643-20df6a2465adv1") !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
        filter: blur(4px); 
        -webkit-filter: blur(4px);
        transform: scale(1.1);
        z-index: -1;
    }

    .stApp {
        background: transparent !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* 3. GLOBAL ELEGANT TYPOGRAPHY */
    /* This forces ALL text to be thin and spaced out */
    h1, h2, h3, p, span, label, div, b, .stMetric label, [data-testid="stMetricValue"] {
        font-family: 'Inter', sans-serif !important;
        font-weight: 200 !important;
        letter-spacing: 1.5px !important;
        color: white !important;
    }

    /* --- ICON RECOVERY FIX --- */
    /* This excludes the sidebar icons from the font override so they render correctly */
    [data-testid="stSidebarCollapseIcon"] span, 
    [data-testid="stIcon"], 
    button[kind="header"] span {
        font-family: "Material Symbols Rounded", sans-serif !important;
        letter-spacing: normal !important;
        font-weight: normal !important;
    }

    /* Make headers feel more 'Architectural' */
    h1, h2, h3 {
        text-transform: uppercase !important;
        letter-spacing: 4px !important;
    }

    /* 4. SIDEBAR & HEADER RESET (Keep them readable but elegant) */
    [data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.4) !important;
        backdrop-filter: blur(15px);
    }
    
    /* Make sidebar text white to match the elegant theme */
    [data-testid="stSidebar"] span, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
        color: white !important;
        font-weight: 300 !important;
    }

    header[data-testid="stHeader"] {
        background-color: transparent !important;
    }

    /* 5. GLASSMORPHISM FOR CONTAINERS */
    div[data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart),
    .performance-row {
        background-color: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 15px !important;
        padding: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        margin-bottom: 10px !important;
    }

    /* PERFORMANCE ROWS SPECIFIC LAYOUT */
    .performance-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 25px !important;
    }

    /* 6. CLEANING UP METRIC BOXES */
    [data-testid="stMetricValue"] {
        font-size: 2.8rem !important;
        line-height: 1 !important;
    }

    /* Ensure the elegant stats stay transparent */
    [data-testid="stVerticalBlock"] > div:has(div[style*="text-shadow"]) {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    /* Prevent global font rules from blowing up the Hero containers */
    [data-testid="stHorizontalBlock"] {
        gap: 10px !important;
    }

    /* Adjusting the subheaders to be smaller and cleaner */
    h3 {
        font-size: 0.9rem !important;
        margin-bottom: 1rem !important;
        opacity: 0.8;
    }

    /* Ensure metrics don't overflow if you still use them elsewhere */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important; /* Scaled down from 2.8rem */
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
well_json, act_json, ath_json = get_ytd_data()

# --- MAIN DASHBOARD ---
if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

well_json, act_json, ath_json = get_ytd_data()

if act_json:
    latest_act = act_json[0]
    
    # Data Formatting
    secs = latest_act.get('moving_time', 0)
    duration_str = f"{secs // 3600}h {(secs % 3600) // 60}m"
    dist = latest_act.get('distance', 0) / 1000
    hr = latest_act.get('average_heartrate', 0)
    load = latest_act.get('icu_training_load', 0)

    st.markdown(f"### 🚀 Last Session: {latest_act.get('name', 'Workout')}")
    
    # Using a container with custom CSS class for the Hero Row
    h1, h2, h3, h4 = st.columns(4)
    
    def elegant_hero_item(col, icon, label, value):
        with col:
            st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 15px; background: rgba(255,255,255,0.03); padding: 10px 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                    <div style="font-size: 2rem; line-height: 1;">{icon}</div>
                    <div>
                        <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 2px; color: rgba(255,255,255,0.5);">{label}</div>
                        <div style="font-size: 1.4rem; font-weight: 200; line-height: 1.1;">{value}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    elegant_hero_item(h1, "⏱️", "Duration", duration_str)
    elegant_hero_item(h2, "⚡", "Impact", f"{load} pts")
    elegant_hero_item(h3, "🗺️", "Distance", f"{dist:.2f} km" if dist > 0 else "N/A")
    elegant_hero_item(h4, "💓", "Avg. HR", f"{hr:.0f} bpm" if hr > 0 else "N/A")

    st.markdown("<hr style='border-top: 1px solid white; opacity: 1; margin: 2rem 0;'>", unsafe_allow_html=True)

# --- WELLNESS SECTION ---
# --- WELLNESS & DATA PREP ---
if well_json is not None:
    # 1. Standardize the data into a DataFrame
    df = pd.DataFrame([well_json]) if isinstance(well_json, dict) else pd.DataFrame(well_json)

    if not df.empty:
        # Standardize date column
        date_col = next((c for c in ['timestamp', 'id', 'date'] if c in df.columns), None)
        if date_col:
            df = df.rename(columns={date_col: 'date'})
            df['date'] = pd.to_datetime(df['date'])

        # Safety Check for metrics
        for col in ['ctl', 'atl', 'tsb']:
            if col not in df.columns:
                df[col] = 0.0

        if (df['tsb'] == 0).all() and 'ctl' in df.columns and 'atl' in df.columns:
             df['tsb'] = df['ctl'] - df['atl']

                # --- FEATURE: FLOATING STATS (Current Status) ---
        st.markdown("### ⚡ Your Current Training Status")
        latest = df.iloc[-1]
        s1, s2, s3 = st.columns(3)

        def elegant_stat(col, label, value, color):
            with col:
             st.markdown(f"""
            <div style="text-align: center; padding: 25px 10px; background: rgba(255, 255, 255, 0.03); 
                        border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px);">
                <p style="color: rgba(255,255,255,0.5); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 0; font-weight: 200;">{label}</p>
                <h1 style="color: white; font-size: 4rem; font-weight: 200; margin: 0; line-height: 1.2; text-shadow: 0 0 30px {color}66; font-family: 'Inter', sans-serif;">{int(value)}</h1>
            </div>
        """, unsafe_allow_html=True)

        elegant_stat(s1, "Fitness (CTL)", latest.get('ctl', 0), "#70C4B0")
        elegant_stat(s2, "Fatigue (ATL)", latest.get('atl', 0), "#E16C45")
        
        tsb_val = latest.get('tsb', 0)
        tsb_color = "#4BD4B0" if tsb_val > -10 else "#E16C45"
        elegant_stat(s3, "Form (TSB)", tsb_val, tsb_color)
        st.markdown("<hr style='border-top: 1px solid white; opacity: 1; margin: 2rem 0;'>", unsafe_allow_html=True)
        # --- FEATURE: YEARLY AREA CHART ---
        st.markdown("### 📈 Yearly Training Load Progression")
        
        fig = px.area(df, x='date', y=['ctl', 'atl', 'tsb'], labels=pretty_labels)
        fig.for_each_trace(lambda t: t.update(name = pretty_labels.get(t.name, t.name)))
        
        fig.update_traces(
            stackgroup=None, fill='tozeroy', opacity=0.5,
            hovertemplate="<b>%{fullData.name}</b>: %{y:.1f}<extra></extra>"
        )

        fig.update_layout(
            hovermode="x unified",
            hoverlabel=dict(bgcolor="white", font_size=14, font_color="black"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor="rgba(255, 255, 255, 0.2)", tickfont=dict(color="white")),
            yaxis=dict(gridcolor="rgba(255, 255, 255, 0.1)", tickfont=dict(color="white"))
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("<hr style='border-top: 1px solid white; opacity: 1; margin: 2rem 0;'>", unsafe_allow_html=True)

else:
    st.error("Could not load wellness data.")
# --- ACTIVITIES SECTION ---
if act_json:
    # Prepare Data
    df_act = pd.DataFrame(act_json)
    df_act['date_dt'] = pd.to_datetime(df_act['start_date_local'])
    df_act['Month'] = df_act['date_dt'].dt.strftime('%B %Y')
    
    # Ensure months are sorted newest to oldest
    monthly = df_act.groupby('Month', sort=False).agg({'id':'count', 'icu_training_load':'sum'}).reset_index()
    monthly.columns = ['Month', 'Sessions', 'Total Load']

    st.markdown("### 📅 Monthly Performance History")

    for index, row in monthly.iterrows():
        # Using a custom div class 'performance-row' for total control
        st.markdown(f"""
            <div class="performance-row">
                <div style="flex: 2; font-weight: bold; font-size: 1.1rem;">{row['Month']}</div>
                <div style="flex: 1; text-align: center;">🏃 <b>{row['Sessions']}</b> Sessions</div>
                <div style="flex: 1; text-align: right;">🔥 <b>{row['Total Load']:.0f}</b> Load</div>
            </div>
        """, unsafe_allow_html=True)