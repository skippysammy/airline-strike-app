import streamlit as st
import json
from datetime import datetime

# --- 1. SETUP & DATA LOADING ---
# Removed emoji icon, replaced with standard text
st.set_page_config(page_title="Smoot: Smooth Travel Checker", page_icon="✈️")
@st.cache_data
def load_data():
    try:
        with open('airlines_db.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Added quotes around the error message
        st.error("Database file not found. Please ensure 'airlines_db.json' is in the folder.")
        return {}

# Load the database
db = load_data()

# Create a helper dictionary to swap names for codes
airline_map = {data['name']: code for code, data in db.items()}

# --- 2. THE RISK LOGIC (Hidden Engine) ---
def get_airline_risk(code, travel_date, db):
    """
    Returns a dictionary with color and message for a SINGLE airline.
    """
    airline_data = db.get(code)
    risk_color = "GREEN"
    reasons = []

    # Loop through unions (Pilots, Flight Attendants)
    for group, details in airline_data['unions'].items():
        status = details['status']
        
        # Check if expiration date exists and is valid
        if details['expiration_date'] == "N/A":
             expiry_date = datetime(2099, 12, 31).date() # Far future
        else:
             expiry_date = datetime.strptime(details['expiration_date'], "%Y-%m-%d").date()

        # LOGIC: Check for Danger
        if status in ["Non-Union", "Binding Arbitration"]:
            continue # Safe

        # Red Flags
        if any(x in status for x in ["Strike", "Impasse", "Cooling-off"]):
            risk_color = "RED"
            # Replaced Red Circle Emoji with [CRITICAL]
            reasons.append(f"[CRITICAL] {group.title()}: {status}")

        # Yellow Flags (Expires soon or Negotiating)
        elif risk_color != "RED":
            days_until_travel = (expiry_date - travel_date).days
            
            if days_until_travel < 30:
                risk_color = "YELLOW"
                # Replaced Yellow Circle Emoji with [WARNING]
                reasons.append(f"[WARNING] {group.title()}: Contract expires near your trip ({details['expiration_date']})")
            elif status == "Negotiating":
                risk_color = "YELLOW"
                reasons.append(f"[WARNING] {group.title()}: Currently negotiating.")

    if risk_color == "GREEN":
        # Replaced Checkmark Emoji with [OK]
        reasons.append(f"[OK] All contracts active.")

    return risk_color, reasons

# --- 3. THE VISUAL INTERFACE (What users see) ---

# --- 3. THE VISUAL INTERFACE (What users see) ---
col1, col2 = st.columns([1, 4]) # Create a small column for logo, big for text

# Add vertical_alignment="center"
col1, col2 = st.columns([1, 5], vertical_alignment="center") 

with col1:
    st.image("logo.png", width=100)

with col2:
    # I also added '###' to make the text a bit larger and bolder (like a slogan)
    st.markdown("### Don't get stranded, use Smoot.")
# --- INPUT SECTION ---
col1, col2 = st.columns(2)

with col1:
    travel_date = st.date_input("When is your trip?", min_value=datetime.today())

with col2:
    selected_names = st.multiselect(
        "Select Airline(s)", 
        options=list(airline_map.keys()),
        default=None
    )

# --- RESULTS SECTION ---
if st.button("Analyze Risk"):
    if not selected_names:
        st.warning("Please select at least one airline.")
    else:
        st.divider()
        
        trip_status = "GREEN"
        
        for name in selected_names:
            code = airline_map[name]
            color, messages = get_airline_risk(code, travel_date, db)
            
            # Display a card for this airline
            with st.expander(f"{name} (Status: {color})", expanded=True):
                if color == "RED":
                    trip_status = "RED"
                    st.error(f"**High Risk**\n\n" + "\n\n".join(messages))
                elif color == "YELLOW":
                    if trip_status != "RED": trip_status = "YELLOW"
                    st.warning(f"**Medium Risk**\n\n" + "\n\n".join(messages))
                else:
                    st.success(f"**Low Risk**\n\n" + "\n\n".join(messages))

        # Final Summary
        st.subheader("Verdict")
        if trip_status == "RED":
            st.error("JEOPARDY DETECTED: At least one of your flights has a high risk of strike action. Check refund policies.")
        elif trip_status == "YELLOW":
            st.warning("CAUTION: Labor disputes are active. Disruption is unlikely but possible. Monitor news.")
        else:
            st.success("GOOD TO GO: No active labor disputes found for your dates.")
