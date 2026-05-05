
import os
import base64
import uuid
from flask import current_app
from werkzeug.utils import secure_filename

def save_base64_image(data_url, folder='img'):
    """
    Decodes a base64 Data URL and saves it as an image file.
    Returns the filename.
    """
    if not data_url:
        return None

    # Parse the data URL
    # Format: data:image/png;base64,iVBORw...
    try:
        header, encoded = data_url.split(',', 1)
        # Verify it's an image
        if 'image/' not in header:
            return None
            
        ext = header.split(';')[0].split('/')[1]
        if ext == 'jpeg': ext = 'jpg'
        
        # specific fix for svg
        if 'svg+xml' in header: ext = 'svg'

        # Generate unique filename
        filename = f"{uuid.uuid4().hex}.{ext}"
        
        # Ensure directory exists
        path = os.path.join(current_app.static_folder, folder)
        os.makedirs(path, exist_ok=True)
        
        # Save file
        file_path = os.path.join(path, filename)
        with open(file_path, 'wb') as f:
            f.write(base64.b64decode(encoded))
            
        return filename
    except Exception as e:
        print(f"Error saving image: {e}")
        return None
