import streamlit as st
import urllib.parse
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Yearly Fitness Dashboard", layout="wide")

# --- 2. STYLING ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400&display=swap');
    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: linear-gradient(rgba(0, 0, 0, 0.4), rgba(0, 0, 0, 0.4)), 
                    url("https://images.unsplash.com/photo-1597773179486-8af5ca939ddb") !important;
        background-size: cover !important; background-position: center !important;
        background-attachment: fixed !important; filter: blur(4px); z-index: -1;
    }
    .stApp { background: transparent !important; font-family: 'Inter', sans-serif !important; }
    h1, h2, h3, p, span, label, div, b, [data-testid="stMetricValue"] {
        font-family: 'Inter', sans-serif !important; font-weight: 200 !important; color: white !important;
    }
    [data-testid="stSidebar"] { background-color: rgba(0, 0, 0, 0.4) !important; backdrop-filter: blur(15px); }
    div[data-testid="stVerticalBlock"] > div:has(div.stPlotlyChart), .performance-row {
        background-color: rgba(255, 255, 255, 0.05) !important; backdrop-filter: blur(10px) !important;
        border-radius: 15px !important; padding: 20px !important; border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    .performance-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 25px !important; margin-bottom: 10px !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 3. FUNCTIONS ---

def show_login_screen():
    st.title("❤️ Fitness Command Center")
    st.write("Securely sync your 2025 performance data.")
    try:
        auth_url = f"https://intervals.icu/oauth/authorize?{urllib.parse.urlencode({
            'client_id': st.secrets['INTERVALS_CLIENT_ID'],
            'redirect_uri': st.secrets['REDIRECT_URI'],
            'response_type': 'code',
            'scope': 'ACTIVITY:READ,WELLNESS:READ'
        })}"
        st.link_button("🚀 Connect with Intervals.icu", auth_url, type="primary")
    except Exception as e:
        st.error(f"Missing Secrets: {e}")

def get_access_token(auth_code):
    token_url = "https://intervals.icu/api/oauth/token"
    payload = {
        "client_id": st.secrets["INTERVALS_CLIENT_ID"],
        "client_secret": st.secrets["INTERVALS_CLIENT_SECRET"],
        "code": auth_code,
        "redirect_uri": st.secrets["REDIRECT_URI"],
        "grant_type": "authorization_code",
    }
    try:
        res = requests.post(token_url, data=payload)
        return res.json() if res.status_code == 200 else {}
    except:
        return {}

