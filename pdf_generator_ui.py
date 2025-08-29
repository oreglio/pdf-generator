#!/usr/bin/env python3
"""
Web Interface for A4 PDF Generator
Using Streamlit for easy configuration
"""

import streamlit as st
import subprocess
import os
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, A3, letter, legal, B4, B5
# Define tabloid size (11x17 inches)
tabloid = (11*72, 17*72)  # 72 points per inch
from PIL import Image
import io
import json
from datetime import datetime

# Import the generator module
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(
    page_title="A4 PDF Todo Generator",
    page_icon="📄",
    layout="wide"  # Changed to wide for side-by-side layout
)

st.title("📄 A4 PDF Todo Generator")
st.markdown("Configure and generate your custom PDF with todo lists and detail pages")

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

def generate_preview(config_dict, page_size=A4):
    """Generate a preview of the first todo page as PNG"""
    from reportlab.graphics import renderPM
    from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
    from reportlab.lib import colors
    
    # Page size in points
    PAGE_WIDTH, PAGE_HEIGHT = page_size
    
    # Create a simple PIL image directly
    img_width = int(PAGE_WIDTH)
    img_height = int(PAGE_HEIGHT) 
    
    # Create white background image
    img = Image.new('RGB', (img_width, img_height), 'white')
    
    # For a simpler preview, let's just generate a PDF and return it as bytes
    # We'll use the PDF embed which works well in Streamlit
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(PAGE_WIDTH, PAGE_HEIGHT))
    
    # White background
    c.setFillColor(colors.white)
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
                c.setFillColor(Color(config_dict['num_color'], config_dict['num_color'], config_dict['num_color']))
                
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
    return buffer

