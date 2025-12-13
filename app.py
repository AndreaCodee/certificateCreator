import streamlit as st
import fitz  # PyMuPDF
import io

def generate_pdf(input_pdf_stream, template_idx, name, date_str):
    # Read the uploaded file from memory
    doc = fitz.open(stream=input_pdf_stream.read(), filetype="pdf")
    page = doc[template_idx]
    
    # Define replacements
    replacements = [
        ("[Employee Name]", name, 12, True),
        ("DD-MMM-YYYY", date_str, 12, False)
    ]

    for placeholder, new_value, f_size, is_bold in replacements:
        instances = page.search_for(placeholder)
        if instances:
            for rect in instances:
                # White-out the old text
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                
                # Insert new text
                insert_point = fitz.Point(rect.x0, rect.y1 - 2)
                
                # --- FIX: USE 'hebo' FOR BOLD, 'helv' FOR REGULAR ---
                font_name = "hebo" if is_bold else "helv"
                
                page.insert_text(
                    insert_point, 
                    new_value, 
                    fontsize=f_size, 
                    fontname=font_name, 
                    color=(0, 0, 0)
                )
    
    # Save the modified PDF to a memory buffer (not a file on disk)
    output_buffer = io.BytesIO()
    
    # Create a new PDF with ONLY the selected page
    output_doc = fitz.open()
    output_doc.insert_pdf(doc, from_page=template_idx, to_page=template_idx)
    output_doc.save(output_buffer)
    output_doc.close()
    
    return output_buffer.getvalue()

# --- STREAMLIT USER INTERFACE ---
st.title("🎓 Certificate Generator")
st.write("Upload the blank certificate PDF below.")

# 1. File Uploader
uploaded_file = st.file_uploader("Upload 'Onboarding Certificate [CR team].pdf'", type="pdf")

if uploaded_file:
    # 2. Form Inputs (Only show if file is uploaded)
    with st.form("certificate_form"):
        st.subheader("Certificate Details")
        emp_name = st.text_input("Employee Name", placeholder="Mario Rossi")
        cert_date = st.text_input("Date", value="12-Dec-2025")
        
        # Template Selection
        option = st.selectbox(
            "Select Template Version",
            ("Monitoring (2 Signers)", "Monitoring (1 Signer)", "EasyMap")
        )
        
        submitted = st.form_submit_button("Generate Certificate")

    # 3. Process the Form
    if submitted and emp_name:
        # Map user selection to page index
        idx_map = {
            "Monitoring (2 Signers)": 3,  # Page 4
            "Monitoring (1 Signer)": 4,   # Page 5
            "EasyMap": 9                  # Page 10
        }
        
        try:
            # We must reset the file pointer to the beginning before reading it
            uploaded_file.seek(0)
            
            with st.spinner("Creating PDF..."):
                pdf_bytes = generate
