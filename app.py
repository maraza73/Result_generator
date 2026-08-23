import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import zipfile
from PIL import Image
from google import genai
from google.genai import types
import json

# Streamlit Page Config
st.set_page_config(page_title="AI Result Card Generator", layout="wide")
st.title("🎓 AI Result Card Generator")

# Sidebar Configurations
st.sidebar.header("1. API Configuration")
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

st.sidebar.header("2. Academy Details")
academy_name = st.sidebar.text_input("Academy Name", "THE STEP-UP ACADEMY")
address = st.sidebar.text_input("Address", "Lahore, Pakistan")

# Function to extract structured data from image using updated SDK
def extract_data_from_image(image, key):
    client = genai.Client(api_key=key)
    
    prompt = """
    Extract all student results from this image. Return ONLY a valid JSON array where each object represents a student.
    Keys required for each student:
    - Name (string)
    - RollNo (string)
    - Class (string)
    - Subject names as keys and their obtained marks as numeric values (e.g. "Math": 85, "Physics": 90)
    
    Do not wrap response in markdown fence. Plain JSON array only.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[image, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    
    text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

# Function to generate individual PDF Result Card
def generate_pdf(student_data, academy, addr):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Header / Academy Title
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(300, 750, academy)
    p.setFont("Helvetica", 10)
    p.drawCentredString(300, 735, addr)
    p.line(50, 720, 550, 720)
    
    # Student Metadata
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, 690, f"Student Name: {student_data.get('Name', '')}")
    p.drawString(350, 690, f"Roll No: {student_data.get('RollNo', '')}")
    p.drawString(50, 670, f"Class: {student_data.get('Class', '')}")
    
    # Marks Table Header
    p.line(50, 650, 550, 650)
    p.drawString(60, 635, "Subject")
    p.drawString(250, 635, "Total Marks")
    p.drawString(400, 635, "Obtained Marks")
    p.line(50, 625, 550, 625)
    
    # Table Rows Parsing
    y = 605
    p.setFont("Helvetica", 11)
    ignore_cols = ['Name', 'RollNo', 'Class']
    
    for key, val in student_data.items():
        if key not in ignore_cols:
            p.drawString(60, y, str(key))
            p.drawString(250, y, "100")
            p.drawString(400, y, str(val))
            y -= 20
            
    p.line(50, y+10, 550, y+10)
    
    # Signatures
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, 100, "Teacher's Signature: ____________")
    p.drawString(380, 100, "Principal's Signature: ____________")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.getvalue()

# Input Options Tab
tab1, tab2 = st.tabs(["📸 Upload Handwritten Image", "📊 Upload Excel/CSV"])

with tab1:
    uploaded_img = st.file_uploader("Upload Image of Result Sheet (JPG/PNG)", type=['jpg', 'jpeg', 'png'])
    if uploaded_img:
        image = Image.open(uploaded_img)
        st.image(image, caption="Uploaded Result Page", use_container_width=True)
        
        if st.button("✨ Extract Data with Gemini AI"):
            if not api_key:
                st.error("Please enter your Gemini API Key in the sidebar first!")
            else:
                with st.spinner("AI is reading handwritten marks..."):
                    try:
                        raw_data = extract_data_from_image(image, api_key)
                        st.session_state['data'] = pd.DataFrame(raw_data)
                        st.success("Extraction Complete!")
                    except Exception as e:
                        st.error(f"Error processing image: {e}")

with tab2:
    uploaded_file = st.file_uploader("Upload CSV or Excel Sheet", type=['csv', 'xlsx'])
    if uploaded_file:
        if uploaded_file.name.endswith('.csv'):
            st.session_state['data'] = pd.read_csv(uploaded_file)
        else:
            st.session_state['data'] = pd.read_excel(uploaded_file)

# Data Verification and PDF Generation Area
if 'data' in st.session_state and st.session_state['data'] is not None:
    st.markdown("---")
    st.subheader("📋 Verify & Edit Extracted Results")
    st.info("Check for any handwriting misreadings before generating final PDFs.")
    
    edited_df = st.data_editor(st.session_state['data'], num_rows="dynamic")
    
    if st.button("🚀 Generate All Result Cards (PDF)"):
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for idx, row in edited_df.iterrows():
                data_dict = row.dropna().to_dict()
                pdf_bytes = generate_pdf(data_dict, academy_name, address)
                student_name = data_dict.get('Name', f'Student_{idx+1}')
                zf.writestr(f"{student_name}_ResultCard.pdf", pdf_bytes)
                
        zip_buffer.seek(0)
        
        st.success("✅ All PDF Result Cards Generated Successfully!")
        st.download_button(
            label="📦 Download All PDFs (ZIP)",
            data=zip_buffer,
            file_name="Result_Cards.zip",
            mime="application/zip"
        )
