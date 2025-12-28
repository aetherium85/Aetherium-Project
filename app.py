import streamlit.components.v1 as components
import urllib.parse
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURATION (MUST BE FIRST) ---
st.set_page_config(page_title="Aetherium Project", layout="wide")

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

st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {
    visibility: hidden;
    height: 0%;
}

/* Hide the "Made with Streamlit" footer */
footer {
    visibility: hidden;
}
    /* 1. IMPORT FONT */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400&display=swap');

    /* 2. BACKGROUND & GLOBAL SETUP */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.4)), 
                    url("https://images.unsplash.com/photo-1663104192417-6804188a9a8e?v1") !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
        filter: blur(4px); 
        transform: scale(1.1);
        z-index: -1;
    }

    .stApp { background: transparent !important; }

    /* 3. TARGETED WHITE TEXT (Safe for Icons) */
    /* We target headers, paragraphs, and our custom classes specifically */
    h1, h2, h3, p, label, .performance-row, .performance-row div, .performance-row b {
        font-family: 'Inter', sans-serif !important;
        font-weight: 200 !important;
        color: white !important;
        letter-spacing: 1px;
    }

    /* 4. LAST SESSION (Hero) & METRIC FIX */
    /* This ensures the values inside your h1-h4 columns stay white */
    [data-testid="stHorizontalBlock"] div, 
    [data-testid="stMetricValue"], 
    [data-testid="stMetricLabel"] {
        color: white !important;
    }

    /* 5. GLASSMORPHISM CONTAINERS */
    div[data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart),
    .performance-row {
        background-color: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 15px !important;
        padding: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        margin-bottom: 10px !important;
    }

    .performance-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 25px !important;
    }

    /* 6. TRAINING STATUS GLOW (The Floating Stats) */
    [data-testid="stVerticalBlock"] > div:has(div[style*="text-shadow"]) {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* Architectural Header Styling */
    h3 {
        text-transform: uppercase !important;
        letter-spacing: 4px !important;
        font-size: 0.9rem !important;
        opacity: 0.8;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 3. FUNCTION DEFINITIONS ---

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
def elegant_hero_item(col, icon, label, value):
    with col:
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 15px; background: rgba(255,255,255,0.03); padding: 10px 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05);">
                <div style="font-size: 2rem; line-height: 1;">{icon}</div>
                <div>
                    <div style="font-size: 0.65rem; text-transform: uppercase; letter-spacing: 2px; color: rgba(255,255,255,0.5);">{label}</div>
                    <div style="font-size: 1.4rem; font-weight: 200; line-height: 1.1; color: white;">{value}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

# Muscle Focus Keyword Mapping
MUSCLE_KEYWORDS = {
    "Legs": ["squat", "leg", "quad", "hamstring", "glute", "calf", "deadlift", "lunge"],
    "Chest/Push": ["bench", "press", "push", "chest", "tricep", "shoulder", "dip"],
    "Back/Pull": ["row", "pull", "back", "deadlift", "lat", "bicep", "chin"],
    "Core": ["plank", "core", "abs", "situp", "crunch"],
    "Full Body": ["crossfit", "hiit", "metcon", "full"]
}

def get_muscle_focus(activity_name, description=""):
    text = (str(activity_name) + " " + str(description or "")).lower()
    for focus, keywords in MUSCLE_KEYWORDS.items():
        if any(word in text for word in keywords):
            return focus
    return "Mixed"

def get_ytd_data():
    if "token_data" not in st.session_state or st.session_state.token_data is None:
        return None, None, None
    
    # 1. DEFINE VARIABLES FIRST (So they are available everywhere in the function)
    token = st.session_state.token_data.get('access_token')
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://intervals.icu/api/v1/athlete/0" 
    
    first_day = datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    params = {'oldest': first_day, 'newest': today}
    
    try:
        # 2. PERFORM THE REQUESTS
        well_res = requests.get(f"{base_url}/wellness", headers=headers, params=params)
        act_res = requests.get(f"{base_url}/activities", headers=headers, params=params)
        ath_res = requests.get(base_url, headers=headers)
        
        # 3. DEBUGGING CHECK (This will now work because base_url/headers are defined)
        if well_res.status_code != 200:
            st.error(f"Wellness API Error {well_res.status_code}: {well_res.text}")
            return None, None, None

        wellness = well_res.json()
        activities = act_res.json()
        athlete = ath_res.json()

        # 4. DEEPER FETCH for Strength Details
        if activities and activities[0].get('type') == 'WeightTraining':
            act_id = activities[0].get('id')
            detail_res = requests.get(f"{base_url}/activities/{act_id}", headers=headers)
            if detail_res.status_code == 200:
                activities[0].update(detail_res.json())

        return wellness, activities, athlete

    except Exception as e:
        st.error(f"Connection failed: {e}")
        return None, None, None


# --- 6. DASHBOARD LOGIC ---
well_json, act_json, ath_json = get_ytd_data()

if act_json:
    latest_act = act_json[0]
    raw_type = latest_act.get('type', 'Other')
    display_type = TYPE_MAPPING.get(raw_type, "Workout")
    
    # Safe metrics (the 'or 0' prevents your distance crash!)
    secs = latest_act.get('moving_time') or 0
    duration_str = f"{secs // 3600}h {(secs % 3600) // 60}m"
    load = latest_act.get('icu_training_load') or 0

    # Dynamic Swap: Cardio vs Strength
    if display_type == "Strength":
        total_kg = latest_act.get('icu_weight') or 0
        h3_icon, h3_label, h3_value = "🏋️", "Total Volume", f"{total_kg:,.0f} kg"
        
        focus = get_muscle_focus(latest_act.get('name', ''), latest_act.get('description', ''))
        h4_icon, h4_label, h4_value = "🧬", "Muscle Focus", focus
    else:
        dist = (latest_act.get('distance') or 0) / 1000
        h3_icon, h3_label, h3_value = "🗺️", "Distance", f"{dist:.2f} km"
        
        hr = latest_act.get('average_heartrate') or 0
        h4_icon, h4_label, h4_value = "💓", "Avg. HR", f"{hr:.0f} bpm" if hr > 0 else "N/A"

    st.markdown(f"### 🚀 Last Session: {latest_act.get('name', 'Workout')} — {display_type}")
    
    h1, h2, h3, h4 = st.columns(4)
    elegant_hero_item(h1, "⏱️", "Duration", duration_str)
    elegant_hero_item(h2, "⚡", "Impact", f"{load} pts")
    elegant_hero_item(h3, h3_icon, h3_label, h3_value)
    elegant_hero_item(h4, h4_icon, h4_label, h4_value)
    st.markdown("<hr style='border-top: 1px solid white; opacity: 1; margin: 2rem 0;'>", unsafe_allow_html=True)


# --- WELLNESS SECTION ---
if well_json is not None:
    # Safely convert to DataFrame even if it's an empty list
    df = pd.DataFrame(well_json) 

    if df.empty:
        # Instead of an error, show a helpful warning for new users
        st.warning("📊 No wellness data found for 2025 yet. Start logging to see your fitness trends!")
    else:
        # Standardize date column names
        date_col = next((c for c in ['timestamp', 'id', 'date'] if c in df.columns), None)
        if date_col:
            df = df.rename(columns={date_col: 'date'})
            df['date'] = pd.to_datetime(df['date'])

        # Ensure core metrics exist to prevent chart crashes
        for col in ['ctl', 'atl', 'tsb']:
            if col not in df.columns:
                df[col] = 0.0

        # Calculate Form (TSB) if missing but CTL/ATL exist
        if (df['tsb'] == 0).all() and 'ctl' in df.columns and 'atl' in df.columns:
             df['tsb'] = df['ctl'] - df['atl']

        # --- RENDER STATS & CHARTS ---
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
        
        # --- YEARLY AREA CHART ---
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
    # This only triggers if the API call itself failed (e.g., 401 Unauthorized)
    st.error("🚫 Authentication Error: Could not connect to your wellness data.")    # --- ACTIVITIES SECTION ---
if act_json:
    df_act = pd.DataFrame(act_json)
    df_act['date_dt'] = pd.to_datetime(df_act['start_date_local'])
    df_act['Month'] = df_act['date_dt'].dt.strftime('%B %Y')
    
    monthly = df_act.groupby('Month', sort=False).agg({'id':'count', 'icu_training_load':'sum'}).reset_index()
    monthly.columns = ['Month', 'Sessions', 'Total Load']

    st.markdown("### 📅 Monthly Performance History")

    for index, row in monthly.iterrows():
        st.markdown(f"""
            <div class="performance-row">
                <div style="flex: 1; font-weight: bold; font-size: 1rem;">{row['Month']}</div>
                <div style="flex: 1; text-align: left;">🏃 <b>{row['Sessions']}</b> Sessions</div>
                <div style="flex: 1; text-align: left;">🔥 <b>{row['Total Load']:.0f}</b> Load</div>
            </div>
        """, unsafe_allow_html=True)