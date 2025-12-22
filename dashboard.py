import requests
from datetime import datetime, timedelta

ATHLETE_ID = "i322980"  # Your ID
API_KEY = "3u9d5nxuxpf2i52j60zmhgi3n"   # Your Key

# This function gets your stats (HRV, Fitness, etc.)
def get_wellness():
    url = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/wellness"
    response = requests.get(url, auth=('API_KEY', API_KEY))
    return response.json()[-1] if response.status_code == 200 else {}

# This function gets your actual workouts
def get_activities():
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    url = f"https://intervals.icu/api/v1/athlete/{ATHLETE_ID}/activities"
    params = {'oldest': seven_days_ago}
    response = requests.get(url, auth=('API_KEY', API_KEY), params=params)
    return response.json() if response.status_code == 200 else []

# --- RUNNING THE DASHBOARD ---
print("Fetching your Intervals.icu Data...")

wellness = get_wellness()
activities = get_activities()

print("\n=== CURRENT STATUS ===")
print(f"Fitness (CTL): {wellness.get('ctl')}")
print(f"Form (TSB):    {wellness.get('tsb')}")

print("\n=== RECENT ACTIVITIES ===")
for act in activities:
    print(f"- {act.get('start_date_local')[:10]}: {act.get('name')} ({act.get('icu_training_load')} Load)")