@st.cache_data(ttl=3600)
def fetch_api_data(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    # Adjust URL for specific athlete ID if needed, defaulting to '0' (self)
    base_url = "https://intervals.icu/api/v1/athlete/0" 
    first_day = datetime(datetime.now().year, 1, 1).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    params = {'oldest': first_day, 'newest': today}
    
    try:
        well_res = requests.get(f"{base_url}/wellness", headers=headers, params=params)
        act_res = requests.get(f"{base_url}/activities", headers=headers, params=params)
        return well_res.json(), act_res.json()
    except:
        return None, None

def elegant_stat_card(col, label, value, color):
    with col:
        st.markdown(f"""
        <div style="text-align: center; padding: 25px 10px; background: rgba(255, 255, 255, 0.03); 
                    border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px);">
            <p style="color: rgba(255,255,255,0.5); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 0;">{label}</p>
            <h1 style="color: white; font-size: 4rem; font-weight: 200; margin: 0; line-height: 1.2; text-shadow: 0 0 30px {color}66;">{int(value)}</h1>
        </div>
        """, unsafe_allow_html=True)

# --- 4. SAFE STATE MANAGEMENT ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "token_data" not in st.session_state:
    st.session_state.token_data = None 

# --- 5. MAIN LOGIC BRANCHING ---

# HANDLE AUTH CALLBACK
if "code" in st.query_params and not st.session_state.authenticated:
    with st.spinner("Authenticating..."):
        token_response = get_access_token(st.query_params["code"])
        if "access_token" in token_response:
            st.session_state.authenticated = True
            st.session_state.token_data = token_response
            st.query_params.clear() 
            st.rerun()
        else:
            st.error("Authentication failed.")

# BRANCH 1: NOT LOGGED IN
if not st.session_state.authenticated:
    show_login_screen()

# BRANCH 2: LOGGED IN (Dashboard)
else:
    # 2a. Verify Data Integrity (The fix for your crash)
    token_data = st.session_state.get('token_data')
    
    if not token_data or not isinstance(token_data, dict) or 'access_token' not in token_data:
        # If we are here, state is corrupted. Reset and reload.
        st.session_state.authenticated = False
        st.session_state.token_data = None
        st.rerun()
    
    # 2b. If we survive the check above, it is now 100% safe to access the token
    token = token_data['access_token']
    
    # --- DASHBOARD STARTS HERE ---
    with st.sidebar:
        st.title(f"2025 SEASON")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.token_data = None
            st.rerun()

    well_json, act_json = fetch_api_data(token)

    if not act_json or not well_json:
        st.warning("No data found or API connection failed.")
        if st.button("Retry Connection"):
            st.cache_data.clear()
            st.rerun()
    else:
        # --- HERO ---
        latest_act = act_json[0]
        secs = latest_act.get('moving_time', 0)
        dur = f"{secs // 3600}h {(secs % 3600) // 60}m"
        
        st.markdown(f"### 🚀 Last Session: {latest_act.get('name', 'Workout')}")
        h1, h2, h3, h4 = st.columns(4)
        
        # Helper for hero
        def hm(col, icon, label, val):
            col.markdown(f"""
                <div style="display:flex; align-items:center; gap:15px; background:rgba(255,255,255,0.03); padding:10px 15px; border-radius:12px; border:1px solid rgba(255,255,255,0.05);">
                    <div style="font-size:2rem;">{icon}</div>
                    <div><div style="font-size:0.65rem; text-transform:uppercase; color:rgba(255,255,255,0.5);">{label}</div>
                    <div style="font-size:1.4rem;">{val}</div></div>
                </div>""", unsafe_allow_html=True)

        hm(h1, "⏱️", "Duration", dur)
        hm(h2, "⚡", "Load", f"{latest_act.get('icu_training_load',0)} pts")
        hm(h3, "🗺️", "Dist", f"{(latest_act.get('distance',0)/1000):.1f} km")
        hm(h4, "💓", "HR", f"{latest_act.get('average_heartrate','-')} bpm")
        
        st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)

        # --- WELLNESS ---
        df = pd.DataFrame(well_json)
        if not df.empty:
            date_col = next((c for c in ['date', 'timestamp'] if c in df.columns), 'date')
            df.rename(columns={date_col: 'date'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'])
            
            for c in ['ctl','atl','tsb']: 
                if c not in df.columns: df[c] = 0
            
            latest = df.iloc[-1]
            st.markdown("### ⚡ Current Status")
            s1, s2, s3 = st.columns(3)
            elegant_stat_card(s1, "Fitness", latest['ctl'], "#70C4B0")
            elegant_stat_card(s2, "Fatigue", latest['atl'], "#E16C45")
            elegant_stat_card(s3, "Form", latest['tsb'], "#4BD4B0" if latest['tsb']>-10 else "#E16C45")

            st.markdown("### 📈 Load Progression")
            fig = px.area(df, x='date', y=['ctl','atl','tsb'], 
                          color_discrete_map={'ctl':'#70C4B0', 'atl':'#E16C45', 'tsb':'#ffffff'})
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", 
                              font_color="white", height=350, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        
        # --- LIST ---
        st.markdown("<hr style='margin: 2rem 0;'>", unsafe_allow_html=True)
        st.markdown("### 📅 History")
        df_act = pd.DataFrame(act_json)
        if not df_act.empty:
            df_act['Month'] = pd.to_datetime(df_act['start_date_local']).dt.strftime('%B %Y')
            m_stats = df_act.groupby('Month', sort=False).agg({'id':'count', 'icu_training_load':'sum'}).reset_index().iloc[::-1]
            
            for _, row in m_stats.iterrows():
                st.markdown(f"""
                <div class="performance-row">
                    <div style="flex:2; font-weight:bold;">{row['Month']}</div>
                    <div style="flex:1;">🏃 {row['id']} Sessions</div>
                    <div style="flex:1; text-align:right;">🔥 {row['icu_training_load']:.0f} Load</div>
                </div>""", unsafe_allow_html=True)