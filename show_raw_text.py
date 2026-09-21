import fitz
doc = fitz.open("temp.pdf")
text = "\n".join(page.get_text() for page in doc)
doc.close()
print(text)