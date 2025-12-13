import streamlit as st
import fitz  # PyMuPDF
import io

def generate_pdf(input_pdf_stream, template_idx, name, date_str):
    # Read the uploaded file
    doc = fitz.open(stream=input_pdf_stream.read(), filetype="pdf")
    page = doc[template_idx]
    
    # 1. ANALYZE REFERENCE TEXT ("We acknowledge that")
    # We use this to get the perfect Font Size and Y-Alignment (Baseline)
    ref_phrase = "We acknowledge that"
    ref_instances = page.search_for(ref_phrase)
    
    # Default values (fallback)
    ref_y = None
    ref_height = 12 
    
    if ref_instances:
        # Use the first instance found to establish the baseline
        ref_rect = ref_instances[0] 
        ref_y = ref_rect.y1   # The bottom coordinates of the text "that"
        ref_height = ref_rect.height # The height of the text "that"
    
    # 2. DEFINE REPLACEMENTS
    replacements = [
        {"placeholder": "[Employee Name]", "value": name, "is_name": True},
        {"placeholder": "DD-MMM-YYYY", "value": date_str, "is_name": False}
    ]

    # Queue for text to insert
    insertions = []

    # 3. MARK OLD TEXT FOR DELETION & CALCULATE NEW POSITIONS
    for item in replacements:
        instances = page.search_for(item["placeholder"])
        
        if instances:
            for rect in instances:
                # Mark for redaction (transparent delete)
                page.add_redact_annot(rect)
                
                # Determine Font Size and Position
                if item["is_name"] and ref_y:
                    # SMART ALIGNMENT: 
                    # We force the name to sit on the same Y-line as "We acknowledge that"
                    # We use the reference height to ensure the name matches the sentence size.
                    f_size = ref_height * 0.95 
                    insert_y = ref_y - 2 # Tiny adjustment to align baseline perfectly
                else:
                    # Fallback for Date (use its own placeholder size)
                    f_size = rect.height * 0.9
                    insert_y = rect.y1 - 2

                insertions.append({
                    "x": rect.x0,
                    "y": insert_y,
                    "text": item["value"],
                    "size": f_size,
                    "font": "hebo" if item["is_name"] else "helv" # Bold Name, Regular Date
                })

    # 4. APPLY REDACTION (Erase old text, keep background images)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_IMAGE_NONE)

    # 5. INSERT NEW TEXT (Always White)
    for insert in insertions:
        page.insert_text(
            fitz.Point(insert["x"], insert["y"]),
            insert["text"],
            fontsize=insert["size"],
            fontname=insert["font"],
            color=(1, 1, 1) # Pure White
        )
    
    # Save output
    output_buffer = io.BytesIO()
    output_doc = fitz.open()
    output_doc.insert_pdf(doc, from_page=template_idx, to_page=template_idx)
    output_doc.save(output_buffer)
    output_doc.close()
    
    return output_buffer.getvalue()

# --- STREAMLIT UI ---
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
        option = st.selectbox("Version", ("Monitoring (2 Signers)", "Monitoring (1 Signer)", "EasyMap"))
        
        submitted = st.form_submit_button("Generate Certificate")

    if submitted and emp_name:
        idx_map = {"Monitoring (2 Signers)": 3, "Monitoring (1 Signer)": 4, "EasyMap": 9}
        
        try:
            uploaded_file.seek(0)
            with st.spinner("Processing..."):
                pdf_bytes = generate_pdf(uploaded_file, idx_map[option], emp_name, cert_date)
            
            st.success(f"✅ Ready: {emp_name}")
            st.download_button("⬇️ Download PDF", pdf_bytes, f"{emp_name.replace(' ', '_')}_Certificate.pdf", "application/pdf")

        except Exception as e:
            st.error(f"An error occurred: {e}")

else:
    st.info("👋 Waiting for file upload...")
