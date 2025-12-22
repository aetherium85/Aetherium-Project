import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Layout: Large YTD Chart
pretty_labels = {
    "ctl": "Fitness (CTL)",
    "atl": "Fatigue (ATL)",
    "tsb": "Form (TSB)",
    "id": "Date",
    "value": "Score"
}

# --- 1. CONFIGURATION ---
DEFAULT_ID = "i322980"
API_KEY = st.secrets["INTERVALS_API_KEY"]

st.set_page_config(page_title="Yearly Fitness Dashboard", layout="wide")

# --- 2. DATA FETCHING FUNCTION ---
def get_ytd_data(athlete_id, params=None):
    first_day = datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    
    if params is None:
        params = {'oldest': first_day, 'newest': today}
    
    wellness_url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness"
    activities_url = f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities"

    try:
        well_res = requests.get(wellness_url, auth=('API_KEY', API_KEY), params=params)
        act_res = requests.get(activities_url, auth=('API_KEY', API_KEY), params=params)
        return well_res.json(), act_res.json()
    except Exception as e:
        st.error(f"Fetch failed: {e}")
        return [], []

# --- 3. MAIN DASHBOARD LOGIC ---
st.title("❤️ My Fitness Command Center")

# --- INITIALIZE SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.athlete_id = ""

if not st.session_state.authenticated:
    col1, _ = st.columns([1, 2])
    with col1:
        st.subheader("🔑 Access")
        entered_id = st.text_input("Enter Athlete ID:", value=st.session_state.athlete_id)
        if st.button("Log In"):
            if entered_id:
                st.session_state.authenticated = True
                st.session_state.athlete_id = entered_id
                st.rerun()
            else:
                st.error("ID is required.")
    st.stop()

# --- IF AUTHENTICATED, THE REST OF THE CODE RUNS ---
athlete_id_input = st.session_state.athlete_id

# Button to "Logout" or switch athletes
if st.button("Logout / Switch Athlete"):
    st.session_state.authenticated = False
    st.rerun()

well_json, act_json = get_ytd_data(athlete_id=st.session_state.athlete_id)

TYPE_MAPPING = {
    "Ride": "Cycling", "GravelRide": "Cycling", "VirtualRide": "Cycling", 
    "EBikeRide": "Cycling", "MountainBikeRide": "Cycling", "Velomobile": "Cycling",
    "Handcycle": "Cycling", "TrackCycling": "Cycling",
    "Run": "Running", "TrailRun": "Running", "VirtualRun": "Running", 
    "Treadmill": "Running", "Walk": "Running/Walking", "Hike": "Running/Walking",
    "Swim": "Swimming", "OpenWaterSwim": "Swimming", "Rowing": "Water Sports", 
    "WeightTraining": "Strength", "Yoga": "Mobility", "Pilates": "Mobility"
}

# --- 4. CURRENT STATUS SECTION (WELLNESS) ---
if well_json:
    st.subheader("⚡ Current Training Status")
    if isinstance(well_json, dict):
        df = pd.DataFrame([well_json])
    else:
        df = pd.DataFrame(well_json)
    
    # Calculate Form (TSB)
    if 'ctl' in df.columns and 'atl' in df.columns:
        df['tsb'] = df['ctl'].shift(1) - df['atl'].shift(1)
        df['tsb'] = df['tsb'].fillna(0)
    
    for col in ['ctl', 'atl', 'tsb']:
        if col not in df.columns:
            df[col] = 0.0

    latest = df.iloc[-1]
    
    # Gauge Layout
    g1, g2, g3 = st.columns(3)

    def create_gauge(value, title, color_steps, min_val, max_val):
        return go.Figure(go.Indicator(
            mode="gauge+number",
            value=value,
            title={'text': title, 'font': {'size': 16}},
            gauge={
                'axis': {'range': [min_val, max_val], 'tickwidth': 0},
                'bar': {'color': "rgba(0,0,0,0)"}, # Transparent bar for dot look
                'borderwidth': 0,
                'steps': color_steps,
                'threshold': {
                    'line': {'color': "white", 'width': 4},
                    'thickness': 1,
                    'value': value
                }
            }
        )).update_layout(height=200, margin=dict(l=20, r=20, t=60, b=40))

    with g1:
        st.plotly_chart(create_gauge(latest['ctl'], "Fitness (CTL)", [{'range': [0, 100], 'color': "#70B3C4"}], 0, 100), width='stretch')
    with g2:
        st.plotly_chart(create_gauge(latest['atl'], "Fatigue (ATL)", [{'range': [0, 120], 'color': "#F35555"}], 0, 120), width='stretch')
    with g3:
        form_steps = [
            {'range': [-60, -30], 'color': "#F35555"},
            {'range': [-30, -10], 'color': "#4BD4B0"},
            {'range': [-10, 10], 'color': "#70B3C4"},
            {'range': [10, 60], 'color': "#E2B465"}
        ]
        st.plotly_chart(create_gauge(latest['tsb'], "Form (TSB)", form_steps, -60, 60), width='stretch')

    st.divider()

   
