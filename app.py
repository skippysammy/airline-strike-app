import streamlit as st
import json
from datetime import datetime, timedelta

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(page_title="Smoot: Smooth Travel Checker", page_icon="✈️")

# --- 2. DATA LOADING ---
@st.cache_data
def load_data():
    try:
        with open('airlines_db.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("⚠️ Database file not found.")
        return {}

# Load the airline database
db = load_data()
airline_map = {data['name']: code for code, data in db.items()}

# Define Airport Data 
airport_db = {
    "YYZ (Toronto Pearson)": ["AC", "WS", "TS", "UA", "DL", "AA"],
    "YVR (Vancouver)": ["AC", "WS", "UA", "DL", "AA", "AS"],
    "YUL (Montreal)": ["AC", "TS", "UA", "DL", "AA"],
    "ATL (Atlanta)": ["DL", "WN", "NK", "UA", "AA"],
    "ORD (Chicago O'Hare)": ["UA", "AA", "DL", "WN", "AC", "WS"],
    "DFW (Dallas/Fort Worth)": ["AA", "UA", "DL", "NK", "AC"],
    "DEN (Denver)": ["UA", "WN", "DL", "AA", "AC"],
    "LAX (Los Angeles)": ["UA", "AA", "DL", "AS", "WN", "B6", "NK", "AC", "WS"],
    "JFK (New York JFK)": ["DL", "B6", "AA", "AS"],
    "SEA (Seattle)": ["AS", "DL", "UA", "WN", "AC"]
}

# --- 3. THE LOGIC (RISK CALCULATOR) ---
def get_airline_risk(code, start_date, end_date, db):
    """
    Checks risk for Departure (Cancellation) AND Return (Stranded).
    """
    if code not in db:
        return "GREY", [f"No data for airline code: {code}"]

    airline_data = db.get(code)
    risk_color = "GREEN"
    reasons = []

    # Loop through unions (Pilots, Flight Attendants)
    for group, details in airline_data['unions'].items():
        status = details['status']
        
        # Parse Expiration Date
        if details['expiration_date'] == "N/A":
             expiry_date = datetime(2099, 12, 31).date()
        else:
             expiry_date = datetime.strptime(details['expiration_date'], "%Y-%m-%d").date()

        # SAFE SCENARIOS
        if status in ["Non-Union", "Binding Arbitration"]:
            continue 

        # CRITICAL RISKS (Strike Votes, Impasse)
        if any(x in status for x in ["Strike", "Impasse", "Cooling-off"]):
            risk_color = "RED"
            reasons.append(f"[CRITICAL] {group.title()}: {status}")

        # DATE-BASED RISKS
        elif risk_color != "RED":
            
            # Scenario A: Contract expires BEFORE you even leave
            if expiry_date < start_date:
                risk_color = "YELLOW"
                reasons.append(f"[WARNING] {group.title()}: Contract expires BEFORE your trip ({details['expiration_date']}). Risk of cancellation.")

            # Scenario B: Contract expires WHILE you are away
            elif start_date <= expiry_date <= end_date:
                risk_color = "YELLOW"
                reasons.append(f"[WARNING] {group.title()}: Contract expires DURING your trip ({details['expiration_date']}). Risk of getting stranded.")
            
            # Scenario C: Contract expires shortly AFTER you return (Buffer zone)
            elif 0 < (expiry_date - end_date).days < 30:
                risk_color = "YELLOW"
                reasons.append(f"[CAUTION] {group.title()}: Contract expires shortly after your return ({details['expiration_date']}).")

            # Scenario D: Active Negotiations (Always a mild risk)
            if status == "Negotiating" and risk_color == "GREEN":
                risk_color = "YELLOW"
                reasons.append(f"[WARNING] {group.title()}: Active negotiations (No date set).")

    if risk_color == "GREEN":
        reasons.append(f"[OK] Contracts active through your travel dates.")

    return risk_color, reasons

# --- 4. THE UI (AIRBNB STYLE) ---

# Header Section
col1, col2 = st.columns([1, 5], vertical_alignment="center")
with col1:
    try:
        st.image("logo_image.png", width=80)
    except:
        st.write("✈️") 
with col2:
    st.markdown("### Don't get stranded, use Smoot.")

st.markdown("---") 

# Search Section
with st.container():
    st.write("**1. When are you travelling?**")
    today = datetime.today()
    date_range = st.date_input(
        "Select Departure and Return dates",
        value=(today, today + timedelta(days=7)),
        min_value=today,
        format="YYYY/MM/DD"
    )

    st.write("**2. How do you want to search?**")
    tab_airline, tab_airport = st.tabs(["✈️ By Airline", "🏢 By Airport"])

    with tab_airline:
        selected_airlines = st.multiselect(
            "Select Airline(s)",
            options=list(airline_map.keys())
        )
        search_trigger = st.button("Search by Airline", type="primary")

    with tab_airport:
        selected_airport = st.selectbox(
            "Select Departure/Arrival Airport",
            options=list(airport_db.keys())
        )
        search_airport_trigger = st.button("Search by Airport", type="primary")

# --- 5. RESULTS SECTION ---
st.markdown("---")

# Helper to validate dates
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    st.info("Please select both a Departure and Return date above.")
    st.stop()

# Run Search
results = {} 

if search_trigger and selected_airlines:
    st.subheader(f"Results for your trip ({start_date} to {end_date})")
    for name in selected_airlines:
        code = airline_map[name]
        results[name] = get_airline_risk(code, start_date, end_date, db)

elif search_airport_trigger and selected_airport:
    st.subheader(f"Risk Report for {selected_airport}")
    st.info(f"Showing risks for all major airlines operating at {selected_airport}...")
    airport_codes = airport_db[selected_airport]
    for name, code in airline_map.items():
        if code in airport_codes:
            results[name] = get_airline_risk(code, start_date, end_date, db)

# Display Sorted Results
if results:
    def sort_key(item):
        color = item[1][0]
        if color == "RED": return 0
        if color == "YELLOW": return 1
        return 2
    
    sorted_results = sorted(results.items(), key=sort_key)

    for airline_name, (color, messages) in sorted_results:
        with st.expander(f"{airline_name}  —  Status: {color}", expanded=(color != "GREEN")):
            if color == "RED":
                st.error("\n\n".join(messages))
            elif color == "YELLOW":
                st.warning("\n\n".join(messages))
            else:
                st.success("\n\n".join(messages))