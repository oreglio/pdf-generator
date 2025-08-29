# 📝 A4 PDF Todo Generator

A powerful, customizable PDF generator for creating todo lists and detail pages, optimized for A4 paper and e-readers (Boox, reMarkable, etc.).

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.29.0-red)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ Features

- 📄 **Flexible Page Formats**: A3, A4, A5, Letter, Legal, Tabloid, or custom sizes
- 📱 **E-Reader Optimized**: Support for custom resolutions with PPI input (perfect for Boox, reMarkable, Kindle Scribe)
- 🎨 **Fully Customizable**:
  - Adjustable margins with auto-scaling
  - Configurable dot grid (spacing, size, color)
  - Variable items per column (10-30)
  - Multiple detail pages per todo (1-5)
  - Font sizes for all elements
  - Todo number placement options
- 💾 **Save/Load Configurations**: Store and reuse your favorite settings
- 👁️ **Live Preview**: See changes instantly before generating
- 🚀 **High Performance**: Uses Form XObject for efficient PDF generation

## 🖼️ Screenshots

### Main Interface
- Clean, intuitive web interface
- Real-time preview of your PDF layout
- Organized configuration sections

### Generated PDFs
- **Index Page**: Quick navigation to all todo pages
- **Todo Pages**: Numbered items with detail page links
- **Detail Pages**: Dot grid pages for extended notes (2 pages per todo by default)

## 🚀 Quick Start

### Option 1: Local Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/pdf-todo-generator.git
cd pdf-todo-generator
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
streamlit run pdf_generator_ui.py
```

5. **Open in browser**
Navigate to `http://localhost:8501`

### Option 2: Docker

```bash
docker build -t pdf-generator .
docker run -p 8501:8501 -v $(pwd)/saved_configs:/app/saved_configs -v $(pwd)/generated_pdfs:/app/generated_pdfs pdf-generator
```

## 📖 Usage Guide

### Basic Usage

1. **Select Page Format**
   - Choose from preset formats (A4, A5, etc.)
   - Or select "Custom" for specific dimensions

2. **Configure Layout**
   - Set margins (or use auto-scaling)
   - Adjust dot grid density
   - Choose number of todo items per column

3. **Customize Appearance**
   - Font sizes for headers, icons, numbers
   - Colors for lines and text
   - Todo number placement

4. **Generate PDF**
   - Click "Update Preview" to see changes
   - Click "Generate PDF" to create final document
   - Download the generated file

### Custom E-Reader Setup

For e-readers like Boox Note Air 3:

1. Select "Custom" page format
2. Choose "Pixels + PPI" input method
3. Enter your device specs:
   - Width: 1872 pixels
   - Height: 1404 pixels  
   - PPI: 227
4. Enable auto-scaling for optimal layout

### Common E-Reader Resolutions

| Device | Resolution | PPI | Screen Size |
|--------|------------|-----|-------------|
| Boox Note Air 3 | 1872×1404 | 227 | 10.3" |
| Boox Note Max | 2200×1650 | 207 | 13.3" |
| reMarkable 2 | 1872×1404 | 226 | 10.3" |
| Kindle Scribe | 1860×2480 | 300 | 10.2" |
| iPad Pro 11" | 2388×1668 | 264 | 11" |

## ⚙️ Configuration Options

### Page Layout
- **Page Format**: Preset or custom dimensions
- **Margins**: Auto-scaling or manual (2-40mm)
- **Orientation**: Portrait (default)

### Dot Grid
- **Spacing**: 3-15mm between dots
- **Radius**: 0.1-1.0mm dot size
- **Color**: Grayscale intensity (0.3-0.9)
- **Auto-scaling**: Adapts to page size

### Content Structure
- **Items per Column**: 10-30 items
- **Columns**: 1 or 2 columns
- **Todo Pages**: 10-100 pages
- **Detail Pages**: 1-5 pages per todo

### Typography
- **Header Size**: 10-20pt
- **Icon Size**: 10-18pt (for ">" symbol)
- **Detail Size**: 10-16pt
- **Number Size**: 5-10pt

### Todo Numbers
- **Placement Options**:
  - Outside (left/right margins)
  - Inside (left of line)
  - Inside (right of line)
  - Hidden
- **Position Offset**: Fine-tune X/Y position

### Output Quality
- **Standard (72 DPI)**: Screen viewing
- **High (150 DPI)**: Good quality
- **Print (300 DPI)**: E-readers
- **Maximum (600 DPI)**: Professional printing

## 💾 Configuration Management

### Saving Configurations
1. Configure all settings as desired
2. Enter a name for your configuration
3. Click "Save Configuration"
4. Configuration is stored in `saved_configs/` directory

### Loading Configurations
1. Select from dropdown of saved configurations
2. Click "Load Configuration"
3. All settings are restored instantly

## 🛠️ Advanced Features

### Auto-Scaling
The app intelligently scales the following based on page size:
- Margins (proportional to page dimensions)
- Dot spacing (maintains visual density)
- Items per column (based on available height)
- Detail page header position

### Efficient PDF Generation
- Uses ReportLab's Form XObject for dot patterns
- Reuses dot grid across all detail pages
- Generates compact PDFs even with thousands of pages

## 📁 Project Structure

```
pdf-todo-generator/
├── pdf_generator_ui.py              # Main Streamlit interface
├── generator-pdf-todo-boox-double-details_16.py  # Core PDF generator
├── requirements.txt                  # Python dependencies
├── README.md                        # This file
├── LICENSE                          # MIT License
├── saved_configs/                   # Stored configurations (JSON)
│   └── .gitkeep
└── generated_pdfs/                  # Output directory
    └── .gitkeep
```

## 🔧 Requirements

- Python 3.9+
- Streamlit 1.29.0
- ReportLab 4.0.7

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for the web interface
- PDF generation powered by [ReportLab](https://www.reportlab.com/)
- Optimized for [Boox](https://www.boox.com/) e-readers and similar devices

## 📧 Contact

For questions or suggestions, please open an issue on GitHub.

---
Made with ❤️ for productivity enthusiasts and e-reader users