import streamlit.components.v1 as components
import urllib.parse
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==============================================================================
# --- SECTION 1: APP CONFIGURATION & STYLING ---
# ==============================================================================
st.set_page_config(page_title="Aetherium Project", layout="wide")

# Custom CSS for Glassmorphism UI
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] { visibility: visible; height: 0%; }
    footer { visibility: visible; }
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400&display=swap');

    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.4)), 
                    url("https://images.unsplash.com/photo-1663104192417-6804188a9a8e") !important;
        background-size: cover !important; background-position: center !important;
        background-attachment: fixed !important; filter: blur(4px); transform: scale(1.1); z-index: -1;
    }
    .stApp { background: transparent !important; }
    h1, h2, h3, p, label, .performance-row, .performance-row div, .performance-row b {
        font-family: 'Inter', sans-serif !important; font-weight: 200 !important;
        color: white !important; letter-spacing: 1px;
    }
    [data-testid="stHorizontalBlock"] div, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: white !important; }
    div[data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart), .performance-row {
        background-color: rgba(255, 255, 255, 0.05) !important; backdrop-filter: blur(10px) !important;
        border-radius: 15px !important; padding: 20px !important; border: 1px solid rgba(255, 255, 255, 0.1) !important;
        margin-bottom: 10px !important;
    }

    .stExpander {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }

    /* Target the text inside the expander specifically */
    .stExpander p, .stExpander span, .stExpander label {
        color: white !important;
    }

    /* Fix for Tables inside expanders */
    .stExpander table, .stExpander th, .stExpander td {
        color: white !important;
        background-color: transparent !important;
    }

    /* Fix for the Expander Header text specifically */
    summary[data-testid="stExpanderSummary"] {
        color: black !important;
    }
    
    .performance-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 25px !important; }
    h3 { text-transform: uppercase !important; letter-spacing: 4px !important; font-size: 0.9rem !important; opacity: 0.8; }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# --- SECTION 2: MAPPINGS & CONFIGURATION ---
# ==============================================================================
pretty_labels = {"ctl": "Fitness (CTL)", "atl": "Fatigue (ATL)", "tsb": "Form (TSB)", "date": "Date"}

TYPE_MAPPING = {
    "Ride": "Cycling", "GravelRide": "Cycling", "VirtualRide": "Cycling", 
    "Run": "Running", "TrailRun": "Running", "Treadmill": "Running", 
    "Walk": "Running/Walking", "Hike": "Running/Walking",
    "WeightTraining": "Strength", "Yoga": "Mobility", "Pilates": "Mobility"
}

MUSCLE_KEYWORDS = {
    "Legs": ["squat", "leg", "quad", "hamstring", "glute", "calf", "deadlift", "lunge"],
    "Chest/Push": ["bench", "press", "push", "chest", "tricep", "shoulder", "dip"],
    "Back/Pull": ["row", "pull", "back", "deadlift", "lat", "bicep", "chin"],
    "Core": ["plank", "core", "abs", "situp", "crunch"],
    "Full Body": ["crossfit", "hiit", "metcon", "full"]
}

# ==============================================================================
# --- SECTION 3: UTILITY FUNCTIONS (Logic & Processing) ---
# ==============================================================================
def get_status_label(metric, value):
    # Convert to lowercase and check if the keyword is IN the string
    m = metric.lower()
    
    if "fitness" in m:
        if value > 50: return "Elite Base"
        if value > 30: return "Strong Base"
        return "Building"
        
    if "fatigue" in m:
        if value > 40: return "Heavy Load"
        if value > 20: return "Productive"
        return "Light"
        
    if "form" in m:
        if value < -30: return "Overload"
        if value < -10: return "Productive"
        if value < 10: return "Optimal"
        return "Fresh"
    
    return "Neutral"

