"""
Gallery UI Component for PDF Generator
Provides a public gallery interface for sharing configurations
"""

import streamlit as st
from public_config_manager import PublicConfigGallery, ConfigThemes
from datetime import datetime

def render_gallery_ui(config_manager):
    """Render the configuration gallery UI"""
    
    gallery = PublicConfigGallery()
    
    st.header("🎨 Configuration Gallery")
    st.markdown("Browse and share PDF configurations with the community")
    
    # Create tabs for different sections
    tabs = st.tabs(["🔥 Featured", "🔍 Browse", "📤 Share", "🏷️ Themes"])
    
    # Featured/Themes Tab
    with tabs[0]:
        st.subheader("Featured Themes")
        themes = ConfigThemes.get_themes()
        
        for theme_name, theme_data in themes.items():
            with st.expander(f"{theme_name} - {theme_data['description']}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Show theme details
                    st.markdown(f"**Tags:** {', '.join(theme_data['tags'])}")
                    
                    # Show key settings
                    config = theme_data['config']
                    st.markdown(f"""
                    - **Format:** {config.get('page_format', 'Custom')}
                    - **Layout:** {config.get('columns', 2)} columns × {config.get('items_per_col', 20)} items
                    - **Guide Lines:** {'Yes' if config.get('guide_lines_enabled') else 'No'}
                    - **Orientation:** {'Landscape' if config.get('landscape') else 'Portrait'}
                    """)
                
                with col2:
                    if st.button(f"Load", key=f"load_theme_{theme_name}"):
                        st.session_state['loaded_config'] = config
                        st.success(f"Loaded theme: {theme_name}")
                        st.rerun()
                    
                    if st.button(f"Share", key=f"share_theme_{theme_name}"):
                        # Publish this theme to gallery
                        config_id, is_new = gallery.publish_config(
                            config,
                            name=theme_name,
                            description=theme_data['description'],
                            tags=theme_data['tags']
                        )
                        if config_id:
                            share_url = gallery.get_share_url(config_id)
                            st.info(f"Share URL: {share_url}")
                            st.code(config_id, language="text")
    
    # Browse Tab
    with tabs[1]:
        st.subheader("Browse Public Configurations")
        
        # Search and filter
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_query = st.text_input("🔍 Search", placeholder="Search by name or description...")
        
        with col2:
            # Get popular tags for filter
            popular_tags = gallery.get_popular_tags(10)
            tag_options = [tag for tag, _ in popular_tags] if popular_tags else []
            selected_tags = st.multiselect("Filter by tags", tag_options)
        
        with col3:
            sort_by = st.selectbox("Sort by", ["Recent", "Popular", "Name"])
        
        # Search results
        results = gallery.search_configs(
            query=search_query,
            tags=selected_tags,
            sort_by=sort_by.lower()
        )
        
        if results:
            st.markdown(f"Found {len(results)} configurations")
            
            for config_data in results[:20]:  # Limit to 20 results
                with st.expander(f"{config_data['name']} - {config_data.get('preview', {}).get('format', 'Unknown')}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**Description:** {config_data.get('description', 'No description')}")
                        st.markdown(f"**Tags:** {', '.join(config_data.get('tags', []))}")
                        st.markdown(f"**Created:** {config_data.get('created', 'Unknown')[:10]}")
                        st.markdown(f"**Views:** {config_data.get('views', 0)}")
                        
                        # Preview data
                        preview = config_data.get('preview', {})
                        st.markdown(f"""
                        - **Format:** {preview.get('format', 'Unknown')}
                        - **Layout:** {preview.get('columns', 2)} × {preview.get('items', 20)}
                        - **Guide Lines:** {'Yes' if preview.get('guide_lines') else 'No'}
                        - **Landscape:** {'Yes' if preview.get('landscape') else 'No'}
                        """)
                    
                    with col2:
                        if st.button("Load", key=f"load_{config_data['id']}"):
                            loaded_data = gallery.load_config(config_data['id'])
                            if loaded_data:
                                st.session_state['loaded_config'] = loaded_data['config']
                                st.success(f"Loaded: {config_data['name']}")
                                st.rerun()
                        
                        if st.button("Share", key=f"share_{config_data['id']}"):
                            share_url = gallery.get_share_url(config_data['id'])
                            st.code(config_data['id'], language="text")
                            st.caption(f"ID: {config_data['id']}")
        else:
            st.info("No configurations found. Be the first to share!")
    
    # Share Tab
    with tabs[2]:
        st.subheader("Share Your Configuration")
        st.markdown("Publish your current configuration to the public gallery")
        
        with st.form("share_config_form"):
            config_name = st.text_input(
                "Configuration Name",
                value=f"Config {datetime.now().strftime('%Y-%m-%d')}",
                help="Give your configuration a memorable name"
            )
            
            config_description = st.text_area(
                "Description",
                placeholder="Describe what makes this configuration special...",
                help="Help others understand when to use this configuration"
            )
            
            # Predefined tag suggestions
            suggested_tags = ["academic", "business", "creative", "minimal", "ereader", 
                            "notes", "tasks", "planning", "journal", "sketch"]
            
            selected_tags = st.multiselect(
                "Tags",
                suggested_tags,
                help="Add tags to help others find your configuration"
            )
            
            # Option to add custom tags
            custom_tags = st.text_input(
                "Custom tags (comma-separated)",
                placeholder="tag1, tag2, tag3"
            )
            
            share_submitted = st.form_submit_button("📤 Publish to Gallery")
            
            if share_submitted:
                # Collect current configuration
                current_config = st.session_state.get('current_config', {})
                if not current_config:
                    # Build config from session state
                    current_config = {
                        'page_format': st.session_state.get('page_format', 'A4 (210×297 mm)'),
                        'landscape': st.session_state.get('landscape', False),
                        'items_per_col': st.session_state.get('items_per_col', 20),
                        'columns': st.session_state.get('columns', 2),
                        'pages_of_todos': st.session_state.get('pages_of_todos', 30),
                        'detail_pages_per_todo': st.session_state.get('detail_pages_per_todo', 2),
                        'margin_left': st.session_state.get('margin_left', 8),
                        'margin_right': st.session_state.get('margin_right', 8),
                        'margin_top': st.session_state.get('margin_top', 18),
                        'margin_bottom': st.session_state.get('margin_bottom', 8),
                        'dot_spacing': st.session_state.get('dot_spacing', 5.0),
                        'dot_radius': st.session_state.get('dot_radius', 0.3),
                        'guide_lines_enabled': st.session_state.get('guide_lines_enabled', False),
                        'guide_h_color': st.session_state.get('guide_h_color', '#E0E0E0'),
                        'guide_v_color': st.session_state.get('guide_v_color', '#E0E0E0'),
                        'guide_h_width': st.session_state.get('guide_h_width', 0.5),
                        'guide_v_width': st.session_state.get('guide_v_width', 0.5),
                    }
                
                # Combine selected and custom tags
                all_tags = selected_tags
                if custom_tags:
                    all_tags.extend([tag.strip() for tag in custom_tags.split(',') if tag.strip()])
                
                # Publish to gallery
                config_id, is_new = gallery.publish_config(
                    current_config,
                    name=config_name,
                    description=config_description,
                    tags=all_tags
                )
                
                if config_id:
                    if is_new:
                        st.success(f"✅ Configuration published successfully!")
                    else:
                        st.info(f"ℹ️ This configuration already exists in the gallery")
                    
                    share_url = gallery.get_share_url(config_id)
                    st.markdown("### Share Link")
                    st.code(config_id, language="text")
                    st.caption(f"Share ID: **{config_id}**")
                    st.info(f"Others can load this configuration using the ID: {config_id}")
                else:
                    st.error("Failed to publish configuration")
    
    # Themes Tab
    with tabs[3]:
        st.subheader("Configuration Themes")
        st.markdown("Quick-start templates for common use cases")
        
        # Group themes by tag
        themes = ConfigThemes.get_themes()
        
        # Create columns for theme cards
        cols = st.columns(2)
        
        for i, (theme_name, theme_data) in enumerate(themes.items()):
            with cols[i % 2]:
                with st.container():
                    st.markdown(f"### {theme_name}")
                    st.caption(theme_data['description'])
                    
                    # Quick preview
                    config = theme_data['config']
                    st.markdown(f"""
                    📄 {config.get('page_format', 'Custom')[:10]}...  
                    📊 {config.get('columns', 2)}×{config.get('items_per_col', 20)} items  
                    {"📏 Guide lines" if config.get('guide_lines_enabled') else ""}
                    {"🔄 Landscape" if config.get('landscape') else ""}
                    """)
                    
                    if st.button(f"Use This Theme", key=f"use_{theme_name}"):
                        st.session_state['loaded_config'] = config
                        st.success(f"Loaded theme: {theme_name}")
                        st.rerun()
                    
                    st.markdown("---")

    return gallery