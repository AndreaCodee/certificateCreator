import streamlit as st
import fitz  # PyMuPDF
import io
import os
import zipfile
from datetime import datetime

# --- CONFIGURATION ---
TEMPLATE_FILENAME = "Onboarding Certificate [CR team].pdf"

# 1. DEFINE TEAM & FILES
# NOTE: These PNGs must now contain the Signature AND the typed Name/Title.
TEAM = {
    "Andrea Bondi": {
        "file": "sig_andrea.png" # Not used for insertion, but good to have
    },
    "Laura Carrera": {
        "file": "sig_laura.png"
    },
    "Tomislav Cicin-Karlov": {
        "file": "sig_tomislav.png"
    },
    "Lisa Harrsen": {
        "file": "sig_lisa.png"
    }
}

def get_template_index(mode, signer_name):
    """
    Selects the correct page from the PDF.
    - If your new template has different page numbers, adjust these indices!
    - Currently: Monitoring (Pg 4/5), EasyMap (Pg 10)
    """
    is_andrea = (signer_name == "Andrea Bondi")
    
    if mode == "Monitoring":
        # If the new template merged everything into one layout, 
        # you might just need one index here (e.g., always return 3).
        # For now, keeping legacy logic just in case:
        return 4 if is_andrea else 3
    elif mode == "EasyMap":
        return 9
    return 3

def generate_pdf(filename, template_idx, emp_name, date_str, creator_name):
    doc = fitz.open(filename)
    page = doc[template_idx]
    
    # --- PART 1: FILL EMPLOYEE NAME & DATE ---
    
    # 1. Find the baseline using "We acknowledge that"
    ref_phrase = "We acknowledge that"
    ref_instances = page.search_for(ref_phrase)
    ref_y = None
    ref_height = 12 
    
    if ref_instances:
        ref_rect = ref_instances[0]
        ref_y = ref_rect.y1
        ref_height = ref_rect.height

    # 2. Define Content to Fill
    replacements = [
        {"placeholder": "[Employee Name]", "value": emp_name, "is_name": True},
        {"placeholder": "DD-MMM-YYYY", "value": date_str, "is_name": False}
    ]

    insertions = []

    # 3. Calculate Positions (and hide placeholders)
    for item in replacements:
        instances = page.search_for(item["placeholder"])
        if instances:
            for rect in instances:
                # Mark placeholder for transparent deletion
                page.add_redact_annot(rect)
                
                # Smart Alignment logic
                if item["is_name"] and ref_y:
                    f_size = ref_height * 0.95 
                    insert_y = ref_y - 2 
                else:
                    f_size = rect.height * 0.9
                    insert_y = rect.y1 - 2

                insertions.append({
                    "x": rect.x0, "y": insert_y, "text": item["value"],
                    "size": f_size, "font": "hebo" if item["is_name"] else "helv",
                    "color": (1, 1, 1) # White text
                })

    # --- PART 2: HANDLE SIGNATURES ---
    
    # Logic:
    # 1. If Creator == Andrea: Do nothing (She is already in the template).
    # 2. If Creator != Andrea: Insert their PNG to the right of Andrea.

    image_insertion = None

    if creator_name != "Andrea Bondi":
        # A. Find Andrea to use as an "Anchor"
        anchor_text = "Andrea Bondi"
        anchor_instances = page.search_for(anchor_text)
        
        if anchor_instances:
            base_rect = anchor_instances[0] # This is where "Andrea Bondi" is written
            
            # B. Calculate "Right Side" Position
            # We want the new signature to be to the right of Andrea.
            # Assuming standard layout, we shift X by roughly 250-300 points.
            # We align the BOTTOM of the image with the text baseline.
            
            spacing_x = 280 # Distance between the two signatures
            new_x = base_rect.x0 + spacing_x
            
            # Image Dimensions (Adjust these if your PNGs are huge/tiny)
            # Width 150, Height 60 is a good standard for signature blocks
            img_w = 150
            img_h = 60
            
            # Create the rectangle for the image
            # We align it so the text in the PNG roughly lands where the old text was
            new_rect = fitz.Rect(new_x, base_rect.y1 - img_h + 5, new_x + img_w, base_rect.y1 + 5)
            
            # Check if file exists
            sig_file = TEAM[creator_name]["file"]
            if os.path.exists(sig_file):
                image_insertion = {"rect": new_rect, "file": sig_file}

    # --- EXECUTE CHANGES ---

    # 1. Apply Redactions (Delete [Employee Name] placeholder)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_IMAGE_NONE)

    # 2. Insert Name and Date
    for insert in insertions:
        page.insert_text(
            fitz.Point(insert["x"], insert["y"]),
            insert["text"],
            fontsize=insert["size"],
            fontname=insert["font"],
            color=insert["color"]
        )

    # 3. Insert Signature Image (If applicable)
    if image_insertion:
        page.insert_image(
            image_insertion["rect"],
            filename=image_insertion["file"]
        )

    # Output
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
    st.error(f"⚠️ Error: '{TEMPLATE_FILENAME}' not found.")
