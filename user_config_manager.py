"""
User Configuration Manager for Public Deployment
Handles user-specific configurations using Streamlit session state and browser storage
"""

import streamlit as st
import json
import os
import uuid
from datetime import datetime
import hashlib
import base64

class UserConfigManager:
    """Manages user-specific configurations"""
    
    def __init__(self):
        # Initialize user session
        if 'user_session_id' not in st.session_state:
            # Create a unique session ID for this user
            st.session_state.user_session_id = str(uuid.uuid4())
            st.session_state.user_configs = {}
            st.session_state.current_config = {}
            st.session_state.config_history = []
        
        # Use a temp directory for session-based storage
        self.temp_dir = os.path.join(os.path.expanduser("~"), ".pdf_generator_configs")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
    
    def get_session_id(self):
        """Get current session ID"""
        return st.session_state.user_session_id
    
    def save_to_session(self, config, name="current"):
        """Save configuration to session state"""
        st.session_state.user_configs[name] = config.copy()
        st.session_state.current_config = config.copy()
        
        # Add to history
        if len(st.session_state.config_history) > 10:
            st.session_state.config_history.pop(0)
        
        st.session_state.config_history.append({
            'timestamp': datetime.now().isoformat(),
            'name': name,
            'config': config.copy()
        })
        
        return True
    
    def load_from_session(self, name="current"):
        """Load configuration from session state"""
        if name in st.session_state.user_configs:
            return st.session_state.user_configs[name]
        return st.session_state.current_config if st.session_state.current_config else {}
    
    def export_config(self, config):
        """Export configuration as base64 encoded JSON for sharing via URL"""
        config_json = json.dumps(config, separators=(',', ':'))
        config_bytes = config_json.encode('utf-8')
        config_b64 = base64.urlsafe_b64encode(config_bytes).decode('utf-8')
        return config_b64
    
    def import_config(self, config_b64):
        """Import configuration from base64 encoded string"""
        try:
            config_bytes = base64.urlsafe_b64decode(config_b64.encode('utf-8'))
            config_json = config_bytes.decode('utf-8')
            config = json.loads(config_json)
            return config
        except Exception as e:
            st.error(f"Failed to import configuration: {e}")
            return None
    
    def generate_share_url(self, config):
        """Generate a shareable URL with configuration"""
        config_b64 = self.export_config(config)
        # Get current URL (this is a simplified version)
        base_url = st.get_option('browser.serverAddress') or 'http://localhost:8501'
        return f"{base_url}?config={config_b64}"
    
    def load_from_url(self):
        """Load configuration from URL parameters"""
        try:
            # Try new API first (Streamlit >= 1.30)
            query_params = st.query_params
        except AttributeError:
            try:
                # Fall back to old API (Streamlit < 1.30)
                query_params = st.experimental_get_query_params()
            except:
                # No query params support
                return None
        
        if query_params and 'config' in query_params:
            # Handle both dict and object-like access
            if isinstance(query_params, dict):
                config_b64 = query_params.get('config', [None])[0] if isinstance(query_params.get('config'), list) else query_params.get('config')
            else:
                config_b64 = query_params['config']
            
            if config_b64:
                config = self.import_config(config_b64)
                if config:
                    self.save_to_session(config, "imported")
                    return config
        return None
    
    def save_to_browser_storage(self):
        """Save configuration to browser storage using JavaScript"""
        config = st.session_state.current_config
        config_json = json.dumps(config)
        
        # JavaScript to save to localStorage
        js_code = f"""
        <script>
        localStorage.setItem('pdf_generator_config', '{config_json}');
        </script>
        """
        
        st.components.v1.html(js_code, height=0)
    
    def create_preset(self, name, config):
        """Create a named preset configuration"""
        presets_file = os.path.join(self.temp_dir, "presets.json")
        
        try:
            if os.path.exists(presets_file):
                with open(presets_file, 'r') as f:
                    presets = json.load(f)
            else:
                presets = {}
            
            presets[name] = {
                'config': config,
                'created': datetime.now().isoformat(),
                'session_id': self.get_session_id()
            }
            
            with open(presets_file, 'w') as f:
                json.dump(presets, f, indent=2)
            
            return True
        except Exception as e:
            st.error(f"Failed to save preset: {e}")
            return False
    
    def load_presets(self):
        """Load available presets"""
        presets_file = os.path.join(self.temp_dir, "presets.json")
        
        try:
            if os.path.exists(presets_file):
                with open(presets_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception:
            return {}
    
    def get_default_configs(self):
        """Get default configuration presets"""
        return {
            "A4 Standard": {
                "page_format": "A4 (210×297 mm)",
                "items_per_col": 20,
                "columns": 2,
                "pages_of_todos": 30,
                "detail_pages_per_todo": 2,
                "margin_left": 8,
                "margin_right": 8,
                "margin_top": 18,
                "margin_bottom": 8,
                "dot_spacing": 5.0,
                "dot_radius": 0.3
            },
            "Boox Note Max": {
                "page_format": "Custom",
                "custom_method": "Pixels + PPI (for e-readers)",
                "pixels_width": 3200,
                "pixels_height": 2400,
                "ppi": 300,
                "custom_width": 270.93,
                "custom_height": 203.2,
                "items_per_col": 15,
                "columns": 2,
                "pages_of_todos": 25,
                "detail_pages_per_todo": 3,
                "margin_left": 10,
                "margin_right": 10,
                "margin_top": 20,
                "margin_bottom": 10,
                "dot_spacing": 5.5,
                "dot_radius": 0.35
            },
            "Letter Size": {
                "page_format": "Letter (216×279 mm)",
                "items_per_col": 18,
                "columns": 2,
                "pages_of_todos": 25,
                "detail_pages_per_todo": 2,
                "margin_left": 10,
                "margin_right": 10,
                "margin_top": 20,
                "margin_bottom": 10,
                "dot_spacing": 5.0,
                "dot_radius": 0.3
            }
        }

def init_user_config():
    """Initialize user configuration system"""
    if 'config_manager' not in st.session_state:
        st.session_state.config_manager = UserConfigManager()
    return st.session_state.config_manager