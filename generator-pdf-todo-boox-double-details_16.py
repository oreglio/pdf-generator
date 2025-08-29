#!/usr/bin/env python3
"""
Generator PDF To-Do pour Boox avec XObject (Python + ReportLab)
================================================================
- Utilise Form XObject pour réutiliser le motif de points
- Génère 100 pages de listes + 8000 pages de détail (2 par todo)
- Chaque todo a maintenant 2 pages de détails
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Configuration
class Config:
    # Page A4 portrait
    PAGE_WIDTH, PAGE_HEIGHT = A4
    
    # Marges
    MARGIN_LEFT = 8 * mm
    MARGIN_RIGHT = 8 * mm
    MARGIN_TOP = 18 * mm
    MARGIN_BOTTOM = 8 * mm
    
    # Grille de points
    DOT_SPACING = 7 * mm
    DOT_RADIUS = 0.3 * mm  # Plus gros pour être bien visible
    DOT_COLOR = Color(0.7, 0.7, 0.7)  # Gris plus foncé
    
    # Layout
    ITEMS_PER_COL = 20
    COLUMNS = 2
    PAGES_OF_TODOS = 30
    DETAIL_PAGES_PER_TODO = 2  # Nouveau: 2 pages de détail par todo
    
    # Polices
    FONT_SIZE_HEADER = 14
    FONT_SIZE_ICON = 13
    FONT_SIZE_DETAIL = 12
    FONT_SIZE_NUM = 7
    
    # Couleurs
    COLOR_LINE = HexColor('#696969')
    COLOR_TEXT = HexColor('#454545')
    COLOR_NUM = Color(0.85, 0.85, 0.85)

def create_pdf():
    """Génère le PDF avec XObject pour les points et 2 pages de détail par todo"""
    
    output_file = "todo-boox-double-details_16_v1.0.1.pdf"
    c = canvas.Canvas(output_file, pagesize=A4)
    
    # Métadonnées
    c.setTitle("Todo Boox - 100 pages avec double détails")
    c.setAuthor("Generator Python Double Details")
    
    print("⏳ Génération du PDF avec XObject et double détails...")
    print("📊 Configuration:")
    print("  → Pages de liste: SANS points (économie)")
    print("  → Pages de détail: 2 pages par todo avec grille XObject réutilisée")
    
    # ============================================
    # CRÉER LE FORM XOBJECT POUR LES POINTS (UNE SEULE FOIS!)
    # ============================================
    
    print("\n🎨 Création du XObject pour la grille de points...")
    
    # Définir le form XObject
    c.beginForm("dotPattern", lowerx=0, lowery=0, 
                upperx=Config.PAGE_WIDTH, uppery=Config.PAGE_HEIGHT)
    
    # Dessiner les points dans le form
    c.setFillColor(Config.DOT_COLOR)
    x_start = Config.MARGIN_LEFT
    x_end = Config.PAGE_WIDTH - Config.MARGIN_RIGHT
    y_start = Config.MARGIN_BOTTOM
    y_end = Config.PAGE_HEIGHT - Config.MARGIN_TOP
    
    dot_count = 0
    x = x_start
    while x <= x_end:
        y = y_start
        while y <= y_end:
            c.circle(x, y, Config.DOT_RADIUS, stroke=0, fill=1)
            y += Config.DOT_SPACING
            dot_count += 1
        x += Config.DOT_SPACING
    
    c.endForm()
    
    print(f"  → XObject créé avec {dot_count} points (défini une seule fois!)")
    
    # ============================================
    # PAGE D'INDEX
    # ============================================
    
    print("\n📚 Création de la page d'index...")
    
    # Créer un bookmark pour l'index
    c.bookmarkPage("index")
    
    # PAS de grille sur l'index
    c.setFont("Helvetica-Bold", Config.FONT_SIZE_HEADER + 2)
    c.setFillColor(Config.COLOR_TEXT)
    c.drawString(Config.MARGIN_LEFT, Config.PAGE_HEIGHT - Config.MARGIN_TOP + 15,
                 "Index")
    
    # Liens vers les pages
    c.setFont("Helvetica", 12)
    c.setFillColor(Config.COLOR_LINE)
    
    usable_width = Config.PAGE_WIDTH - Config.MARGIN_LEFT - Config.MARGIN_RIGHT
    cols = 2
    items_per_col = 8  # 8 pages par colonne
    col_width = usable_width / cols
    y_top = Config.PAGE_HEIGHT - Config.MARGIN_TOP - 40 
    # Utiliser seulement la moitié de la hauteur disponible pour chaque colonne
    usable_height = (y_top - Config.MARGIN_BOTTOM) / 2  # Moitié de la hauteur
    line_height = usable_height / items_per_col
    
    # Stocker les positions pour les liens
    index_links = []
    
    for col in range(cols):
        x = Config.MARGIN_LEFT + col * col_width
        y = y_top
        
        for i in range(items_per_col):
            page_num = col * items_per_col + i + 1
            if page_num > Config.PAGES_OF_TODOS:
                break
            
            text = f"P{page_num}"
            c.drawString(x, y, text)
            
            # Ajouter un trait après le texte (même style que les todos)
            text_width = c.stringWidth(text, "Helvetica", 12)
            line_start_x = x + text_width + 3 * mm  # 3mm d'espace après le texte
            line_end_x = x + col_width - 10 * mm    # Laisser un peu de marge à droite
            
            c.setStrokeColor(Config.COLOR_LINE)
            c.setLineWidth(0.5)
            c.line(line_start_x, y, line_end_x, y)
            
            # Stocker pour créer le lien plus tard
            # ReportLab utilise des bookmarks et liens internes
            link_name = f"page_{page_num}"
            c.bookmarkPage(link_name)
            c.linkRect("", link_name, (x, y - 3, x + 50, y + 12))
            
            y -= line_height
    
    c.showPage()
    
    # ============================================
    # PAGES DE LISTE (sans points)
    # ============================================
    
    print("\n📝 Création des pages de liste...")
    
    usable_width = Config.PAGE_WIDTH - Config.MARGIN_LEFT - Config.MARGIN_RIGHT
    col_width = usable_width / Config.COLUMNS
    inner_height = Config.PAGE_HEIGHT - Config.MARGIN_TOP - Config.MARGIN_BOTTOM - 12 * mm
    line_gap = inner_height / Config.ITEMS_PER_COL
    
    # Stocker les infos pour les liens
    detail_page_info = []
    
    for p in range(Config.PAGES_OF_TODOS):
        if p % 10 == 0:
            print(f"  Page {p + 1}/{Config.PAGES_OF_TODOS}...")
        
        # Créer un bookmark pour cette page
        page_bookmark = f"page_{p + 1}"
        c.bookmarkPage(page_bookmark)
        
        # PAS de grille sur les pages de liste
        
        # En-tête de page
        c.setFont("Helvetica-Bold", Config.FONT_SIZE_HEADER)
        c.setFillColor(Config.COLOR_TEXT)
        page_text = f"Page {p + 1}"
        text_width = c.stringWidth(page_text, "Helvetica-Bold", Config.FONT_SIZE_HEADER)
        header_x = Config.PAGE_WIDTH - Config.MARGIN_RIGHT - text_width
        header_y = Config.PAGE_HEIGHT - Config.MARGIN_TOP + 15  # Remonté de 15 points
        c.drawString(header_x, header_y, page_text)
        
        # Lien retour vers l'index sur le texte "Page X"
        c.linkRect("", "index", (header_x, header_y - 5, header_x + text_width, header_y + 15))
        
        # Dessiner les lignes de todo
        c.setFont("Helvetica", 10)
        top_y = Config.PAGE_HEIGHT - Config.MARGIN_TOP - 30
        
        for col in range(Config.COLUMNS):
            x0 = Config.MARGIN_LEFT + col * col_width
            y = top_y
            
            for i in range(Config.ITEMS_PER_COL):
                global_idx = p * Config.ITEMS_PER_COL * Config.COLUMNS + col * Config.ITEMS_PER_COL + i + 1
                todo_num = ((global_idx - 1) % (Config.ITEMS_PER_COL * Config.COLUMNS)) + 1
                
                # Numéro dans la marge
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
                
                c.drawString(num_x, y - 1 * mm, str(todo_num))
                
                # Ligne de todo
                c.setStrokeColor(Config.COLOR_LINE)
                c.setLineWidth(0.5)
                line_right = x0 + col_width - 16 * mm
                c.line(x0, y, line_right, y)
                
                # Icône ">" pour lien vers détail
                c.setFont("Helvetica-Bold", Config.FONT_SIZE_ICON)
                c.setFillColor(HexColor('#555555'))
                box_x1 = x0 + col_width - 14 * mm
                box_x2 = box_x1 + 10 * mm
                box_y1 = y - 2.8 * mm
                box_y2 = y + 2.8 * mm
                
                icon_x = (box_x1 + box_x2) / 2 - 1.6 * mm
                # Aligner le chevron avec la ligne de todo (plus haut)
                icon_y = y - 2 * mm  # Aligné plus haut avec la ligne
                c.drawString(icon_x - 2, icon_y + 6 , ">")
                
                # Créer le lien vers la première page de détail
                detail_bookmark = f"detail_{global_idx}_1"
                c.linkRect("", detail_bookmark, (box_x1, box_y1, box_x2, box_y2))
                
                y -= line_gap
        
        c.showPage()
    
    # ============================================
    # PAGES DE DÉTAIL (avec grille XObject) - 2 pages par todo
    # ============================================
    
    print("\n📄 Création des pages de détail (2 pages par todo)...")
    total_items = Config.PAGES_OF_TODOS * Config.ITEMS_PER_COL * Config.COLUMNS
    
    for idx in range(1, total_items + 1):
        if (idx - 1) % 400 == 0:
            print(f"  Todo {idx}/{total_items} (2 pages chacun)...")
        
        # Calculer le numéro de page et position
        page_num = ((idx - 1) // (Config.ITEMS_PER_COL * Config.COLUMNS)) + 1
        position_in_page = ((idx - 1) % (Config.ITEMS_PER_COL * Config.COLUMNS)) + 1
        
        # ===== PREMIÈRE PAGE DE DÉTAIL =====
        # UTILISER LE XOBJECT (pas de redessiner!)
        c.doForm("dotPattern")
        
        # Bookmark pour cette première page de détail
        detail_bookmark_1 = f"detail_{idx}_1"
        c.bookmarkPage(detail_bookmark_1)
        
        # En-tête avec flèche de retour
        c.setFont("Helvetica-Bold", Config.FONT_SIZE_DETAIL)
        
        # Position remontée de 1cm et couleur gris clair
        arrow_x = Config.MARGIN_LEFT - 4 * mm
        arrow_y = Config.PAGE_HEIGHT - Config.MARGIN_TOP + 10 * mm  # Remonté de 10mm (1cm)
        
        # Flèche retour en gris clair
        c.setFillColor(Color(0.6, 0.6, 0.6))  # Gris clair
        c.drawString(arrow_x, arrow_y, "<")
        
        # Texte du header en gris clair avec indication de page 1/2
        c.setFillColor(Color(0.6, 0.6, 0.6))  # Gris clair
        header_text = f"Details — Page {page_num} — #{position_in_page} — 1/2"
        c.drawString(Config.MARGIN_LEFT, arrow_y, header_text)
        
        # Lien "Index" du côté opposé (à droite)
        index_text = "Index"
        index_text_width = c.stringWidth(index_text, "Helvetica-Bold", Config.FONT_SIZE_DETAIL)
        index_x = Config.PAGE_WIDTH - Config.MARGIN_RIGHT - index_text_width
        c.drawString(index_x, arrow_y, index_text)
        
        # Lien retour vers la page de liste
        header_width = c.stringWidth(header_text, "Helvetica-Bold", Config.FONT_SIZE_DETAIL)
        source_bookmark = f"page_{page_num}"
        c.linkRect("", source_bookmark, 
                  (arrow_x, arrow_y - 5, Config.MARGIN_LEFT + header_width, arrow_y + 15))
        
        # Lien vers l'index
        c.linkRect("", "index", 
                  (index_x, arrow_y - 5, index_x + index_text_width, arrow_y + 15))
        
        # Lien vers la page suivante (2ème page de détail)
        c.setFont("Helvetica", 10)
        c.setFillColor(Color(0.5, 0.5, 0.5))
        next_text = "Next >"
        next_x = Config.PAGE_WIDTH - Config.MARGIN_RIGHT - c.stringWidth(next_text, "Helvetica", 10)
        next_y = Config.MARGIN_BOTTOM - 12
        c.drawString(next_x, next_y, next_text)
        
        # Lien vers la deuxième page de détail
        detail_bookmark_2 = f"detail_{idx}_2"
        c.linkRect("", detail_bookmark_2, 
                  (next_x, next_y - 3, Config.PAGE_WIDTH - Config.MARGIN_RIGHT, next_y + 10))
        
        c.showPage()
        
        # ===== DEUXIÈME PAGE DE DÉTAIL =====
        # UTILISER LE XOBJECT à nouveau
        c.doForm("dotPattern")
        
        # Bookmark pour cette deuxième page de détail
        c.bookmarkPage(detail_bookmark_2)
        
        # En-tête avec flèche de retour
        c.setFont("Helvetica-Bold", Config.FONT_SIZE_DETAIL)
        
        # Flèche retour en gris clair
        c.setFillColor(Color(0.6, 0.6, 0.6))  # Gris clair
        c.drawString(arrow_x, arrow_y, "<")
        
        # Texte du header en gris clair avec indication de page 2/2
        c.setFillColor(Color(0.6, 0.6, 0.6))  # Gris clair
        header_text = f"Details — Page {page_num} — #{position_in_page} — 2/2"
        c.drawString(Config.MARGIN_LEFT, arrow_y, header_text)
        
        # Lien "Index" du côté opposé (à droite)
        index_text = "Index"
        index_text_width = c.stringWidth(index_text, "Helvetica-Bold", Config.FONT_SIZE_DETAIL)
        index_x = Config.PAGE_WIDTH - Config.MARGIN_RIGHT - index_text_width
        c.drawString(index_x, arrow_y, index_text)
        
        # Lien retour vers la page de liste
        header_width = c.stringWidth(header_text, "Helvetica-Bold", Config.FONT_SIZE_DETAIL)
        c.linkRect("", source_bookmark, 
                  (arrow_x, arrow_y - 5, Config.MARGIN_LEFT + header_width, arrow_y + 15))
        
        # Lien vers l'index
        c.linkRect("", "index", 
                  (index_x, arrow_y - 5, index_x + index_text_width, arrow_y + 15))
        
        # Lien vers la page précédente (1ère page de détail)
        c.setFont("Helvetica", 10)
        c.setFillColor(Color(0.5, 0.5, 0.5))
        prev_text = "< Prev"
        prev_x = Config.MARGIN_LEFT
        prev_y = Config.MARGIN_BOTTOM - 12
        c.drawString(prev_x, prev_y, prev_text)
        
        # Lien vers la première page de détail
        c.linkRect("", detail_bookmark_1, 
                  (prev_x, prev_y - 3, prev_x + c.stringWidth(prev_text, "Helvetica", 10), prev_y + 10))
        
        c.showPage()
    
    # ============================================
    # FINALISATION
    # ============================================
    
    # Ajouter les liens des pages de liste vers les détails
    print("\n🔗 Finalisation des liens...")
    
    # Note: Dans ReportLab, les liens internes sont créés au fur et à mesure
    # Les bookmarks et liens sont déjà en place
    
    # Sauvegarder le PDF
    print("\n💾 Sauvegarde du PDF...")
    c.save()
    
    # Statistiques
    file_size = os.path.getsize(output_file)
    file_size_mb = file_size / (1024 * 1024)
    
    total_detail_pages = total_items * Config.DETAIL_PAGES_PER_TODO
    
    print(f"\n✅ Fichier généré: {output_file}")
    print(f"📦 Taille du fichier: {file_size_mb:.2f} MB")
    print(f"📊 Statistiques:")
    print(f"  → 1 page d'index (sans points)")
    print(f"  → {Config.PAGES_OF_TODOS} pages de liste (sans points)")
    print(f"  → {total_detail_pages} pages de détail ({Config.DETAIL_PAGES_PER_TODO} par todo, avec XObject réutilisé)")
    print(f"  → Total: {1 + Config.PAGES_OF_TODOS + total_detail_pages} pages")
    print(f"  → Grille de {dot_count} points définie UNE SEULE FOIS")
    print(f"\n🎉 Chaque todo a maintenant {Config.DETAIL_PAGES_PER_TODO} pages de détail pour plus d'espace!")

if __name__ == "__main__":
    create_pdf()