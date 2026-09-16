#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x venv/bin/python ]; then
    echo "L’environnement Python local est absent. Consultez PLANNER.md pour l’installation."
    read -r -p "Appuyez sur Entrée pour fermer."
    exit 1
fi
exec venv/bin/python -m streamlit run pdf_generator_ui.py --server.address=127.0.0.1
