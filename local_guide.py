import streamlit as st
import openai
import googlemaps
import requests
from datetime import datetime
import json
import os
from typing import List, Dict, Optional

# Page configuration
st.set_page_config(
    page_title="Local Guide Chat",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

class LocalGuide:
    def __init__(self):
        self.openai_client = None
        self.gmaps_client = None
        self.setup_apis()
    
    def setup_apis(self):
        """Initialize API clients"""
        try:
            # OpenAI setup
            if "openai_api_key" in st.secrets:
                openai.api_key = st.secrets["openai_api_key"]
                self.openai_client = openai
            elif "OPENAI_API_KEY" in os.environ:
                openai.api_key = os.environ["OPENAI_API_KEY"]
                self.openai_client = openai
            
            # Google Maps setup
            if "google_maps_api_key" in st.secrets:
                self.gmaps_client = googlemaps.Client(key=st.secrets["google_maps_api_key"])
            elif "GOOGLE_MAPS_API_KEY" in os.environ:
                self.gmaps_client = googlemaps.Client(key=os.environ["GOOGLE_MAPS_API_KEY"])
                
        except Exception as e:
            st.error(f"API setup error: {str(e)}")
    
    def get_nearby_places(self, location: str, query: str, radius: int = 1000) -> List[Dict]:
        """Search for nearby places using Google Places API"""
        if not self.gmaps_client:
            return []
        
        try:
            # First, geocode the location
            geocode_result = self.gmaps_client.geocode(location)
            if not geocode_result:
                return []
            
            lat_lng = geocode_result[0]['geometry']['location']
            
            # Search for nearby places
            places_result = self.gmaps_client.places_nearby(
                location=lat_lng,
                radius=radius,
                keyword=query,
                open_now=True
            )
            
            # Format results
            places = []
            for place in places_result.get('results', [])[:10]:  # Limit to 10 results
                place_details = {
                    'name': place.get('name', ''),
                    'rating': place.get('rating', 'N/A'),
                    'price_level': place.get('price_level', 'N/A'),
                    'types': place.get('types', []),
                    'vicinity': place.get('vicinity', ''),
                    'opening_hours': place.get('opening_hours', {}).get('open_now', 'Unknown'),
                    'place_id': place.get('place_id', '')
                }
                places.append(place_details)
            
            return places
            
        except Exception as e:
            st.error(f"Places search error: {str(e)}")
            return []
    
    def get_place_details(self, place_id: str) -> Dict:
        """Get detailed information about a specific place"""
        if not self.gmaps_client:
            return {}
        
        try:
            details = self.gmaps_client.place(
                place_id=place_id,
                fields=['name', 'rating', 'formatted_phone_number', 'website', 
                       'opening_hours', 'price_level', 'reviews', 'formatted_address']
            )
            return details.get('result', {})
        except Exception as e:
            return {}
    
    def create_local_guide_prompt(self, user_query: str, location: str, places_data: List[Dict]) -> str:
        """Create a prompt that makes the AI act like a knowledgeable local guide"""
        
        places_info = ""
        if places_data:
            places_info = "\n\nHere are some relevant local places I found:\n"
            for i, place in enumerate(places_data, 1):
                price_indicator = "💰" * (place.get('price_level', 1) if place.get('price_level', 1) != 'N/A' else 1)
                places_info += f"{i}. **{place['name']}** ({place.get('vicinity', 'Unknown location')})\n"
                places_info += f"   - Rating: {place.get('rating', 'N/A')} ⭐\n"
                places_info += f"   - Price: {price_indicator}\n"
                places_info += f"   - Currently open: {'Yes' if place.get('opening_hours') else 'Unknown'}\n\n"
        
        prompt = f"""You are a friendly, knowledgeable local guide for {location}. You know this area like the back of your hand and love helping visitors and locals discover great spots.

User's question: "{user_query}"
Location context: {location}

{places_info}

Respond as a helpful local who:
- Gives personalized, enthusiastic recommendations
- Includes practical details (walking time, price ranges, best times to visit)
- Shares insider tips and local knowledge
- Mentions alternatives if the first suggestion might not work
- Uses a warm, conversational tone like you're chatting with a friend
- References the specific places found above when relevant

Keep your response concise but informative (2-3 paragraphs max). Act like you've personally been to these places and can vouch for them."""

        return prompt
    
    def chat_with_guide(self, user_query: str, location: str, conversation_history: List[Dict]) -> str:
        """Generate AI response using OpenAI with local context"""
        if not self.openai_client:
            return "Sorry, I need an OpenAI API key to help you. Please add it to your secrets or environment variables."
        
        # Extract keywords for place search
        search_keywords = self.extract_search_keywords(user_query)
        
        # Get nearby places data
        places_data = []
        if search_keywords:
            places_data = self.get_nearby_places(location, search_keywords)
        
        # Create the prompt
        system_prompt = self.create_local_guide_prompt(user_query, location, places_data)
        
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last 6 messages to keep context manageable)
        for msg in conversation_history[-6:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": user_query})
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # or "gpt-3.5-turbo" for lower cost
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
    
    def extract_search_keywords(self, query: str) -> str:
        """Extract relevant keywords for place searching"""
        # Simple keyword extraction - you could make this more sophisticated
        food_keywords = ['breakfast', 'lunch', 'dinner', 'coffee', 'restaurant', 'cafe', 'food', 'eat', 'drink']
        activity_keywords = ['shop', 'shopping', 'park', 'museum', 'gym', 'movie', 'bar', 'nightlife']
        service_keywords = ['bank', 'pharmacy', 'hospital', 'gas', 'hotel']
        
        query_lower = query.lower()
        
        for keyword in food_keywords:
            if keyword in query_lower:
                return 'restaurant'
        
        for keyword in activity_keywords:
            if keyword in query_lower:
                return keyword
        
        for keyword in service_keywords:
            if keyword in query_lower:
                return keyword
        
        return query  # Return original query if no specific keywords found

def main():
    st.title("🗺️ Your Personal Local Guide")
    st.markdown("*Ask me anything about your area - I'm like having a knowledgeable local friend!*")
    
    # Initialize the guide
    guide = LocalGuide()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("📍 Location Settings")
        
        # Location input
        location = st.text_input(
            "Your Location", 
            value=st.session_state.get('location', 'New York, NY'),
            help="Enter your city, neighborhood, or address"
        )
        
        if st.button("📍 Use My Current Location", help="This will prompt for location access"):
            st.info("Location detection would require additional browser permissions and setup.")
        
        st.markdown("---")
        
        # API Status
        st.header("🔧 API Status")
        openai_status = "✅ Connected" if guide.openai_client else "❌ Not configured"
        gmaps_status = "✅ Connected" if guide.gmaps_client else "❌ Not configured"
        
        st.write(f"OpenAI: {openai_status}")
        st.write(f"Google Maps: {gmaps_status}")
        
        if not guide.openai_client or not guide.gmaps_client:
            st.warning("Configure API keys in secrets.toml or environment variables")
            
        st.markdown("---")
        
        # Quick suggestions
        st.header("💡 Try asking:")
        suggestions = [
            "Where can I get cheap breakfast within walking distance?",
            "Best coffee shops that are open now?",
            "Fun things to do this evening?",
            "Grocery stores near me?",
            "Good restaurants for a date night?",
            "Places to work with WiFi?",
            "Best local bars?",
            "Family-friendly activities?"
        ]
        
        for suggestion in suggestions:
            if st.button(suggestion, key=f"suggest_{suggestion[:20]}"):
                st.session_state.suggested_query = suggestion
    
    # Store location in session state
    if location:
        st.session_state['location'] = location
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Add welcome message
        welcome_msg = f"Hey there! I'm your local guide for {location}. What would you like to explore or find today? 😊"
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Handle suggested queries
    if "suggested_query" in st.session_state:
        query = st.session_state.suggested_query
        del st.session_state.suggested_query
    else:
        # Chat input
        query = st.chat_input("Ask me about local places, food, activities, or anything!")
    
    if query:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Looking up local spots..."):
                response = guide.chat_with_guide(
                    query, 
                    st.session_state.get('location', 'Current location'),
                    st.session_state.messages[:-1]  # Exclude the just-added user message
                )
            st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Clear chat button
    if st.sidebar.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

if __name__ == "__main__":
    main()