if not df.empty:
    # 1. FIND THE DATE COLUMN (Whatever the API decided to call it)
    possible_date_cols = ['timestamp', 'id', 'date']
    found_date_col = next((col for col in possible_date_cols if col in df.columns), None)

    if found_date_col:
        # Rename it to 'date' for consistency
        df = df.rename(columns={found_date_col: 'date'})
        
        # Convert to actual datetime objects
        df['date'] = pd.to_datetime(df['date'])

        # --- DRAW THE CHART ---
        st.subheader("📈 Yearly Training Load Progression")
        
        # Ensure ctl, atl, tsb exist (default to 0 if missing)
        for col in ['ctl', 'atl', 'tsb']:
            if col not in df.columns:
                df[col] = 0.0

    if not df.empty:
    # 1. Standardize the date column name
        if 'timestamp' in df.columns:
            df = df.rename(columns={'timestamp': 'date'})
    elif 'id' in df.columns:
        df = df.rename(columns={'id': 'date'})
    
    # 2. Check if 'date' now exists
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        
        # 3. Ensure the Y-axis columns exist so Plotly doesn't panic
        for col in ['ctl', 'atl', 'tsb']:
            if col not in df.columns:
                df[col] = 0.0

        # 4. Create Figure
        fig = px.area(
            df,
            x='date', # This matches the rename above
            y=['ctl', 'atl', 'tsb'],
            title="Fitness (CTL), Fatigue (ATL) and Form (TSB)",
            labels=pretty_labels
        )

        # 5. ALL styling MUST be indented here
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
        st.warning("⚠️ Wellness data loaded, but no date column found.")
else:
    st.warning("No wellness data found.")

    with st.expander("ℹ️ What do these metrics mean?"):
            st.markdown("""
            * **Fitness (CTL)**: 42-day rolling average load. Long-term capacity.
            * **Fatigue (ATL)**: 7-day rolling average load. Recent stress.
            * **Form (TSB)**: Fitness minus Fatigue. Negative (-10 to -30) is the 'Optimal' zone.
            """)

st.divider()

# --- 5. MONTHLY BREAKDOWN SECTION (ACTIVITIES) ---
all_categories = []
df_activities = pd.DataFrame()

if act_json:
    # 2. Load data safely
    data_list = act_json if isinstance(act_json, list) else [act_json]
    df_activities = pd.DataFrame(data_list)
    
    # 3. Process if 'type' exists
    if 'type' in df_activities.columns:
        df_activities['type'] = df_activities['type'].fillna('Other').astype(str)
        df_activities['category'] = df_activities['type'].map(lambda x: TYPE_MAPPING.get(x, x))
        
        # Now this variable is guaranteed to be defined here
        all_categories = sorted(df_activities['category'].unique().tolist())
    else:
        st.warning("⚠️ No activity types found for 2025.")

# 4. Only show the filter if we actually found categories
if all_categories:
    selected_categories = st.multiselect(
        "Filter Monthly Breakdown by Sport:", 
        options=all_categories, 
        default=all_categories
    )
    
    df_filtered_act = df_activities[df_activities['category'].isin(selected_categories)]
    
    if not df_filtered_act.empty:
        df_filtered_act['date_dt'] = pd.to_datetime(df_filtered_act['start_date_local'])
        df_filtered_act['Sort_Key'] = df_filtered_act['date_dt'].dt.strftime('%Y-%m')
        df_filtered_act['Month_Name'] = df_filtered_act['date_dt'].dt.strftime('%B %Y')

        monthly_summary = df_filtered_act.groupby(['Sort_Key', 'Month_Name']).agg({
            'id': 'count',
            'icu_training_load': 'sum'
        }).reset_index()

        monthly_summary = monthly_summary.sort_values('Sort_Key')

        # Calculate Averages
        avg_sessions = monthly_summary['id'].mean()
        avg_load = monthly_summary['icu_training_load'].mean()
        avg_intensity = monthly_summary['icu_training_load'].sum() / monthly_summary['id'].sum()
        max_load = monthly_summary['icu_training_load'].max()

        st.write("### ⚖️ Monthly Averages")
        sm1, sm2, sm3, sm4 = st.columns(4)
        sm1.metric("Avg. Sessions", f"{avg_sessions:.1f}")
        sm2.metric("Avg. Monthly Load", f"{avg_load:.0f}")
        sm3.metric("Avg. Load / Session", f"{avg_intensity:.1f}")
        sm4.metric("Peak Monthly Load", f"{max_load:.0f}")

        st.divider()
        st.subheader("🏆 Monthly Performance Summary")
        st.dataframe(
            monthly_summary.drop(columns=['Sort_Key']),
            width='stretch',
            hide_index=True,
            column_config={
                "Month_Name": st.column_config.Column("Month"),
                "id": st.column_config.NumberColumn("Sessions", format="%d"),
                "icu_training_load": st.column_config.NumberColumn("Total Load", format="%d")
            }
        )
    else:
        st.info("Select a sport to see the monthly breakdown.")
else:
    st.info("💡 Once you upload 2025 activities to Intervals.icu, your breakdown will appear here.")

if not act_json:
    st.warning("No activity data found.")