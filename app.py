import streamlit as st
import fitz  # PyMuPDF
import io

def generate_pdf(input_pdf_stream, template_idx, name, date_str):
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
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                insert_point = fitz.Point(rect.x0, rect.y1 - 2)
                font_name = "helv-bold" if is_bold else "helv"
                page.insert_text(insert_point, new_value, fontsize=f_size, fontname=font_name, color=(0, 0, 0))
    
    # Save to memory buffer
    output_buffer = io.BytesIO()
    # Create new PDF with only the selected page
    output_doc = fitz.open()
    output_doc.insert_pdf(doc, from_page=template_idx, to_page=template_idx)
    output_doc.save(output_buffer)
    output_doc.close()
    
    return output_buffer.getvalue()

# --- APP LAYOUT ---
st.title("🎓 Certificate Generator")
st.write("Upload the blank certificate and fill in the details below.")

# File Uploader
uploaded_file = st.file_uploader("Upload 'Onboarding Certificate [CR team].pdf'", type="pdf")

# Form Inputs
with st.form("certificate_form"):
    emp_name = st.text_input("Employee Name", placeholder="Mario Rossi")
    cert_date = st.text_input("Date", value="12-Dec-2025")
    
    # Template Selection
    option = st.selectbox(
        "Select Template Version",
        ("Monitoring (2 Signers)", "Monitoring (1 Signer)", "EasyMap")
    )
    
    submitted = st.form_submit_button("Generate Certificate")

if submitted and uploaded_file and emp_name:
    # Map selection to page index
    # Page 4 = index 3, Page 5 = index 4, Page 10 = index 9
    idx_map = {
        "Monitoring (2 Signers)": 3,
        "Monitoring (1 Signer)": 4,
        "EasyMap": 9
    }
    
    with st.spinner("Creating PDF..."):
        pdf_bytes = generate_pdf(uploaded_file, idx_map[option], emp_name, cert_date)
        
    st.success(f"Certificate ready for {emp_name}!")
    
    st.download_button(
        label="⬇️ Download PDF",
        data=pdf_bytes,
        file_name=f"{emp_name.replace(' ', '_')}_Certificate.pdf",
        mime="application/pdf"
    )
