with open("app.py", "w",encoding = "utf-8") as f:
    f.write("""
import streamlit as st
import psycopg2
import os
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from symspellpy import SymSpell, Verbosity

# PostgreSQL connection details
DB_HOST = "localhost"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "9965"
DB_PORT = "5432"

# Define paths
poppler_path = r"C:\\Program Files\\poppler-24.08.0\\Library\\bin"
tesseract_path = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = tesseract_path

# Initialize SymSpell
sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
dictionary_path = r"D:\\space kids india\\en-80k.txt"

if not sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1):
    st.error("Dictionary file not found! Check the file path.")
    st.stop()

# Function to correct spelling
def correct_spelling(text):
    words = text.split()
    corrected_words = [sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)[0].term if sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2) else word for word in words]
    return " ".join(corrected_words)

# Function to connect to PostgreSQL
def connect_to_db():
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT
        )
        return conn
    except Exception as e:
        st.error(f"Failed to connect to PostgreSQL: {e}")
        return None

# Ensure database table exists
def initialize_db():
    conn = connect_to_db()
    if conn:
        with conn.cursor() as cursor:
            cursor.execute(\"\"\"
                CREATE TABLE IF NOT EXISTS extracted_text (
                    id SERIAL PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    page_number INT DEFAULT NULL,
                    corrected_text TEXT NOT NULL
                )
            \"\"\")
            conn.commit()
        conn.close()

# Upload File via Streamlit
st.title(" PDF & Image Text Extraction with Streamlit")
uploaded_file = st.file_uploader("Upload a PDF or Image", type=["pdf", "png", "jpg", "jpeg", "bmp", "tiff", "gif"])

if uploaded_file is not None:
    file_name = uploaded_file.name
    conn = connect_to_db()
    if conn:
        initialize_db()
        cursor = conn.cursor()
        
        if uploaded_file.type == "application/pdf":
            images = convert_from_path(uploaded_file, poppler_path=poppler_path, dpi=300)
            for i, image in enumerate(images, start=1):
                text = pytesseract.image_to_string(image, lang='eng')
                corrected_text = correct_spelling(text)
                cursor.execute("INSERT INTO extracted_text (file_name, page_number, corrected_text) VALUES (%s, %s, %s)",
                               (file_name, i, corrected_text))
                conn.commit()
                st.success(f"Page {i} processed and stored in database.")
        else:
            image = Image.open(uploaded_file)
            text = pytesseract.image_to_string(image, lang='eng')
            corrected_text = correct_spelling(text)
            cursor.execute("INSERT INTO extracted_text (file_name, corrected_text) VALUES (%s, %s)",
                           (file_name, corrected_text))
            conn.commit()
            st.success("Image text saved to PostgreSQL successfully!")
        
        cursor.close()
        conn.close()

# Search Extracted Text
st.header("Search Extracted Text")
search_type = st.selectbox("Search by", ["ID", "File Name", "Page Number"])
search_value = st.text_input("Enter search value")

if st.button("Search"):
    conn = connect_to_db()
    if conn:
        query = "SELECT id, file_name, page_number, corrected_text FROM extracted_text WHERE "
        
        if search_type == "ID":
            query += "id = %s"
        elif search_type == "File Name":
            query += "file_name = %s"
        elif search_type == "Page Number":
            query += "page_number = %s"
        
        with conn.cursor() as cursor:
            cursor.execute(query, (search_value,))
            results = cursor.fetchall()
            
            if results:
                for row in results:
                    st.write(f"** ID:** {row[0]}  **| File Name:** {row[1]}  **| Page:** {row[2]}")
                    st.text_area(" Extracted Text:", row[3], height=150)
            else:
                st.warning(" No results found.")
        conn.close()
""")
