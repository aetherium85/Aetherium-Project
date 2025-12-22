import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

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
def get_ytd_data(athlete_id):
    # API key from st.secrets
    API_KEY = st.secrets["INTERVALS_API_KEY"]
    
    first_day = datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    params = {'oldest': first_day, 'newest': today}
    
    wellness_url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness"
    activities_url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities"

    try:
        # Note: Intervals.icu uses 'API_KEY' as the username for Basic Auth
        well_res = requests.get(wellness_url, auth=('API_KEY', API_KEY), params=params)
        act_res = requests.get(activities_url, auth=('API_KEY', API_KEY), params=params)
        
        # Check for HTTP errors
        well_res.raise_for_status()
        act_res.raise_for_status()
        
        return well_res.json(), act_res.json()
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return None, None

# --- 3. AUTHENTICATION & SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.athlete_id = ""

if not st.session_state.authenticated:
    st.title("❤️ Fitness Command Center")
    col1, _ = st.columns([1, 2])
    with col1:
        st.subheader("🔑 Access")
        entered_id = st.text_input("Enter Athlete ID (e.g., i322980):", value=st.session_state.athlete_id)
        if st.button("Log In"):
            if entered_id:
                st.session_state.authenticated = True
                st.session_state.athlete_id = entered_id
                st.rerun()
            else:
                st.error("Athlete ID is required.")
    st.stop()

# --- 4. MAIN DASHBOARD ---
st.title(f"📊 Dashboard for {st.session_state.athlete_id}")

if st.sidebar.button("Logout / Switch Athlete"):
    st.session_state.authenticated = False
    st.rerun()

# Fetch data
well_json, act_json = get_ytd_data(st.session_state.athlete_id)

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
        form_steps = [{'range': [-60, -30], 'color': "#F35555"}, {'range': [-30, -10], 'color': "#4BD4B0"}, {'range': [10, 60], 'color': "#E2B465"}]
        g3.plotly_chart(create_gauge(latest['tsb'], "Form (TSB)", form_steps, -60, 60))

        # Yearly Chart
        st.divider()
        st.subheader("📈 Yearly Training Load Progression")
        fig = px.area(df, x='date', y=['ctl', 'atl', 'tsb'], labels=pretty_labels)
        fig.for_each_trace(lambda t: t.update(name = pretty_labels.get(t.name, t.name)))
        fig.update_layout(hovermode="x unified", legend=dict(orientation="h", y=1.02))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No wellness records found.")
else:
    st.error("Could not load wellness data.")

# --- ACTIVITIES SECTION ---
st.divider()
if act_json:
    df_act = pd.DataFrame([act_json]) if isinstance(act_json, dict) else pd.DataFrame(act_json)
    
    if 'type' in df_act.columns and 'start_date_local' in df_act.columns:
        df_act['category'] = df_act['type'].map(lambda x: TYPE_MAPPING.get(x, x))
        all_cats = sorted(df_act['category'].unique().tolist())
        
        selected = st.multiselect("Filter by Sport:", all_cats, default=all_cats)
        df_filt = df_act[df_act['category'].isin(selected)]
        
        if not df_filt.empty:
            df_filt['date_dt'] = pd.to_datetime(df_filt['start_date_local'])
            df_filt['Month'] = df_filt['date_dt'].dt.strftime('%B %Y')
            df_filt['Sort'] = df_filt['date_dt'].dt.strftime('%Y-%m')
            
            summary = df_filt.groupby(['Sort', 'Month']).agg({'id': 'count', 'icu_training_load': 'sum'}).reset_index().sort_values('Sort')
            
            st.subheader("🏆 Monthly Summary")
            st.dataframe(summary.drop(columns=['Sort']), use_container_width=True, hide_index=True)
        else:
            st.info("Select a sport to see details.")
    else:
        st.warning("No activity details available.")
else:
    st.info("No activities found for this year.")