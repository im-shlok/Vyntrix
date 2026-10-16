from typing import Dict, Any
from app.core.database import SessionLocal, FarmerProfile
from app.agents.state import AgentState

def memory_agent(state: AgentState) -> Dict[str, Any]:
    """Retrieves and updates farmer profiles and histories from SQLAlchemy database."""
    session = SessionLocal()
    profile = None
    
    try:
        # Authenticated requests must only read their own profile. The
        # unauthenticated path deliberately retains the legacy seeded profile
        # for existing API consumers.
        profile_query = session.query(FarmerProfile)
        # The API places the authenticated ID in a private profile context
        # field. Accept ``user_id`` as well for direct agent callers/tests.
        user_id = getattr(state, "user_id", None) or state.farmer_profile.get(
            "_user_id", state.farmer_profile.get("user_id")
        )
        if user_id is not None:
            profile_query = profile_query.filter(FarmerProfile.user_id == user_id)
        profile_row = profile_query.first()
        if profile_row:
            profile = {
                "farmer_name": profile_row.farmer_name,
                "contact_number": profile_row.contact_number or "",
                "location": profile_row.location,
                "address": profile_row.address or "",
                "current_crop": profile_row.current_crop,
                "land_size_hectares": profile_row.land_size_hectares,
                "soil_type": profile_row.soil_type,
                "ph": profile_row.ph,
                "irrigation_type": profile_row.irrigation_type,
                "budget": profile_row.budget,
                "lat": profile_row.latitude,
                "lng": profile_row.longitude,
                "language": profile_row.language,
                "historical_diseases": ["Early Blight (2025)"]
            }
        else:
            # Fallback default values
            profile = {
                "farmer_name": "Ramesh Kumar",
                "location": "Bhatinda, Punjab",
                "current_crop": "Tomato",
                "land_size_hectares": 1.5,
                "soil_type": "Loam",
                "ph": 6.8,
                "irrigation_type": "Drip",
                "budget": "Medium",
                "contact_number": "",
                "address": "",
                "lat": None,
                "lng": None,
                "historical_diseases": ["Early Blight (2025)"],
                "language": state.language
            }
            
        # Parse user query to adapt crop context in database memory
        query = state.user_query.lower()
        needs_commit = False
        
        if profile_row:
            if "rice" in query and profile_row.current_crop != "Rice":
                profile_row.current_crop = "Rice"
                profile_row.soil_type = "Clay"
                profile_row.ph = 6.2
                profile["current_crop"] = "Rice"
                profile["soil_type"] = "Clay"
                profile["ph"] = 6.2
                needs_commit = True
            elif "cotton" in query and profile_row.current_crop != "Cotton":
                profile_row.current_crop = "Cotton"
                profile_row.soil_type = "Black Soil"
                profile_row.ph = 7.4
                profile["current_crop"] = "Cotton"
                profile["soil_type"] = "Black Soil"
                profile["ph"] = 7.4
                needs_commit = True
                
            if "punjabi" in query and profile_row.language != "pa":
                profile_row.language = "pa"
                state.language = "pa"
                needs_commit = True
            elif "hindi" in query and profile_row.language != "hi":
                profile_row.language = "hi"
                state.language = "hi"
                needs_commit = True
                
            if needs_commit:
                session.commit()
                print(f"[SQL Database] Farmer profile updated to crop: {profile_row.current_crop}")
                
    finally:
        session.close()
        
    profile["language"] = state.language
    exp = f"Memory loaded for Farmer: {profile['farmer_name']}. Crop: {profile['current_crop']}, Soil type: {profile['soil_type']}."
    
    return {
        "farmer_profile": profile,
        "explanation": state.explanation + f"\n\n[Memory Context Retrieval]\n{exp}",
        "messages": state.messages + [{"role": "assistant", "content": "[Memory] Retrieved profile and preference constraints."}]
    }
