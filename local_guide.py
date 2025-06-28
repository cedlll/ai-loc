def generate_concierge_response(self, user_query: str, location: str, persona: Dict, behavior_tracker: UserBehaviorTracker) -> str:
        """Generate personalized concierge response"""
        if not self.openai_client:
            return "I need API access to assist you properly."
        
        # Get user patterns
        preferred_time = behavior_tracker.get_preferred_time()
        skipped_types = [s["type"] for s in behavior_tracker.behavior_data["skipped_suggestionsimport streamlit as st
import openai
import googlemaps
import requests
from datetime import datetime, timedelta
import json
import os
import random
import time
from typing import List, Dict, Optional
import urllib.parse

# Page configuration
st.set_page_config(
    page_title="AI Travel Concierge",
    page_icon="🌟",
    layout="wide",
    initial_sidebar_state="expanded"
)

class UserBehaviorTracker:
    """Tracks user behavior and preferences to learn patterns"""
    
    def __init__(self):
        self.behavior_data = {
            "location_history": [],
            "activity_preferences": {},
            "timing_patterns": {},
            "skipped_suggestions": [],
            "chosen_suggestions": [],
            "price_sensitivity": "unknown",
            "group_type": "unknown",
            "interaction_times": [],
            "persona_indicators": {
                "foodie": 0,
                "romantic": 0,
                "explorer": 0,
                "cultural": 0,
                "budget": 0,
                "luxury": 0
            }
        }
    
    def track_interaction(self, query: str, response: str, choices_made: List[str] = None):
        """Track user interaction patterns"""
        current_time = datetime.now()
        self.behavior_data["interaction_times"].append({
            "time": current_time.strftime("%H:%M"),
            "day": current_time.strftime("%A"),
            "query": query.lower()
        })
        
        # Analyze for persona indicators
        self._analyze_persona_indicators(query, response, choices_made)
        
        # Track timing patterns
        hour = current_time.hour
        if hour < 12:
            self.behavior_data["timing_patterns"]["morning"] = self.behavior_data["timing_patterns"].get("morning", 0) + 1
        elif hour < 17:
            self.behavior_data["timing_patterns"]["afternoon"] = self.behavior_data["timing_patterns"].get("afternoon", 0) + 1
        else:
            self.behavior_data["timing_patterns"]["evening"] = self.behavior_data["timing_patterns"].get("evening", 0) + 1
    
    def _analyze_persona_indicators(self, query: str, response: str, choices_made: List[str] = None):
        """Analyze conversation for persona indicators"""
        text = (query + " " + response).lower()
        
        # Foodie indicators
        food_words = ["restaurant", "food", "eat", "cuisine", "chef", "menu", "taste", "delicious", "recipe"]
        if any(word in text for word in food_words):
            self.behavior_data["persona_indicators"]["foodie"] += 1
        
        # Romantic indicators
        romantic_words = ["romantic", "date", "couple", "intimate", "sunset", "wine", "cozy", "candlelit"]
        if any(word in text for word in romantic_words):
            self.behavior_data["persona_indicators"]["romantic"] += 1
        
        # Explorer indicators
        explorer_words = ["adventure", "explore", "hidden", "off beaten", "unique", "discover", "outdoor", "hike"]
        if any(word in text for word in explorer_words):
            self.behavior_data["persona_indicators"]["explorer"] += 1
        
        # Cultural indicators
        cultural_words = ["museum", "history", "art", "culture", "heritage", "traditional", "local customs"]
        if any(word in text for word in cultural_words):
            self.behavior_data["persona_indicators"]["cultural"] += 1
        
        # Budget indicators
        budget_words = ["cheap", "budget", "affordable", "free", "inexpensive", "deal", "discount"]
        luxury_words = ["luxury", "expensive", "premium", "upscale", "fine dining", "high-end"]
        
        if any(word in text for word in budget_words):
            self.behavior_data["persona_indicators"]["budget"] += 1
        elif any(word in text for word in luxury_words):
            self.behavior_data["persona_indicators"]["luxury"] += 1
    
    def get_dominant_persona(self) -> str:
        """Get the user's dominant persona based on interactions"""
        indicators = self.behavior_data["persona_indicators"]
        if not any(indicators.values()):
            return "general"
        
        return max(indicators, key=indicators.get)
    
    def get_preferred_time(self) -> str:
        """Get user's preferred interaction time"""
        patterns = self.behavior_data["timing_patterns"]
        if not patterns:
            return "any"
        return max(patterns, key=patterns.get)
    
    def track_choice(self, suggestion_type: str, chosen: bool, details: str = ""):
        """Track whether user chose or skipped suggestions"""
        choice_data = {
            "type": suggestion_type,
            "chosen": chosen,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        
        if chosen:
            self.behavior_data["chosen_suggestions"].append(choice_data)
        else:
            self.behavior_data["skipped_suggestions"].append(choice_data)

class PersonaManager:
    """Manages AI persona based on user behavior"""
    
    def __init__(self, behavior_tracker: UserBehaviorTracker):
        self.behavior_tracker = behavior_tracker
        self.personas = {
            "foodie": {
                "greeting_style": "Hey food lover! 🍽️",
                "suggestion_focus": "culinary experiences, local specialties, hidden food gems",
                "tone": "enthusiastic about flavors and dining experiences",
                "proactive_suggestions": ["unique restaurants", "food tours", "local markets", "cooking classes"]
            },
            "romantic": {
                "greeting_style": "Looking for something special? 💕",
                "suggestion_focus": "intimate venues, romantic activities, scenic spots",
                "tone": "warm and thoughtful, focusing on memorable moments",
                "proactive_suggestions": ["sunset spots", "romantic restaurants", "couple activities", "scenic walks"]
            },
            "explorer": {
                "greeting_style": "Ready for an adventure? 🗺️",
                "suggestion_focus": "unique experiences, off-the-beaten-path locations, outdoor activities",
                "tone": "energetic and discovery-focused",
                "proactive_suggestions": ["hidden gems", "outdoor adventures", "unique experiences", "local secrets"]
            },
            "cultural": {
                "greeting_style": "Dive into local culture! 🏛️",
                "suggestion_focus": "museums, historical sites, cultural events, traditional experiences",
                "tone": "knowledgeable and respectful of local heritage",
                "proactive_suggestions": ["museums", "cultural sites", "local traditions", "art galleries"]
            },
            "budget": {
                "greeting_style": "Smart travel on a budget! 💰",
                "suggestion_focus": "free activities, budget-friendly options, local deals",
                "tone": "practical and value-conscious",
                "proactive_suggestions": ["free activities", "budget eats", "discounts", "local deals"]
            },
            "luxury": {
                "greeting_style": "Experience the finest! ✨",
                "suggestion_focus": "premium experiences, upscale venues, exclusive access",
                "tone": "sophisticated and quality-focused",
                "proactive_suggestions": ["luxury experiences", "fine dining", "premium activities", "exclusive venues"]
            },
            "general": {
                "greeting_style": "What's your vibe today? 🌟",
                "suggestion_focus": "balanced mix of activities and experiences",
                "tone": "friendly and adaptable",
                "proactive_suggestions": ["popular spots", "recommended activities", "local favorites", "must-sees"]
            }
        }
    
    def get_current_persona(self) -> Dict:
        """Get current persona settings based on user behavior"""
        dominant = self.behavior_tracker.get_dominant_persona()
        return self.personas.get(dominant, self.personas["general"])
    
    def generate_proactive_message(self, location: str, time_context: str = "") -> str:
        """Generate a proactive message based on persona and context"""
        persona = self.get_current_persona()
        current_hour = datetime.now().hour
        
        # Time-based context
        if current_hour < 10:
            time_greeting = "Good morning!"
        elif current_hour < 17:
            time_greeting = "Good afternoon!"
        else:
            time_greeting = "Good evening!"
        
        # Location-based insights
        location_insights = [
            f"I noticed you're in {location}",
            f"Since you're exploring {location}",
            f"While you're in {location}"
        ]
        
        # Persona-based suggestions
        suggestions = persona["proactive_suggestions"]
        suggestion = random.choice(suggestions)
        
        messages = [
            f"{time_greeting} {persona['greeting_style']} {random.choice(location_insights)}, interested in {suggestion}?",
            f"{persona['greeting_style']} I see you're in {location}. How about some {suggestion} recommendations?",
            f"{time_greeting} Perfect timing! Want me to find some great {suggestion} in {location}?"
        ]
        
        return random.choice(messages)

class ConversationThread:
    """Manages conversation threads and cards"""
    
    def __init__(self, thread_id: str, thread_type: str, title: str):
        self.thread_id = thread_id
        self.thread_type = thread_type  # "recommendation", "itinerary", "general", "proactive"
        self.title = title
        self.messages = []
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        self.status = "active"  # active, completed, archived
        self.cards = []
    
    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add a message to the thread"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        self.last_updated = datetime.now()
    
    def add_card(self, card_type: str, data: Dict):
        """Add a card to the thread"""
        card = {
            "type": card_type,  # "recommendation", "place", "itinerary", "ad"
            "data": data,
            "timestamp": datetime.now()
        }
        self.cards.append(card)

class LocalGuide:
    def __init__(self):
        self.openai_client = None
        self.gmaps_client = None
    
    def setup_apis(self, openai_key=None, gmaps_key=None):
        """Initialize API clients"""
        try:
            # OpenAI setup - try multiple sources
            api_key = None
            if openai_key:
                api_key = openai_key
            elif "openai_api_key" in st.secrets:
                api_key = st.secrets["openai_api_key"]
            elif "OPENAI_API_KEY" in os.environ:
                api_key = os.environ["OPENAI_API_KEY"]
            
            if api_key:
                openai.api_key = api_key
                self.openai_client = openai
            
            # Google Maps setup
            maps_key = None
            if gmaps_key:
                maps_key = gmaps_key
            elif "google_maps_api_key" in st.secrets:
                maps_key = st.secrets["google_maps_api_key"]
            elif "GOOGLE_MAPS_API_KEY" in os.environ:
                maps_key = os.environ["GOOGLE_MAPS_API_KEY"]
            
            if maps_key:
                self.gmaps_client = googlemaps.Client(key=maps_key)
                self.maps_api_key = maps_key
                
        except Exception as e:
            st.error(f"API setup error: {str(e)}")
    
    def get_nearby_places(self, location: str, query: str, radius: int = 1000) -> List[Dict]:
        """Search for nearby places using Google Places API"""
        if not self.gmaps_client:
            return []
        
        try:
            geocode_result = self.gmaps_client.geocode(location)
            if not geocode_result:
                return []
            
            lat_lng = geocode_result[0]['geometry']['location']
            
            places_result = self.gmaps_client.places_nearby(
                location=lat_lng,
                radius=radius,
                keyword=query,
                open_now=True
            )
            
            places = []
            for place in places_result.get('results', [])[:8]:
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
    
    def generate_concierge_response(self, user_query: str, location: str, persona: Dict, behavior_tracker: UserBehaviorTracker) -> str:
        """Generate personalized concierge response"""
        if not self.openai_client:
            return "I need API access to assist you properly."
        
        # Get user patterns
        preferred_time = behavior_tracker.get_preferred_time()
        skipped_types = [s["type"] for s in behavior_tracker.behavior_data["skipped_suggestions"]]
        chosen_types = [c["type"] for c in behavior_tracker.behavior_data["chosen_suggestions"]]
        
        # Build context
        context = f"""
        You are an AI Travel Concierge for {location} with a {persona['tone']} personality.
        
        User's demonstrated preferences:
        - Preferred time: {preferred_time}
        - Often skips: {', '.join(skipped_types[-3:]) if skipped_types else 'None detected'}
        - Usually chooses: {', '.join(chosen_types[-3:]) if chosen_types else 'None detected'}
        - Focus areas: {persona['suggestion_focus']}
        
        Current query: "{user_query}"
        
        Respond as a proactive travel concierge who:
        1. Addresses their specific needs with personality
        2. References their past preferences subtly
        3. Offers 2-3 specific, actionable suggestions
        4. Asks a follow-up question to continue helping
        5. Uses {persona['greeting_style']} tone
        
        Keep response to 2-3 paragraphs. Be conversational, not robotic.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": context}],
                max_tokens=400,
                temperature=0.8
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"I'm having trouble connecting right now, but I'm here to help you explore {location}!"

class AdManager:
    """Manages contextual advertisements"""
    
    def __init__(self):
        self.ad_counter = 0
        self.sample_ads = {
            "food": [
                {
                    "title": "🍕 Tony's Authentic Pizza",
                    "description": "Fresh ingredients, wood-fired oven. Order online for 20% off!",
                    "url": "https://example.com/tonys-pizza",
                    "cta": "Order Now",
                    "type": "restaurant"
                },
                {
                    "title": "🥘 DoorDash - Food Delivery",
                    "description": "Get your favorite local restaurants delivered. New users get $10 off!",
                    "url": "https://doordash.com",
                    "cta": "Get $10 Off",
                    "type": "service"
                }
            ],
            "activities": [
                {
                    "title": "🎟️ GetYourGuide Tours",
                    "description": "Skip-the-line tickets & unique experiences. Book now, cancel free!",
                    "url": "https://getyourguide.com",
                    "cta": "Book Tours",
                    "type": "service"
                }
            ],
            "general": [
                {
                    "title": "📱 Citymapper",
                    "description": "Navigate like a local with real-time transit info. Download the app!",
                    "url": "https://citymapper.com",
                    "cta": "Download App",
                    "type": "app"
                }
            ]
        }
    
    def get_contextual_ad(self, conversation_context: str, category: str = "general") -> Optional[Dict]:
        """Get a contextual ad based on conversation topic"""
        self.ad_counter += 1
        if self.ad_counter % 5 != 0:  # Show ad every 5th interaction
            return None
        
        context_lower = conversation_context.lower()
        
        if any(word in context_lower for word in ['restaurant', 'food', 'eat', 'coffee']):
            category = "food"
        elif any(word in context_lower for word in ['activity', 'tour', 'attraction']):
            category = "activities"
        
        ads = self.sample_ads.get(category, self.sample_ads["general"])
        return random.choice(ads) if ads else None
    
    def render_ad_card(self, ad: Dict) -> None:
        """Render an ad as a card"""
        if not ad:
            return
        
        with st.container():
            st.markdown(
                f'''
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 16px;
                    border-radius: 12px;
                    margin: 12px 0;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <div style="font-size: 11px; opacity: 0.8; margin-bottom: 4px;">Sponsored</div>
                            <div style="font-weight: bold; font-size: 16px; margin-bottom: 6px;">{ad["title"]}</div>
                            <div style="font-size: 13px; opacity: 0.9;">{ad["description"]}</div>
                        </div>
                        <div style="margin-left: 16px;">
                            <a href="{ad["url"]}" target="_blank" style="
                                background: rgba(255,255,255,0.2);
                                color: white;
                                padding: 8px 16px;
                                border-radius: 20px;
                                text-decoration: none;
                                font-size: 12px;
                                font-weight: bold;
                                border: 1px solid rgba(255,255,255,0.3);
                                transition: all 0.3s ease;
                            ">{ad["cta"]}</a>
                        </div>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )

def render_place_card(place: Dict) -> None:
    """Render a place as an attractive card"""
    rating_stars = "⭐" * int(float(place.get('rating', 0))) if place.get('rating') != 'N/A' else ""
    price_level = "💰" * (place.get('price_level', 1) if place.get('price_level', 1) != 'N/A' else 1)
    
    st.markdown(
        f'''
        <div style="
            background: white;
            border: 1px solid #e1e5e9;
            border-radius: 12px;
            padding: 16px;
            margin: 8px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        ">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 8px 0; color: #1f2937;">{place['name']}</h4>
                    <div style="color: #6b7280; font-size: 14px; margin-bottom: 8px;">{place.get('vicinity', '')}</div>
                    <div style="display: flex; gap: 12px; align-items: center;">
                        <span style="font-size: 14px;">{rating_stars} {place.get('rating', 'N/A')}</span>
                        <span style="font-size: 14px;">{price_level}</span>
                        <span style="font-size: 12px; color: {'#10b981' if place.get('opening_hours') else '#ef4444'};">
                            {'Open' if place.get('opening_hours') else 'Hours Unknown'}
                        </span>
                    </div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <a href="{place['maps_link']}" target="_blank" style="
                        background: #3b82f6;
                        color: white;
                        padding: 6px 12px;
                        border-radius: 6px;
                        text-decoration: none;
                        font-size: 12px;
                        text-align: center;
                    ">📍 View</a>
                    {f'<a href="{place.get("directions_link", "#")}" target="_blank" style="background: #10b981; color: white; padding: 6px 12px; border-radius: 6px; text-decoration: none; font-size: 12px; text-align: center;">🚶 Directions</a>' if place.get('directions_link') else ''}
                </div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )

def create_thread_sidebar(threads: List[ConversationThread]) -> Optional[str]:
    """Create thread management sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.header("💬 Conversation Threads")
    
    selected_thread = None
    
    if threads:
        # Active threads
        active_threads = [t for t in threads if t.status == "active"]
        if active_threads:
            st.sidebar.markdown("**Active Conversations**")
            for thread in active_threads[-5:]:  # Show last 5
                age = datetime.now() - thread.last_updated
                age_str = f"{age.seconds // 60}m" if age.seconds < 3600 else f"{age.seconds // 3600}h"
                
                if st.sidebar.button(
                    f"{thread.title[:20]}..." if len(thread.title) > 20 else thread.title,
                    key=f"thread_{thread.thread_id}",
                    help=f"Updated {age_str} ago"
                ):
                    selected_thread = thread.thread_id
        
        # Completed threads
        completed_threads = [t for t in threads if t.status == "completed"]
        if completed_threads:
            with st.sidebar.expander("📋 Completed Plans"):
                for thread in completed_threads[-3:]:
                    st.markdown(f"✅ {thread.title}")
    
    if st.sidebar.button("➕ New Conversation"):
        selected_thread = "new"
    
    return selected_thread

def main():
    st.title("🌟 AI Travel Concierge")
    st.markdown("*Your intelligent travel companion that learns your style and suggests perfect experiences*")
    
    # Initialize systems
    if 'behavior_tracker' not in st.session_state:
        st.session_state.behavior_tracker = UserBehaviorTracker()
    
    if 'persona_manager' not in st.session_state:
        st.session_state.persona_manager = PersonaManager(st.session_state.behavior_tracker)
    
    if 'ad_manager' not in st.session_state:
        st.session_state.ad_manager = AdManager()
    
    if 'threads' not in st.session_state:
        st.session_state.threads = []
    
    if 'current_thread_id' not in st.session_state:
        st.session_state.current_thread_id = None
    
    # Get current persona
    current_persona = st.session_state.persona_manager.get_current_persona()
    
    # Sidebar
    with st.sidebar:
        st.header("🔑 Configuration")
        
        # API Keys
        openai_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        gmaps_key = st.text_input("Google Maps API Key", type="password", placeholder="AIza...")
        
        guide = LocalGuide()
        guide.setup_apis(openai_key, gmaps_key)
        
        st.markdown("---")
        
        # Location
        location = st.text_input(
            "Current Location", 
            value=st.session_state.get('location', 'Baguio, Philippines'),
            placeholder="e.g., Paris, France"
        )
        st.session_state['location'] = location
        
        # Show current persona
        st.markdown(f"**Your Travel Style:** {st.session_state.behavior_tracker.get_dominant_persona().title()}")
        
        # Thread management
        selected_thread = create_thread_sidebar(st.session_state.threads)
        
        if selected_thread:
            st.session_state.current_thread_id = selected_thread
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Proactive greeting if no active conversation
        if not st.session_state.threads or st.session_state.current_thread_id == "new":
            st.markdown("### Welcome to Your Personal Travel Concierge! 🌟")
            
            # Generate proactive message
            proactive_msg = st.session_state.persona_manager.generate_proactive_message(location)
            st.info(proactive_msg)
            
            # Quick action buttons
            st.markdown("**Quick Start Options:**")
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                if st.button("🍽️ Food Adventure", use_container_width=True):
                    st.session_state.quick_action = "food"
            
            with col_b:
                if st.button("🎯 Local Experiences", use_container_width=True):
                    st.session_state.quick_action = "activities"
            
            with col_c:
                if st.button("📅 Full Day Plan", use_container_width=True):
                    st.session_state.quick_action = "itinerary"
        
        # Handle quick actions
        if "quick_action" in st.session_state:
            action = st.session_state.quick_action
            del st.session_state.quick_action
            
            # Create new thread for this action
            thread_id = f"thread_{len(st.session_state.threads)}_{int(time.time())}"
            thread_title = f"{action.title()} in {location}"
            new_thread = ConversationThread(thread_id, action, thread_title)
            
            with st.spinner(f"Creating your {action} recommendations..."):
                if action == "food":
                    places = guide.get_nearby_places(location, "restaurant", radius=2000)
                    response = f"Here are some amazing {action} spots I found for you in {location}!"
                elif action == "activities":
                    places = guide.get_nearby_places(location, "attraction", radius=2000)
                    response = f"Exciting {action} awaiting you in {location}!"
                else:
                    places = []
                    response = guide.generate_concierge_response(
                        f"Create a full day itinerary in {location}",
                        location,
                        current_persona,
                        st.session_state.behavior_tracker
                    )
                
                new_thread.add_message("assistant", response)
                
                # Add place cards if we have places
                if places:
                    st.markdown(f"### {response}")
                    for place in places[:4]:  # Show top 4
                        render_place_card(place)
                        new_thread.add_card("place", place)
                else:
                    st.markdown(response)
                
                # Add contextual ad
                ad = st.session_state.ad_manager.get_contextual_ad(response, action)
                if ad:
                    st.session_state.ad_manager.render_ad_card(ad)
                    new_thread.add_card("ad", ad)
            
            # Track this interaction
            st.session_state.behavior_tracker.track_interaction(
                f"Quick action: {action}", response, [action]
            )
            st.session_state.behavior_tracker.track_choice(action, True, f"Used quick action for {action}")
            
            st.session_state.threads.append(new_thread)
            st.session_state.current_thread_id = thread_id
            st.rerun()
        
        # Chat input
        if user_input := st.chat_input("What would you like to explore?"):
            # Find or create current thread
            current_thread = None
            if st.session_state.current_thread_id:
                current_thread = next(
                    (t for t in st.session_state.threads if t.thread_id == st.session_state.current_thread_id),
                    None
                )
            
            if not current_thread:
                # Create new thread
                thread_id = f"thread_{len(st.session_state.threads)}_{int(time.time())}"
                current_thread = ConversationThread(thread_id, "general", user_input[:30])
                st.session_state.threads.append(current_thread)
                st.session_state.current_thread_id = thread_id
            
            # Add user message
            current_thread.add_message("user", user_input)
            
            # Generate response
            with st.spinner("Thinking like your personal concierge..."):
                response = guide.generate_concierge_response(
                    user_input, location, current_persona, st.session_state.behavior_tracker
                )
                
                current_thread.add_message("assistant", response)
                
                # Track interaction
                st.session_state.behavior_tracker.track_interaction(user_input, response)
            
            st.rerun()
        
        # Display current thread messages
        if st.session_state.current_thread_id:
            current_thread = next(
                (t for t in st.session_state.threads if t.thread_id == st.session_state.current_thread_id),
                None
            )
            
            if current_thread:
                st.markdown(f"### {current_thread.title}")
                
                # Display messages and cards
                for item in sorted(
                    current_thread.messages + current_thread.cards,
                    key=lambda x: x.get('timestamp', datetime.now())
                ):
                    if 'role' in item:  # It's a message
                        with st.chat_message(item['role']):
                            st.markdown(item['content'])
                    elif item.get('type') == 'place':  # It's a place card
                        render_place_card(item['data'])
                    elif item.get('type') == 'ad':  # It's an ad card
                        st.session_state.ad_manager.render_ad_card(item['data'])
    
    with col2:
        # Insights panel
        st.markdown("### 🧠 Your Travel Profile")
        
        behavior = st.session_state.behavior_tracker.behavior_data
        persona_scores = behavior["persona_indicators"]
        
        if any(persona_scores.values()):
            st.markdown("**Detected Interests:**")
            for persona, score in sorted(persona_scores.items(), key=lambda x: x[1], reverse=True)[:3]:
                if score > 0:
                    bar_width = min(100, (score / max(persona_scores.values())) * 100)
                    st.markdown(f"{persona.title()}: {'●' * (score // 2)}")
        
        preferred_time = st.session_state.behavior_tracker.get_preferred_time()
        if preferred_time != "any":
            st.markdown(f"**Preferred Time:** {preferred_time.title()}")
        
        # Recent activity
        if behavior["chosen_suggestions"]:
            st.markdown("**Recent Choices:**")
            for choice in behavior["chosen_suggestions"][-3:]:
                st.markdown(f"✅ {choice['type'].title()}")
        
        # Learning insights
        skipped = len(behavior["skipped_suggestions"])
        chosen = len(behavior["chosen_suggestions"])
        if skipped + chosen > 0:
            st.markdown(f"**Learning Progress:** {chosen}/{chosen + skipped} preferences captured")

if __name__ == "__main__":
    main()
