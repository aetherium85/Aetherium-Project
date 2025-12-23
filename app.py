import streamlit.components.v1 as components
import urllib.parse
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def show_login_screen():
    st.title("❤️ Fitness Command Center")
    st.write("Securely sync your 2025 performance data.")
    
    # 1. Prepare your credentials
    CLIENT_ID = st.secrets["INTERVALS_CLIENT_ID"]
    REDIRECT_URI = st.secrets["REDIRECT_URI"]
    scopes = "ACTIVITY:READ,WELLNESS:READ"
    
    # 2. Build the URL parameters
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": scopes
    }
    
    # 3. Encode and build the clean URL
    auth_url = f"https://intervals.icu/oauth/authorize?{urllib.parse.urlencode(params)}"
    
    # 4. Use the reliable standard button
    st.link_button("🚀 Connect with Intervals.icu", auth_url, type="primary")

# --- INITIALIZATION (DO THIS FIRST) ---
if "athlete_id" not in st.session_state:
    st.session_state.athlete_id = "" # Initialized as an empty string

# --- 1. CONFIGURATION & GLOBALS ---
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

# --- 2. DATA FETCHING FUNCTION ---
def get_ytd_data():
    # Safety Check: If there's no token, return None instead of crashing
    if "token_data" not in st.session_state or st.session_state.token_data is None:
        return None, None, None

    token = st.session_state.token_data.get('access_token')
    if not token:
        return None, None, None

    headers = {"Authorization": f"Bearer {token}"}
    
    # Intervals.icu lets you use '0' as the ID for the 'current authenticated user'
    base_url = "https://intervals.icu/api/v1/athlete/0" 
    
    first_day = datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    params = {'oldest': first_day, 'newest': today}

    try:
        well_res = requests.get(f"{base_url}/wellness", headers=headers, params=params)
        act_res = requests.get(f"{base_url}/activities", headers=headers, params=params)
        ath_res = requests.get(base_url, headers=headers) # For the user's name
        
        return well_res.json(), act_res.json(), ath_res.json()
    except Exception as e:
        st.error(f"Fetch failed: {e}")
        return None, None, None