else:
    # Sidebar
    st.sidebar.header("Configuration")
    
    creator = st.sidebar.selectbox("Certificate Creator", list(TEAM.keys()))
    
    # Check signature file logic
    if creator != "Andrea Bondi":
        sig_file = TEAM[creator]["file"]
        if os.path.exists(sig_file):
             st.sidebar.caption(f"✅ Signature found: {sig_file}")
        else:
             st.sidebar.error(f"❌ Missing file: {sig_file}")
             st.sidebar.info("Please upload the PNG to the repository.")

    tab1, tab2 = st.tabs(["👤 Single Certificate", "👥 Batch Generation"])
    
    today_str = datetime.today().strftime('%d-%b-%Y')

    # --- SINGLE MODE ---
    with tab1:
        with st.form("single_form"):
            s_name = st.text_input("Employee Name", placeholder="Mario Rossi")
            s_date = st.text_input("Date", value=today_str)
            s_type = st.selectbox("Certificate Type", ["Monitoring", "EasyMap"])
            s_submit = st.form_submit_button("Generate PDF")
        
        if s_submit and s_name:
            t_idx = get_template_index(s_type, creator)
            try:
                pdf_data = generate_pdf(TEMPLATE_FILENAME, t_idx, s_name, s_date, creator)
                st.success(f"✅ Generated for {s_name}")
                st.download_button("⬇️ Download PDF", pdf_data, f"{s_name.replace(' ', '_')}_Certificate.pdf", "application/pdf")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- BATCH MODE ---
    with tab2:
        with st.form("batch_form"):
            b_names = st.text_area("List of Names", height=150)
            c1, c2 = st.columns(2)
            with c1: b_date = st.text_input("Date", value=today_str, key="bd")
            with c2: b_type = st.selectbox("Certificate Type", ["Monitoring", "EasyMap"], key="bt")
            b_submit = st.form_submit_button("Generate Batch")
        
        if b_submit and b_names:
            names = [n.strip() for n in b_names.split('\n') if n.strip()]
            t_idx = get_template_index(b_type, creator)
            
            if names:
                zip_buffer = io.BytesIO()
                with st.spinner(f"Processing {len(names)} certificates..."):
                    with zipfile.ZipFile(zip_buffer, "w") as zf:
                        for name in names:
                            pdf_bytes = generate_pdf(TEMPLATE_FILENAME, t_idx, name, b_date, creator)
                            zf.writestr(f"{name.replace(' ', '_')}_Certificate.pdf", pdf_bytes)
                st.success("✅ Batch Complete!")
                st.download_button("📦 Download ZIP", zip_buffer.getvalue(), f"Certificates_{datetime.today().strftime('%Y%m%d')}.zip", "application/zip")
