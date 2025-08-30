"""
Public Configuration Gallery Manager
Handles public sharing of configs without user collisions
"""

import streamlit as st
import json
import os
import hashlib
import base64
from datetime import datetime
import glob

class PublicConfigGallery:
    """Manages a public gallery of configurations"""
    
    def __init__(self, gallery_dir="public_configs"):
        self.gallery_dir = gallery_dir
        self.index_file = os.path.join(gallery_dir, "gallery_index.json")
        
        # Create directory if it doesn't exist
        if not os.path.exists(gallery_dir):
            os.makedirs(gallery_dir)
        
        # Initialize or load index
        self.load_index()
    
    def load_index(self):
        """Load the gallery index"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            except:
                self.index = {"configs": {}, "tags": {}, "stats": {"total": 0, "views": {}}}
        else:
            self.index = {"configs": {}, "tags": {}, "stats": {"total": 0, "views": {}}}
    
    def save_index(self):
        """Save the gallery index"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            st.error(f"Failed to save gallery index: {e}")
    
    def generate_config_id(self, config):
        """Generate a unique hash ID for a configuration"""
        # Create hash from config content
        config_str = json.dumps(config, sort_keys=True)
        hash_obj = hashlib.md5(config_str.encode())
        return hash_obj.hexdigest()[:8]  # Use first 8 chars for shorter IDs
    
    def publish_config(self, config, name="Untitled", description="", tags=None):
        """Publish a configuration to the public gallery"""
        config_id = self.generate_config_id(config)
        
        # Check if already exists
        if config_id in self.index["configs"]:
            return config_id, False  # Already exists, return existing ID
        
        # Save config file
        config_file = os.path.join(self.gallery_dir, f"{config_id}.json")
        
        # Add metadata
        config_data = {
            "id": config_id,
            "name": name,
            "description": description,
            "tags": tags or [],
            "config": config,
            "created": datetime.now().isoformat(),
            "views": 0,
            "likes": 0
        }
        
        try:
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Update index
            self.index["configs"][config_id] = {
                "name": name,
                "description": description,
                "tags": tags or [],
                "created": config_data["created"],
                "views": 0,
                "likes": 0,
                "preview": self.generate_preview_data(config)
            }
            
            # Update tags index
            for tag in (tags or []):
                if tag not in self.index["tags"]:
                    self.index["tags"][tag] = []
                self.index["tags"][tag].append(config_id)
            
            self.index["stats"]["total"] += 1
            self.save_index()
            
            return config_id, True  # New config created
            
        except Exception as e:
            st.error(f"Failed to publish configuration: {e}")
            return None, False
    
    def load_config(self, config_id):
        """Load a configuration from the gallery"""
        config_file = os.path.join(self.gallery_dir, f"{config_id}.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                # Update view count
                if config_id in self.index["configs"]:
                    self.index["configs"][config_id]["views"] += 1
                    self.save_index()
                
                return data
            except Exception as e:
                st.error(f"Failed to load configuration: {e}")
        return None
    
    def search_configs(self, query="", tags=None, sort_by="recent"):
        """Search configurations in the gallery"""
        results = []
        
        for config_id, meta in self.index["configs"].items():
            # Filter by query (in name or description)
            if query:
                query_lower = query.lower()
                if (query_lower not in meta["name"].lower() and 
                    query_lower not in meta.get("description", "").lower()):
                    continue
            
            # Filter by tags
            if tags:
                if not any(tag in meta["tags"] for tag in tags):
                    continue
            
            results.append({
                "id": config_id,
                **meta
            })
        
        # Sort results
        if sort_by == "recent":
            results.sort(key=lambda x: x["created"], reverse=True)
        elif sort_by == "popular":
            results.sort(key=lambda x: x["views"], reverse=True)
        elif sort_by == "name":
            results.sort(key=lambda x: x["name"])
        
        return results
    
    def get_popular_tags(self, limit=10):
        """Get most popular tags"""
        tag_counts = [(tag, len(configs)) for tag, configs in self.index["tags"].items()]
        tag_counts.sort(key=lambda x: x[1], reverse=True)
        return tag_counts[:limit]
    
    def generate_preview_data(self, config):
        """Generate preview data for quick display"""
        return {
            "format": config.get("page_format", "Unknown"),
            "items": config.get("items_per_col", 0),
            "columns": config.get("columns", 0),
            "guide_lines": config.get("guide_lines_enabled", False),
            "landscape": config.get("landscape", False)
        }
    
    def get_share_url(self, config_id):
        """Generate a share URL for a config"""
        base_url = st.get_option('browser.serverAddress') or 'http://localhost:8501'
        return f"{base_url}?load={config_id}"
    
    def cleanup_old_configs(self, days=30):
        """Remove configs older than specified days (optional)"""
        # This could be implemented to clean up old, unused configs
        pass

class ConfigThemes:
    """Predefined configuration themes"""
    
    @staticmethod
    def get_themes():
        return {
            "📚 Academic": {
                "description": "Classic academic note-taking layout",
                "tags": ["academic", "notes", "study"],
                "config": {
                    "page_format": "A4 (210×297 mm)",
                    "items_per_col": 25,
                    "columns": 2,
                    "margin_left": 10,
                    "margin_right": 10,
                    "margin_top": 15,
                    "margin_bottom": 10,
                    "dot_spacing": 5.0,
                    "guide_lines_enabled": True,
                    "guide_h_color": "#E0E0E0",
                    "guide_v_color": "#E0E0E0"
                }
            },
            "💼 Business": {
                "description": "Professional meeting notes and tasks",
                "tags": ["business", "professional", "meetings"],
                "config": {
                    "page_format": "Letter (216×279 mm)",
                    "items_per_col": 20,
                    "columns": 2,
                    "margin_left": 12,
                    "margin_right": 12,
                    "margin_top": 20,
                    "margin_bottom": 15,
                    "dot_spacing": 5.5,
                    "guide_lines_enabled": False,
                    "num_placement": "Inside (left)"
                }
            },
            "📱 E-Reader": {
                "description": "Optimized for e-ink displays",
                "tags": ["ereader", "digital", "boox", "remarkable"],
                "config": {
                    "page_format": "Custom",
                    "custom_method": "Pixels + PPI (for e-readers)",
                    "pixels_width": 1872,
                    "pixels_height": 1404,
                    "ppi": 227,
                    "items_per_col": 15,
                    "columns": 2,
                    "margin_left": 8,
                    "margin_right": 8,
                    "margin_top": 15,
                    "margin_bottom": 8,
                    "dot_spacing": 6.0,
                    "guide_lines_enabled": True
                }
            },
            "🎨 Creative": {
                "description": "Mixed layout for sketches and notes",
                "tags": ["creative", "art", "sketch"],
                "config": {
                    "page_format": "A4 (210×297 mm)",
                    "landscape": True,
                    "items_per_col": 10,
                    "columns": 3,
                    "detail_pages_per_todo": 4,
                    "margin_left": 15,
                    "margin_right": 15,
                    "margin_top": 20,
                    "margin_bottom": 15,
                    "dot_spacing": 7.0,
                    "dot_radius": 0.4,
                    "guide_lines_enabled": False
                }
            },
            "📝 Minimal": {
                "description": "Clean, distraction-free layout",
                "tags": ["minimal", "clean", "simple"],
                "config": {
                    "page_format": "A5 (148×210 mm)",
                    "items_per_col": 15,
                    "columns": 1,
                    "margin_left": 10,
                    "margin_right": 10,
                    "margin_top": 15,
                    "margin_bottom": 10,
                    "dot_spacing": 5.0,
                    "dot_radius": 0.2,
                    "num_placement": "Hidden",
                    "guide_lines_enabled": False
                }
            }
        }