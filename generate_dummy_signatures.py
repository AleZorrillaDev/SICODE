import os
from PIL import Image, ImageDraw, ImageFont

firmas = [
    'Director General',
    'Subdirector de Gestión',
    'Jefe de Área',
    'Gerente de Operaciones',
    'Coordinador Legal',
    'Especialista Tributario',
    'Asistente Administrativo'
]

output_dir = os.path.join('app', 'modulos', 'autodoc', 'firmas')
os.makedirs(output_dir, exist_ok=True)

for firma in firmas:
    img = Image.new('RGBA', (400, 200), color=(255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a simple box and text to simulate a stamp/signature
    draw.rectangle([10, 10, 390, 190], outline=(0, 51, 153), width=5)
    draw.line([50, 150, 350, 150], fill=(0, 51, 153), width=3)
    
    # Text
    draw.text((120, 160), firma, fill=(0, 51, 153))
    
    # Save
    safe_name = firma.strip() + ".png"
    img.save(os.path.join(output_dir, safe_name))

print("Dummy signatures generated in", output_dir)
