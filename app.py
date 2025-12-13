import streamlit as st
import fitz  # PyMuPDF
import io
import os
from datetime import datetime

# --- CONFIGURATION ---
TEMPLATE_FILENAME = "Onboarding Certificate [CR team].pdf"

def generate_pdf(filename, template_idx, name, date_str):
    # Open the file directly from the disk
    doc = fitz.open(filename)
    page = doc[template_idx]
    
    # 1. ANALYZE REFERENCE TEXT ("We acknowledge that")
    ref_phrase = "We acknowledge that"
    ref_instances = page.search_for(ref_phrase)
    
    # Default values
    ref_y = None
    ref_height = 12 
    
    if ref_instances:
        ref_rect = ref_instances[0] 
        ref_y = ref_rect.y1 
        ref_height = ref_rect.height 
    
    # 2. DEFINE REPLACEMENTS
    replacements = [
        {"placeholder": "[Employee Name]", "value": name, "is_name": True},
        {"placeholder": "DD-MMM-YYYY", "value": date_str, "is_name": False}
    ]

    insertions = []

    # 3. MARK OLD TEXT FOR DELETION & CALCULATE NEW POSITIONS
    for item in replacements:
        instances = page.search_for(item["placeholder"])
        
        if instances:
            for rect in instances:
                page.add_redact_annot(rect)
                
                if item["is_name"] and ref_y:
                    f_size = ref_height * 0.95 
                    insert_y = ref_y - 2 
                else:
                    f_size = rect.height * 0.9
                    insert_y = rect.y1 - 2

                insertions.append({
                    "x": rect.x0,
                    "y": insert_y,
                    "text": item["value"],
                    "size": f_size,
                    "font": "hebo" if item["is_name"] else "helv"
                })

    # 4. APPLY REDACTION
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_IMAGE_NONE)

    # 5. INSERT NEW TEXT
    for insert in insertions:
        page.insert_text(
            fitz.Point(insert["x"], insert["y"]),
            insert["text"],
            fontsize=insert["size"],
            fontname=insert["font"],
            color=(1, 1, 1) # Pure White
        )
    
    output_buffer = io.BytesIO()
    output_doc = fitz.open()
    output_doc.insert_pdf(doc, from_page=template_idx, to_page=template_idx)
    output_doc.save(output_buffer)
    output_doc.close()
    
    return output_buffer.getvalue()

# --- STREAMLIT USER INTERFACE ---
st.set_page_config(page_title="Cert Generator", layout="centered")

st.title("🎓 Certificate Generator")

if not os.path.exists(TEMPLATE_FILENAME):
    st.error(f"⚠️ Error: The file '{TEMPLATE_FILENAME}' was not found.")
    st.info("Please make sure the PDF is in the same folder as this script.")
else:
    st.write("Fill in the details below to generate a new certificate.")
    
    # Get today's date formatted as DD-MMM-YYYY (e.g., 13-Dec-2025)
    today_str = datetime.today().strftime('%d-%b-%Y')
    
    with st.form("certificate_form"):
        st.subheader("1. Enter Details")
        col1, col2 = st.columns(2)
        with col1:
            emp_name = st.text_input("Employee Name", placeholder="Mario Rossi")
        with col2:
            # Set default value to today_str
            cert_date = st.text_input("Date", value=today_str)
        
        st.subheader("2. Select Template")
        option = st.selectbox("Version", ("Monitoring (2 Signers)", "Monitoring (1 Signer)", "EasyMap"))
        
        submitted = st.form_submit_button("Generate Certificate")

    if submitted and emp_name:
        idx_map = {"Monitoring (2 Signers)": 3, "Monitoring (1 Signer)": 4, "EasyMap": 9}
        
        try:
            with st.spinner("Processing..."):
                pdf_bytes = generate_pdf(TEMPLATE_FILENAME, idx_map[option], emp_name, cert_date)
            
            st.success(f"✅ Ready: {emp_name}")
            
            st.download_button(
                label="⬇️ Download PDF", 
                data=pdf_bytes, 
                file_name=f"{emp_name.replace(' ', '_')}_Certificate.pdf", 
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"An error occurred: {e}")
