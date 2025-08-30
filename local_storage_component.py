"""
Local Storage Component for Streamlit
Provides browser localStorage access for user-specific configurations
"""

import streamlit as st
import streamlit.components.v1 as components
import json

def init_local_storage():
    """Initialize localStorage component"""
    
    # JavaScript code to handle localStorage
    local_storage_js = """
    <script>
    // Local Storage Manager for Streamlit
    const LocalStorageManager = {
        // Get item from localStorage
        get: function(key) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : null;
            } catch(e) {
                console.error('Error reading from localStorage:', e);
                return null;
            }
        },
        
        // Set item in localStorage
        set: function(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch(e) {
                console.error('Error writing to localStorage:', e);
                return false;
            }
        },
        
        // Remove item from localStorage
        remove: function(key) {
            try {
                localStorage.removeItem(key);
                return true;
            } catch(e) {
                console.error('Error removing from localStorage:', e);
                return false;
            }
        },
        
        // Clear all items
        clear: function() {
            try {
                localStorage.clear();
                return true;
            } catch(e) {
                console.error('Error clearing localStorage:', e);
                return false;
            }
        },
        
        // Get all keys
        getAllKeys: function() {
            try {
                return Object.keys(localStorage);
            } catch(e) {
                console.error('Error getting localStorage keys:', e);
                return [];
            }
        }
    };
    
    // Make it available globally
    window.LocalStorageManager = LocalStorageManager;
    
    // Send initial data to Streamlit
    window.parent.postMessage({
        type: 'localStorage_ready',
        data: {
            available: typeof(Storage) !== "undefined",
            keys: LocalStorageManager.getAllKeys()
        }
    }, '*');
    </script>
    """
    
    components.html(local_storage_js, height=0)

def get_local_storage(key, default=None):
    """Get value from localStorage"""
    
    js_code = f"""
    <script>
    (function() {{
        const value = window.LocalStorageManager ? window.LocalStorageManager.get('{key}') : null;
        window.parent.postMessage({{
            type: 'localStorage_get',
            key: '{key}',
            value: value
        }}, '*');
    }})();
    </script>
    """
    
    result = components.html(js_code, height=0)
    return result if result else default

def set_local_storage(key, value):
    """Set value in localStorage"""
    
    value_json = json.dumps(value)
    js_code = f"""
    <script>
    (function() {{
        const success = window.LocalStorageManager ? window.LocalStorageManager.set('{key}', {value_json}) : false;
        window.parent.postMessage({{
            type: 'localStorage_set',
            key: '{key}',
            success: success
        }}, '*');
    }})();
    </script>
    """
    
    components.html(js_code, height=0)

def remove_local_storage(key):
    """Remove value from localStorage"""
    
    js_code = f"""
    <script>
    (function() {{
        const success = window.LocalStorageManager ? window.LocalStorageManager.remove('{key}') : false;
        window.parent.postMessage({{
            type: 'localStorage_remove',
            key: '{key}',
            success: success
        }}, '*');
    }})();
    </script>
    """
    
    components.html(js_code, height=0)

def clear_local_storage():
    """Clear all localStorage"""
    
    js_code = """
    <script>
    (function() {
        const success = window.LocalStorageManager ? window.LocalStorageManager.clear() : false;
        window.parent.postMessage({
            type: 'localStorage_clear',
            success: success
        }, '*');
    })();
    </script>
    """
    
    components.html(js_code, height=0)

class LocalStorageManager:
    """Manager class for localStorage operations"""
    
    def __init__(self, prefix="pdf_gen_"):
        self.prefix = prefix
        
    def get_user_config(self, user_id=None):
        """Get user-specific configuration"""
        if not user_id:
            # Use session ID as user identifier
            if 'user_id' not in st.session_state:
                import uuid
                st.session_state.user_id = str(uuid.uuid4())
            user_id = st.session_state.user_id
            
        key = f"{self.prefix}{user_id}_config"
        return get_local_storage(key, {})
    
    def save_user_config(self, config, user_id=None):
        """Save user-specific configuration"""
        if not user_id:
            if 'user_id' not in st.session_state:
                import uuid
                st.session_state.user_id = str(uuid.uuid4())
            user_id = st.session_state.user_id
            
        key = f"{self.prefix}{user_id}_config"
        set_local_storage(key, config)
        
    def list_user_configs(self, user_id=None):
        """List all saved configurations for a user"""
        if not user_id:
            if 'user_id' not in st.session_state:
                import uuid
                st.session_state.user_id = str(uuid.uuid4())
            user_id = st.session_state.user_id
            
        prefix = f"{self.prefix}{user_id}_saved_"
        # This would need to be implemented with getAllKeys
        return []
    
    def export_config(self, config):
        """Export configuration as JSON string for sharing"""
        return json.dumps(config, indent=2)
    
    def import_config(self, config_json):
        """Import configuration from JSON string"""
        try:
            return json.loads(config_json)
        except json.JSONDecodeError:
            return None