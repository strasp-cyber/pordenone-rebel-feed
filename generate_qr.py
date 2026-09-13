import os
import qrcode
from PIL import Image, ImageDraw, ImageOps, ImageFont

TARGET_URL = "https://pordenone-rebel-feed.onrender.com"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_IMG_DIR = os.path.join(BASE_DIR, "static", "img")
ARTIFACT_DIR = "/Users/stefanoraspa/.gemini/antigravity/brain/178bdf58-88a9-45d4-8d5a-f04aedbb36fa"

def generate_qr():
    # 1. Crea il QR Code HD con correzione errore ALTA (H = 30% recuperabile)
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=20,
        border=2,
    )
    qr.add_data(TARGET_URL)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF").convert("RGBA")
    qr_w, qr_h = qr_img.size

    # 2. Carica il logo da posizionare al centro del QR Code
    logo_path = os.path.join(STATIC_IMG_DIR, "iniziativalibertaria.jpg")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        
        # Dimensione logo: 22% del QR code
        logo_size = int(qr_w * 0.22)
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

        # Crea maschera circolare
        mask = Image.new("L", (logo_size, logo_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, logo_size, logo_size), fill=255)
        
        circular_logo = ImageOps.fit(logo, (logo_size, logo_size))
        circular_logo.putalpha(mask)

        # Sfondo bianco circolare leggermente più grande con bordo rosso
        border_size = int(logo_size * 1.15)
        border_img = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border_img)
        border_draw.ellipse((0, 0, border_size, border_size), fill="#FFFFFF", outline="#DC2626", width=int(border_size * 0.05))

        offset = (border_size - logo_size) // 2
        border_img.paste(circular_logo, (offset, offset), circular_logo)

        pos = ((qr_w - border_size) // 2, (qr_h - border_size) // 2)
        qr_img.paste(border_img, pos, border_img)

    # Salva QR Code puro HD
    qr_pure_path = os.path.join(STATIC_IMG_DIR, "qr_code_pordenone_rebel.png")
    qr_img.save(qr_pure_path, "PNG")
    
    artifact_qr_path = os.path.join(ARTIFACT_DIR, "qr_code_pordenone_rebel.png")
    qr_img.save(artifact_qr_path, "PNG")
    print(f"QR Code salvato: {qr_pure_path}")

    # 3. Creazione Locandina Grafica A4 pronta per la stampa
    card_w = 1240
    card_h = 1754 # Proporzione standard A4
    card = Image.new("RGBA", (card_w, card_h), "#F8FAFC")
    draw = ImageDraw.Draw(card)

    font_path_bold = "/System/Library/Fonts/Supplemental/Arial.ttf"
    font_path_regular = "/System/Library/Fonts/Helvetica.ttc"
    
    font_title = ImageFont.truetype(font_path_bold, 54)
    font_subtitle = ImageFont.truetype(font_path_regular, 28)
    font_scan = ImageFont.truetype(font_path_bold, 40)
    font_desc = ImageFont.truetype(font_path_regular, 28)
    font_url = ImageFont.truetype(font_path_bold, 32)
    font_footer = ImageFont.truetype(font_path_regular, 24)

    # Header scuro elegante
    header_h = 320
    draw.rectangle([0, 0, card_w, header_h], fill="#0F172A")
    draw.rectangle([0, header_h - 10, card_w, header_h], fill="#DC2626") # accento rosso

    # Disegna i due loghi in cima
    logo1 = Image.open(os.path.join(STATIC_IMG_DIR, "iniziativalibertaria.jpg")).convert("RGBA")
    logo2 = Image.open(os.path.join(STATIC_IMG_DIR, "amicizapatisti.jpg")).convert("RGBA")
    
    def make_round(img, size):
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        m = Image.new("L", (size, size), 0)
        ImageDraw.Draw(m).ellipse((0, 0, size, size), fill=255)
        res = ImageOps.fit(img, (size, size))
        res.putalpha(m)
        return res

    thumb_size = 140
    r_logo1 = make_round(logo1, thumb_size)
    r_logo2 = make_round(logo2, thumb_size)
    
    # Contenitore circolare per i loghi
    card.paste(r_logo1, (100, 90), r_logo1)
    card.paste(r_logo2, (260, 90), r_logo2)

    # Testo Header
    draw.text((440, 95), "PORDENONE REBEL FEED", fill="#FFFFFF", font=font_title)
    draw.text((440, 175), "Bacheca Comunicati & Prossimi Eventi", fill="#CBD5E1", font=font_subtitle)
    draw.text((440, 220), "Iniziativa Libertaria • Amici Zapatisti", fill="#EF4444", font=font_subtitle)

    # Box bianco centrale per il QR code
    box_w = 980
    box_h = 1000
    box_x = (card_w - box_w) // 2
    box_y = 390
    draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + box_h], radius=36, fill="#FFFFFF", outline="#E2E8F0", width=3)

    # Titolo scansione
    draw.text((card_w // 2, box_y + 60), "INQUADRA CON LA FOTOCAMERA", fill="#0F172A", font=font_scan, anchor="mm")
    draw.text((card_w // 2, box_y + 115), "per aprire la bacheca e salvare l'app sul tuo smartphone", fill="#64748B", font=font_desc, anchor="mm")

    # Incolla il QR code
    qr_display_size = 640
    qr_card_resized = qr_img.resize((qr_display_size, qr_display_size), Image.Resampling.LANCZOS)
    card.paste(qr_card_resized, ((card_w - qr_display_size) // 2, box_y + 160), qr_card_resized)

    # Badge pillola con link in fondo al box
    pill_w = 780
    pill_h = 80
    pill_x = (card_w - pill_w) // 2
    pill_y = box_y + 860
    draw.rounded_rectangle([pill_x, pill_y, pill_x + pill_w, pill_y + pill_h], radius=24, fill="#F1F5F9", outline="#CBD5E1", width=2)
    draw.text((card_w // 2, pill_y + 40), "pordenone-rebel-feed.onrender.com", fill="#DC2626", font=font_url, anchor="mm")

    # Istruzioni smartphone in basso
    draw.text((card_w // 2, 1470), "Ottimizzato per iPhone & Android", fill="#0F172A", font=font_scan, anchor="mm")
    draw.text((card_w // 2, 1530), "Nessun download dagli store richiesto • Si installa con 1 tocco", fill="#475569", font=font_desc, anchor="mm")
    draw.text((card_w // 2, 1650), "Pordenone Rebel Aggregator • Progetto Libero e Autogestito", fill="#94A3B8", font=font_footer, anchor="mm")

    card_pure_path = os.path.join(STATIC_IMG_DIR, "locandina_stampa_qr.png")
    card.save(card_pure_path, "PNG")

    artifact_card_path = os.path.join(ARTIFACT_DIR, "locandina_stampa_qr.png")
    card.save(artifact_card_path, "PNG")
    print(f"Locandina salvata: {card_pure_path}")

if __name__ == "__main__":
    generate_qr()
