import streamlit as st
import fitz  # PyMuPDF
import io
import os
import zipfile
from datetime import datetime

# --- CONFIGURATION ---
TEMPLATE_FILENAME = "Onboarding Certificate [CR team].pdf"

def generate_pdf(filename, template_idx, name, date_str):
    """Generates a single PDF certificate in memory."""
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

    # 3. MARK OLD TEXT & CALCULATE POSITIONS
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

    # 4. APPLY REDACTION (Transparent)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_IMAGE_NONE)

    # 5. INSERT NEW TEXT (White)
    for insert in insertions:
        page.insert_text(
            fitz.Point(insert["x"], insert["y"]),
            insert["text"],
            fontsize=insert["size"],
            fontname=insert["font"],
            color=(1, 1, 1) # White
        )
    
    output_buffer = io.BytesIO()
    output_doc = fitz.open()
    output_doc.insert_pdf(doc, from_page=template_idx, to_page=template_idx)
    output_doc.save(output_buffer)
    output_doc.close()
    
    return output_buffer.getvalue()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Cert Generator", layout="centered")

st.title("🎓 Certificate Generator")

if not os.path.exists(TEMPLATE_FILENAME):
    st.error(f"⚠️ Error: The file '{TEMPLATE_FILENAME}' was not found.")
    st.info("Please make sure the PDF is in the same folder as this script.")

else:
    # Template Map
    idx_map = {"Monitoring (2 Signers)": 3, "Monitoring (1 Signer)": 4, "EasyMap": 9}
    
    # Default Date
    today_str = datetime.today().strftime('%d-%b-%Y')

    # Create Tabs for Single vs Batch
    tab1, tab2 = st.tabs(["👤 Single Certificate", "👥 Batch Generation"])

    # --- TAB 1: SINGLE USER ---
    with tab1:
        st.write("Generate a certificate for one person.")
        with st.form("single_form"):
            s_name = st.text_input("Employee Name", placeholder="Mario Rossi")
            s_date = st.text_input("Date", value=today_str, key="date_single")
            s_template = st.selectbox("Template Version", list(idx_map.keys()), key="temp_single")
            
            s_submit = st.form_submit_button("Generate PDF")
        
        if s_submit and s_name:
            try:
                with st.spinner("Processing..."):
                    pdf_data = generate_pdf(TEMPLATE_FILENAME, idx_map[s_template], s_name, s_date)
                st.success(f"✅ Ready: {s_name}")
                st.download_button("⬇️ Download PDF", pdf_data, f"{s_name.replace(' ', '_')}_Certificate.pdf", "application/pdf")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- TAB 2: BATCH PROCESSING ---
    with tab2:
        st.write("Generate multiple certificates at once (Download as ZIP).")
        with st.form("batch_form"):
            st.write("Enter names below (one per line):")
            b_names_text = st.text_area("List of Names", height=150, placeholder="Mario Rossi\nLuigi Verdi\nPeach Toadstool")
            
            col1, col2 = st.columns(2)
            with col1:
                b_date = st.text_input("Date", value=today_str, key="date_batch")
            with col2:
                b_template = st.selectbox("Template Version", list(idx_map.keys()), key="temp_batch")
            
            b_submit = st.form_submit_button("Generate All Certificates")
        
        if b_submit and b_names_text:
            # Clean up list of names (remove empty lines)
            name_list = [n.strip() for n in b_names_text.split('\n') if n.strip()]
            
            if not name_list:
                st.warning("Please enter at least one name.")
            else:
                try:
                    # Create a ZIP file in memory
                    zip_buffer = io.BytesIO()
                    
                    with st.spinner(f"Generating {len(name_list)} certificates..."):
                        with zipfile.ZipFile(zip_buffer, "w") as zf:
                            for name in name_list:
                                # Generate PDF bytes
                                pdf_bytes = generate_pdf(TEMPLATE_FILENAME, idx_map[b_template], name, b_date)
                                
                                # Define filename inside ZIP
                                file_name = f"{name.replace(' ', '_')}_Certificate.pdf"
                                
                                # Add to zip
                                zf.writestr(file_name, pdf_bytes)
                    
                    st.success(f"✅ Successfully created {len(name_list)} certificates!")
                    
                    # Download Button for ZIP
                    st.download_button(
                        label="📦 Download ZIP Package",
                        data=zip_buffer.getvalue(),
                        file_name=f"Certificates_{datetime.today().strftime('%Y%m%d')}.zip",
                        mime="application/zip"
                    )
                    
                except Exception as e:
                    st.error(f"An error occurred: {e}")
