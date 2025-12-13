import streamlit as st
import fitz  # PyMuPDF
import io

def hex_to_rgb(hex_color):
    """Converts hex color (e.g., #FFFFFF) to a tuple (1, 1, 1) for PyMuPDF"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

def generate_pdf(input_pdf_stream, template_idx, name, date_str, bg_rgb, text_rgb):
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
                # 1. HIDE OLD TEXT
                # We draw a rectangle with the user-selected background color
                page.draw_rect(rect, color=bg_rgb, fill=bg_rgb)
                
                # 2. INSERT NEW TEXT
                # Adjust Y position (-2) to align with baseline
                insert_point = fitz.Point(rect.x0, rect.y1 - 2)
                
                # Use 'hebo' for Bold, 'helv' for Regular
                font_name = "hebo" if is_bold else "helv"
                
                page.insert_text(
                    insert_point, 
                    new_value, 
                    fontsize=f_size, 
                    fontname=font_name, 
                    color=text_rgb # Use user-selected text color
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

# 1. File Uploader
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

        st.subheader("3. Visual Blending (Merge with Background)")
        st.caption("Adjust these if the text looks like a 'sticker'.")
        
        col3, col4 = st.columns(2)
        with col3:
            # Default is slightly off-white (Cream) to blend better, user can adjust
            bg_color_hex = st.color_picker("Background Mask Color", "#FFFFFF")
        with col4:
            # Default is Dark Grey (not pure black) for a natural ink look
            text_color_hex = st.color_picker("Text Color (Ink)", "#252525")
        
        submitted = st.form_submit_button("Generate Certificate")

    # 4. Process
    if submitted and emp_name:
        idx_map = {
            "Monitoring (2 Signers)": 3,
            "Monitoring (1 Signer)": 4,
            "EasyMap": 9
        }
        
        try:
            uploaded_file.seek(0)
            
            # Convert colors to the format PyMuPDF needs (0.0 to 1.0)
            bg_rgb = hex_to_rgb(bg_color_hex)
            text_rgb = hex_to_rgb(text_color_hex)
            
            with st.spinner("Processing..."):
                pdf_bytes = generate_pdf(uploaded_file, idx_map[option], emp_name, cert_date, bg_rgb, text_rgb)
            
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
