"""
Configuration Collector - Ensures ALL settings are saved
"""

import streamlit as st

def collect_complete_config():
    """Collect ALL configuration parameters from session state"""
    return {
        # Page Settings
        'page_format': st.session_state.get('page_format', 'A4 (210×297 mm)'),
        'landscape': st.session_state.get('landscape', False),
        'custom_method': st.session_state.get('custom_method', 'Direct measurements (mm)'),
        'custom_width': st.session_state.get('custom_width', 210),
        'custom_height': st.session_state.get('custom_height', 297),
        'pixels_width': st.session_state.get('pixels_width', 1920),
        'pixels_height': st.session_state.get('pixels_height', 2560),
        'ppi': st.session_state.get('ppi', 300),
        
        # Auto Settings
        'auto_margins': st.session_state.get('auto_margins', False),
        'auto_items': st.session_state.get('auto_items', False),
        'auto_dot_spacing': st.session_state.get('auto_dot_spacing', True),
        
        # Layout
        'items_per_col': st.session_state.get('items_per_col', 20),
        'columns': st.session_state.get('columns', 2),
        'pages_of_todos': st.session_state.get('pages_of_todos', 30),
        'detail_pages_per_todo': st.session_state.get('detail_pages_per_todo', 2),
        
        # Margins
        'margin_left': st.session_state.get('margin_left', 8),
        'margin_right': st.session_state.get('margin_right', 8),
        'margin_top': st.session_state.get('margin_top', 18),
        'margin_bottom': st.session_state.get('margin_bottom', 8),
        
        # Dots
        'dot_spacing': st.session_state.get('dot_spacing', 5.0),
        'dot_radius': st.session_state.get('dot_radius', 0.3),
        'dot_color_intensity': st.session_state.get('dot_color_intensity', 0.7),
        
        # Font Sizes
        'font_size_header': st.session_state.get('font_size_header', 14),
        'font_size_icon': st.session_state.get('font_size_icon', 13),
        'font_size_detail': st.session_state.get('font_size_detail', 12),
        'num_size': st.session_state.get('num_size', 7),
        
        # Colors
        'color_line': st.session_state.get('color_line', '#696969'),
        'color_text': st.session_state.get('color_text', '#454545'),
        'num_color_hex': st.session_state.get('num_color_hex', '#808080'),  # Todo number color!
        
        # Number Placement
        'num_placement': st.session_state.get('num_placement', 'Outside (left/right)'),
        'num_offset_x_left': st.session_state.get('num_offset_x_left', 0),
        'num_offset_x_right': st.session_state.get('num_offset_x_right', 0),
        'num_offset_y': st.session_state.get('num_offset_y', -1),
        
        # Guide Lines
        'guide_lines_enabled': st.session_state.get('guide_lines_enabled', False),
        'guide_h_color': st.session_state.get('guide_h_color', '#E0E0E0'),
        'guide_v_color': st.session_state.get('guide_v_color', '#E0E0E0'),
        'guide_h_width': st.session_state.get('guide_h_width', 0.5),
        'guide_v_width': st.session_state.get('guide_v_width', 0.5),
        
        # Title Page Settings
        'title_page_enabled': st.session_state.get('title_page_enabled', False),
        'title_text': st.session_state.get('title_text', 'My Todo List'),
        'title_font': st.session_state.get('title_font', 'Helvetica-Bold'),
        'title_size': st.session_state.get('title_size', 48),
        'title_color': st.session_state.get('title_color', '#000000'),
        'title_description': st.session_state.get('title_description', ''),
        'desc_font': st.session_state.get('desc_font', 'Helvetica'),
        'desc_size': st.session_state.get('desc_size', 18),
        'desc_color': st.session_state.get('desc_color', '#666666'),
        'title_alignment': st.session_state.get('title_alignment', 'Center'),
        'title_position': st.session_state.get('title_position', 'Golden Ratio'),
        'title_add_date': st.session_state.get('title_add_date', False),
        'title_decoration': st.session_state.get('title_decoration', 'Simple Line'),
        
        # Output
        'output_filename': st.session_state.get('output_filename', 'todo-a4-custom.pdf'),
        'pdf_quality_index': st.session_state.get('pdf_quality_index', 1),
    }

def get_config_summary(config):
    """Generate a summary of key config settings for display"""
    return {
        'format': config.get('page_format', 'Unknown'),
        'layout': f"{config.get('columns', 2)}×{config.get('items_per_col', 20)}",
        'pages': config.get('pages_of_todos', 30),
        'landscape': config.get('landscape', False),
        'guide_lines': config.get('guide_lines_enabled', False),
        'number_color': config.get('num_color_hex', '#808080'),
        'number_placement': config.get('num_placement', 'Outside'),
    }