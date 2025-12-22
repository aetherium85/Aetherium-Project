import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURATION ---
# Get these from https://www.strava.com/settings/api
CLIENT_ID = st.secrets["STRAVA_CLIENT_ID"]
CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
REFRESH_TOKEN = st.secrets["STRAVA_REFRESH_TOKEN"]

st.set_page_config(page_title="Strava Performance Dashboard", layout="wide")

# --- 2. AUTHENTICATION & DATA FETCHING ---
def get_strava_access_token():
    """Exchange refresh token for a fresh access token."""
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': "refresh_token"
    }
    res = requests.post("https://www.strava.com/oauth/token", data=payload)
    return res.json().get('access_token')

@st.cache_data(ttl=900) # 👈 This saves your API quota for 15 minutes
def fetch_strava_activities(access_token):
    after = int(datetime(datetime.now().year, 1, 1).timestamp())
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {'Authorization': f"Bearer {access_token}"}
    
    activities = []
    page = 1
    
    while True:
        params = {'after': after, 'per_page': 100, 'page': page}
        res = requests.get(url, headers=headers, params=params, timeout=10)
        
        # 1. Handle Rate Limiting
        if res.status_code == 429:
            st.error("🚦 Strava Rate Limit Hit! Please wait 15 minutes.")
            return activities # Return whatever we managed to get so far
            
        # 2. Handle other Errors
        if res.status_code != 200:
            st.error(f"Strava API Error: {res.json()}")
            break # 👈 Now inside the 'while' loop, so this works!
            
        data = res.json()
        
        # 3. Check if we are at the end of the list
        if not data: 
            break
            
        activities.extend(data)
        page += 1
        
    return activities

# --- 3. MAIN DASHBOARD ---
st.title("🚴 Strava Performance Dashboard")

access_token = get_strava_access_token()

if access_token:
    with st.spinner("Fetching data from Strava..."):
        act_json = fetch_strava_activities(access_token)
    
    if act_json:
        df = pd.DataFrame(act_json)
        
        # Data Cleaning
        df['start_date_local'] = pd.to_datetime(df['start_date_local'])
        df['distance_km'] = df['distance'] / 1000
        df['moving_time_hr'] = df['moving_time'] / 3600
        
        # --- 4. TOP LEVEL METRICS (Current YTD) ---
        st.subheader("⚡ Year-to-Date Progress")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Activities", len(df))
        m2.metric("Distance", f"{df['distance_km'].sum():,.1f} km")
        m3.metric("Time", f"{df['moving_time_hr'].sum():,.1f} hrs")
        m4.metric("Elevation", f"{df['total_elevation_gain'].sum():,.0f} m")

        st.divider()

        # --- 5. PROGRESSION CHART ---
        st.subheader("📈 Cumulative Distance Over Time")
        # Prepare cumulative data
        df_sorted = df.sort_values('start_date_local')
        df_sorted['cumulative_dist'] = df_sorted['distance_km'].cumsum()
        
        fig = px.area(
            df_sorted, 
            x='start_date_local', 
            y='cumulative_dist',
            title="Total Distance Progression (km)",
            labels={'start_date_local': 'Date', 'cumulative_dist': 'Distance (km)'}
        )
        fig.update_traces(line_color='#FC4C02') # Strava Orange
        st.plotly_chart(fig, use_container_width=True)

        # --- 6. MONTHLY BREAKDOWN ---
        st.divider()
        st.subheader("🏆 Monthly Summary")
        
        df['Month'] = df['start_date_local'].dt.strftime('%B %Y')
        df['Sort_Key'] = df['start_date_local'].dt.strftime('%Y-%m')
        
        monthly = df.groupby(['Sort_Key', 'Month']).agg({
            'id': 'count',
            'distance_km': 'sum',
            'moving_time_hr': 'sum',
            'total_elevation_gain': 'sum'
        }).reset_index().sort_values('Sort_Key')

        st.dataframe(
            monthly.drop(columns=['Sort_Key']),
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": "Activities",
                "distance_km": st.column_config.NumberColumn("Dist (km)", format="%.1f"),
                "moving_time_hr": st.column_config.NumberColumn("Time (hrs)", format="%.1f"),
                "total_elevation_gain": st.column_config.NumberColumn("Elev (m)", format="%d")
            }
        )

    else:
        st.warning("No activities found for this year.")
else:
    st.error("Could not authenticate with Strava. Check your API credentials.")