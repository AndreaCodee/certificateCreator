import streamlit as st
import fitz  # PyMuPDF
import io

def hex_to_rgb(hex_color):
    """Converts hex color (e.g., #FFFFFF) to a tuple (1, 1, 1) for PyMuPDF"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

def generate_pdf(input_pdf_stream, template_idx, name, date_str, text_rgb):
    # Read the uploaded file
    doc = fitz.open(stream=input_pdf_stream.read(), filetype="pdf")
    page = doc[template_idx]
    
    # Define replacements
    replacements = [
        ("[Employee Name]", name, 12, True),
        ("DD-MMM-YYYY", date_str, 12, False)
    ]

    # Store future insertions here so we can erase everything first
    insertions_queue = []

    # 1. MARK TEXT FOR DELETION
    for placeholder, new_value, f_size, is_bold in replacements:
        instances = page.search_for(placeholder)
        
        if instances:
            for rect in instances:
                # Add a "Redaction Annotation" (marks area for deletion)
                page.add_redact_annot(rect)
                
                # Save coordinates for the new text
                insertions_queue.append({
                    "rect": rect,
                    "text": new_value,
                    "size": f_size,
                    "bold": is_bold
                })

    # 2. APPLY DELETION (Preserving Images)
    # This deletes the text marked above, but keeps background images/graphics intact.
    page.apply_redactions(
        images=fitz.PDF_REDACT_IMAGE_NONE, 
        graphics=fitz.PDF_REDACT_IMAGE_NONE
    )

    # 3. INSERT NEW TEXT
    for item in insertions_queue:
        rect = item["rect"]
        
        # Adjust Y position slightly (-2) to align with baseline
        insert_point = fitz.Point(rect.x0, rect.y1 - 2)
        
        font_name = "hebo" if item["bold"] else "helv"
        
        page.insert_text(
            insert_point, 
            item["text"], 
            fontsize=item["size"], 
            fontname=font_name, 
            color=text_rgb
        )
    
    # Save output
    output_buffer = io.BytesIO()
    output_doc = fitz.open()
    output_doc.insert_pdf(doc, from_page=template_idx, to_page=template_idx)
    output_doc.save(output_buffer)
    output_doc.close()
    
    return output_buffer.getvalue()

# --- STREAMLIT USER INTERFACE ---
st.set_page_config(page_title="Cert Generator", layout="centered")
st.title("🎓 Certificate Generator")
st.write("Upload the blank certificate PDF below.")

uploaded_file = st.file_uploader("Upload 'Onboarding Certificate [CR team].pdf'", type="pdf")

if uploaded_file:
    with st.form("certificate_form"):
        st.subheader("1. Enter Details")
        col1, col2 = st.columns(2)
        with col1:
            emp_name = st.text_input("Employee Name", placeholder="Mario Rossi")
        with col2:
            cert_date = st.text_input("Date", value="12-Dec-2025")
        
        st.subheader("2. Select Template")
        option = st.selectbox(
            "Version",
            ("Monitoring (2 Signers)", "Monitoring (1 Signer)", "EasyMap")
        )

        st.subheader("3. Text Styling")
        # Removed Background Picker since we are now transparent!
        text_color_hex = st.color_picker("Text Color (Ink)", "#252525")
        
        submitted = st.form_submit_button("Generate Certificate")

    if submitted and emp_name:
        idx_map = {
            "Monitoring (2 Signers)": 3,
            "Monitoring (1 Signer)": 4,
            "EasyMap": 9
        }
        
        try:
            uploaded_file.seek(0)
            text_rgb = hex_to_rgb(text_color_hex)
            
            with st.spinner("Processing..."):
                pdf_bytes = generate_pdf(uploaded_file, idx_map[option], emp_name, cert_date, text_rgb)
            
            st.success(f"✅ Ready: {emp_name}")
            
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"{emp_name.replace(' ', '_')}_Certificate.pdf",
                mime="application/pdf"
            )

        except Exception as e:
            st.error(f"An error occurred: {e}")

else:
    st.info("👋 Waiting for file upload...")
