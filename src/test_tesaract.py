import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Users\agarg2\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
)

print("Version:", pytesseract.get_tesseract_version())