from PIL import Image
from pathlib import Path
import base64
from openai import OpenAI
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader


def validate_images(path="files"):
    for p in Path("files").glob("*.*"):
        # JPEG images are already in the correct format
        if p.suffix.lower() in {".jpg", ".jpeg"}: 
            continue
        
        # Non-image files ignored
        try:
            Image.open(p).verify()
        except Exception:
            continue

        try:
            img = Image.open(p)
            if img.mode in ("RGBA", "LA"):
                # Convert images with transparency to a solid background
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])  # Preserve transparency
                bg.save(p.with_suffix(".jpg"), "JPEG", quality=99)
                p.unlink()  # Delete the previous image
            else:
                Image.open(p).convert("RGB").save(p.with_suffix(".jpg"), "JPEG", quality=99)
                p.unlink()  # Delete the previous image
                
        except Exception as e:
            raise RuntimeError(f"Failed to convert {p}: {e}")
        
    return True
        
def jpgs_to_pdf(jpg_folder, output_pdf):
    jpg_files = [f for f in os.listdir(jpg_folder) if f.lower().endswith('.jpg')]
    jpg_files.sort()
    c = canvas.Canvas(output_pdf, pagesize=letter)
    page_w, page_h = letter
    for jpg in jpg_files:
        img_path = os.path.join(jpg_folder, jpg)
        img = Image.open(img_path)
        # Resize image to exactly fill the page (may stretch/distort)
        img_resized = img.resize((int(page_w), int(page_h)), Image.LANCZOS)
        img_io = ImageReader(img_resized)
        c.drawImage(img_io, 0, 0, page_w, page_h)
        c.showPage()
    c.save()
    return output_pdf