# --- 3. AUTHENTICATION & SESSION STATE ---
# --- NEW OAUTH CONSTANTS ---
CLIENT_ID = st.secrets["INTERVALS_CLIENT_ID"]
CLIENT_SECRET = st.secrets["INTERVALS_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]

# --- OAUTH FUNCTIONS ---
def get_access_token(auth_code):
    """Swaps the one-time code for a reusable access token."""
    token_url = "https://intervals.icu/api/oauth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = requests.post(token_url, data=payload)
    if response.status_code != 200:
        st.error(f"Token Error {response.status_code}: {response.text}")
        return {}
    return response.json()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.token_data = None

# Check if we are returning from Intervals.icu with a 'code'
query_params = st.query_params
if "code" in query_params and not st.session_state.authenticated:
    with st.spinner("Finalizing secure connection..."):
        token_response = get_access_token(query_params["code"])
        if "access_token" in token_response:
            st.session_state.authenticated = True
            st.session_state.token_data = token_response
            # Clear the URL parameters so the 'code' doesn't stay in the address bar
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Authentication failed. Please try again.")

well_json = None
act_json = None

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.athlete_id = ""

# ONLY show this if NOT authenticated
if not st.session_state.authenticated:
    st.title("❤️ Fitness Command Center")
    col1, _ = st.columns([1, 2])
    with col1:
        st.subheader("🔑 Access")
        # Ensure this is NOT inside an 'if well_json' block
        entered_id = st.text_input("Enter Athlete ID (e.g., i123456):")
        
        if st.button("Log In"):
            if entered_id:
                st.session_state.authenticated = True
                st.session_state.athlete_id = entered_id
                st.rerun() # Forces the app to restart and see the new 'True' state
            else:
                st.error("Athlete ID is required.")
    
    # STOP the rest of the script from running if not logged in
    st.stop()
    
    # SCOPES: We need wellness and activity read access
    scopes = "ACTIVITY:READ,WELLNESS:READ"
    auth_url = (
        f"https://intervals.icu/oauth/authorize?"
        f"client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&"
        f"response_type=code&scope={scopes}"
    )
    
    st.link_button("🚀 Connect with Intervals.icu", auth_url)
    st.stop()

# --- 4. MAIN DASHBOARD ---

if st.sidebar.button("Logout / Switch Athlete"):
    st.session_state.authenticated = False
    st.rerun()

# Fetch data
if st.session_state.get("authenticated"):
    st.success("✅ Connection Active! You can close the login tab.")
    well_json, act_json, ath_json = get_ytd_data()
else:
    show_login_screen() # This should contain your "Connect with Intervals" button
    st.stop()
# --- WELLNESS SECTION ---
if well_json is not None:
    # Handle single dictionary vs list of dictionaries
    df = pd.DataFrame([well_json]) if isinstance(well_json, dict) else pd.DataFrame(well_json)

    if not df.empty:
        # Standardize date column
        date_col = next((c for c in ['timestamp', 'id', 'date'] if c in df.columns), None)
        if date_col:
            df = df.rename(columns={date_col: 'date'})
            df['date'] = pd.to_datetime(df['date'])

        # Calculate Form (TSB) manually if missing
        if 'ctl' in df.columns and 'atl' in df.columns:
            df['tsb'] = df['ctl'].shift(1) - df['atl'].shift(1)
            df['tsb'] = df['tsb'].fillna(0)
        
        # Ensure metrics exist
        for col in ['ctl', 'atl', 'tsb']:
            if col not in df.columns: df[col] = 0.0

        latest = df.iloc[-1]
        
        # Gauges
        st.subheader("⚡ Current Training Status")
        g1, g2, g3 = st.columns(3)

        def create_gauge(value, title, color_steps, min_val, max_val):
            return go.Figure(go.Indicator(
                mode="gauge+number",
                value=value,
                title={'text': title, 'font': {'size': 16}},
                gauge={
                    'axis': {'range': [min_val, max_val]},
                    'bar': {'color': "rgba(0,0,0,0)"},
                    'steps': color_steps,
                    'threshold': {'line': {'color': "white", 'width': 4}, 'value': value}
                }
            )).update_layout(height=200, margin=dict(l=20, r=20, t=60, b=40))

        g1.plotly_chart(create_gauge(latest['ctl'], "Fitness (CTL)", [{'range': [0, 100], 'color': "#70B3C4"}], 0, 100))
        g2.plotly_chart(create_gauge(latest['atl'], "Fatigue (ATL)", [{'range': [0, 120], 'color': "#F35555"}], 0, 120))
        form_steps = [{'range': [-60, -30], 'color': "#F35555"}, {'range': [-30, -10], 'color': "#4BD4B0"}, {'range': [-10, 10], 'color': "#C69C49"}, {'range': [10, 60], 'color': "#F35555"}]
        g3.plotly_chart(create_gauge(latest['tsb'], "Form (TSB)", form_steps, -60, 60))

        # Yearly Chart
        st.divider()
        st.subheader("📈 Yearly Training Load Progression")
        fig = px.area(df, x='date', y=['ctl', 'atl', 'tsb'], labels=pretty_labels)
        fig.for_each_trace(lambda t: t.update(name = pretty_labels.get(t.name, t.name)))
        fig.update_traces(stackgroup=None, fill='tozeroy', opacity=1,
    hovertemplate="<b>%{fullData.name} Score:</b> %{y:.1f}<extra></extra>"
)
        fig.update_layout(hovermode="x unified",hoverlabel=dict(bgcolor="white", font_size=14),
    xaxis=dict(hoverformat="%b %d, %Y"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No wellness records found.")
else:
    st.error("Could not load wellness data.")

# --- ACTIVITIES SECTION ---
st.divider()

st.subheader("📅 Monthly Performance Summary")

all_categories = []
df_activities = pd.DataFrame()

if not act_json:
    st.warning("No activity data found.")
else:
    data_list = act_json if isinstance(act_json, list) else [act_json]
    df_activities = pd.DataFrame(data_list)
    
    if 'type' not in df_activities.columns:
        st.warning("⚠️ No activity types found.")
    else:
        df_activities['type'] = df_activities['type'].fillna('Other').astype(str)
        df_activities['category'] = df_activities['type'].map(lambda x: TYPE_MAPPING.get(x, x))
        
        unique_cats = df_activities['category'].unique()
        all_categories = sorted([str(cat) for cat in unique_cats if pd.notna(cat)])

# 1. Show the filter
if all_categories:
    selected_categories = st.multiselect(
        "Filter by Sport:", 
        options=all_categories, 
        default=all_categories
    )
    
    # 2. Filter the data
    df_filtered_act = df_activities[df_activities['category'].isin(selected_categories)]
    
    # 3. RUN CALCULATIONS (This replaces the 'pass')
    if not df_filtered_act.empty:
        df_filtered_act['date_dt'] = pd.to_datetime(df_filtered_act['start_date_local'])
        df_filtered_act['Sort_Key'] = df_filtered_act['date_dt'].dt.strftime('%Y-%m')
        df_filtered_act['Month_Name'] = df_filtered_act['date_dt'].dt.strftime('%B %Y')

        # Group and aggregate
        monthly_summary = df_filtered_act.groupby(['Sort_Key', 'Month_Name']).agg({
            'id': 'count',
            'icu_training_load': 'sum'
        }).reset_index().sort_values('Sort_Key')

        # Display Metrics
        avg_sessions = monthly_summary['id'].mean()
        avg_load = monthly_summary['icu_training_load'].mean()
        
        m1, m2 = st.columns(2)
        m1.metric("Avg. Monthly Sessions", f"{avg_sessions:.1f}")
        m2.metric("Avg. Monthly Load", f"{avg_load:.0f}")

        # Display Table
        st.dataframe(
            monthly_summary.drop(columns=['Sort_Key']),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Month_Name": "Month",
                "id": "Sessions",
                "icu_training_load": "Total Load"
            }
        )
    else:
        st.info("Select at least one sport to see data.")