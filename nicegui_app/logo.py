"""Logo helper module for TJM Time Calendar."""
import base64
from pathlib import Path


def get_logo_data_url():
    """Return the TJM logo as a base64 data URL."""
    logo_path = Path(__file__).parent / 'static' / 'TJMLogo.png'
    with open(logo_path, 'rb') as f:
        logo_bytes = f.read()
    logo_base64 = base64.b64encode(logo_bytes).decode('utf-8')
    return f'data:image/png;base64,{logo_base64}'


# Pre-compute the logo data URL for faster access
LOGO_DATA_URL = get_logo_data_url()
