from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

# ---------------------------------
# GitHub Models Configuration
# ---------------------------------

API_KEY = os.getenv("GITHUB_TOKEN")

if not API_KEY:
    raise ValueError("GITHUB_TOKEN not found in .env")

MODEL_NAME = "openai/gpt-4.1-mini"

client = OpenAI(
    base_url="https://models.github.ai/inference",
    api_key=API_KEY,
)

# ---------------------------------
# Microsoft Graph Configuration
# (Future use — not required yet)
# ---------------------------------

CLIENT_ID = os.getenv("CLIENT_ID", "")
TENANT_ID = os.getenv("TENANT_ID", "")

# ---------------------------------
# Business Central Configuration
# ---------------------------------

BC_CLIENT_ID = os.getenv("BC_CLIENT_ID", "")
BC_CLIENT_SECRET = os.getenv("BC_CLIENT_SECRET", "")
BC_TENANT_ID = os.getenv("BC_TENANT_ID", "")
BC_ENVIRONMENT = os.getenv("BC_ENVIRONMENT", "Sandbox_Sumit")
BC_COMPANY_ID = os.getenv("BC_COMPANY_ID", "")
BC_MODE = os.getenv("BC_MODE", "mock")

# ---------------------------------
# Journals Team Configuration
# ---------------------------------

# Email address to forward journal subscription
# requests to when detected in a book quote email
# Leave blank to skip forwarding
JOURNALS_TEAM_EMAIL = os.getenv("JOURNALS_TEAM_EMAIL", "")

# ---------------------------------
# Tesseract OCR Configuration
# ---------------------------------

# Optional: set full path to tesseract.exe in .env
# If not set, system PATH is used automatically
TESSERACT_PATH = os.getenv("TESSERACT_PATH", "")

# ---------------------------------
# Business Rules
# ---------------------------------

CONFIDENCE_THRESHOLD = 0.90

# Minimum characters extracted from a PDF page
# before it is considered a scanned (image-based) page
# and OCR fallback is triggered
PDF_TEXT_THRESHOLD = 50