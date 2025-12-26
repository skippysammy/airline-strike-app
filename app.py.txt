import streamlit as st
import json
from datetime import datetime

# --- 1. SETUP & DATA LOADING ---
st.set_page_config(page_title=Airline Strike Predictor, page_icon=✈️)

# We cache this function so it doesn't reload the file every time you click a button
@st.cache_data
def load_data()
    try
        with open('airlines_db.json', 'r') as f
            return json.load(f)
    except FileNotFoundError
        st.error(⚠️ Database file not found. Please ensure 'airlines_db.json' is in the folder.)
        return {}

# Load the database
db = load_data()

# Create a helper dictionary to swap names for codes
# Example {Air Canada AC, United Airlines UA}
airline_map = {data['name'] code for code, data in db.items()}

# --- 2. THE RISK LOGIC (Hidden Engine) ---
def get_airline_risk(code, travel_date, db)
    
    Returns a dictionary with color and message for a SINGLE airline.
    
    airline_data = db.get(code)
    risk_color = GREEN
    reasons = []

    # Loop through unions (Pilots, Flight Attendants)
    for group, details in airline_data['unions'].items()
        status = details['status']
        
        # Check if expiration date exists and is valid
        if details['expiration_date'] == NA
             expiry_date = datetime(2099, 12, 31).date() # Far future
        else
             expiry_date = datetime.strptime(details['expiration_date'], %Y-%m-%d).date()

        # LOGIC Check for Danger
        if status in [Non-Union, Binding Arbitration]
            continue # Safe

        # Red Flags
        if any(x in status for x in [Strike, Impasse, Cooling-off])
            risk_color = RED
            reasons.append(f🔴 {group.title()} {status})

        # Yellow Flags (Expires soon or Negotiating)
        elif risk_color != RED
            # Check if expiring within 30 days of trip
            days_until_travel = (expiry_date - travel_date).days
            
            if days_until_travel  30
                risk_color = YELLOW
                reasons.append(f🟡 {group.title()} Contract expires near your trip ({details['expiration_date']}))
            elif status == Negotiating
                risk_color = YELLOW
                reasons.append(f🟡 {group.title()} Currently negotiating.)

    if risk_color == GREEN
        reasons.append(f✅ All contracts active.)

    return risk_color, reasons

# --- 3. THE VISUAL INTERFACE (What users see) ---

st.title(✈️ Flight Disruption Check)
st.markdown(Check if labor strikes might jeopardize your upcoming trip.)

# --- INPUT SECTION ---
col1, col2 = st.columns(2)

with col1
    # THE CALENDAR WIDGET
    travel_date = st.date_input(When is your trip, min_value=datetime.today())

with col2
    # THE MULTI-SELECT WIDGET (Friendly Names)
    selected_names = st.multiselect(
        Select Airline(s), 
        options=list(airline_map.keys()),
        default=None
    )

# --- RESULTS SECTION ---
if st.button(Analyze Risk)
    if not selected_names
        st.warning(Please select at least one airline.)
    else
        st.divider()
        
        # We track the Worst color found across all airlines
        trip_status = GREEN
        
        for name in selected_names
            code = airline_map[name]
            color, messages = get_airline_risk(code, travel_date, db)
            
            # Display a card for this airline
            with st.expander(f{name} (Status {color}), expanded=True)
                if color == RED
                    trip_status = RED
                    st.error(fHigh Risknn + nn.join(messages))
                elif color == YELLOW
                    if trip_status != RED trip_status = YELLOW
                    st.warning(fMedium Risknn + nn.join(messages))
                else
                    st.success(fLow Risknn + nn.join(messages))

        # Final Summary
        st.subheader(Verdict)
        if trip_status == RED
            st.error(🚫 JEOPARDY DETECTED At least one of your flights has a high risk of strike action. Check refund policies.)
        elif trip_status == YELLOW
            st.warning(⚠️ CAUTION Labor disputes are active. Disruption is unlikely but possible. Monitor news.)
        else
            st.success(✅ GOOD TO GO No active labor disputes found for your dates.)