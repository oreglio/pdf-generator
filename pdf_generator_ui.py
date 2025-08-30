#!/usr/bin/env python3
"""
Web Interface for A4 PDF Generator
Using Streamlit for easy configuration
"""

import streamlit as st
import subprocess
import sys
import os
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, A3, letter, legal, B4, B5
# Define tabloid size (11x17 inches)
tabloid = (11*72, 17*72)  # 72 points per inch
from PIL import Image, ImageDraw
import io
import json
from datetime import datetime

# Import the generator module
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import user configuration manager
from user_config_manager import init_user_config
from gallery_ui import render_gallery_ui
from config_collector import collect_complete_config

st.set_page_config(
    page_title="A4 PDF Todo Generator",
    page_icon="📄",
    layout="wide"  # Changed to wide for side-by-side layout
)

# Debug: Verify Python environment and reportlab
if st.checkbox("🔧 Show Debug Info", value=False):
    st.code(f"Python: {sys.executable}\nVersion: {sys.version}", language="text")
    try:
        import reportlab
        st.success(f"✅ ReportLab {reportlab.Version} is installed")
    except ImportError as e:
        st.error(f"❌ ReportLab import error: {e}")

st.title("📄 A4 PDF Todo Generator")
st.markdown("Configure and generate your custom PDF with todo lists and detail pages")

# Initialize user configuration manager
config_manager = init_user_config()

# Main navigation tabs
main_tabs = st.tabs(["⚙️ Generator", "🎨 Gallery", "ℹ️ About"])

with main_tabs[0]:
    st.markdown("### Configure and Generate Your PDF")
    
    # Check if there's a configuration in the URL
    url_config = config_manager.load_from_url()
    if url_config:
        st.success("✅ Configuration loaded from shared link!")
        st.session_state.loaded_config = url_config

# Configuration management
def save_config(config_dict, name="default"):
    """Save configuration to a JSON file"""
    config_dir = "saved_configs"
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    filename = os.path.join(config_dir, f"{name}.json")
    with open(filename, 'w') as f:
        json.dump(config_dict, f, indent=2)
    return filename

def load_config(name="default"):
    """Load configuration from a JSON file"""
    config_dir = "saved_configs"
    filename = os.path.join(config_dir, f"{name}.json")
    
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return None