def get_muscle_focus(activity_name):
    """Detects multiple muscle groups from the activity name."""
    text = str(activity_name).lower()
    matches = []
    for focus, keywords in MUSCLE_KEYWORDS.items():
        if any(word in text for word in keywords):
            matches.append(focus)
    
    if not matches: return "General"
    if len(matches) >= 3: return "Full Body"
    return ", ".join(matches)

def elegant_hero_item(col, icon, label, value):
    """Renders a single glassmorphism metric card."""
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

def elegant_stat(col, label, value, color):
    # We pass the full label to the helper function now
    status_text = get_status_label(label, value)
    
    with col:
        st.markdown(f"""
            <div style="text-align: center; padding: 25px 10px; background: rgba(255, 255, 255, 0.03); 
                        border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px);">
                <p style="color: rgba(255,255,255,0.5); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 0;">{label}</p>
                <h1 style="color: white; font-size: 4rem; font-weight: 200; margin: 0; line-height: 1.1; text-shadow: 0 0 30px {color}66;">{int(value)}</h1>
                <div style="color: {color}; font-size: 0.85rem; font-weight: 400; text-transform: uppercase; letter-spacing: 2px; margin-top: 5px;">
                    ● {status_text}
                </div>
            </div>
        """, unsafe_allow_html=True)

# ==============================================================================
# --- SECTION 4: API & AUTHENTICATION ---
# ==============================================================================
def show_login_screen():
    st.title("❤️ Fitness Command Center")
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
        "client_id": st.secrets["INTERVALS_CLIENT_ID"], "client_secret": st.secrets["INTERVALS_CLIENT_SECRET"],
        "code": auth_code, "redirect_uri": st.secrets["REDIRECT_URI"], "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=payload)
    return response.json() if response.status_code == 200 else {}