# Configuration save/load UI
with st.expander("💾 Save/Load Configuration", expanded=False):
    col_save, col_load = st.columns(2)
    
    with col_save:
        st.markdown("**Save Current Configuration**")
        config_name = st.text_input("Configuration name", value="my_config")
        if st.button("💾 Save Configuration"):
            # We'll collect the config after the form
            st.session_state['save_config'] = config_name
            st.success(f"Configuration will be saved as '{config_name}' after updating preview")
    
    with col_load:
        st.markdown("**Load Saved Configuration**")
        saved_configs = list_saved_configs()
        if saved_configs:
            selected_config = st.selectbox("Select configuration", [""] + saved_configs)
            if st.button("📂 Load Configuration"):
                if selected_config:
                    loaded = load_config(selected_config)
                    if loaded:
                        st.session_state['loaded_config'] = loaded
                        st.success(f"Loaded configuration: {selected_config}")
                        st.rerun()
        else:
            st.info("No saved configurations found")

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
                **Boox Note Max:** 2200×1650 @ 207 PPI (13.3")  
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
    
    # Smart margin defaults based on page size (proportional)
    # Scale margins proportionally to page size relative to A4
    margin_scale = min(page_width_mm / 210, page_height_mm / 297)
    
    # Base margins for A4: 8mm horizontal, 18mm top, 8mm bottom
    default_margin_h = max(3, round(8 * margin_scale))  # Min 3mm
    default_margin_v = max(5, round(18 * margin_scale))  # Min 5mm for top
    default_margin_bottom = max(3, round(8 * margin_scale))  # Min 3mm for bottom
    
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
        
        st.header("📊 Content Structure")
        
        # Auto-scale items per column based on page height
        auto_items = st.checkbox(
            "Auto-scale items per column for page size",
            value=default_config.get('auto_items', False),
            help="Automatically adjust number of items based on available page height"
        )
        
        col5, col6 = st.columns(2)
        
        with col5:
            if auto_items:
                # Calculate based on available height
                available_height = page_height_mm - margin_top - margin_bottom - 30  # 30mm for header
                # Assume ~12mm per item (based on A4 having 20 items in ~240mm)
                items_per_col_default = min(30, max(10, int(available_height / 12)))
                items_per_col = int(items_per_col_default)
                st.info(f"Auto: {items_per_col} items (based on {available_height:.0f}mm available height)")
            else:
                items_per_col_input = st.number_input("Items per Column", min_value=10, max_value=30, value=int(default_config.get('items_per_col', 20)), step=1)
                items_per_col = int(items_per_col_input)
                st.caption(f"Current value: {items_per_col}")  # Debug display
            columns = st.radio("Number of Columns", [1, 2], index=[1, 2].index(default_config.get('columns', 2)))
        
        with col6:
            pages_of_todos = int(st.number_input("Number of Todo Pages", min_value=10, max_value=100, value=int(default_config.get('pages_of_todos', 30)), step=1))
            detail_pages_per_todo = st.selectbox("Detail Pages per Todo", [1, 2, 3, 4, 5], index=[1, 2, 3, 4, 5].index(default_config.get('detail_pages_per_todo', 2)))
        
        st.header("🔤 Font Sizes")
        col7, col8 = st.columns(2)
        
        with col7:
            font_size_header = st.slider("Header Font Size", 10, 20, default_config.get('font_size_header', 14))
            font_size_icon = st.slider("Icon Font Size", 10, 18, default_config.get('font_size_icon', 13))
        
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
            num_color = st.slider("Number Color (Gray)", 0.3, 1.0, default_config.get('num_color', 0.85), step=0.05)
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
    
    # Generate preview when button is clicked or on first load
    if preview_clicked or 'preview_config' not in st.session_state:
        # Create configuration dictionary
        config = {
            'page_format': page_format,
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
            'num_color': num_color,
            'num_placement': num_placement,
            'num_offset_x_left': num_offset_x_left,
            'num_offset_x_right': num_offset_x_right,
            'num_offset_y': num_offset_y,
            'pdf_quality_index': ["Standard (72 DPI)", "High (150 DPI)", "Print (300 DPI)", "Maximum (600 DPI)"].index(pdf_quality)
        }
        
        # Generate preview
        with st.spinner("Generating preview..."):
            preview_pdf = generate_preview(config, page_size)
            
            # Display the PDF preview using iframe
            import base64
            pdf_bytes = preview_pdf.read()
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            
            # Adjust height based on screen
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf" style="border: 1px solid #ddd; border-radius: 5px;"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        
        # Save configuration if requested
        if 'save_config' in st.session_state:
            config['output_filename'] = output_filename
            save_config(config, st.session_state['save_config'])
            st.success(f"✅ Configuration saved as '{st.session_state['save_config']}'")
            del st.session_state['save_config']
        
        pages_info = f"Configured for {pages_of_todos} todo pages + {pages_of_todos * items_per_col * columns * detail_pages_per_todo:,} detail pages"
        st.caption(f"Preview shows page 1 only. {pages_info}. Click 'Update Preview' after changing settings.")

if submitted:
    # Prepare page size for config
    if page_format == "Custom":
        page_size_str = f"({custom_width} * mm, {custom_height} * mm)"
    else:
        # Extract just the format name (A4, A5, etc.) from the display string
        page_size_str = page_format.split(" ")[0]
    
    # Create a modified version of the generator with new config
    config_code = f"""
#!/usr/bin/env python3
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, A3, letter, legal, B4, B5
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
    COLOR_NUM = Color({num_color}, {num_color}, {num_color})
    
    # Number placement configuration
    NUM_PLACEMENT = "{num_placement}"
    NUM_OFFSET_X_LEFT = {num_offset_x_left} * mm
    NUM_OFFSET_X_RIGHT = {num_offset_x_right} * mm
    NUM_OFFSET_Y = {num_offset_y} * mm
"""
    
    # Read the original generator and replace the config
    with open("generator-pdf-todo-boox-double-details_16.py", "r") as f:
        original_code = f.read()
    
    # Find where the Config class ends and main function starts
    import_end = original_code.find("def create_pdf")
    
    # Get the imports section
    imports_section = original_code[:original_code.find("# Configuration")]
    
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
    
    # Combine everything
    new_code = imports_section + config_code + "\n" + function_section
    
    # Write temporary generator file
    temp_generator = "temp_generator.py"
    with open(temp_generator, "w") as f:
        f.write(new_code)
    
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
                ["python3", temp_generator],
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