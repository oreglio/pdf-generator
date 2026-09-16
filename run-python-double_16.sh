#!/bin/bash

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel Python..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import reportlab" 2>/dev/null; then
    echo "📦 Installation de ReportLab dans l'environnement virtuel..."
    pip install reportlab
fi

# Run the Python PDF generator with XObject
echo "🚀 Lancement du générateur Python avec XObject..."
python generator-pdf-todo-boox-double-details_16.py

# Deactivate virtual environment
deactivate