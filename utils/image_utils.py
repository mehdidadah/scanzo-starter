from PIL import Image
import io


def optimize_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """
    Optimise l'image pour réduire les tokens et le temps.
    max_size réduit à 1024 pour performance
    """
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convert RGBA to RGB if needed
    if img.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    
    # Resize more aggressively for speed
    if max(img.size) > max_size:
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        img.thumbnail((max_size, max_size), resample)
    
    # Save with lower quality for smaller size
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=75, optimize=True)
    output.seek(0)
    
    return output.read()
