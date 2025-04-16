import os
from mistralai.client import MistralClient
import base64
from PIL import Image
import io
import PyPDF2

class OCRService:
    def __init__(self):
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not found in environment variables")
        self.client = MistralClient(api_key=api_key)
        self.model = "mistral-large-latest"

    def encode_image_to_base64(self, image_bytes: bytes, content_type: str) -> str:
        """Convert image bytes to base64 string"""
        return base64.b64encode(image_bytes).decode('utf-8')

    async def extract_text(self, content: bytes, content_type: str) -> str:
        """Extract text from image/PDF using Mistral's vision capabilities"""
        try:
            # Special case for text files - just return the content
            if content_type == 'text/plain':
                return content.decode('utf-8', errors='ignore')
                    
            # For PDF files, use PyPDF2
            if content_type == 'application/pdf':
                return self._extract_text_from_pdf(content)
                
            # For images, use Mistral's vision capabilities
            return await self._process_image(content, content_type)
                
        except Exception as e:
            raise Exception(f"Text extraction error: {str(e)}")

    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF using PyPDF2"""
        try:
            # Create a file-like object from bytes
            pdf_file = io.BytesIO(pdf_content)
            
            # Create PDF reader object
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
            
            if not text.strip():
                # If no text was extracted, the PDF might be scanned
                return "This appears to be a scanned PDF without extractable text. Please upload a text-based PDF."
                
            return text
        except Exception as e:
            return f"Error extracting text from PDF: {str(e)}"

    async def _process_image(self, image_bytes: bytes, content_type: str) -> str:
        """Process a single image using Mistral"""
        base64_image = self.encode_image_to_base64(image_bytes, content_type)
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": content_type,
                            "data": base64_image
                        }
                    },
                    {
                        "type": "text",
                        "text": "Please extract all the text from this image. Return only the extracted text, formatted exactly as it appears in the image."
                    }
                ]
            }
        ]

        response = self.client.chat.complete(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content

    async def analyze_text(self, text_content: str) -> str:
        """Analyze the extracted text using Mistral"""
        messages = [
            {
                "role": "system",
                "content": """
                You are an academic paper analyzer. Analyze the given paper and extract:
                1. Main thesis/argument
                2. Key findings
                3. Methodology
                4. Limitations
                5. Future research directions
                Provide structured, concise responses.
                """
            },
            {
                "role": "user",
                "content": f"Analyze this academic paper:\n\n{text_content}"
            }
        ]

        try:
            response = self.client.chat.complete(
                model=self.model,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Mistral analysis error: {str(e)}") 