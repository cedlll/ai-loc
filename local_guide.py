import streamlit as st
import openai
import googlemaps
import requests
from datetime import datetime
import json
import os
from typing import List, Dict, Optional
import urllib.parse

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
    
    def setup_apis(self, openai_key=None, gmaps_key=None):
        """Initialize API clients"""
        try:
            # OpenAI setup - try multiple sources
            api_key = None
            if openai_key:  # From user input
                api_key = openai_key
            elif "openai_api_key" in st.secrets:  # From secrets
                api_key = st.secrets["openai_api_key"]
            elif "OPENAI_API_KEY" in os.environ:  # From environment
                api_key = os.environ["OPENAI_API_KEY"]
            
            if api_key:
                openai.api_key = api_key
                self.openai_client = openai
            
            # Google Maps setup - try multiple sources
            maps_key = None
            if gmaps_key:  # From user input
                maps_key = gmaps_key
            elif "google_maps_api_key" in st.secrets:  # From secrets
                maps_key = st.secrets["google_maps_api_key"]
            elif "GOOGLE_MAPS_API_KEY" in os.environ:  # From environment
                maps_key = os.environ["GOOGLE_MAPS_API_KEY"]
            
            if maps_key:
                self.gmaps_client = googlemaps.Client(key=maps_key)
                self.maps_api_key = maps_key  # Store for static maps
                
        except Exception as e:
            st.error(f"API setup error: {str(e)}")
    
    def get_user_location_js(self):
        """JavaScript code to get user's current location"""
        return """
        <script>
        function getLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    
                    // Send location back to Streamlit
                    window.parent.postMessage({
                        type: 'geolocation',
                        latitude: lat,
                        longitude: lng
                    }, '*');
                    
                    // Update the display
                    document.getElementById('location-status').innerHTML = 
                        `✅ Location found: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
                }, function(error) {
                    document.getElementById('location-status').innerHTML = 
                        `❌ Location access denied or failed`;
                });
            } else {
                document.getElementById('location-status').innerHTML = 
                    `❌ Geolocation not supported by this browser`;
            }
        }
        </script>
        <button onclick="getLocation()" style="
            background: #ff4b4b; 
            color: white; 
            border: none; 
            padding: 8px 16px; 
            border-radius: 4px; 
            cursor: pointer;
        ">📍 Get My Location</button>
        <div id="location-status" style="margin-top: 10px; font-size: 12px;"></div>
        """
    
    def reverse_geocode(self, lat: float, lng: float) -> str:
        """Convert coordinates to address"""
        if not self.gmaps_client:
            return f"{lat}, {lng}"
        
        try:
            result = self.gmaps_client.reverse_geocode((lat, lng))
            if result:
                return result[0]['formatted_address']
            return f"{lat}, {lng}"
        except:
            return f"{lat}, {lng}"
    
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
            for place in places_result.get('results', [])[:8]:  # Limit to 8 results for better display
                place_details = {
                    'name': place.get('name', ''),
                    'rating': place.get('rating', 'N/A'),
                    'price_level': place.get('price_level', 'N/A'),
                    'types': place.get('types', []),
                    'vicinity': place.get('vicinity', ''),
                    'opening_hours': place.get('opening_hours', {}).get('open_now', 'Unknown'),
                    'place_id': place.get('place_id', ''),
                    'geometry': place.get('geometry', {}),
                    'photos': place.get('photos', [])
                }
                
                # Generate Google Maps links
                place_details['maps_link'] = self.generate_maps_link(place_details)
                place_details['directions_link'] = self.generate_directions_link(place_details, lat_lng)
                
                places.append(place_details)
            
            return places
            
        except Exception as e:
            st.error(f"Places search error: {str(e)}")
            return []
    
    def generate_maps_link(self, place: Dict) -> str:
        """Generate Google Maps link for a place"""
        if place.get('place_id'):
            return f"https://www.google.com/maps/place/?q=place_id:{place['place_id']}"
        elif place.get('geometry', {}).get('location'):
            loc = place['geometry']['location']
            name = urllib.parse.quote(place.get('name', ''))
            return f"https://www.google.com/maps/search/{name}/@{loc['lat']},{loc['lng']},17z"
        else:
            name = urllib.parse.quote(f"{place.get('name', '')} {place.get('vicinity', '')}")
            return f"https://www.google.com/maps/search/{name}"
    
    def generate_directions_link(self, place: Dict, origin: Dict) -> str:
        """Generate Google Maps directions link"""
        if place.get('geometry', {}).get('location'):
            dest_loc = place['geometry']['location']
            return f"https://www.google.com/maps/dir/{origin['lat']},{origin['lng']}/{dest_loc['lat']},{dest_loc['lng']}"
        else:
            dest_name = urllib.parse.quote(f"{place.get('name', '')} {place.get('vicinity', '')}")
            return f"https://www.google.com/maps/dir/{origin['lat']},{origin['lng']}/{dest_name}"
    
    def generate_static_map(self, places: List[Dict], center_location: str) -> str:
        """Generate static map URL with markers"""
        if not hasattr(self, 'maps_api_key') or not places:
            return None
        
        base_url = "https://maps.googleapis.com/maps/api/staticmap"
        
        # Map parameters
        params = {
            'size': '600x400',
            'zoom': '14',
            'center': center_location,
            'key': self.maps_api_key,
            'maptype': 'roadmap'
        }
        
        # Add markers for each place
        markers = []
        for i, place in enumerate(places[:5]):  # Limit to 5 markers to avoid URL length issues
            if place.get('geometry', {}).get('location'):
                loc = place['geometry']['location']
                label = chr(65 + i)  # A, B, C, etc.
                marker = f"color:red|label:{label}|{loc['lat']},{loc['lng']}"
                markers.append(marker)
        
        if markers:
            params['markers'] = markers
        
        # Build URL
        param_string = "&".join([f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items() if k != 'markers'])
        if markers:
            marker_string = "&".join([f"markers={urllib.parse.quote(marker)}" for marker in markers])
            param_string += "&" + marker_string
        
        return f"{base_url}?{param_string}"
    
    def create_local_guide_prompt(self, user_query: str, location: str, places_data: List[Dict]) -> str:
        """Create a prompt that makes the AI act like a focused local guide"""
        
        places_info = ""
        if places_data:
            places_info = "\n\nHere are some relevant local places I found:\n"
            for i, place in enumerate(places_data, 1):
                price_indicator = "💰" * (place.get('price_level', 1) if place.get('price_level', 1) != 'N/A' else 1)
                places_info += f"{chr(64 + i)}. **{place['name']}** ({place.get('vicinity', 'Unknown location')})\n"
                places_info += f"   - Rating: {place.get('rating', 'N/A')} ⭐\n"
                places_info += f"   - Price: {price_indicator}\n"
                places_info += f"   - Currently open: {'Yes' if place.get('opening_hours') else 'Unknown'}\n"
                places_info += f"   - Maps: {place.get('maps_link', 'N/A')}\n\n"
        
        prompt = f"""You are a helpful LOCAL GUIDE for {location}. You ONLY help with travel, tourism, and location-based questions.

STRICT GUIDELINES:
- ONLY answer questions about: restaurants, attractions, transportation, accommodations, local events, directions, weather, cultural sites, shopping, nightlife, and travel tips
- REFUSE to answer questions about: politics, personal advice, technical support, medical advice, financial advice, or anything unrelated to being a local guide
- DO NOT provide sensitive information like personal data, addresses of private individuals, or confidential information
- BE RESPECTFUL and inclusive - never make discriminatory comments about any group of people
- If asked non-travel questions, politely redirect: "I'm a local guide focused on helping you explore {location}. Ask me about places to visit, eat, or things to do!"

User's question: "{user_query}"
Location context: {location}

{places_info}

Respond as a friendly local guide who:
- Gives enthusiastic, practical recommendations
- Includes walking times, price ranges, best times to visit
- Shares local tips and hidden gems
- Mentions alternatives and nearby options
- Uses Google Maps links when available
- Keeps responses concise (2-3 paragraphs max)
- Stays focused ONLY on travel and local guidance

Remember: You are ONLY a local guide. Politely decline any non-travel related questions."""

        return prompt
    
    def chat_with_guide(self, user_query: str, location: str, conversation_history: List[Dict]) -> str:
        """Generate AI response using OpenAI with local context"""
        if not self.openai_client:
            return "Sorry, I need an OpenAI API key to help you. Please add it in the sidebar."
        
        # Extract keywords for place search
        search_keywords = self.extract_search_keywords(user_query)
        
        # Get nearby places data
        places_data = []
        if search_keywords and self.is_location_query(user_query):
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
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=600,
                temperature=0.7
            )
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"
    
    def is_location_query(self, query: str) -> bool:
        """Check if query is asking for location-based recommendations"""
        location_indicators = [
            'where', 'near', 'close', 'nearby', 'around', 'find', 'search',
            'restaurant', 'cafe', 'bar', 'shop', 'store', 'museum', 'park',
            'hotel', 'place', 'spot', 'location', 'best', 'good', 'recommend'
        ]
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in location_indicators)
    
    def extract_search_keywords(self, query: str) -> str:
        """Extract relevant keywords for place searching"""
        food_keywords = ['breakfast', 'lunch', 'dinner', 'coffee', 'restaurant', 'cafe', 'food', 'eat', 'drink', 'pizza', 'burger', 'sushi', 'thai', 'chinese', 'italian']
        activity_keywords = ['shop', 'shopping', 'park', 'museum', 'gym', 'movie', 'bar', 'nightlife', 'club', 'theater', 'art', 'gallery']
        service_keywords = ['bank', 'pharmacy', 'hospital', 'gas', 'hotel', 'accommodation', 'atm', 'wifi', 'work', 'coworking']
        
        query_lower = query.lower()
        
        # Check for specific food types
        for keyword in food_keywords:
            if keyword in query_lower:
                return keyword if keyword in ['restaurant', 'cafe', 'bar'] else 'restaurant'
        
        # Check for activities
        for keyword in activity_keywords:
            if keyword in query_lower:
                return keyword
        
        # Check for services
        for keyword in service_keywords:
            if keyword in query_lower:
                return keyword
        
        return query  # Return original query if no specific keywords found