def get_ytd_data():
    if "token_data" not in st.session_state or st.session_state.token_data is None:
        return None, None, None
    token = st.session_state.token_data.get('access_token')
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://intervals.icu/api/v1/athlete/0" 
    params = {'oldest': datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d'), 'newest': datetime.now().strftime('%Y-%m-%d')}
    
    try:
        well_res = requests.get(f"{base_url}/wellness", headers=headers, params=params)
        act_res = requests.get(f"{base_url}/activities", headers=headers, params=params)
        ath_res = requests.get(base_url, headers=headers)
        return well_res.json(), act_res.json(), ath_res.json()
    except Exception as e:
        st.error(f"Fetch failed: {e}"); return None, None, None

# ==============================================================================
# --- SECTION 5: APP ROUTING & SESSION STATE ---
# ==============================================================================
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

if not st.session_state.authenticated:
    show_login_screen()
    st.stop()

# ==============================================================================
# --- SECTION 6: HERO DASHBOARD (LAST SESSION) ---
# ==============================================================================
with st.sidebar:
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

well_json, act_json, ath_json = get_ytd_data()

if act_json:
    latest_act = act_json[0]
    raw_type = latest_act.get('type', 'Other')
    display_type = TYPE_MAPPING.get(raw_type, "Workout")
    
    # Common Data
    secs = latest_act.get('moving_time') or 0
    duration_str = f"{secs // 3600}h {(secs % 3600) // 60}m"
    load = latest_act.get('icu_training_load') or 0

    # STRENGTH Logic
    if display_type == "Strength":
        hours = secs / 3600
        intensity = load / hours if hours > 0 else 0
        h3_icon, h3_label, h3_value = "🔥", "Intensity", f"{intensity:.1f} pts/hr"
        focus_text = get_muscle_focus(latest_act.get('name', ''))
        h4_icon, h4_label, h4_value = "🧬", "Focus", focus_text
            
    # CARDIO Logic
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

# ==============================================================================
# --- SECTION 7: TRAINING STATUS (WELLNESS) ---
# ==============================================================================
if well_json:
    df = pd.DataFrame(well_json)
    if not df.empty:
        # Data Cleanup
        date_col = next((c for c in ['timestamp', 'id', 'date'] if c in df.columns), None)
        if date_col:
            df = df.rename(columns={date_col: 'date'})
            df['date'] = pd.to_datetime(df['date'])

        # Fitness Metrics Logic
        for col in ['ctl', 'atl', 'tsb']:
            if col not in df.columns: df[col] = 0.0
        if (df['tsb'] == 0).all(): df['tsb'] = df['ctl'] - df['atl']

        st.markdown("### ⚡ Your Current Training Status")
        latest = df.iloc[-1]
        s1, s2, s3 = st.columns(3)
        elegant_stat(s1, "Fitness - 42-day average load", latest.get('ctl', 0), "#70C4B0")
        elegant_stat(s2, "Fatigue - 7-day average load", latest.get('atl', 0), "#E16C45")
        tsb_val = latest.get('tsb', 0)
        tsb_color = "#4BD4B0" if tsb_val > -10 else "#E16C45"
        elegant_stat(s3, "Form - Readiness (Fitness - Fatigue)", tsb_val, tsb_color)
        
        st.markdown("<hr style='border-top: 1px solid white; opacity: 1; margin: 2rem 0;'>", unsafe_allow_html=True)
        
    # --- 📈 Yearly Training Load Progression ---
        st.markdown("### 📈 Yearly Training Load Progression")

        fig = px.line(df, x='date', y=['ctl', 'atl', 'tsb'], labels=pretty_labels)

        # 1. FIX: Clean up the hover template for each line
        fig.update_traces(
        line=dict(width=3),
        # <extra></extra> removes the "variable=ctl" side box
        # %{fullData.name} uses the human-readable name from pretty_labels
        hovertemplate="<b>%{fullData.name}</b>: %{y:.1f}<extra></extra>"
)

    # Apply colors if you are using the custom color mapping
    for trace in fig.data:
        trace_name = pretty_labels.get(trace.name, trace.name)
        if trace_name in colors:
            trace.line.color = colors[trace_name]

    fig.update_layout(
    hovermode="x unified",  # Keeps all metrics in one box
    hoverlabel=dict(
        bgcolor="rgba(30, 30, 30, 0.9)", # Dark background for the box
        font_size=14,
        font_family="Inter",
        font_color="white"
    ),
    # ... rest of your styling ...
    xaxis=dict(
        gridcolor="rgba(255, 255, 255, 0.1)",
        tickfont=dict(color="white"),
        title=None,
        # 2. FIX: Format the date at the top of the hover box
        hoverformat="%b %d, %Y" 
    ),
    yaxis=dict(
        gridcolor="rgba(255, 255, 255, 0.1)",
        tickfont=dict(color="white"),
        zeroline=True,
        zerolinecolor="rgba(255, 255, 255, 0.5)",
        title=dict(text="Score", font=dict(color="white"))
    ),
    # ... ensure paper_bgcolor and plot_bgcolor are transparent ...
)

    st.plotly_chart(fig, use_container_width=True)
        
# ==============================================================================
# --- SECTION 8: PERFORMANCE HISTORY ---
# ==============================================================================
if act_json:
    df_act = pd.DataFrame(act_json)
    df_act['Month'] = pd.to_datetime(df_act['start_date_local']).dt.strftime('%B %Y')
    monthly = df_act.groupby('Month', sort=False).agg({'id':'count', 'icu_training_load':'sum'}).reset_index()
    monthly.columns = ['Month', 'Sessions', 'Total Load']

    st.markdown("### 📅 Monthly Performance History")
    for _, row in monthly.iterrows():
        st.markdown(f"""
            <div class="performance-row">
                <div style="flex: 1; font-weight: bold; font-size: 1rem;">{row['Month']}</div>
                <div style="flex: 1; text-align: left;">🏃 <b>{row['Sessions']}</b> Sessions</div>
                <div style="flex: 1; text-align: left;">🔥 <b>{row['Total Load']:.0f}</b> Load</div>
            </div>
        """, unsafe_allow_html=True)