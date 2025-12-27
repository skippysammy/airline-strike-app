import streamlit as st
import json
from datetime import datetime, timedelta

# --- 1. CONFIGURATION & CSS STYLING ---
st.set_page_config(page_title="Smoot", page_icon="✈️", layout="wide")

# Custom CSS to mimic Airbnb's "Rounded/Pill" look
st.markdown("""
<style>
    /* Round the Date Picker and Dropdowns */
    .stDateInput > div > div {
        border-radius: 20px;
        border: 1px solid #E0E0E0;
    }
    .stSelectbox > div > div {
        border-radius: 20px;
        border: 1px solid #E0E0E0;
    }
    /* Round the Search Button and make it 'Airbnb Rose' color */
    div.stButton > button {
        border-radius: 20px;
        background-color: #FF385C; 
        color: white;
        border: none;
        width: 100%;
        height: 50px;
        font-weight: bold;
        font-size: 18px;
    }
    div.stButton > button:hover {
        background-color: #D90B3E;
        color: white;
    }
    /* Clean up top padding */
    .block-container {
        padding-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. DATA LOADING ---
@st.cache_data
def load_data():
    try:
        with open('airlines_db.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("⚠️ Database file not found.")
        return {}

db = load_data()
# Map "Air Canada" -> "AC"
name_to_code = {data['name']: code for code, data in db.items()}
# Map "AC" -> "Air Canada" (for displaying alternatives)
code_to_name = {code: data['name'] for code, data in db.items()}

# EXPANDED City/Hub Database
city_db = {
    "Toronto (YYZ)": ["AC", "WS", "TS", "UA", "DL", "AA"],
    "Vancouver (YVR)": ["AC", "WS", "UA", "DL", "AA", "AS"],
    "Montreal (YUL)": ["AC", "TS", "UA", "DL", "AA"],
    "New York (JFK)": ["DL", "B6", "AA", "AS"],
    "New York (LGA)": ["DL", "AA", "UA", "WN", "AC", "WS"],
    "Newark (EWR)": ["UA", "DL", "AA", "AC", "AS", "NK"],
    "Los Angeles (LAX)": ["UA", "AA", "DL", "AS", "WN", "B6", "NK", "AC", "WS"],
    "Chicago (ORD)": ["UA", "AA", "DL", "WN", "AC", "WS"],
    "Atlanta (ATL)": ["DL", "WN", "NK", "UA", "AA"],
    "Dallas (DFW)": ["AA", "UA", "DL", "NK", "AC"],
    "Denver (DEN)": ["UA", "WN", "DL", "AA", "AC"],
    "Seattle (SEA)": ["AS", "DL", "UA", "WN", "AC"],
    "San Francisco (SFO)": ["UA", "AS", "DL", "AA", "AC", "WS", "B6"],
    "Miami (MIA)": ["AA", "DL", "UA", "AC", "WS", "NK"],
    "Orlando (MCO)": ["WN", "NK", "DL", "UA", "AA", "AC", "WS", "B6"],
    "Las Vegas (LAS)": ["WN", "NK", "UA", "DL", "AA", "AC", "WS", "AS", "B6"],
    "Boston (BOS)": ["B6", "DL", "UA", "AA", "AC", "WS", "NK"],
    "Fort Lauderdale (FLL)": ["NK", "B6", "WN", "DL", "UA", "AA", "AC", "WS"]
}

# Sort the cities alphabetically for the dropdown
sorted_cities = sorted(city_db.keys())

# --- 3. RISK ENGINE ---
def get_airline_risk(code, start_date, end_date, db):
    """
    Returns: (Color, List of Messages)
    """
    if code not in db:
        return "GREY", ["No data available"]

    airline_data = db.get(code)
    risk_color = "GREEN"
    reasons = []

    for group, details in airline_data['unions'].items():
        status = details['status']
        if details['expiration_date'] == "N/A":
             expiry_date = datetime(2099, 12, 31).date()
        else:
             expiry_date = datetime.strptime(details['expiration_date'], "%Y-%m-%d").date()

        # Safe
        if status in ["Non-Union", "Binding Arbitration"]:
            continue 

        # Critical
        if any(x in status for x in ["Strike", "Impasse", "Cooling-off"]):
            risk_color = "RED"
            reasons.append(f"🔴 [CRITICAL] {group.title()}: {status}")

        # Warnings
        elif risk_color != "RED":
            # Expiry Logic
            if expiry_date < start_date:
                risk_color = "YELLOW"
                reasons.append(f"⚠️ [WARNING] {group.title()} contract expires BEFORE your trip ({details['expiration_date']}).")
            elif start_date <= expiry_date <= end_date:
                risk_color = "YELLOW"
                reasons.append(f"⚠️ [WARNING] {group.title()} contract expires DURING your trip.")
            elif 0 < (expiry_date - end_date).days < 30:
                risk_color = "YELLOW"
                reasons.append(f"⚠️ [CAUTION] {group.title()} contract expires shortly after return.")
            
            if status == "Negotiating" and risk_color == "GREEN":
                risk_color = "YELLOW"
                reasons.append(f"⚠️ [WARNING] {group.title()} are currently negotiating.")

    if risk_color == "GREEN":
        reasons.append("✅ Contracts active.")

    return risk_color, reasons

# --- 4. LAYOUT & SEARCH BAR ---

# LOGO FIX: Changed ratio from [0.6, 10] to [1, 12]
# This prevents the logo from being chopped while keeping text close.
col_logo, col_title = st.columns([1, 20], vertical_alignment="center")

with col_logo:
    try:
        st.image("logo_image.png", width=60) 
    except:
        st.write("✈️") 
with col_title:
    st.markdown("### Smoot")

st.write("") # Spacer

# THE SEARCH BUCKETS (3 Columns)
with st.container():
    c1, c2, c3 = st.columns(3)
    
    # Bucket 1: Dates
    with c1:
        st.markdown("**1. When are you traveling?**")
        today = datetime.today()
        date_range = st.date_input(
            "Trip Dates",
            value=(today, today + timedelta(days=7)),
            min_value=today,
            label_visibility="collapsed" 
        )

    # Bucket 2: City
    with c2:
        st.markdown("**2. To which city?**")
        selected_city = st.selectbox(
            "Destination",
            options=sorted_cities,
            index=0, 
            label_visibility="collapsed"
        )

    # Bucket 3: Airline (Dynamic)
    with c3:
        st.markdown("**3. With which Airline?**")
        # Get airlines available for the selected city
        available_codes = city_db[selected_city]
        
        # Convert codes (AC) back to names (Air Canada) for the dropdown
        available_names = [code_to_name.get(c, c) for c in available_codes if c in code_to_name]
        
        selected_airline_name = st.selectbox(
            "Airline",
            options=available_names,
            label_visibility="collapsed"
        )

    st.write("") # Spacer
    
    # Search Button (Full Width)
    search_clicked = st.button("Search")

# --- 5. RESULTS ---
st.markdown("---")

if search_clicked:
    # 1. Validate Dates
    if not isinstance(date_range, tuple) or len(date_range) != 2:
        st.error("Please select both a departure and return date.")
        st.stop()
    
    start, end = date_range
    
    # 2. Analyze the CHOSEN Airline
    chosen_code = name_to_code[selected_airline_name]
    risk_color, messages = get_airline_risk(chosen_code, start, end, db)
    
    # Display Main Result
    st.subheader("Risk Assessment")
    
    with st.expander(f"{selected_airline_name} — Status: {risk_color}", expanded=True):
        if risk_color == "RED":
            st.error("\n\n".join(messages))
        elif risk_color == "YELLOW":
            st.warning("\n\n".join(messages))
        else:
            st.success("\n\n".join(messages))

    # 3. IF RISK DETECTED -> Show Alternatives
    if risk_color in ["RED", "YELLOW"]:
        st.markdown("### 💡 Recommendation")
        
        st.info(f"**Notice:** Our algorithm indicates a probability that **{selected_airline_name}** may encounter labor disputes during your trip. To be safe, consider the alternatives below or purchase travel insurance.")
        
        # Find Safe Alternatives for THIS City
        st.markdown(f"**Smoother options flying to {selected_city}:**")
        
        safe_alternatives = []
        # Check every other airline that flies here
        available_codes = city_db[selected_city]
        
        for code in available_codes:
            if code == chosen_code: continue # Skip the one we just picked
            
            # Check risk for this alternative
            alt_color, _ = get_airline_risk(code, start, end, db)
            
            if alt_color == "GREEN":
                alt_name = code_to_name.get(code, code)
                safe_alternatives.append(alt_name)
        
        # Display Alternatives
        if safe_alternatives:
            for alt in safe_alternatives:
                st.success(f"✅ **{alt}** is currently marked Safe/Green.")
        else:

            st.write("No 'Green' alternatives found for this route. Check travel insurance policies.")
