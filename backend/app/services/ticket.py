import io
import json
import logging
import qrcode
from typing import Dict, Any

logger = logging.getLogger(__name__)

class TicketService:
    """
    Service for generating QR codes for tickets.
    """
    
    def generate_qr_code(self, payload: Dict[str, Any]) -> bytes:
        """
        Generates a QR code from the provided payload and returns the image bytes.
        The payload is converted to a JSON string.
        """
        try:
            # Convert payload to deterministic JSON string
            payload_str = json.dumps(payload, sort_keys=True)
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(payload_str)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to bytes buffer
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue()
            
        except Exception as e:
            logger.error(f"Failed to generate QR code: {str(e)}")
            raise

ticket_service = TicketService()
