from google import genai
import os
import textwrap
import streamlit.components.v1 as components
import urllib.parse
import streamlit as st
import base64
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta


# ==============================================================================
# --- SECTION 1: CONFIG & CSS ---
# ==============================================================================
st.set_page_config(page_title="Aetherium Project", page_icon="⚡", layout="wide")

# Custom CSS for Glassmorphism UI
st.markdown(
    """
    <style>
    /* 1. IMPORTS & BASICS */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;600&family=Michroma&display=swap');
    
    /* Global Text Defaults */
    h1, h2, h3, h4, h5, h6, p, label, strong, b, li {
        color: white !important; 
        font-family: 'Inter', sans-serif !important;
    }

    /* 2. BACKGROUND IMAGE */
    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.4)), 
                    url("https://images.unsplash.com/photo-1663104192417-6804188a9a8e");
        background-size: cover; background-position: center;
        background-attachment: fixed; filter: blur(18px); transform: scale(1.1); z-index: -1;
    }
    .stApp { background: transparent !important; }

    /* 3. THE "RESULT BOX" FIX (Dark Glass Container) */
    /* This targets st.container(border=True) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: rgba(0, 0, 0, 0.6) !important; /* Dark background */
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
    }
    
    /* Fix the white background issue on inner elements */
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: transparent !important;
    }

    /* Force Text inside the box to be WHITE and readable */
    div[data-testid="stVerticalBlockBorderWrapper"] p,
    div[data-testid="stVerticalBlockBorderWrapper"] li, 
    div[data-testid="stVerticalBlockBorderWrapper"] div {
        color: #FFFFFF !important;
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
    }

    /* Header Styling inside the box */
    div[data-testid="stVerticalBlockBorderWrapper"] h3 {
        color: #70C4B0 !important; /* Teal Header */
        font-weight: 600 !important;
        margin-bottom: 15px !important;
    }

    /* 4. BUTTON FIX (Prevent White-on-White) */
    /* Target buttons inside the container */
    div[data-testid="stVerticalBlockBorderWrapper"] button {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] button:hover {
        border-color: #70C4B0 !important;
        color: #70C4B0 !important;
    }
    
    /* 5. METRICS & PLOTS */
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: white !important; }
    div[data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart) {
        background-color: rgba(255, 255, 255, 0.03) !important; 
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 15px;
    }

    /* 6. SIDEBAR & LOGOUT */
    button[data-testid="stSidebarCollapseButton"] { color: white !important; }
    
    /* 7. TITLE BRANDING */
    .title-main {
        font-family: 'Michroma', sans-serif !important;
        font-size: 3rem !important;
        color: white !important;
        text-shadow: 0 0 15px rgba(112, 196, 176, 0.4);
    }
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
def upload_workout_to_intervals(token, athlete_id, workout_text, sport, date_str):
    """
    Pushes the AI workout directly to the athlete's Intervals.icu calendar.
    """
    url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/events"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Map our internal sport names to Intervals.icu types
    type_map = {
        "Running": "Run",
        "Cycling": "Ride",
        "Swimming": "Swim",
        "Strength Training": "WeightTraining",
        "Hyrox / Functional": "Workout"
    }
    sport_type = type_map.get(sport, "Workout")
    
    # Construct the payload
    payload = {
        "category": "WORKOUT",
        "start_date_local": f"{date_str}T09:00:00", # Default to 9 AM
        "type": sport_type,
        "name": f"AI Coach: {sport}",
        "description": f"{workout_text}\n\n(Generated by Aetherium AI)",
        "moving_time": 3600 # Default duration placeholder
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code in [200, 201]:
            return True, res.json()
        else:
            return False, res.text
    except Exception as e:
        return False, str(e)

def get_status_label(metric, value):
    m = metric.lower()
    
    # FITNESS: Long-term base building
    if "fitness" in m:
        if value > 50: return "Elite Base"
        if value > 30: return "Strong Base"
        return "Building"
        
    # FATIGUE: Short-term training stress
    if "fatigue" in m:
        if value > 40: return "Heavy Load"
        if value > 20: return "Productive"
        return "Light"
        
    # FORM: Readiness and Recovery (TSB)
    if "form" in m:
        if value < -30: return "Overload / Risk"
        if value < -10: return "Productive"
        if value < 5:   return "Optimal / Ready"
        if value < 15:  return "Fresh"
        return "Recovery"
    
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

def infer_primary_sport(activities):
    if not activities:
        return "General Fitness"
    
    # Count occurrences of mapped types (Running, Cycling, etc.)
    type_counts = {}
    for a in activities:
        # Use your existing TYPE_MAPPING dict
        raw_type = a.get('type', 'Other')
        # Map 'VirtualRide' -> 'Cycling', etc.
        sport = TYPE_MAPPING.get(raw_type, raw_type)
        type_counts[sport] = type_counts.get(sport, 0) + 1
    
    # Return the most frequent sport
    return max(type_counts, key=type_counts.get)

def show_login_screen():
    # Re-applying your clean branding
    st.markdown(f"""
        <div class="brand-wrapper">
            <img src="data:image/png;base64,{LOGO_BASE64}" style="width: 70px; margin-bottom: 20px;">
            <div class="title-container">
                <div class="title-main">aetherium</div>
                <div class="title-sub">PROJECT</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Standard URL construction using urllib
    params = {
        'client_id': st.secrets['INTERVALS_CLIENT_ID'],
        'redirect_uri': st.secrets['REDIRECT_URI'],
        'response_type': 'code',
        'scope': 'ACTIVITY:READ,WELLNESS:READ'
    }
    auth_url = f"https://intervals.icu/oauth/authorize?{urllib.parse.urlencode(params)}"

    # Create 3 columns: [Spacer, Button, Spacer]
    # The middle column (2) is where the button goes.
    col1, col2, col3 = st.columns([1, 2, 1]) 

    with col2:
        # The CSS above will still style the colors, but this forces the position
        st.link_button("🚀 Connect with Intervals.icu", auth_url, type="primary", use_container_width=True)

def get_access_token(auth_code):
    token_url = "https://intervals.icu/api/oauth/token"
    payload = {
        "client_id": st.secrets["INTERVALS_CLIENT_ID"], "client_secret": st.secrets["INTERVALS_CLIENT_SECRET"],
        "code": auth_code, "redirect_uri": st.secrets["REDIRECT_URI"], "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=payload)
    return response.json() if response.status_code == 200 else {}

# --- PERSISTENCE HELPERS ---
TOKEN_FILE = "auth_token.json"

def save_token_to_disk(token_data):
    """Saves the token to a local JSON file."""
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)

def load_token_from_disk():
    """Loads the token from disk if it exists."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None

def get_ytd_data():
    if "token_data" not in st.session_state or st.session_state.token_data is None:
        return None, None, None
        
    token = st.session_state.token_data.get('access_token')
    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://intervals.icu/api/v1/athlete/0" 
    
    # --- CHANGED LOGIC HERE ---
    # Old: datetime(datetime.now().year, 1, 1)  (Jan 1st of this year)
    # New: datetime.now() - timedelta(days=365) (Exactly 1 year ago today)
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now() + timedelta(days=1)
    params = {
        'oldest': start_date.strftime('%Y-%m-%d'), 
        'newest': end_date.strftime('%Y-%m-%d')
    }
    
    try:
        well_res = requests.get(f"{base_url}/wellness", headers=headers, params=params)
        act_res = requests.get(f"{base_url}/activities", headers=headers, params=params)
        ath_res = requests.get(base_url, headers=headers)
        return well_res.json(), act_res.json(), ath_res.json()
    except Exception as e:
        st.error(f"Fetch failed: {e}")
        return None, None, None

def build_ai_prompt(sport, discipline, goal, time_str, form, recent_activities):
    """
    Constructs the prompt for the AI, now including the specific Discipline.
    """
    # 1. Summarize last 3 workouts
    recent_context = "None"
    if recent_activities:
        sorted_acts = sorted(recent_activities, key=lambda x: x['start_date_local'], reverse=True)[:3]
        recent_context = ""
        for act in sorted_acts:
            name = act.get('name', 'Unknown')
            type_ = act.get('type', 'Workout')
            date = act.get('start_date_local', '')[:10]
            recent_context += f"- {date}: {type_} ({name})\n"

    # 2. Determine Biological State
    bio_state = "Neutral"
    if form < -20: bio_state = "High Fatigue"
    elif -20 <= form < -5: bio_state = "Fatigued"
    elif -5 <= form <= 15: bio_state = "Fresh"
    elif form > 15: bio_state = "Very Fresh"

    # 1. Handle Time String
    if str(time_str).lower() == "no limit":
        time_text = "Unlimited (Design the optimal duration for this specific workout)"
    else:
        # Strip " mins" from the string if it exists to get just the number
        clean_time = str(time_str).replace(" mins", "")
        time_text = f"{clean_time} minutes"
    
    # 2. The Strict Prompt (Update the 'Time Available' line)
    prompt = f"""
    Act as an elite {sport} coach. Write a specific {discipline} workout for today.
    
    **Context:**
    - Macro Sport: {sport}
    - Specific Discipline: {discipline}
    - Goal: {goal}
    - Time Available: {time_text}
    - Athlete Status: {int(form)} ({bio_state})
    - Recent History:
    {recent_context}
    
    **Strict Output Rules:**
    1. NO conversational filler.
    2. BE CONCISE. Use short bullet points.
    3. Format exactly like this:
       **Workout Name**
       **Warm Up** (Bullet points)
       **Main Set** (Bullet points, specific intervals)
       **Cool Down** (Bullet points)
       **Coach's Logic** (1 sentence explaining why this fits the history/status)
    """
    return prompt

# ==============================================================================
# --- SECTION 5: AUTHENTICATION (MULTI-USER SAFE) ---
# ==============================================================================
query_params = st.query_params

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 1. Handle the OAuth Callback (The "Return" from Intervals.icu)
if "code" in query_params:
    if not st.session_state.authenticated:
        code = query_params["code"]
        token_response = get_access_token(code)
        
        if "access_token" in token_response:
            st.session_state.authenticated = True
            st.session_state.token_data = token_response
            st.toast("✅ Login Successful!", icon="🔐")
            # Clear the code from URL so it doesn't try to log in again on refresh
            st.query_params.clear()
        else:
            st.error("Login failed. Please try again.")

# 2. Show Login Screen if not authenticated
if not st.session_state.authenticated:
    show_login_screen()
    st.stop() # Stop the app here until they log in

# ==============================================================================
# --- SECTION 6: HERO DASHBOARD (LAST SESSION) ---
# ==============================================================================
with st.sidebar:
    if st.button("Logout"):
        # 1. Remove the persistent file
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            
        # 2. Clear Session State
        st.session_state.authenticated = False
        st.session_state.token_data = None
        st.rerun()

well_json, act_json, ath_json = get_ytd_data()

if ath_json:
    st.session_state.athlete_profile = ath_json

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

    st.markdown(f"### 🚀 Last Session: {display_type} - {latest_act.get('name', 'Workout')}")
    h1, h2, h3, h4 = st.columns(4)
    elegant_hero_item(h1, "⏱️", "Duration", duration_str)
    elegant_hero_item(h2, "⚡", "Impact", f"{load} pts")
    elegant_hero_item(h3, h3_icon, h3_label, h3_value)
    elegant_hero_item(h4, h4_icon, h4_label, h4_value)

st.markdown("<hr style='border-top: 1px solid white; opacity: 1; margin: 2rem 0;'>", unsafe_allow_html=True)

# ==============================================================================
# --- SECTION 6.1: METRICS CALCULATION (The Math) ---
# ==============================================================================
import pandas as pd
from datetime import datetime, timedelta

# # 1. PREPARE DATA
if 'act_json' not in locals() or not act_json:
    # Fallback if no data exists
    current_fitness = 0
    current_fatigue = 0
    current_form = 0
    df_daily = pd.DataFrame() # Create empty DF to prevent errors
else:
    df = pd.DataFrame(act_json)
    
    # Ensure date column is actual datetime objects
    df['start_date_local'] = pd.to_datetime(df['start_date_local'])
    df = df.sort_values('start_date_local')

    # 2. CALCULATE DAILY LOAD (TSS Estimate)
    def estimate_load(row):
        if 'suffer_score' in row and row['suffer_score']:
            return row['suffer_score']
        elif 'moving_time' in row:
            hours = row['moving_time'] / 3600
            return hours * 50 
        return 0

    df['TSS'] = df.apply(estimate_load, axis=1)

    # 3. CALCULATE ATL, CTL, TSB
    # We set index to date to resample daily
    df_indexed = df.set_index('start_date_local')
    daily_load = df_indexed['TSS'].resample('D').sum().fillna(0)

    # Constants
    ctl_decay = 42 
    atl_decay = 7 

    # Calculate Exponential Weighted Averages
    ctl = daily_load.ewm(span=ctl_decay, adjust=False).mean()
    atl = daily_load.ewm(span=atl_decay, adjust=False).mean()
    tsb = ctl - atl

    # 4. SAVE TO A DEDICATED PLOTTING DATAFRAME (The Fix)
    # We create a new DataFrame specifically for the chart
    df_daily = pd.DataFrame({
        'ctl': ctl,
        'atl': atl,
        'tsb': tsb
    })
    # The index is already the date, let's make it a column for easier plotting
    df_daily['date'] = df_daily.index

    # 5. GET CURRENT VALUES (For the top dashboard cards)
    if not ctl.empty:
        current_fitness = ctl.iloc[-1]
        current_fatigue = atl.iloc[-1]
        current_form = tsb.iloc[-1]
    else:
        current_fitness = 0
        current_fatigue = 0
        current_form = 0

# ==============================================================================
# --- SECTION 7: TRAINING STATUS DASHBOARD ---
# ==============================================================================
st.markdown("### ⚡ Your Current Training Status")

# 1. THE INSIGHT BOX (The "Green Zone" Box)
# -----------------------------------------------------------
# (This logic remains the same as your previous code)
if current_form >= 5:
    status_color = "#4CAF50" # Green
    status_title = "PRIME FOR INTENSITY"
    status_msg = "You are fresh and ready to absorb stress. Recommended: Threshold Intervals, Hill Repeats, or Heavy Strength Session."
elif -10 < current_form < 5:
    status_color = "#FFC107" # Amber
    status_title = "MAINTENANCE / PRODUCTIVE"
    status_msg = "You are in the sweet spot. Keep training consistent. Recommended: Zone 2 Base, Tempo work, or Technique drills."
else:
    status_color = "#FF5252" # Red
    status_title = "HIGH FATIGUE WARNING"
    status_msg = "Your fatigue is high. Risk of overtraining or injury. Recommended: Active Recovery, Yoga, or a Complete Rest Day."

st.markdown(f"""
    <div style="background-color: rgba(255,255,255,0.05); border-left: 4px solid {status_color}; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <strong style="color: {status_color}; letter-spacing: 1px;">{status_title}</strong><br>
        <span style="font-size: 0.9rem; color: #ddd;">{status_msg}</span>
    </div>
""", unsafe_allow_html=True)

# 2. THE METRICS CARDS (Moved UP to be visible immediately)
# -----------------------------------------------------------
m1, m2, m3 = st.columns(3)

def render_metric_card(col, title, value, subtext, color="#70C4B0"):
    with col:
        st.markdown(f"""
            <div style="background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 15px; text-align: center;">
                <div style="font-size: 0.8rem; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 1px;">{title}</div>
                <div style="font-size: 2rem; font-weight: 700; color: white; margin: 5px 0;">{int(value)}</div>
                <div style="font-size: 0.7rem; color: {color}; font-weight: 600; text-transform: uppercase;">● {subtext}</div>
            </div>
        """, unsafe_allow_html=True)

render_metric_card(m1, "Fitness (CTL)", current_fitness, "Building")
render_metric_card(m2, "Fatigue (ATL)", current_fatigue, "Productive")
render_metric_card(m3, "Form (TSB)", current_form, "Fresh" if current_form >= 0 else "Tired", color=status_color)


# ==============================================================================
# --- SECTION 7.1: AI WORKOUT PLANNER (WITH SAVE BUTTON) ---
# ==============================================================================
st.markdown("---") # Visual Separator

# 1. SETUP CLIENT
try:
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else None
except:
    client = None

# 2. CONFIGURATION & MAPPINGS
st.markdown("### ⚙️ AI Coach Settings")

# --- A. SPORT & DISCIPLINE DEFINITIONS ---
SPORT_DISCIPLINES = {
    "Triathlon": ["Bike", "Run", "Swim", "Brick (Bike+Run)", "Strength / Core"],
    "Hyrox / Functional": ["Hyrox Sim (Run+Station)", "Sled Work", "MetCon / HIIT", "Engine (Running)", "Strength"],
    "Running": ["Road Run", "Track / Intervals", "Trail Run", "Long Run", "Strength / Plyos"],
    "Cycling": ["Road Ride", "Indoor Trainer", "Gravel / MTB", "Strength"],
    "Swimming": ["Pool Session", "Open Water", "Dryland Strength"],
    "General Fitness": ["Full Body Strength", "Upper Body", "Lower Body", "Cardio / Zone 2", "Mobility / Yoga"]
}

# --- B. GOAL CATEGORIES ---
GOAL_SETS = {
    "Cardio": ["Base Building (Zone 2)", "Threshold / FTP", "VO2 Max", "Race Pace Intervals", "Recovery"],
    "Strength": ["Hypertrophy (Muscle Gain)", "Max Strength (Low Reps)", "Power / Explosiveness", "Muscular Endurance", "Recovery / Mobility"],
    "Swim": ["Technique / Drills", "Aerobic Endurance", "CSS / Threshold", "Sprints / Anaerobic", "Recovery"],
    "Hyrox": ["Race Simulation", "Sled Power", "Running Engine", "Muscular Endurance", "Technique"]
}

# --- C. HELPER: GET GOALS FOR SELECTION ---
def get_relevant_goals(sport, discipline):
    d = discipline.lower()
    if "strength" in d or "plyo" in d or "upper" in d or "lower" in d: return GOAL_SETS["Strength"]
    if "swim" in d or "pool" in d: return GOAL_SETS["Swim"]
    if "hyrox" in d or "sled" in d or "metcon" in d: return GOAL_SETS["Hyrox"]
    return GOAL_SETS["Cardio"]

# --- D. SMART AUTO-DETECT DEFAULTS ---
default_sport_index = 0
if 'act_json' in locals() and act_json:
    try:
        detected_raw = infer_primary_sport(act_json)
        mapping_map = {
            "Run": "Running", "Ride": "Cycling", "Swim": "Swimming",
            "WeightTraining": "General Fitness", "CrossFit": "Hyrox / Functional"
        }
        detected = mapping_map.get(detected_raw, detected_raw)
        sport_keys = list(SPORT_DISCIPLINES.keys())
        if detected in sport_keys:
            default_sport_index = sport_keys.index(detected)
    except: pass

# --- E. RENDER INPUTS (4 Columns) ---
c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 0.8])

with c1:
    selected_sport = st.selectbox("Sport Focus", list(SPORT_DISCIPLINES.keys()), index=default_sport_index, key="sport_select")
with c2:
    discipline_options = SPORT_DISCIPLINES[selected_sport]
    selected_discipline = st.selectbox("Discipline", discipline_options, index=0, key="disc_select")
with c3:
    available_goals = get_relevant_goals(selected_sport, selected_discipline)
    default_goal_idx = 0
    if 'current_form' in locals():
        if current_form < -10: 
            for i, g in enumerate(available_goals):
                if "Recovery" in g: default_goal_idx = i; break
        elif current_form >= 0:
            keywords = ["Threshold", "Max Strength", "Race Simulation", "CSS"]
            for i, g in enumerate(available_goals):
                if any(k in g for k in keywords): default_goal_idx = i; break
        else:
            default_goal_idx = 0
    user_goal = st.selectbox("Goal", available_goals, index=default_goal_idx, key="goal_select")
with c4:
    time_options = ["30 mins", "45 mins", "60 mins", "75 mins", "90 mins", "120 mins", "No Limit"]
    time_avail = st.select_slider("Time Available", options=time_options, value="60 mins", key="time_select")

# 3. GENERATION ACTION
b1, b2, b3 = st.columns([1, 2, 1])

with b2:
    st.markdown("""<style>div[data-testid="column"] { margin-top: 15px; }</style>""", unsafe_allow_html=True)
    generate_btn = st.button("✨ GENERATE NEXT WORKOUT", type="primary", use_container_width=True)

if generate_btn:
    if not client:
        st.error("❌ AI Client not connected.")
    else:
        with st.spinner(f"Designing {selected_sport} ({selected_discipline}) session..."):
            ai_prompt = build_ai_prompt(selected_sport, selected_discipline, user_goal, time_avail, current_form, act_json)
            
            try:
                # 1. GENERATE CONTENT
                response = client.models.generate_content(
                    model="gemini-2.0-flash-lite", 
                    contents=ai_prompt
                )

                # 2. SAVE TO SESSION STATE (Crucial for the Save Button to work!)
                st.session_state.last_workout = response.text
                st.session_state.last_sport = selected_sport

                # 3. INJECT CSS
                st.markdown("""
                <style>
                .ai-response { color: white !important; }
                .ai-response p, .ai-response li, .ai-response strong { color: white !important; font-size: 0.9rem; }
                </style>
                """, unsafe_allow_html=True)

                # 4. DISPLAY RESULT
                st.markdown("---")
                st.markdown(f"### ⚡ Recommended: {selected_discipline}")
                
                with st.container(border=True):
                    st.markdown(response.text)
                
                # 5. SAVE BUTTON (NEW FEATURE)
                st.markdown("###") # Spacer
                c_save, c_void = st.columns([1, 2])
                
                with c_save:
                    if st.button("📅 Add to Calendar (Tomorrow)", type="secondary", icon="📤"):
                        # Get ID and Token
                        athlete = st.session_state.get('athlete_profile', {})
                        athlete_id = athlete.get('id', '0')
                        token = st.session_state.token_data.get('access_token') if st.session_state.token_data else None
                        
                        if not token:
                            st.error("You must be logged in to save workouts.")
                        else:
                            # Set Date (Tomorrow)
                            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                            
                            # Upload
                            success, msg = upload_workout_to_intervals(
                                token,
                                athlete_id,
                                st.session_state.last_workout,
                                st.session_state.last_sport,
                                tomorrow
                            )
                            
                            if success:
                                st.toast(f"✅ Saved to {tomorrow}!", icon="📅")
                                st.balloons()
                            else:
                                st.error(f"Save failed: {msg}")

            except Exception as e:
                if "429" in str(e):
                    st.toast("⚠️ Primary model busy. Retrying...", icon="🔄")
                else:
                    st.error(f"Generation Failed: {e}")

# # ==============================================================================
# --- (NEXT SECTION: YEARLY TRAINING LOAD) ---
# ==============================================================================
st.markdown("<hr style='border-top: 1px solid white; opacity: 1; margin: 2rem 0;'>", unsafe_allow_html=True)
st.markdown("### 📈 Yearly Training Load Progression")

# Check if our new 'df_daily' exists and has data
if 'df_daily' in locals() and not df_daily.empty:
    colors = {
        "Fitness (CTL)": "#70C4B0",
        "Fatigue (ATL)": "#E16C45",
        "Form (TSB)": "#4BD4B0"
    }

    fig = go.Figure()

    for col in ['ctl', 'atl', 'tsb']:
        full_name = pretty_labels.get(col, col)
        fig.add_trace(go.Scatter(
            x=df_daily['date'],  # <--- Uses the correct Daily dataframe
            y=df_daily[col],     # <--- Uses the correct columns
            mode='lines',
            name=full_name,
            line=dict(color=colors.get(full_name), width=3),
            hovertemplate=f"<b>{full_name}</b>: %{{y:.1f}}<extra></extra>"
        ))

    fig.update_layout(
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(30, 30, 30, 0.9)", font_size=14, font_color="white"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="white")),
        xaxis=dict(gridcolor="rgba(255, 255, 255, 0.1)", tickfont=dict(color="white"), title=None, hoverformat="%b %d, %Y"),
        yaxis=dict(gridcolor="rgba(255, 255, 255, 0.1)", tickfont=dict(color="white"), zeroline=True, 
                   zerolinecolor="rgba(255, 255, 255, 0.5)", zerolinewidth=1.5, title="Score")
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Not enough data to generate Training Load Chart.")

st.markdown("<hr style='border-top: 1px solid white; opacity: 1; margin: 2rem 0;'>", unsafe_allow_html=True)

# ==============================================================================
# --- SECTION 8: PERFORMANCE HISTORY ---
# ==============================================================================
if 'act_json' in locals() and act_json:
    df_history = pd.DataFrame(act_json)
    
    if not df_history.empty and 'start_date_local' in df_history.columns:
        
        # --- A. DATA PROCESSING ---
        df_history['date_dt'] = pd.to_datetime(df_history['start_date_local'])
        df_history['month_period'] = df_history['date_dt'].dt.to_period('M')

        if 'icu_training_load' not in df_history.columns:
            df_history['icu_training_load'] = 0
        df_history['icu_training_load'] = df_history['icu_training_load'].fillna(0)

        # --- B. AGGREGATION ---
        monthly = df_history.groupby('month_period').agg({
            'start_date_local': 'count', 
            'icu_training_load': 'sum'
        }).reset_index()

        monthly.columns = ['MonthPeriod', 'Sessions', 'Total Load']
        monthly = monthly.sort_values('MonthPeriod', ascending=False)
        monthly['MonthDisplay'] = monthly['MonthPeriod'].dt.strftime('%B %Y')

        # --- C. RENDER UI ---
        st.markdown("### 📅 Monthly Performance History")

        # 1. THE HEADER ROW
        st.markdown("""
            <div style="display: flex; justify-content: space-between; padding: 10px 25px; margin-bottom: 5px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <div style="flex: 2; text-align: left; color: #70C4B0; font-family: 'Michroma'; font-size: 0.8rem; letter-spacing: 2px;">MONTH</div>
                <div style="flex: 1; text-align: center; color: rgba(255,255,255,0.6); font-family: 'Michroma'; font-size: 0.7rem; letter-spacing: 2px;">SESSIONS</div>
                <div style="flex: 1; text-align: right; color: rgba(255,255,255,0.6); font-family: 'Michroma'; font-size: 0.7rem; letter-spacing: 2px;">LOAD</div>
            </div>
        """, unsafe_allow_html=True)

        # 2. THE DATA LOOP
        for _, row in monthly.iterrows():
            st.markdown(f"""
            <div class="performance-row">
                <div style="flex: 2; text-align: left; font-family: 'Michroma', sans-serif; font-size: 0.9rem; color: #70C4B0;">
                    {row['MonthDisplay']}
                </div>
                <div style="flex: 1; text-align: center; font-family: 'Michroma', sans-serif; font-size: 0.9rem; color: white;">
                    <span style="opacity: 0.6; margin-right: 5px;">🏃</span> 
                    <b>{int(row['Sessions'])}</b>
                </div>
                <div style="flex: 1; text-align: right; font-family: 'Michroma', sans-serif; font-size: 0.9rem; color: white;">
                    <span style="opacity: 0.6; margin-right: 5px;">🔥</span> 
                    <b>{row['Total Load']:.0f}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.warning("⚠️ Activity data found, but date information is missing.")
else:
    st.info("No activity history found for this year.")