def main():
    st.title("🗺️ AI Local Guide")
    st.markdown("*Ask me about local spots, restaurants, attractions, and travel tips for any city worldwide!*")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("🔑 API Configuration")
        
        # Location input
        location = st.text_input(
            "Your Location", 
            value=st.session_state.get('location', 'London, UK'),
            help="Enter any city, neighborhood, or address worldwide",
            placeholder="e.g., Paris, France or Tokyo, Japan"
        )
        
        # Check for geolocation data in session state
        if 'user_lat' in st.session_state and 'user_lng' in st.session_state:
            user_location = guide.reverse_geocode(st.session_state.user_lat, st.session_state.user_lng)
            st.success(f"📍 Found: {user_location}")
            if st.button("Use This Location"):
                st.session_state.location = user_location
                location = user_location
        
        st.markdown("---")
        
        # Quick suggestions
        st.header("💡 Try asking:")
        suggestions = [
            "Best breakfast spots nearby?",
            "Coffee shops with WiFi?",
            "Fun evening activities?",
            "Local markets and shopping?",
            "Romantic dinner restaurants?",
            "Bars with live music?",
            "Family-friendly attractions?",
            "Hidden gems locals love?"
        ]
        
        for suggestion in suggestions:
            if st.button(suggestion, key=f"suggest_{suggestion[:15]}"):
                st.session_state.suggested_query = suggestion
        
        st.markdown("---")
        st.caption("🛡️ This guide only answers travel and location questions for your safety and privacy.")

    # API Key inputs
        openai_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Get your key from platform.openai.com",
            placeholder="sk-..."
        )
        
        gmaps_key = st.text_input(
            "Google Maps API Key", 
            type="password",
            help="Get your key from console.cloud.google.com",
            placeholder="AIza..."
        )
        
     # Initialize the guide with API keys
        guide = LocalGuide()
        guide.setup_apis(openai_key, gmaps_key)
        
        st.markdown("---")
        
    # Store location in session state
    if location:
        st.session_state['location'] = location
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Add welcome message
        welcome_msg = f"Hello! I'm your personal local guide for {location}. I can help you discover amazing restaurants, attractions, hidden gems, and everything you need to explore like a local! What would you like to find today? 🌟"
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
        query = st.chat_input("Ask me about local places, restaurants, attractions, or travel tips!")
    
    if query:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Searching for the best local spots..."):
                # Get location for search
                current_location = st.session_state.get('location', 'Current location')
                
                # Check if we should get places data
                if guide.is_location_query(query) and guide.gmaps_client:
                    search_keywords = guide.extract_search_keywords(query)
                    places_data = guide.get_nearby_places(current_location, search_keywords)
                    
                    # Generate response
                    response = guide.chat_with_guide(query, current_location, st.session_state.messages[:-1])
                    st.markdown(response)
                    
                    # Show map if places found
                    if places_data and hasattr(guide, 'maps_api_key'):
                        st.markdown("---")
                        st.markdown("📍 **Locations on Map:**")
                        
                        map_url = guide.generate_static_map(places_data, current_location)
                        if map_url:
                            st.image(map_url, caption="Map of recommended places")
                        
                        # Show place details with links
                        st.markdown("🔗 **Quick Access Links:**")
                        for i, place in enumerate(places_data):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**{chr(65+i)}. {place['name']}**")
                                st.markdown(f"⭐ {place.get('rating', 'N/A')} | {'💰' * (place.get('price_level', 1) if place.get('price_level', 1) != 'N/A' else 1)}")
                            with col2:
                                st.markdown(f"[📍 View on Maps]({place['maps_link']})")
                                if place.get('directions_link'):
                                    st.markdown(f"[🚶 Get Directions]({place['directions_link']})")
                else:
                    # Regular response without places data
                    response = guide.chat_with_guide(query, current_location, st.session_state.messages[:-1])
                    st.markdown(response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Clear chat button
    if st.sidebar.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        welcome_msg = f"Hello! I'm your personal local guide for {st.session_state.get('location', 'your area')}. I can help you discover amazing restaurants, attractions, hidden gems, and everything you need to explore like a local! What would you like to find today? 🌟"
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
        st.rerun()

if __name__ == "__main__":
    main()
