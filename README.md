# 📝 A4 PDF Todo Generator

## Viwoods AiPaper : Meetings & actions

Le nouveau carnet comprend 200 Meetings non datés, deux pages de notes par
Meeting, 10 listes de 40 tâches et deux pages de contexte par tâche. Le format
AiPaper et la police Manrope sont configurés par défaut, avec des liens internes.

### Télécharger les exemples complets

Les deux PDF sont prêts à importer sur la tablette, sans installation :

| Langue / Language | Téléchargement / Download | Contenu | Taille |
| --- | --- | --- | --- |
| Français | [Télécharger le carnet PDF](examples/aipaper-manrope-200j.pdf?raw=true) | 1 416 pages | ≈ 9 Mo |
| English | [Download the PDF notebook](examples/aipaper-manrope-en-200d.pdf?raw=true) | 1,416 pages | ≈ 9 MB |

Chaque carnet contient 200 journées non datées, 400 tâches et **30 533 liens
internes**. Les versions française et anglaise ont la même mise en page Manrope
au format Viwoods AiPaper (1 920 × 2 560 px à 300 ppp). Ce sont des carnets vierges
complets, pas seulement des aperçus. Les exemplaires publiés sont versionnés dans
[`examples/`](examples/).

### Lancer ou régénérer en local

**[Installation locale et régénération sans interface → PLANNER.md](PLANNER.md)**

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements-local.txt
venv/bin/python -m streamlit run pdf_generator_ui.py --server.address=127.0.0.1
```

Pour régénérer les deux langues sans interface :

```bash
venv/bin/python generate_planner.py
venv/bin/python generate_planner.py --language en
```

Les PDF sont créés dans `output/pdf/`. Dans l’interface, le champ **Langue du PDF**
permet de choisir Français ou English. Le générateur historique reste accessible
dans la barre latérale de l’interface ; sa documentation suit ci-dessous.

### Variante datée : calendrier, semaines et backlog

Le mode **Viwoods daté** ajoute un calendrier mensuel cliquable, des Meetings
datés et une à trois listes d’actions par semaine. Les listes actuelles deviennent
le **backlog permanent**, avec les mêmes fiches de notes détaillées.

- **Calendrier → date → Meeting**, ou numéro **Wxx → actions de la semaine**.
- **Meeting → semaine → backlog** ; les onglets Wxx permettent de revenir à la
  semaine choisie depuis chaque liste et chaque fiche de contexte.
- Dans la semaine, écrire **02-12** pour désigner une tâche du backlog ; dans le
  backlog, écrire **W38** pour se rappeler la semaine. Ces références restent
  manuscrites : ce sont les boutons imprimés qui assurent la navigation.

Exemples distincts, du **16 septembre au 15 décembre 2026** : 91 journées,
14 semaines et 400 tâches permanentes, soit **1 102 pages** par carnet.

| Français | English |
| --- | --- |
| [Télécharger le carnet daté](examples/dated/dated-aipaper-manrope-fr-2026-09-16-2026-12-15.pdf?raw=true) | [Download the dated planner](examples/dated/dated-aipaper-manrope-en-2026-09-16-2026-12-15.pdf?raw=true) |

```bash
venv/bin/python generate_dated_planner.py --start-date 2026-09-16 --months 3
venv/bin/python generate_dated_planner.py --start-date 2026-09-16 --months 3 --language en
```

La date de début et la durée (1, 2 ou 3 mois) se choisissent aussi dans l’interface.
Les sorties datées vont dans `output/pdf/dated/`. **Le générateur et les deux PDF
non datés restent inchangés** ; un test compare leur régénération octet pour octet
aux exemples publiés. [Détails de la variante datée](PLANNER.md#variante-datée).

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
git clone https://github.com/oreglio/pdf-generator.git
cd pdf-generator
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
| Boox Note Max | 3200×2400 | 300 | 13.3" |
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