def list_saved_configs():
    """List all saved configurations"""
    config_dir = "saved_configs"
    if not os.path.exists(config_dir):
        return []
    
    configs = []
    for file in os.listdir(config_dir):
        if file.endswith('.json'):
            configs.append(file[:-5])  # Remove .json extension
    return configs

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple (0-1 range for ReportLab)"""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))
    return r, g, b

def generate_title_page(c, config_dict, PAGE_WIDTH, PAGE_HEIGHT):
    """Generate a beautiful title page for the PDF"""
    from datetime import datetime
    
    # White background
    c.setFillColor(Color(1, 1, 1))
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    
    # Calculate vertical position based on selected option
    title_position = config_dict.get('title_position', 'Golden Ratio')
    if title_position == 'Top':
        title_y = PAGE_HEIGHT - (PAGE_HEIGHT * 0.2)  # 20% from top
    elif title_position == 'Center':
        title_y = PAGE_HEIGHT * 0.5  # 50% (center)
    elif title_position == 'Golden Ratio':
        title_y = PAGE_HEIGHT * 0.618  # Golden ratio (most aesthetic)
    
    # Get alignment
    alignment = config_dict.get('title_alignment', 'Center')
    
    # Draw title
    title_text = config_dict.get('title_text', 'My Todo List')
    title_font = config_dict.get('title_font', 'Helvetica-Bold')
    title_size = config_dict.get('title_size', 48)
    title_color = config_dict.get('title_color', '#000000')
    
    c.setFont(title_font, title_size)
    c.setFillColor(HexColor(title_color))
    
    # Calculate text position based on alignment
    title_width = c.stringWidth(title_text, title_font, title_size)
    if alignment == 'Center':
        title_x = (PAGE_WIDTH - title_width) / 2
    elif alignment == 'Left':
        title_x = config_dict.get('margin_left', 20) * mm
    else:  # Right
        title_x = PAGE_WIDTH - config_dict.get('margin_right', 20) * mm - title_width
    
    c.drawString(title_x, title_y, title_text)
    
    # Draw description if provided
    description = config_dict.get('title_description', '').strip()
    if description:
        desc_font = config_dict.get('desc_font', 'Helvetica')
        desc_size = config_dict.get('desc_size', 18)
        desc_color = config_dict.get('desc_color', '#666666')
        
        c.setFont(desc_font, desc_size)
        c.setFillColor(HexColor(desc_color))
        
        # Split description into lines if it's too long
        lines = description.split('\n')
        desc_y = title_y - title_size - 20  # 20 points below title
        
        for line in lines:
            line = line.strip()
            if line:
                desc_width = c.stringWidth(line, desc_font, desc_size)
                if alignment == 'Center':
                    desc_x = (PAGE_WIDTH - desc_width) / 2
                elif alignment == 'Left':
                    desc_x = config_dict.get('margin_left', 20) * mm
                else:  # Right
                    desc_x = PAGE_WIDTH - config_dict.get('margin_right', 20) * mm - desc_width
                
                c.drawString(desc_x, desc_y, line)
                desc_y -= desc_size + 8  # Move down for next line
    else:
        desc_y = title_y - title_size - 20
    
    # Add date if enabled
    if config_dict.get('title_add_date', False):
        date_text = datetime.now().strftime('%B %d, %Y')
        date_font = 'Helvetica'
        date_size = 14
        
        c.setFont(date_font, date_size)
        c.setFillColor(HexColor('#999999'))
        
        date_width = c.stringWidth(date_text, date_font, date_size)
        date_y = desc_y - 30
        
        if alignment == 'Center':
            date_x = (PAGE_WIDTH - date_width) / 2
        elif alignment == 'Left':
            date_x = config_dict.get('margin_left', 20) * mm
        else:  # Right
            date_x = PAGE_WIDTH - config_dict.get('margin_right', 20) * mm - date_width
        
        c.drawString(date_x, date_y, date_text)
        decoration_y = date_y - 30
    else:
        decoration_y = desc_y - 30
    
    # Add decoration if selected
    decoration = config_dict.get('title_decoration', 'Simple Line')
    if decoration != 'None':
        c.setStrokeColor(HexColor('#CCCCCC'))
        
        if decoration == 'Simple Line':
            c.setLineWidth(1)
            line_width = min(200, PAGE_WIDTH * 0.3)
            line_x = (PAGE_WIDTH - line_width) / 2
            c.line(line_x, decoration_y, line_x + line_width, decoration_y)
            
        elif decoration == 'Double Line':
            c.setLineWidth(0.5)
            line_width = min(200, PAGE_WIDTH * 0.3)
            line_x = (PAGE_WIDTH - line_width) / 2
            c.line(line_x, decoration_y, line_x + line_width, decoration_y)
            c.line(line_x, decoration_y - 4, line_x + line_width, decoration_y - 4)
            
        elif decoration == 'Dots':
            c.setFillColor(HexColor('#CCCCCC'))
            dot_count = 5
            dot_spacing = 20
            total_width = (dot_count - 1) * dot_spacing
            start_x = (PAGE_WIDTH - total_width) / 2
            for i in range(dot_count):
                c.circle(start_x + i * dot_spacing, decoration_y, 2, fill=1, stroke=0)
                
        elif decoration == 'Frame':
            c.setLineWidth(2)
            margin = 30 * mm
            c.rect(margin, margin, PAGE_WIDTH - 2 * margin, PAGE_HEIGHT - 2 * margin, fill=0, stroke=1)

def generate_pdf_preview(config_dict, page_size=A4):
    """Generate a preview of the first todo page as PDF"""
    PAGE_WIDTH, PAGE_HEIGHT = page_size
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    
    # Generate title page if enabled
    if config_dict.get('title_page_enabled', False):
        generate_title_page(c, config_dict, PAGE_WIDTH, PAGE_HEIGHT)
        c.showPage()
    
    # Draw the actual PDF preview content
    # White background
    c.setFillColor(Color(1, 1, 1))
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    
    # Draw the preview page - calculate usable area
    usable_width = PAGE_WIDTH - config_dict['margin_left'] * mm - config_dict['margin_right'] * mm
    col_width = usable_width / config_dict['columns']
    # Adjust inner height to use full available space
    header_space = 30  # Space for header
    inner_height = PAGE_HEIGHT - config_dict['margin_top'] * mm - config_dict['margin_bottom'] * mm - header_space
    # Calculate line gap to distribute items evenly across available height
    line_gap = inner_height / config_dict.get('items_per_col', 20)
    
    # Draw margins as light gray lines (optional, for preview)
    c.setStrokeColor(Color(0.9, 0.9, 0.9))
    c.setLineWidth(0.5)
    c.setDash([2, 2])  # Dashed line
    # Left margin
    c.line(config_dict['margin_left'] * mm, 0, config_dict['margin_left'] * mm, PAGE_HEIGHT)
    # Right margin  
    c.line(PAGE_WIDTH - config_dict['margin_right'] * mm, 0, PAGE_WIDTH - config_dict['margin_right'] * mm, PAGE_HEIGHT)
    # Top margin
    c.line(0, PAGE_HEIGHT - config_dict['margin_top'] * mm, PAGE_WIDTH, PAGE_HEIGHT - config_dict['margin_top'] * mm)
    # Bottom margin
    c.line(0, config_dict['margin_bottom'] * mm, PAGE_WIDTH, config_dict['margin_bottom'] * mm)
    c.setDash([])  # Reset to solid line
    
    # Header (showing TODO page, not index)
    c.setFont("Helvetica-Bold", config_dict['font_size_header'])
    c.setFillColor(HexColor(config_dict['color_text']))
    # Show "Page 1" like in actual todo pages (this would be page 2 in the real PDF)
    page_text = "Page 1"
    text_width = c.stringWidth(page_text, "Helvetica-Bold", config_dict['font_size_header'])
    header_x = PAGE_WIDTH - config_dict['margin_right'] * mm - text_width
    header_y = PAGE_HEIGHT - config_dict['margin_top'] * mm + 15
    c.drawString(header_x, header_y, page_text)
    
    # Draw ALL todo lines based on items_per_col setting
    c.setFont("Helvetica", 10)
    top_y = PAGE_HEIGHT - config_dict['margin_top'] * mm - 30
    
    # Use the actual items_per_col from config
    items_to_show = config_dict.get('items_per_col', 20)
    
    for col in range(config_dict['columns']):
        x0 = config_dict['margin_left'] * mm + col * col_width
        y = top_y
        
        for i in range(items_to_show):
            todo_num = col * config_dict['items_per_col'] + i + 1
            
            # Draw number if not hidden
            if config_dict['num_placement'] != "Hidden":
                c.setFont("Helvetica", config_dict['num_size'])
                # Convert hex color to RGB for todo numbers - set it for each number
                if 'num_color_hex' in config_dict:
                    r, g, b = hex_to_rgb(config_dict['num_color_hex'])
                    c.setFillColor(Color(r, g, b))
                else:
                    # Fallback to gray value for backward compatibility
                    gray = config_dict.get('num_color', 0.85)
                    c.setFillColor(Color(gray, gray, gray))
                
                num_text = str(todo_num)
                num_width = c.stringWidth(num_text, "Helvetica", config_dict['num_size'])
                
                if config_dict['num_placement'] == "Outside (left/right)":
                    if col == 0:
                        num_x = config_dict['margin_left'] * mm - 3 * mm - num_width + config_dict['num_offset_x_left'] * mm
                    else:
                        num_x = PAGE_WIDTH - config_dict['margin_right'] * mm + 1 * mm + config_dict['num_offset_x_right'] * mm
                elif config_dict['num_placement'] == "Inside (left)":
                    offset = config_dict['num_offset_x_left'] if col == 0 else config_dict['num_offset_x_right']
                    num_x = x0 + 2 * mm + offset * mm
                elif config_dict['num_placement'] == "Inside (right)":
                    offset = config_dict['num_offset_x_left'] if col == 0 else config_dict['num_offset_x_right']
                    num_x = x0 + col_width - 20 * mm - num_width + offset * mm
                
                num_y = y + config_dict['num_offset_y'] * mm
                c.drawString(num_x, num_y, num_text)
            
            # Draw todo line
            c.setStrokeColor(HexColor(config_dict['color_line']))
            c.setLineWidth(0.5)
            line_right = x0 + col_width - 16 * mm
            c.line(x0, y, line_right, y)
            
            # Draw ">" icon
            c.setFont("Helvetica-Bold", config_dict['font_size_icon'])
            c.setFillColor(HexColor('#555555'))
            icon_x = x0 + col_width - 14 * mm + 5 * mm - 1.6 * mm - 2
            icon_y = y - 2 * mm + 6
            c.drawString(icon_x, icon_y, ">")
            
            y -= line_gap
    
    # Draw guide lines if enabled
    if config_dict.get('guide_lines_enabled', False):
        # Horizontal line boundaries - align with todo number positions
        if config_dict['num_placement'] == "Outside (left/right)":
            # When numbers are outside, align symmetrically
            h_left_boundary = config_dict['margin_left'] * mm - 3 * mm - 8 * mm + config_dict['num_offset_x_left'] * mm  # 2mm before left numbers
            h_right_boundary = PAGE_WIDTH - config_dict['margin_right'] * mm + 1 * mm + 8 * mm + config_dict['num_offset_x_right'] * mm  # 2mm after right numbers
        elif config_dict['num_placement'] == "Inside (left)":
            # Numbers are inside on the left
            h_left_boundary = config_dict['margin_left'] * mm + 2 * mm + config_dict['num_offset_x_left'] * mm
            h_right_boundary = PAGE_WIDTH - config_dict['margin_right'] * mm + 2 * mm
        elif config_dict['num_placement'] == "Inside (right)":
            # Numbers are inside on the right
            h_left_boundary = config_dict['margin_left'] * mm - 2 * mm
            h_right_boundary = PAGE_WIDTH - config_dict['margin_right'] * mm - 20 * mm + config_dict['num_offset_x_right'] * mm
        else:  # Hidden
            # No numbers, use small margins
            h_left_boundary = config_dict['margin_left'] * mm - 2 * mm
            h_right_boundary = PAGE_WIDTH - config_dict['margin_right'] * mm + 2 * mm
        
        # Calculate position between todo lines (middle of the items)
        middle_item = items_to_show // 2
        middle_y = top_y - (middle_item * line_gap) - (line_gap / 2)  # Position between two middle lines
        
        # Horizontal line (between middle todo lines)
        c.setStrokeColor(HexColor(config_dict.get('guide_h_color', '#E0E0E0')))
        c.setLineWidth(config_dict.get('guide_h_width', 0.5) * mm)
        c.line(h_left_boundary, middle_y, h_right_boundary, middle_y)
        
        # Vertical line (centered between columns)
        c.setStrokeColor(HexColor(config_dict.get('guide_v_color', '#E0E0E0')))
        c.setLineWidth(config_dict.get('guide_v_width', 0.5) * mm)
        
        # Center the vertical line between the two columns
        # The ">" icon ends roughly at: margin_left + col_width - 7*mm
        # Column 2 starts at: margin_left + col_width
        col1_visual_end = config_dict['margin_left'] * mm + col_width - 7 * mm  # After the ">" icon
        col2_line_start = config_dict['margin_left'] * mm + col_width
        # Place the line in the middle of this visual gap
        mid_x = (col1_visual_end + col2_line_start) / 2
        
        # Vertical line boundaries - align with header position
        v_top_boundary = PAGE_HEIGHT - config_dict['margin_top'] * mm  # Align with text top margin
        # Bottom should align with the last todo line
        v_bottom_boundary = top_y - ((items_to_show - 1) * line_gap) - line_gap
        c.line(mid_x, v_bottom_boundary, mid_x, v_top_boundary)
    
    # Add a note at the bottom with total pages info
    c.setFont("Helvetica", 8)
    c.setFillColor(Color(0.6, 0.6, 0.6))
    pages_of_todos = config_dict.get('pages_of_todos', 30)
    items_per_page = config_dict.get('items_per_col', 20) * config_dict.get('columns', 2)
    detail_pages = pages_of_todos * items_per_page * config_dict.get('detail_pages_per_todo', 2)
    total_pages = 1 + pages_of_todos + detail_pages  # 1 index + todo pages + detail pages
    
    c.drawString(config_dict['margin_left'] * mm, config_dict['margin_bottom'] * mm + 10, 
                 f"Preview: Todo page 1/{pages_of_todos} | {items_to_show} items × {config_dict.get('columns', 2)} cols | Total: {total_pages:,} pages")
    
    c.showPage()
    c.save()
    
    buffer.seek(0)
    return buffer.getvalue()

def generate_preview(config_dict, page_size=A4, format='image'):
    """Generate a preview of the first todo page as PNG image or PDF"""    
    if format == 'pdf':
        return generate_pdf_preview(config_dict, page_size)
    
    # Generate PNG image preview
    # Page size in points (convert to pixels for display)
    PAGE_WIDTH, PAGE_HEIGHT = page_size
    # Higher quality preview - scale up for better rendering
    dpi = 150  # Higher DPI for better quality
    scale = dpi / 72.0  # Convert from points (72 DPI) to target DPI
    img_width = int(PAGE_WIDTH * scale)
    img_height = int(PAGE_HEIGHT * scale)
    
    # Create a high-quality PNG preview with anti-aliasing
    img = Image.new('RGB', (img_width, img_height), 'white')
    draw = ImageDraw.Draw(img)
    
    # Font setup - use default font which always works
    # System fonts often fail on cloud deployments
    font = None
    header_font = None
    icon_font = None
    
    try:
        from PIL import ImageFont
        # Just use the default font - it always works
        font_size = int(12 * scale)
        header_font_size = int(16 * scale)
        # Default font doesn't support size, so we'll skip custom fonts
        # This ensures the preview works everywhere
    except ImportError:
        pass
    
    # Draw margins as light gray lines
    margin_color = (230, 230, 230)
    # Scaled margins
    left_margin = int(config_dict['margin_left'] * mm * scale)
    right_margin = int(config_dict['margin_right'] * mm * scale)
    top_margin = int(config_dict['margin_top'] * mm * scale)
    bottom_margin = int(config_dict['margin_bottom'] * mm * scale)
    
    # Draw margin lines with better width for visibility
    line_width = max(1, int(scale))
    draw.line([(left_margin, 0), (left_margin, img_height)], fill=margin_color, width=line_width)
    draw.line([(img_width - right_margin, 0), (img_width - right_margin, img_height)], fill=margin_color, width=line_width)
    draw.line([(0, top_margin), (img_width, top_margin)], fill=margin_color, width=line_width)
    draw.line([(0, img_height - bottom_margin), (img_width, img_height - bottom_margin)], fill=margin_color, width=line_width)
    
    # Draw todo lines
    line_color = (105, 105, 105)
    usable_width = img_width - left_margin - right_margin
    col_width = usable_width // config_dict['columns']
    items_per_col = config_dict.get('items_per_col', 20)
    top_y = top_margin + int(30 * scale)  # Start below header with more space
    line_height = (img_height - top_y - bottom_margin) // items_per_col if items_per_col > 0 else int(20 * scale)
    
    # Better line width for todo lines
    todo_line_width = max(1, int(0.5 * scale))
    
    for col in range(config_dict['columns']):
        x0 = left_margin + col * col_width
        y = top_y
        
        for i in range(min(items_per_col, 50)):  # Allow more items for better preview
            if y > img_height - bottom_margin - int(10 * scale):
                break
                
            # Draw horizontal line with better quality
            line_end = x0 + col_width - int(16 * mm * scale)
            draw.line([(x0, y), (line_end, y)], fill=line_color, width=todo_line_width)
            
            # Draw ">" at the end with better positioning
            try:
                icon_x = line_end + int(2 * mm * scale)
                icon_y = y - int(4 * scale)
                draw.text((icon_x, icon_y), ">", fill=(85, 85, 85))
            except:
                pass  # Skip if font issues
            
            # Draw todo numbers if configured
            if config_dict.get('num_placement') != "Hidden":
                try:
                    todo_num = col * items_per_col + i + 1
                    # Convert hex color to RGB for todo numbers
                    if 'num_color_hex' in config_dict:
                        hex_color = config_dict['num_color_hex'].lstrip('#')
                        num_color_rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    else:
                        # Fallback to gray value for backward compatibility
                        gray_value = int(config_dict.get('num_color', 0.7) * 255)
                        num_color_rgb = (gray_value, gray_value, gray_value)
                    num_text = str(todo_num)
                    
                    if config_dict['num_placement'] == "Outside (left/right)":
                        if col == 0:
                            num_x = left_margin - int(10 * mm * scale)
                        else:
                            num_x = img_width - right_margin + int(3 * mm * scale)
                    elif config_dict['num_placement'] == "Inside (left)":
                        num_x = x0 + int(2 * mm * scale)
                    else:  # Inside (right)
                        num_x = line_end - int(20 * mm * scale)
                    
                    num_y = y - int(4 * scale)
                    draw.text((num_x, num_y), num_text, fill=num_color_rgb)
                except:
                    pass
            
            y += line_height
    
    # Draw guide lines if enabled
    if config_dict.get('guide_lines_enabled', False):
        # Horizontal line boundaries - align with todo number positions
        if config_dict['num_placement'] == "Outside (left/right)":
            # When numbers are outside, align symmetrically
            h_left_boundary = left_margin - int(11 * mm * scale) + int(config_dict['num_offset_x_left'] * mm * scale)  # 2mm before left numbers
            h_right_boundary = img_width - right_margin + int(9 * mm * scale) + int(config_dict['num_offset_x_right'] * mm * scale)  # 2mm after right numbers
        elif config_dict['num_placement'] == "Inside (left)":
            # Numbers are inside on the left
            h_left_boundary = left_margin + int(2 * mm * scale) + int(config_dict['num_offset_x_left'] * mm * scale)
            h_right_boundary = img_width - right_margin + int(2 * mm * scale)
        elif config_dict['num_placement'] == "Inside (right)":
            # Numbers are inside on the right
            h_left_boundary = left_margin - int(2 * mm * scale)
            h_right_boundary = img_width - right_margin - int(20 * mm * scale) + int(config_dict['num_offset_x_right'] * mm * scale)
        else:  # Hidden
            # No numbers, use small margins
            h_left_boundary = left_margin - int(2 * mm * scale)
            h_right_boundary = img_width - right_margin + int(2 * mm * scale)
        
        # Calculate position between todo lines (middle of the items)
        middle_item = items_per_col // 2
        middle_y = top_y + (middle_item * line_height) + (line_height // 2)  # Position between two middle lines
        
        # Horizontal line (between middle todo lines)
        hex_h_color = config_dict.get('guide_h_color', '#E0E0E0').lstrip('#')
        h_color_rgb = tuple(int(hex_h_color[i:i+2], 16) for i in (0, 2, 4))
        h_width = max(1, int(config_dict.get('guide_h_width', 0.5) * mm * scale))
        draw.line([(h_left_boundary, middle_y), (h_right_boundary, middle_y)], fill=h_color_rgb, width=h_width)
        
        # Vertical line (centered between columns)
        hex_v_color = config_dict.get('guide_v_color', '#E0E0E0').lstrip('#')
        v_color_rgb = tuple(int(hex_v_color[i:i+2], 16) for i in (0, 2, 4))
        v_width = max(1, int(config_dict.get('guide_v_width', 0.5) * mm * scale))
        
        # Center the vertical line between the two columns
        # The ">" icon ends roughly at: left_margin + col_width - 7*mm*scale
        # Column 2 starts at: left_margin + col_width
        col1_visual_end = left_margin + col_width - int(7 * mm * scale)  # After the ">" icon
        col2_line_start = left_margin + col_width
        # Place the line in the middle of this visual gap
        mid_x = (col1_visual_end + col2_line_start) // 2
        
        # Vertical line boundaries - align with header position
        v_top_boundary = top_margin  # Align with text top margin
        # Bottom should align with the last todo line
        v_bottom_boundary = top_y + ((items_per_col - 1) * line_height) + line_height
        draw.line([(mid_x, v_top_boundary), (mid_x, v_bottom_boundary)], fill=v_color_rgb, width=v_width)
    
    # Add preview text with better fonts
    try:
        # Page header
        page_text = "Page 1"
        header_x = img_width - right_margin - int(80 * scale)
        header_y = top_margin - int(20 * scale)
        draw.text((header_x, header_y), page_text, fill=(69, 69, 69))
        
        # Add info text at bottom
        pages_of_todos = config_dict.get('pages_of_todos', 30)
        items_per_page = items_per_col * config_dict.get('columns', 2)
        detail_pages = config_dict.get('detail_pages_per_todo', 2)
        total_pages = 1 + pages_of_todos + (pages_of_todos * items_per_page * detail_pages)
        
        info_text = f"Preview: {pages_of_todos} todo pages | {items_per_col} items × {config_dict.get('columns', 2)} cols | Total: {total_pages:,} pages"
        info_x = left_margin
        info_y = img_height - bottom_margin + int(10 * scale)
        draw.text((info_x, info_y), info_text, fill=(150, 150, 150))
    except:
        pass  # Skip text if font issues
    
    return img


# Configuration save/load UI with user-specific storage
with st.expander("💾 Configuration Management", expanded=False):
    
    # Add tabs for different config options
    config_tabs = st.tabs(["📥 My Configs", "🔗 Share/Import", "📚 Presets"])
    
    with config_tabs[0]:
        st.markdown("### Your Configurations")
        st.info("💡 Configurations are stored in your browser session (private to you)")
        
        col_save, col_load = st.columns(2)
        
        with col_save:
            st.markdown("**Save Current**")
            config_name = st.text_input("Name", value=f"config_{datetime.now().strftime('%H%M')}", key="save_name")
            if st.button("💾 Save", key="save_btn"):
                st.session_state['save_config'] = config_name
                st.success(f"Will save as '{config_name}' after preview")
        
        with col_load:
            st.markdown("**Load Saved**")
            # Show session configs first
            session_configs = list(st.session_state.get('user_configs', {}).keys())
            file_configs = list_saved_configs()
            all_configs = list(set(session_configs + file_configs))
            
            if all_configs:
                selected = st.selectbox("Select", [""] + all_configs, key="load_sel")
                if st.button("📂 Load", key="load_btn"):
                    if selected:
                        # Try session first, then file
                        if selected in st.session_state.get('user_configs', {}):
                            loaded = st.session_state.user_configs[selected]
                        else:
                            loaded = load_config(selected)
                        
                        if loaded:
                            st.session_state['loaded_config'] = loaded
                            config_manager.save_to_session(loaded, selected)
                            st.success(f"Loaded: {selected}")
                            st.rerun()
            else:
                st.info("No configs found")
    
    with config_tabs[1]:
        col_export, col_import = st.columns(2)
        
        with col_export:
            st.markdown("**Export Config**")
            if st.button("📤 Generate Code", key="export"):
                # Collect COMPLETE configuration with ALL fields
                current_config = collect_complete_config()
                
                # Generate and display the code immediately
                export_code = config_manager.export_config(current_config)
                st.success("✅ Configuration exported! Copy the code below:")
                st.code(export_code, language="text")
                st.info("📋 Share this code with others. They can import it in the Import section.")
        
        with col_import:
            st.markdown("**Import Config**")
            code = st.text_area("Paste code:", height=100, key="import_code")
            if st.button("📥 Import", key="import"):
                if code:
                    try:
                        imported = config_manager.import_config(code)
                        if imported:
                            st.session_state['loaded_config'] = imported
                            config_manager.save_to_session(imported, "imported")
                            st.success("✅ Imported!")
                            st.rerun()
                    except:
                        st.error("Invalid code")
    
    with config_tabs[2]:
        st.markdown("### Quick Presets")
        presets = {
            "A4 Standard": {"page_format": "A4 (210×297 mm)", "items_per_col": 20},
            "Letter": {"page_format": "Letter (216×279 mm)", "items_per_col": 18},
            "Boox Note": {"page_format": "Custom", "custom_method": "Pixels + PPI (for e-readers)", "pixels_width": 1920, "pixels_height": 2560, "ppi": 300}
        }
        
        for name, config in presets.items():
            if st.button(f"Load {name}", key=f"preset_{name}"):
                st.session_state['loaded_config'] = config
                config_manager.save_to_session(config, name)
                st.success(f"Loaded preset: {name}")
                st.rerun()

# Load configuration if available
default_config = st.session_state.get('loaded_config', {})

# Create two columns - controls on left, preview on right
col_controls, col_preview = st.columns([2, 1.5])

with col_controls:
    st.subheader("⚙️ Configuration")
    
    # Page format selection OUTSIDE the form so it updates immediately
    st.header("📐 Page Layout")
    col_format1, col_format2 = st.columns(2)
    with col_format1:
        page_formats = {
            "A3 (297×420 mm)": A3,
            "A4 (210×297 mm)": A4,
            "A5 (148×210 mm)": A5,
            "B4 (250×353 mm)": B4,
            "B5 (176×250 mm)": B5,
            "Letter (216×279 mm)": letter,
            "Legal (216×356 mm)": legal,
            "Tabloid (279×432 mm)": tabloid,
            "Custom": "custom"
        }
        # Handle page format selection with saved config
        saved_format = default_config.get('page_format', 'A4 (210×297 mm)')
        # Try to find the saved format in the list
        try:
            format_index = list(page_formats.keys()).index(saved_format)
        except ValueError:
            # If exact match not found, try to match by prefix (A4, A5, etc.)
            format_index = 1  # Default to A4
            for i, fmt in enumerate(page_formats.keys()):
                if fmt.startswith(saved_format.split(' ')[0]):
                    format_index = i
                    break
        
        page_format = st.selectbox(
            "Page Format",
            list(page_formats.keys()),
            index=format_index,
            key="page_format_selector"
        )
    
    with col_format2:
        # Initialize default values
        custom_width = default_config.get('custom_width', 210)
        custom_height = default_config.get('custom_height', 297)
        custom_method = default_config.get('custom_method', 'Millimeters')
        pixels_width = default_config.get('pixels_width', 1404)
        pixels_height = default_config.get('pixels_height', 1872)
        ppi = default_config.get('ppi', 300)
        
        # Always show custom options if Custom is selected
        if page_format == "Custom":
            custom_method = st.radio(
                    "Input method",
                    ["Millimeters", "Pixels + PPI (for e-readers)"],
                    index=["Millimeters", "Pixels + PPI (for e-readers)"].index(default_config.get('custom_method', 'Millimeters'))
            )
            
            if custom_method == "Millimeters":
                custom_width = st.number_input("Width (mm)", 50, 500, default_config.get('custom_width', 210))
                custom_height = st.number_input("Height (mm)", 50, 700, default_config.get('custom_height', 297))
            else:
                # Pixels + PPI method
                pixels_width = st.number_input("Width (pixels)", 100, 5000, default_config.get('pixels_width', 1404))
                pixels_height = st.number_input("Height (pixels)", 100, 5000, default_config.get('pixels_height', 1872))
                ppi = st.number_input("Screen PPI", 50, 600, default_config.get('ppi', 300))
                # Calculate mm from pixels and PPI
                custom_width = (pixels_width / ppi) * 25.4  # 25.4 mm per inch
                custom_height = (pixels_height / ppi) * 25.4
                st.info(f"➜ {custom_width:.1f} × {custom_height:.1f} mm")
                st.caption(f"Screen: {pixels_width/ppi:.1f}\" × {pixels_height/ppi:.1f}\"")
            
            # Common e-reader examples
            with st.expander("📱 Common E-Reader Resolutions"):
                st.markdown("""
                **Boox Note Air 3:** 1872×1404 @ 227 PPI (10.3")  
                **Boox Note Max:** 3200×2400 @ 300 PPI (13.3")  
                **reMarkable 2:** 1872×1404 @ 226 PPI (10.3")  
                **Kindle Scribe:** 1860×2480 @ 300 PPI (10.2")  
                **Kindle Oasis:** 1680×1264 @ 300 PPI (7")  
                **iPad Pro 11":** 2388×1668 @ 264 PPI  
                **iPad Pro 12.9":** 2732×2048 @ 264 PPI
                """)
            
            page_size = (custom_width * mm, custom_height * mm)
        else:
            page_size = page_formats[page_format]
            # Show dimensions for reference
            width_mm = int(page_size[0] / mm)
            height_mm = int(page_size[1] / mm)
            st.info(f"Size: {width_mm} × {height_mm} mm")
    
    # Landscape orientation option
    landscape = st.checkbox(
        "🔄 Landscape Orientation", 
        value=default_config.get('landscape', False),
        help="Rotate page to landscape orientation (swaps width and height)"
    )
    
    # Apply landscape orientation if selected
    if landscape:
        page_size = (page_size[1], page_size[0])  # Swap width and height
        # Also swap custom dimensions if custom format
        if page_format == "Custom":
            custom_width, custom_height = custom_height, custom_width
    
    # PDF Quality setting (moved up, outside form)
    st.header("🎨 Quality")
    pdf_quality = st.selectbox(
        "PDF Quality / Compression",
        ["Standard (72 DPI)", "High (150 DPI)", "Print (300 DPI)", "Maximum (600 DPI)"],
        index=default_config.get('pdf_quality_index', 1),
        help="Higher DPI = better quality but larger file size"
    )
    # Map to actual DPI values
    dpi_map = {"Standard (72 DPI)": 72, "High (150 DPI)": 150, "Print (300 DPI)": 300, "Maximum (600 DPI)": 600}
    dpi = dpi_map[pdf_quality]
    st.info(f"📊 DPI: {dpi} | Best for: {'Screen viewing' if dpi <= 150 else 'E-readers (300 PPI screens)' if dpi == 300 else 'Professional printing'}")
    
    # Calculate suggested margins based on page size
    page_width_mm = page_size[0] / mm if 'page_size' in locals() else 210
    page_height_mm = page_size[1] / mm if 'page_size' in locals() else 297
    
    # Content Structure - OUTSIDE the form for proper loading
    st.header("📊 Content Structure")
    
    # Auto-scale items per column based on page height
    auto_items = st.checkbox(
        "Auto-scale items per column for page size",
        value=default_config.get('auto_items', False),
        help="Automatically adjust number of items based on available page height",
        key="auto_items_checkbox"
    )
    
    col_content1, col_content2 = st.columns(2)
    
    with col_content1:
        if auto_items:
            # Calculate based on available height (using default margins since they're not defined yet)
            # We'll use proportional margins based on page size
            margin_scale = min(page_width_mm / 210, page_height_mm / 297)
            est_margin_top = max(5, round(18 * margin_scale))
            est_margin_bottom = max(3, round(8 * margin_scale))
            available_height = page_height_mm - est_margin_top - est_margin_bottom - 30  # 30mm for header
            # Assume ~12mm per item (based on A4 having 20 items in ~240mm)
            items_per_col_default = min(30, max(10, int(available_height / 12)))
            items_per_col = int(items_per_col_default)
            st.info(f"Auto: {items_per_col} items")
        else:
            items_per_col = int(st.number_input("Items per Column", min_value=10, max_value=30, value=int(default_config.get('items_per_col', 20)), step=1, key="items_input"))
        columns = st.radio("Number of Columns", [1, 2], index=[1, 2].index(default_config.get('columns', 2)), key="columns_radio")
    
    with col_content2:
        pages_of_todos = int(st.number_input("Number of Todo Pages", min_value=2, max_value=100, value=int(default_config.get('pages_of_todos', 30)), step=1, key="pages_input"))
        detail_pages_per_todo = st.selectbox("Detail Pages per Todo", [1, 2, 3, 4, 5], index=[1, 2, 3, 4, 5].index(default_config.get('detail_pages_per_todo', 2)), key="detail_pages_select")
    
    # Smart margin defaults based on page size (proportional)
    # Scale margins proportionally to page size relative to A4
    margin_scale = min(page_width_mm / 210, page_height_mm / 297)
    
    # Base margins for A4: 8mm horizontal, 18mm top, 8mm bottom
    default_margin_h = max(3, round(8 * margin_scale))  # Min 3mm
    default_margin_v = max(5, round(18 * margin_scale))  # Min 5mm for top
    default_margin_bottom = max(3, round(8 * margin_scale))  # Min 3mm for bottom
    
    # Guide Lines section - OUTSIDE the form for immediate updates
    st.header("📏 Guide Lines")
    st.markdown("Add horizontal and vertical guide lines to todo pages")
    
    guide_lines_enabled = st.checkbox(
        "Enable Guide Lines",
        value=default_config.get('guide_lines_enabled', False),
        help="Add horizontal and vertical guide lines on todo pages",
        key="guide_lines_checkbox"
    )
    
    # Show controls immediately when checkbox is checked
    if guide_lines_enabled:
        col_guide1, col_guide2 = st.columns(2)
        
        with col_guide1:
            guide_h_color = st.color_picker(
                "Horizontal Line Color",
                default_config.get('guide_h_color', "#E0E0E0"),
                key="guide_h_color_picker"
            )
            guide_h_width = st.slider(
                "Horizontal Line Width (mm)",
                0.2, 2.0, 
                default_config.get('guide_h_width', 0.5),
                step=0.1,
                format="%.1f",
                key="guide_h_width_slider"
            )
        
        with col_guide2:
            guide_v_color = st.color_picker(
                "Vertical Line Color",
                default_config.get('guide_v_color', "#E0E0E0"),
                key="guide_v_color_picker"
            )
            guide_v_width = st.slider(
                "Vertical Line Width (mm)",
                0.2, 2.0,
                default_config.get('guide_v_width', 0.5),
                step=0.1,
                format="%.1f",
                key="guide_v_width_slider"
            )
    else:
        # Use default values when disabled
        guide_h_color = default_config.get('guide_h_color', "#E0E0E0")
        guide_v_color = default_config.get('guide_v_color', "#E0E0E0")
        guide_h_width = default_config.get('guide_h_width', 0.5)
        guide_v_width = default_config.get('guide_v_width', 0.5)
    
    # Title Page section - OUTSIDE the form for immediate updates
    st.header("📝 Title Page")
    st.markdown("Add an optional title page to your PDF")
    
    title_page_enabled = st.checkbox(
        "Enable Title Page",
        value=default_config.get('title_page_enabled', False),
        help="Add a beautiful title page at the beginning of your PDF",
        key="title_page_checkbox"
    )
    
    if title_page_enabled:
        col_title1, col_title2 = st.columns(2)
        
        with col_title1:
            # Title text
            title_text = st.text_input(
                "Title",
                value=default_config.get('title_text', 'My Todo List'),
                placeholder="Enter your title...",
                key="title_text_input"
            )
            
            # Title font selection
            title_font = st.selectbox(
                "Title Font",
                ["Helvetica", "Helvetica-Bold", "Times-Roman", "Times-Bold", "Courier", "Courier-Bold"],
                index=["Helvetica", "Helvetica-Bold", "Times-Roman", "Times-Bold", "Courier", "Courier-Bold"].index(
                    default_config.get('title_font', 'Helvetica-Bold')
                ),
                key="title_font_select"
            )
            
            # Title size
            title_size = st.slider(
                "Title Size",
                20, 72,
                default_config.get('title_size', 48),
                step=2,
                help="Font size in points",
                key="title_size_slider"
            )
            
            # Title color
            title_color = st.color_picker(
                "Title Color",
                default_config.get('title_color', '#000000'),
                key="title_color_picker"
            )
        
        with col_title2:
            # Description text
            title_description = st.text_area(
                "Description",
                value=default_config.get('title_description', ''),
                placeholder="Add a description or subtitle...",
                height=100,
                key="title_description_input"
            )
            
            # Description font
            desc_font = st.selectbox(
                "Description Font",
                ["Helvetica", "Helvetica-Oblique", "Times-Roman", "Times-Italic", "Courier"],
                index=["Helvetica", "Helvetica-Oblique", "Times-Roman", "Times-Italic", "Courier"].index(
                    default_config.get('desc_font', 'Helvetica')
                ),
                key="desc_font_select"
            )
            
            # Description size
            desc_size = st.slider(
                "Description Size",
                12, 36,
                default_config.get('desc_size', 18),
                step=1,
                help="Font size in points",
                key="desc_size_slider"
            )
            
            # Description color
            desc_color = st.color_picker(
                "Description Color",
                default_config.get('desc_color', '#666666'),
                key="desc_color_picker"
            )
        
        # Layout options
        st.markdown("#### Layout Options")
        col_layout1, col_layout2, col_layout3 = st.columns(3)
        
        with col_layout1:
            title_alignment = st.radio(
                "Alignment",
                ["Center", "Left", "Right"],
                index=["Center", "Left", "Right"].index(default_config.get('title_alignment', 'Center')),
                key="title_alignment_radio"
            )
        
        with col_layout2:
            title_position = st.radio(
                "Vertical Position",
                ["Top", "Center", "Golden Ratio"],
                index=["Top", "Center", "Golden Ratio"].index(default_config.get('title_position', 'Golden Ratio')),
                help="Golden Ratio = 38.2% from top (most aesthetic)",
                key="title_position_radio"
            )
        
        with col_layout3:
            # Add date option
            title_add_date = st.checkbox(
                "Add Date",
                value=default_config.get('title_add_date', False),
                help="Add current date below description",
                key="title_add_date_checkbox"
            )
            
            # Add border/decoration
            title_decoration = st.selectbox(
                "Decoration",
                ["None", "Simple Line", "Double Line", "Dots", "Frame"],
                index=["None", "Simple Line", "Double Line", "Dots", "Frame"].index(
                    default_config.get('title_decoration', 'Simple Line')
                ),
                key="title_decoration_select"
            )
    else:
        # Default values when disabled
        title_text = default_config.get('title_text', 'My Todo List')
        title_font = default_config.get('title_font', 'Helvetica-Bold')
        title_size = default_config.get('title_size', 48)
        title_color = default_config.get('title_color', '#000000')
        title_description = default_config.get('title_description', '')
        desc_font = default_config.get('desc_font', 'Helvetica')
        desc_size = default_config.get('desc_size', 18)
        desc_color = default_config.get('desc_color', '#666666')
        title_alignment = default_config.get('title_alignment', 'Center')
        title_position = default_config.get('title_position', 'Golden Ratio')
        title_add_date = default_config.get('title_add_date', False)
        title_decoration = default_config.get('title_decoration', 'Simple Line')
    
    # Now start the form for the rest of the configuration
    with st.form("pdf_config"):
        st.header("📏 Margins")
        
        # Add auto-scale option
        auto_margins = st.checkbox(
            "Auto-scale margins for page size",
            value=default_config.get('auto_margins', True),
            help="Automatically adjust margins based on page size"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if auto_margins:
                margin_left = default_margin_h
                margin_right = default_margin_h
                st.info(f"Auto: {margin_left}mm")
            else:
                margin_left = st.slider("Left Margin (mm)", 2, 30, default_config.get('margin_left', default_margin_h))
                margin_right = st.slider("Right Margin (mm)", 2, 30, default_config.get('margin_right', default_margin_h))
        
        with col2:
            if auto_margins:
                margin_top = default_margin_v
                margin_bottom = default_margin_bottom
                st.info(f"Auto: {margin_top}mm top, {margin_bottom}mm bottom")
            else:
                margin_top = st.slider("Top Margin (mm)", 5, 40, default_config.get('margin_top', default_margin_v))
                margin_bottom = st.slider("Bottom Margin (mm)", 2, 30, default_config.get('margin_bottom', default_margin_bottom))
        
        st.header("⚫ Dot Grid")
        
        # Auto-scale dot spacing based on page size
        auto_dot_spacing = st.checkbox(
            "Auto-scale dot spacing for page size",
            value=default_config.get('auto_dot_spacing', True),
            help="Automatically adjust dot spacing based on page size"
        )
        
        col3, col4 = st.columns(2)
        
        with col3:
            if auto_dot_spacing:
                # Scale dot spacing proportionally to page size
                # Use both width and height for better scaling
                scale_factor = min(page_width_mm / 210, page_height_mm / 297)  # Scale relative to A4
                dot_spacing_default = round(7 * scale_factor, 1)  # Scale relative to A4
                dot_spacing = max(3, min(15, dot_spacing_default))  # Clamp to reasonable range
                st.info(f"Auto: {dot_spacing}mm (scaled from A4)")
            else:
                dot_spacing = st.slider("Dot Spacing (mm)", 3, 15, default_config.get('dot_spacing', 7))
            
            dot_radius = st.slider("Dot Radius (mm)", 0.1, 1.0, default_config.get('dot_radius', 0.3), step=0.1)
        
        with col4:
            dot_color_intensity = st.slider("Dot Color (Gray)", 0.3, 0.9, default_config.get('dot_color_intensity', 0.7), step=0.1)
        
        st.header("🔤 Font Sizes")
        col7, col8 = st.columns(2)
        
        with col7:
            font_size_header = st.slider("Header Font Size", 10, 20, default_config.get('font_size_header', 14))
            font_size_icon = st.slider("Icon Font Size (>)", 6, 20, default_config.get('font_size_icon', 13), help="Size of the '>' symbol at the end of each todo line")
        
        with col8:
            font_size_detail = st.slider("Detail Font Size", 10, 16, default_config.get('font_size_detail', 12))
            font_size_num = st.slider("Number Font Size", 5, 10, default_config.get('font_size_num', 7))
        
        st.header("🔢 Todo Numbers")
        col_num1, col_num2 = st.columns(2)
        
        with col_num1:
            placement_options = ["Outside (left/right)", "Inside (left)", "Inside (right)", "Hidden"]
            num_placement = st.radio(
                "Number Placement", 
                placement_options,
                index=placement_options.index(default_config.get('num_placement', "Outside (left/right)")),
                help="Outside: left column numbers on left margin, right column on right margin"
            )
            # Handle backward compatibility: convert old num_color gray value to hex
            if 'num_color_hex' in default_config:
                default_hex = default_config.get('num_color_hex')
            elif 'num_color' in default_config:
                # Convert old gray value (0-1) to hex
                gray_val = int(default_config.get('num_color', 0.85) * 255)
                default_hex = f"#{gray_val:02x}{gray_val:02x}{gray_val:02x}"
            else:
                default_hex = "#D8D8D8"
            num_color_hex = st.color_picker("Number Color", default_hex)
            num_size = st.slider("Number Size", 5, 12, default_config.get('num_size', 7))
        
        with col_num2:
            num_offset_x_left = st.slider(
                "Left Column Offset (mm)", 
                -10, 10, default_config.get('num_offset_x_left', 0),
                help="Adjust left column numbers: negative = further left"
            )
            num_offset_x_right = st.slider(
                "Right Column Offset (mm)", 
                -10, 10, default_config.get('num_offset_x_right', 0),
                help="Adjust right column numbers: positive = further right"
            )
            num_offset_y = st.slider(
                "Vertical Offset (mm)", 
                -5, 5, default_config.get('num_offset_y', -1),
                help="Fine-tune vertical position: negative = up, positive = down"
            )
        
        st.header("🎨 Colors")
        col9, col10 = st.columns(2)
        
        with col9:
            color_line = st.color_picker("Line Color", default_config.get('color_line', "#696969"))
        
        with col10:
            color_text = st.color_picker("Text Color", default_config.get('color_text', "#454545"))
        
        
        st.header("📁 Output")
        output_filename = st.text_input(
            "Output Filename", 
            default_config.get('output_filename', "todo-a4-custom.pdf"),
            help="The name of the generated PDF file"
        )
        
        # Submit button
        col_submit, col_preview_btn = st.columns(2)
        with col_submit:
            submitted = st.form_submit_button("🚀 Generate PDF", type="primary", use_container_width=True)
        with col_preview_btn:
            preview_clicked = st.form_submit_button("👁️ Update Preview", use_container_width=True)

# Show preview in right column
with col_preview:
    st.subheader("📄 Preview")
    
    # Check if st.pdf() is available
    has_pdf_viewer = False
    try:
        # Check if st.pdf exists and streamlit-pdf is installed
        if hasattr(st, 'pdf'):
            import streamlit_pdf
            has_pdf_viewer = True
    except ImportError:
        has_pdf_viewer = False
    
    # Show toggle buttons only if PDF viewer is available
    if has_pdf_viewer:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("PDF", use_container_width=True, 
                        type="primary" if st.session_state.get('preview_mode', 'pdf') == 'pdf' else "secondary"):
                st.session_state.preview_mode = 'pdf'
                st.rerun()
        with col2:
            if st.button("IMAGE", use_container_width=True,
                        type="primary" if st.session_state.get('preview_mode', 'pdf') == 'image' else "secondary"):
                st.session_state.preview_mode = 'image'
                st.rerun()
    else:
        # No PDF viewer available, use image mode
        st.session_state.preview_mode = 'image'
    
    # Generate preview when button is clicked or on first load
    if preview_clicked or 'preview_config' not in st.session_state:
        # Create configuration dictionary
        config = {
            'page_format': page_format,
            'landscape': landscape,
            'custom_method': custom_method if page_format == "Custom" else 'Millimeters',
            'custom_width': custom_width,
            'custom_height': custom_height,
            'pixels_width': pixels_width if page_format == "Custom" and custom_method == "Pixels + PPI (for e-readers)" else 1404,
            'pixels_height': pixels_height if page_format == "Custom" and custom_method == "Pixels + PPI (for e-readers)" else 1872,
            'ppi': ppi if page_format == "Custom" and custom_method == "Pixels + PPI (for e-readers)" else 300,
            'auto_margins': auto_margins,
            'auto_items': auto_items,
            'auto_dot_spacing': auto_dot_spacing,
            'margin_left': margin_left,
            'margin_right': margin_right,
            'margin_top': margin_top,
            'margin_bottom': margin_bottom,
            'dot_spacing': dot_spacing,
            'dot_radius': dot_radius,
            'dot_color_intensity': dot_color_intensity,
            'items_per_col': int(items_per_col),
            'columns': int(columns),
            'pages_of_todos': int(pages_of_todos),
            'detail_pages_per_todo': detail_pages_per_todo,
            'font_size_header': font_size_header,
            'font_size_icon': font_size_icon,
            'font_size_detail': font_size_detail,
            'num_size': num_size,
            'color_line': color_line,
            'color_text': color_text,
            'num_color_hex': num_color_hex,
            'num_placement': num_placement,
            'num_offset_x_left': num_offset_x_left,
            'num_offset_x_right': num_offset_x_right,
            'num_offset_y': num_offset_y,
            'guide_lines_enabled': guide_lines_enabled,
            'guide_h_color': guide_h_color,
            'guide_v_color': guide_v_color,
            'guide_h_width': guide_h_width,
            'guide_v_width': guide_v_width,
            'title_page_enabled': title_page_enabled,
            'title_text': title_text,
            'title_font': title_font,
            'title_size': title_size,
            'title_color': title_color,
            'title_description': title_description,
            'desc_font': desc_font,
            'desc_size': desc_size,
            'desc_color': desc_color,
            'title_alignment': title_alignment,
            'title_position': title_position,
            'title_add_date': title_add_date,
            'title_decoration': title_decoration,
            'pdf_quality_index': ["Standard (72 DPI)", "High (150 DPI)", "Print (300 DPI)", "Maximum (600 DPI)"].index(pdf_quality)
        }
        
        # Generate preview
        with st.spinner("Generating preview..."):
            # Always generate PDF first
            pdf_data = generate_preview(config, page_size, format='pdf')
            
            # Display based on selected mode
            if st.session_state.get('preview_mode', 'image') == 'pdf' and has_pdf_viewer:
                # Use native PDF viewer
                try:
                    st.pdf(pdf_data, height=700)
                    st.caption("Native PDF viewer - Scroll to see more pages")
                except Exception as e:
                    st.warning("PDF viewer failed, falling back to image mode")
                    st.session_state.preview_mode = 'image'
                    # Fall through to image display
            
            if st.session_state.get('preview_mode', 'image') == 'image':
                # Convert PDF to image for display (elegant solution!)
                try:
                    # Try using pdf2image if available
                    from pdf2image import convert_from_bytes
                    import io
                    
                    # Convert first page of PDF to image
                    images = convert_from_bytes(pdf_data, dpi=150, first_page=1, last_page=1)
                    if images:
                        pdf_image = images[0]
                        
                        # Add border and shadow styling
                        st.markdown("""
                        <style>
                        div[data-testid="stImage"] {
                            border: 1px solid #d8d8d8;
                            border-radius: 7px;
                            box-shadow: #c6c3c3 0 0 10px 0px;
                            overflow: hidden;
                            padding: 0px;
                            background: white;
                        }
                        div[data-testid="stImage"] img {
                            border-radius: 7px;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        # Display the PDF as image
                        st.image(pdf_image, caption="PDF Preview - Page 1", use_column_width=True)
                        
                        # Show it's actually a PDF with download option
                        st.info("📄 Image preview of page 1. Download to view all pages.")
                    
                except ImportError:
                    # Fallback: Create high-quality image preview directly
                    # This ensures it works even without pdf2image
                    import io
                    from PIL import Image
                    
                    # Generate as high-quality image instead
                    preview_img = generate_preview(config, page_size, format='image')
                    
                    # Add styling
                    st.markdown("""
                        <style>
                        div[data-testid="stImage"] {
                            border: 1px solid #d8d8d8;
                            border-radius: 7px;
                            box-shadow: #c6c3c3 0 0 10px 0px;
                            overflow: hidden;
                            padding: 0px;
                            background: white;
                        }
                        div[data-testid="stImage"] img {
                            border-radius: 7px;
                        }
                        </style>
                    """, unsafe_allow_html=True)
                    
                    # Display the preview
                    st.image(preview_img, caption="PDF Preview - Page 1", use_column_width=True)
                
                except Exception as e:
                    # Final fallback
                    st.warning("PDF preview rendering failed. Use download button below.")
                    st.error(f"Error: {str(e)}")
            
            # Show document info
            pages_of_todos = config.get('pages_of_todos', 30)
            items_per_col = config.get('items_per_col', 20)
            columns = config.get('columns', 2)
            detail_pages = config.get('detail_pages_per_todo', 2)
            total_items = pages_of_todos * items_per_col * columns
            total_detail_pages = total_items * detail_pages
            total_pages = 1 + pages_of_todos + total_detail_pages
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Page Format", page_format)
            with col2:
                st.metric("Todo Pages", pages_of_todos)
            with col3:
                st.metric("Total Pages", f"{total_pages:,}")
                
            # Download button
            st.download_button(
                label="📥 Download Preview PDF",
                data=pdf_data,
                file_name="preview_page1.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
            
            st.caption("PDF Preview - Page 1 of your document")
        
        # Save configuration if requested
        if 'save_config' in st.session_state:
            config['output_filename'] = output_filename
            # Save to both session and file for compatibility
            config_manager.save_to_session(config, st.session_state['save_config'])
            save_config(config, st.session_state['save_config'])
            st.success(f"✅ Configuration saved as '{st.session_state['save_config']}'")
            del st.session_state['save_config']
        
        
        pages_info = f"Configured for {pages_of_todos} todo pages + {pages_of_todos * items_per_col * columns * detail_pages_per_todo:,} detail pages"
        st.caption(f"Preview shows page 1 only. {pages_info}. Click 'Update Preview' after changing settings.")

if submitted:
    # Prepare page size for config
    if page_format == "Custom":
        if landscape:
            page_size_str = f"({custom_height} * mm, {custom_width} * mm)"  # Swapped for landscape
        else:
            page_size_str = f"({custom_width} * mm, {custom_height} * mm)"
    else:
        # Extract just the format name (A4, A5, etc.) from the display string
        page_size_str = page_format.split(" ")[0]
        if landscape:
            from reportlab.lib.pagesizes import landscape as landscape_fn
            page_size_str = f"landscape({page_size_str})"
    
    # Create a modified version of the generator with new config
    config_code = f"""
#!/usr/bin/env python3
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, A3, letter, legal, B4, B5, landscape
# Define tabloid size (11x17 inches)
tabloid = (11*72, 17*72)  # 72 points per inch
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# User Configuration
class Config:
    # Page format: {page_format}
    PAGE_WIDTH, PAGE_HEIGHT = {page_size_str}
    
    MARGIN_LEFT = {margin_left} * mm
    MARGIN_RIGHT = {margin_right} * mm
    MARGIN_TOP = {margin_top} * mm
    MARGIN_BOTTOM = {margin_bottom} * mm
    
    DOT_SPACING = {dot_spacing} * mm
    DOT_RADIUS = {dot_radius} * mm
    DOT_COLOR = Color({dot_color_intensity}, {dot_color_intensity}, {dot_color_intensity})
    
    ITEMS_PER_COL = {int(items_per_col)}
    COLUMNS = {int(columns)}
    PAGES_OF_TODOS = {int(pages_of_todos)}
    DETAIL_PAGES_PER_TODO = {int(detail_pages_per_todo)}
    
    FONT_SIZE_HEADER = {font_size_header}
    FONT_SIZE_ICON = {font_size_icon}
    FONT_SIZE_DETAIL = {font_size_detail}
    FONT_SIZE_NUM = {num_size}
    
    COLOR_LINE = HexColor('{color_line}')
    COLOR_TEXT = HexColor('{color_text}')
    # Convert hex color to RGB for todo numbers
    COLOR_NUM = HexColor('{num_color_hex}')
    
    # Number placement configuration
    NUM_PLACEMENT = "{num_placement}"
    NUM_OFFSET_X_LEFT = {num_offset_x_left} * mm
    NUM_OFFSET_X_RIGHT = {num_offset_x_right} * mm
    NUM_OFFSET_Y = {num_offset_y} * mm
    
    # Guide lines configuration
    GUIDE_LINES_ENABLED = {guide_lines_enabled}
    GUIDE_H_COLOR = HexColor('{guide_h_color}')
    GUIDE_V_COLOR = HexColor('{guide_v_color}')
    GUIDE_H_WIDTH = {guide_h_width} * mm
    GUIDE_V_WIDTH = {guide_v_width} * mm
    
    # Title page configuration
    TITLE_PAGE_ENABLED = {title_page_enabled}
    TITLE_TEXT = '''{title_text}'''
    TITLE_FONT = '{title_font}'
    TITLE_SIZE = {title_size}
    TITLE_COLOR = '{title_color}'
    TITLE_DESCRIPTION = '''{title_description}'''
    DESC_FONT = '{desc_font}'
    DESC_SIZE = {desc_size}
    DESC_COLOR = '{desc_color}'
    TITLE_ALIGNMENT = '{title_alignment}'
    TITLE_POSITION = '{title_position}'
    TITLE_ADD_DATE = {title_add_date}
    TITLE_DECORATION = '{title_decoration}'
"""
    
    # Read the original generator and replace the config
    with open("generator-pdf-todo-boox-double-details_16.py", "r") as f:
        original_code = f.read()
    
    # Find where the Config class ends and main function starts
    import_end = original_code.find("def create_pdf")
    
    # Get the imports section
    imports_section = original_code[:original_code.find("# Configuration")]
    
    # Add title page generation function
    title_page_function = """
from datetime import datetime

def generate_title_page(c, PAGE_WIDTH, PAGE_HEIGHT):
    '''Generate a beautiful title page for the PDF'''
    
    # White background
    c.setFillColor(Color(1, 1, 1))
    c.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)
    
    # Calculate vertical position based on selected option
    if Config.TITLE_POSITION == 'Top':
        title_y = PAGE_HEIGHT - (PAGE_HEIGHT * 0.2)  # 20% from top
    elif Config.TITLE_POSITION == 'Center':
        title_y = PAGE_HEIGHT * 0.5  # 50% (center)
    elif Config.TITLE_POSITION == 'Golden Ratio':
        title_y = PAGE_HEIGHT * 0.618  # Golden ratio (most aesthetic)
    else:
        title_y = PAGE_HEIGHT * 0.618
    
    # Get alignment
    alignment = Config.TITLE_ALIGNMENT
    
    # Draw title
    c.setFont(Config.TITLE_FONT, Config.TITLE_SIZE)
    c.setFillColor(HexColor(Config.TITLE_COLOR))
    
    # Calculate text position based on alignment
    title_width = c.stringWidth(Config.TITLE_TEXT, Config.TITLE_FONT, Config.TITLE_SIZE)
    if alignment == 'Center':
        title_x = (PAGE_WIDTH - title_width) / 2
    elif alignment == 'Left':
        title_x = Config.MARGIN_LEFT
    else:  # Right
        title_x = PAGE_WIDTH - Config.MARGIN_RIGHT - title_width
    
    c.drawString(title_x, title_y, Config.TITLE_TEXT)
    
    # Draw description if provided
    if Config.TITLE_DESCRIPTION and Config.TITLE_DESCRIPTION.strip():
        c.setFont(Config.DESC_FONT, Config.DESC_SIZE)
        c.setFillColor(HexColor(Config.DESC_COLOR))
        
        # Split description into lines if it's too long
        lines = Config.TITLE_DESCRIPTION.split('\\n')
        desc_y = title_y - Config.TITLE_SIZE - 20  # 20 points below title
        
        for line in lines:
            line = line.strip()
            if line:
                desc_width = c.stringWidth(line, Config.DESC_FONT, Config.DESC_SIZE)
                if alignment == 'Center':
                    desc_x = (PAGE_WIDTH - desc_width) / 2
                elif alignment == 'Left':
                    desc_x = Config.MARGIN_LEFT
                else:  # Right
                    desc_x = PAGE_WIDTH - Config.MARGIN_RIGHT - desc_width
                
                c.drawString(desc_x, desc_y, line)
                desc_y -= Config.DESC_SIZE + 8  # Move down for next line
    else:
        desc_y = title_y - Config.TITLE_SIZE - 20
    
    # Add date if enabled
    if Config.TITLE_ADD_DATE:
        date_text = datetime.now().strftime('%B %d, %Y')
        date_font = 'Helvetica'
        date_size = 14
        
        c.setFont(date_font, date_size)
        c.setFillColor(HexColor('#999999'))
        
        date_width = c.stringWidth(date_text, date_font, date_size)
        date_y = desc_y - 30
        
        if alignment == 'Center':
            date_x = (PAGE_WIDTH - date_width) / 2
        elif alignment == 'Left':
            date_x = Config.MARGIN_LEFT
        else:  # Right
            date_x = PAGE_WIDTH - Config.MARGIN_RIGHT - date_width
        
        c.drawString(date_x, date_y, date_text)
        decoration_y = date_y - 30
    else:
        decoration_y = desc_y - 30
    
    # Add decoration if selected
    if Config.TITLE_DECORATION != 'None':
        c.setStrokeColor(HexColor('#CCCCCC'))
        
        if Config.TITLE_DECORATION == 'Simple Line':
            c.setLineWidth(1)
            line_width = min(200, PAGE_WIDTH * 0.3)
            line_x = (PAGE_WIDTH - line_width) / 2
            c.line(line_x, decoration_y, line_x + line_width, decoration_y)
            
        elif Config.TITLE_DECORATION == 'Double Line':
            c.setLineWidth(0.5)
            line_width = min(200, PAGE_WIDTH * 0.3)
            line_x = (PAGE_WIDTH - line_width) / 2
            c.line(line_x, decoration_y, line_x + line_width, decoration_y)
            c.line(line_x, decoration_y - 4, line_x + line_width, decoration_y - 4)
            
        elif Config.TITLE_DECORATION == 'Dots':
            c.setFillColor(HexColor('#CCCCCC'))
            dot_count = 5
            dot_spacing = 20
            total_width = (dot_count - 1) * dot_spacing
            start_x = (PAGE_WIDTH - total_width) / 2
            for i in range(dot_count):
                c.circle(start_x + i * dot_spacing, decoration_y, 2, fill=1, stroke=0)
                
        elif Config.TITLE_DECORATION == 'Frame':
            c.setLineWidth(2)
            margin = 30 * mm
            c.rect(margin, margin, PAGE_WIDTH - 2 * margin, PAGE_HEIGHT - 2 * margin, fill=0, stroke=1)
    
    c.showPage()

"""
    
    # Get the create_pdf function and everything after
    function_section = original_code[import_end:]
    
    # Modify the output file in the function
    function_section = function_section.replace(
        'output_file = "todo-boox-double-details_16_v1.0.1.pdf"',
        f'output_file = "{output_filename}"'
    )
    
    # Fix the canvas creation to use the configured page size
    function_section = function_section.replace(
        'c = canvas.Canvas(output_file, pagesize=A4)',
        'c = canvas.Canvas(output_file, pagesize=(Config.PAGE_WIDTH, Config.PAGE_HEIGHT))'
    )
    
    # Add title page generation after canvas creation
    title_page_call = """
    
    # Generate title page if enabled
    if Config.TITLE_PAGE_ENABLED:
        generate_title_page(c, Config.PAGE_WIDTH, Config.PAGE_HEIGHT)
    """
    
    # Find where to insert title page call (after metadata setting)
    metadata_marker = 'c.setAuthor("Generator Python Double Details")'
    if metadata_marker in function_section:
        function_section = function_section.replace(
            metadata_marker,
            metadata_marker + title_page_call
        )
    
    # Add guide lines drawing code for todo pages
    guide_lines_todo_code = """
        # Draw guide lines on todo page if enabled
        if Config.GUIDE_LINES_ENABLED:
            # Save current state
            c.saveState()
            
            # Horizontal line boundaries - align with todo number positions
            if Config.NUM_PLACEMENT == "Outside (left/right)":
                # When numbers are outside, align symmetrically
                # Left numbers are at: MARGIN_LEFT - 3*mm - num_width + NUM_OFFSET_X_LEFT
                # Right numbers start at: PAGE_WIDTH - MARGIN_RIGHT + 1*mm + NUM_OFFSET_X_RIGHT
                # Add equal spacing: start 2mm before left numbers, end 2mm after right numbers
                h_left_boundary = Config.MARGIN_LEFT - 3 * mm - 2 * mm + Config.NUM_OFFSET_X_LEFT  # 2mm before left numbers (without subtracting num_width)
                h_right_boundary = Config.PAGE_WIDTH - Config.MARGIN_RIGHT + 1 * mm + 2 * mm + Config.NUM_OFFSET_X_RIGHT  # 2mm after right numbers
            elif Config.NUM_PLACEMENT == "Inside (left)":
                # Numbers are inside on the left
                h_left_boundary = Config.MARGIN_LEFT + 2 * mm + Config.NUM_OFFSET_X_LEFT
                h_right_boundary = Config.PAGE_WIDTH - Config.MARGIN_RIGHT + 2 * mm
            elif Config.NUM_PLACEMENT == "Inside (right)":
                # Numbers are inside on the right  
                h_left_boundary = Config.MARGIN_LEFT - 2 * mm
                h_right_boundary = Config.PAGE_WIDTH - Config.MARGIN_RIGHT - 20 * mm + Config.NUM_OFFSET_X_RIGHT
            else:  # Hidden
                # No numbers, use small margins
                h_left_boundary = Config.MARGIN_LEFT - 2 * mm
                h_right_boundary = Config.PAGE_WIDTH - Config.MARGIN_RIGHT + 2 * mm
            
            # Calculate position between todo lines (middle of the items)
            # For even numbers: place between the two middle items
            # For 20 items: 10 above (items 1-10), 10 below (items 11-20), line between 10 and 11
            # For odd numbers: place at the middle item
            if Config.ITEMS_PER_COL % 2 == 0:
                # Even number: place after item n/2 (e.g., for 20 items: after item 10, before item 11)
                items_above = Config.ITEMS_PER_COL // 2
                middle_y = top_y - (items_above * line_gap)  # Position after 'items_above' items
            else:
                # Odd number: place at the middle item (e.g., for 21 items: at item 11 with 10 above and 10 below)
                middle_item = Config.ITEMS_PER_COL // 2
                middle_y = top_y - (middle_item * line_gap) - (line_gap / 2)  # Position at middle line
            
            # Horizontal line (between middle todo lines)
            c.setStrokeColor(Config.GUIDE_H_COLOR)
            c.setLineWidth(Config.GUIDE_H_WIDTH)
            c.line(h_left_boundary, middle_y, h_right_boundary, middle_y)
            
            # Vertical line (centered between columns)
            c.setStrokeColor(Config.GUIDE_V_COLOR)
            c.setLineWidth(Config.GUIDE_V_WIDTH)
            
            # Center the vertical line between the two columns
            # Column 1 todo lines end at: Config.MARGIN_LEFT + col_width - 16*mm
            # The ">" icon is at about: col_width - 14*mm + 5*mm - 1.6*mm - 2 (from original code)
            # So the ">" ends roughly at: Config.MARGIN_LEFT + col_width - 7*mm
            # Column 2 starts at: Config.MARGIN_LEFT + col_width
            # The visual gap is between the end of ">" and start of column 2
            col1_visual_end = Config.MARGIN_LEFT + col_width - 7 * mm  # After the ">" icon
            col2_line_start = Config.MARGIN_LEFT + col_width  # Where column 2 starts
            # Place the line in the middle of this visual gap
            mid_x = (col1_visual_end + col2_line_start) / 2
            
            # Vertical line boundaries - align with header position
            # The header is at PAGE_HEIGHT - MARGIN_TOP + 15, so start just below it
            v_top_boundary = Config.PAGE_HEIGHT - Config.MARGIN_TOP  # Align with text top margin
            # Bottom should align with the last todo line
            v_bottom_boundary = top_y - ((Config.ITEMS_PER_COL - 1) * line_gap) - line_gap
            c.line(mid_x, v_bottom_boundary, mid_x, v_top_boundary)
            
            # Restore state
            c.restoreState()
        
        c.showPage()"""
    
    # Find where todo pages show page (c.showPage() after drawing todo lines)
    # Look for the pattern where todo page ends
    todo_page_end = "        c.showPage()"
    
    if todo_page_end in function_section:
        # Find all occurrences and replace the first one (todo pages)
        # This is after the todo lines loop but before detail pages
        parts = function_section.split(todo_page_end, 2)  # Split at most 2 times
        if len(parts) >= 2:
            # Insert guide lines before first showPage() of todo pages
            function_section = parts[0] + guide_lines_todo_code + todo_page_end.join(parts[1:])
            if guide_lines_enabled:
                st.info(f"✓ Guide lines will be drawn on todo pages")
    
    # Add number placement logic
    number_drawing_original = """                # Numéro dans la marge
                c.setFont("Helvetica", Config.FONT_SIZE_NUM)
                c.setFillColor(Config.COLOR_NUM)
                
                if col == 0:
                    # Colonne gauche: numéro à gauche
                    num_text = str(todo_num)
                    num_width = c.stringWidth(num_text, "Helvetica", Config.FONT_SIZE_NUM)
                    num_x = Config.MARGIN_LEFT - 3 * mm - num_width
                else:
                    # Colonne droite: numéro à droite
                    num_x = Config.PAGE_WIDTH - Config.MARGIN_RIGHT + 1 * mm
                
                c.drawString(num_x, y - 1 * mm, str(todo_num))"""
    
    number_drawing_new = """                # Numéro dans la marge
                if Config.NUM_PLACEMENT != "Hidden":
                    c.setFont("Helvetica", Config.FONT_SIZE_NUM)
                    c.setFillColor(Config.COLOR_NUM)
                    
                    num_text = str(todo_num)
                    num_width = c.stringWidth(num_text, "Helvetica", Config.FONT_SIZE_NUM)
                    
                    if Config.NUM_PLACEMENT == "Outside (left/right)":
                        if col == 0:
                            # Colonne gauche: numéro à gauche en dehors
                            num_x = Config.MARGIN_LEFT - 3 * mm - num_width + Config.NUM_OFFSET_X_LEFT
                        else:
                            # Colonne droite: numéro à droite en dehors
                            num_x = Config.PAGE_WIDTH - Config.MARGIN_RIGHT + 1 * mm + Config.NUM_OFFSET_X_RIGHT
                    elif Config.NUM_PLACEMENT == "Inside (left)":
                        # Toujours à gauche de la ligne - use left offset for both columns
                        offset = Config.NUM_OFFSET_X_LEFT if col == 0 else Config.NUM_OFFSET_X_RIGHT
                        num_x = x0 + 2 * mm + offset
                    elif Config.NUM_PLACEMENT == "Inside (right)":
                        # Toujours à droite de la ligne (avant l'icône) - use appropriate offset
                        offset = Config.NUM_OFFSET_X_LEFT if col == 0 else Config.NUM_OFFSET_X_RIGHT
                        num_x = x0 + col_width - 20 * mm - num_width + offset
                    
                    # Apply vertical offset (default was y - 1 * mm)
                    num_y = y + Config.NUM_OFFSET_Y
                    c.drawString(num_x, num_y, num_text)"""
    
    function_section = function_section.replace(number_drawing_original, number_drawing_new)
    
    # Fix detail page header position for custom page sizes
    # For smaller pages, use a smaller offset; for larger pages, use a larger offset
    detail_header_original = 'arrow_y = Config.PAGE_HEIGHT - Config.MARGIN_TOP + 10 * mm  # Remonté de 10mm (1cm)'
    detail_header_new = 'arrow_y = Config.PAGE_HEIGHT - Config.MARGIN_TOP + max(5 * mm, min(15 * mm, Config.PAGE_HEIGHT * 0.034))  # Adaptive offset'
    function_section = function_section.replace(detail_header_original, detail_header_new)
    
    # Fix hardcoded 2 pages to use actual DETAIL_PAGES_PER_TODO
    # Replace the hardcoded detail page generation with a proper loop
    if 'DETAIL_PAGES_PER_TODO' in config_code and detail_pages_per_todo != 2:
        # Find and replace the hardcoded section
        old_detail_generation = """        # ===== PREMIÈRE PAGE DE DÉTAIL =====
        # UTILISER LE XOBJECT (pas de redessiner!)
        c.doForm("dotPattern")
        
        # Bookmark pour cette première page de détail
        detail_bookmark_1 = f"detail_{idx}_1"
        c.bookmarkPage(detail_bookmark_1)"""
        
        # Check if we need to replace the detail page generation
        if old_detail_generation in function_section:
            # Extract the part before detail pages
            detail_start = function_section.find("        # ===== PREMIÈRE PAGE DE DÉTAIL =====")
            detail_end = function_section.find("        c.showPage()", detail_start)
            # Find the last showPage() for the second detail page
            detail_end = function_section.find("        c.showPage()", detail_end + 10) + len("        c.showPage()")
            
            # Generate new loop-based code for multiple detail pages
            new_detail_code = f'''        # Generate all detail pages for this todo
        for detail_page_num in range(1, Config.DETAIL_PAGES_PER_TODO + 1):
            # UTILISER LE XOBJECT (pas de redessiner!)
            c.doForm("dotPattern")
            
            # Bookmark pour cette page de détail
            detail_bookmark = f"detail_{{idx}}_{{detail_page_num}}"
            c.bookmarkPage(detail_bookmark)
            
            # En-tête avec flèche de retour
            c.setFont("Helvetica-Bold", Config.FONT_SIZE_DETAIL)
            
            # Position remontée et couleur gris clair
            arrow_x = Config.MARGIN_LEFT - 4 * mm
            arrow_y = Config.PAGE_HEIGHT - Config.MARGIN_TOP + max(5 * mm, min(15 * mm, Config.PAGE_HEIGHT * 0.034))
            
            # Flèche retour en gris clair
            c.setFillColor(Color(0.6, 0.6, 0.6))
            c.drawString(arrow_x, arrow_y, "<")
            
            # Texte du header avec indication de page
            c.setFillColor(Color(0.6, 0.6, 0.6))
            header_text = f"Details — Page {{page_num}} — #{{position_in_page}} — {{detail_page_num}}/{{Config.DETAIL_PAGES_PER_TODO}}"
            c.drawString(Config.MARGIN_LEFT, arrow_y, header_text)
            
            # Lien "Index" du côté opposé (à droite)
            index_text = "Index"
            index_text_width = c.stringWidth(index_text, "Helvetica-Bold", Config.FONT_SIZE_DETAIL)
            index_x = Config.PAGE_WIDTH - Config.MARGIN_RIGHT - index_text_width
            c.drawString(index_x, arrow_y, index_text)
            
            # Lien retour vers la page de liste
            header_width = c.stringWidth(header_text, "Helvetica-Bold", Config.FONT_SIZE_DETAIL)
            source_bookmark = f"page_{{page_num}}"
            c.linkRect("", source_bookmark, 
                      (arrow_x, arrow_y - 5, Config.MARGIN_LEFT + header_width, arrow_y + 15))
            
            # Lien vers l'index
            c.linkRect("", "index", 
                      (index_x, arrow_y - 5, index_x + index_text_width, arrow_y + 15))
            
            # Navigation links (Previous/Next)
            c.setFont("Helvetica", 10)
            c.setFillColor(Color(0.5, 0.5, 0.5))
            
            # Previous link (if not first page)
            if detail_page_num > 1:
                prev_text = "< Prev"
                prev_x = Config.MARGIN_LEFT
                prev_y = Config.MARGIN_BOTTOM - 12
                c.drawString(prev_x, prev_y, prev_text)
                prev_bookmark = f"detail_{{idx}}_{{detail_page_num - 1}}"
                c.linkRect("", prev_bookmark, 
                          (prev_x, prev_y - 3, prev_x + c.stringWidth(prev_text, "Helvetica", 10), prev_y + 10))
            
            # Next link (if not last page)
            if detail_page_num < Config.DETAIL_PAGES_PER_TODO:
                next_text = "Next >"
                next_x = Config.PAGE_WIDTH - Config.MARGIN_RIGHT - c.stringWidth(next_text, "Helvetica", 10)
                next_y = Config.MARGIN_BOTTOM - 12
                c.drawString(next_x, next_y, next_text)
                next_bookmark = f"detail_{{idx}}_{{detail_page_num + 1}}"
                c.linkRect("", next_bookmark, 
                          (next_x, next_y - 3, Config.PAGE_WIDTH - Config.MARGIN_RIGHT, next_y + 10))
            
            c.showPage()'''
            
            function_section = function_section[:detail_start] + new_detail_code + function_section[detail_end:]
    
    # Fix index page to show all todo pages dynamically
    # Replace hardcoded items_per_col = 8
    index_fix_original = """    usable_width = Config.PAGE_WIDTH - Config.MARGIN_LEFT - Config.MARGIN_RIGHT
    cols = 2
    items_per_col = 8  # 8 pages par colonne"""
    
    # Calculate items per column based on actual pages
    index_fix_new = f"""    usable_width = Config.PAGE_WIDTH - Config.MARGIN_LEFT - Config.MARGIN_RIGHT
    cols = 2
    # Dynamic items per column based on actual todo pages
    items_per_col = (Config.PAGES_OF_TODOS + cols - 1) // cols  # Ceiling division"""
    
    function_section = function_section.replace(index_fix_original, index_fix_new)
    
    # Also need to adjust the usable height calculation based on number of pages
    height_fix_original = """    # Utiliser seulement la moitié de la hauteur disponible pour chaque colonne
    usable_height = (y_top - Config.MARGIN_BOTTOM) / 2  # Moitié de la hauteur"""
    
    # Use half page for ≤30 pages (to leave bottom half blank), full page for >30
    height_fix_new = f"""    # Use half page for ≤30 pages, full page for >30 pages
    if Config.PAGES_OF_TODOS <= 30:
        usable_height = (y_top - Config.MARGIN_BOTTOM) / 2  # Half height to leave bottom blank
    else:
        usable_height = y_top - Config.MARGIN_BOTTOM  # Full available height for many pages"""
    
    function_section = function_section.replace(height_fix_original, height_fix_new)
    
    # Combine everything with title page function
    new_code = imports_section + config_code + "\n" + title_page_function + "\n" + function_section
    
    # Write temporary generator file
    temp_generator = "temp_generator.py"
    with open(temp_generator, "w") as f:
        f.write(new_code)
    
    # Debug: Also save a copy for inspection if guide lines are enabled
    if guide_lines_enabled:
        with open("debug_generator_with_guides.py", "w") as f:
            f.write(new_code)
        st.success(f"✓ Guide lines enabled - Colors: H={guide_h_color}, V={guide_v_color}")
    
    # Debug: Show what we're generating and verify the config
    st.code(f"Generating PDF with {int(pages_of_todos)} todo pages, {int(items_per_col)} items per column", language="text")
    
    # Check if the config was properly written
    with open(temp_generator, "r") as f:
        temp_content = f.read()
        if f"PAGES_OF_TODOS = {int(pages_of_todos)}" in temp_content:
            st.success(f"✓ Config verified: PAGES_OF_TODOS = {int(pages_of_todos)}")
        else:
            st.error(f"⚠️ Config issue: PAGES_OF_TODOS may not be set correctly")
            # Find what's actually in the file
            import re
            match = re.search(r'PAGES_OF_TODOS = (\d+)', temp_content)
            if match:
                st.warning(f"Found: PAGES_OF_TODOS = {match.group(1)}")
        
        # Also check ITEMS_PER_COL
        if f"ITEMS_PER_COL = {int(items_per_col)}" in temp_content:
            st.success(f"✓ Config verified: ITEMS_PER_COL = {int(items_per_col)}")
        else:
            st.error(f"⚠️ Config issue: ITEMS_PER_COL may not be set correctly")
            match = re.search(r'ITEMS_PER_COL = (\d+)', temp_content)
            if match:
                st.warning(f"Found: ITEMS_PER_COL = {match.group(1)}")
    
    # Run the generator
    with st.spinner("Generating PDF..."):
        try:
            result = subprocess.run(
                [sys.executable, temp_generator],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Success
                st.success(f"✅ PDF generated successfully: {output_filename}")
                
                # Show file size
                if os.path.exists(output_filename):
                    size_mb = os.path.getsize(output_filename) / (1024 * 1024)
                    total_pages = 1 + pages_of_todos + (pages_of_todos * items_per_col * columns * detail_pages_per_todo)
                    
                    st.info(f"""
                    📊 **Generated PDF Stats:**
                    - File: {output_filename}
                    - Size: {size_mb:.2f} MB
                    - Total Pages: {total_pages:,}
                    - Todo Pages: {pages_of_todos}
                    - Detail Pages: {pages_of_todos * items_per_col * columns * detail_pages_per_todo:,}
                    """)
                    
                    # Download button
                    with open(output_filename, "rb") as f:
                        st.download_button(
                            label="📥 Download PDF",
                            data=f,
                            file_name=output_filename,
                            mime="application/pdf",
                            use_container_width=True
                        )
            else:
                st.error(f"Error generating PDF: {result.stderr}")
                st.code(result.stdout, language="text")  # Show stdout too
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
        finally:
            # Clean up temp file
            if os.path.exists(temp_generator):
                os.remove(temp_generator)

# Gallery Tab
with main_tabs[1]:
    render_gallery_ui(config_manager)

# About Tab  
with main_tabs[2]:
    st.markdown("""
    ### About This App
    
    **📄 PDF Todo Generator**
    Generate customizable PDF templates for todo lists and note-taking, optimized for both printing and e-readers.
    
    **🎨 Configuration Gallery**
    - Browse and share configurations with the community
    - Each configuration gets a unique 8-character ID
    - No user accounts required - fully anonymous
    - Configurations are public and shareable
    
    **💡 How Sharing Works**
    - When you publish a configuration, it gets a unique hash ID (e.g., `a3f2b8c1`)
    - Share this ID with others so they can load your exact configuration
    - Same configuration always generates the same ID (no duplicates)
    - All shared configurations are public
    
    **🔧 Features**
    - Custom page sizes (A4, Letter, or pixels for e-readers)
    - Configurable margins, spacing, and layout
    - Guide lines for better organization
    - Landscape/portrait orientation
    - Export configurations for sharing
    
    **📝 Note**
    This is a community tool. Shared configurations are public and can be accessed by anyone with the ID.
    """)

# Instructions
with st.expander("ℹ️ How to use"):
    st.markdown("""
    1. Adjust the configuration parameters using the sliders and inputs above
    2. Click **Generate PDF** to create your custom PDF
    3. Download the generated file
    
    **Tips:**
    - Smaller dot spacing = denser grid
    - More todo pages = more items to track
    - 2 detail pages per todo gives more space for notes
    """)

# Footer
st.markdown("---")
st.markdown("Made with Streamlit • [View Source](generator-pdf-todo-boox-double-details_16.py)")