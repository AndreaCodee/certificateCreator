import streamlit as st
import fitz  # PyMuPDF
import io
import os
import zipfile
from datetime import datetime

# --- CONFIGURATION ---
TEMPLATE_FILENAME = "Onboarding Certificate [CR team].pdf"

# TEAM DEFINITIONS
# Ensure these match your uploaded filenames exactly
TEAM = {
    "Andrea Bondi":          "sig_andrea.png",
    "Laura Carrera":         "sig_laura.png",
    "Tomislav Cicin-Karlov": "sig_tomislav.png",
    "Lisa Harrsen":          "sig_lisa.png"
}

# CONFIG: Signature Dimensions
SIG_WIDTH = 180
SIG_HEIGHT = 70
BOTTOM_MARGIN_CM = 1.5  # Distance from bottom of page

def cm_to_points(cm):
    return cm * 28.3465

def generate_pdf(filename, template_idx, emp_name, date_str, creator_name):
    doc = fitz.open(filename)
    page = doc[template_idx]
    
    # 1. ANALYZE PAGE GEOMETRY
    page_w = page.rect.width
    page_h = page.rect.height
    
    # Calculate Y Position (Bottom aligned)
    # Position = Page Height - Margin - Signature Height
    y_pos = page_h - cm_to_points(BOTTOM_MARGIN_CM) - SIG_HEIGHT

    # --- PART 1: FILL TEXT ---
    replacements = [
        {"placeholder": "[Employee Name]", "value": emp_name, "is_name": True},
        {"placeholder": "DD-MMM-YYYY", "value": date_str, "is_name": False}
    ]

    # Find "Reference" text for alignment (optional but good for polish)
    ref_instances = page.search_for("We acknowledge that")
    ref_y = ref_instances[0].y1 if ref_instances else None
    ref_h = ref_instances[0].height if ref_instances else 12

    for item in replacements:
        instances = page.search_for(item["placeholder"])
        if instances:
            for rect in instances:
                # Clear old text
                page.add_redact_annot(rect)
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_IMAGE_NONE)
                
                # Calculate specific text position
                if item["is_name"] and ref_y:
                    f_size = ref_h * 0.95 
                    t_y = ref_y - 2 
                else:
                    f_size = rect.height * 0.9
                    t_y = rect.y1 - 2

                # Insert Text
                page.insert_text(
                    fitz.Point(rect.x0, t_y),
                    item["value"],
                    fontsize=f_size,
                    fontname="hebo" if item["is_name"] else "helv",
                    color=(1, 1, 1) # White
                )

    # --- PART 2: INSERT SIGNATURES ---
    sigs_to_insert = []
    
    # Case A: Andrea (Single Signer) -> Center
    if creator_name == "Andrea Bondi":
        x_pos = (page_w / 2) - (SIG_WIDTH / 2) # Exact Center
        sigs_to_insert.append({
            "file": TEAM["Andrea Bondi"],
            "rect": fitz.Rect(x_pos, y_pos, x_pos + SIG_WIDTH, y_pos + SIG_HEIGHT)
        })
        
    # Case B: Others (Dual Signer) -> Left & Right
    else:
        # Left Position (25% of page width)
        x_left = (page_w * 0.25) - (SIG_WIDTH / 2)
        sigs_to_insert.append({
            "file": TEAM["Andrea Bondi"],
            "rect": fitz.Rect(x_left, y_pos, x_left + SIG_WIDTH, y_pos + SIG_HEIGHT)
        })
        
        # Right Position (75% of page width)
        x_right = (page_w * 0.75) - (SIG_WIDTH / 2)
        sigs_to_insert.append({
            "file": TEAM[creator_name],
            "rect": fitz.Rect(x_right, y_pos, x_right + SIG_WIDTH, y_pos + SIG_HEIGHT)
        })

    # Execute Insertion
    for sig in sigs_to_insert:
        if os.path.exists(sig["file"]):
            page.insert_image(sig["rect"], filename=sig["file"])

    # --- PART 3: OUTPUT ---
    
    # 1. Save PDF Bytes
    output_buffer = io.BytesIO()
    # Create new PDF with ONLY the modified page
    output_doc = fitz.open()
    output_doc.insert_pdf(doc, from_page=template_idx, to_page=template_idx)
    output_doc.save(output_buffer)
    
    # 2. Generate Preview Image
    # Get the page from the NEW document (which has only 1 page now, index 0)
    preview_page = output_doc[0]
    pix = preview_page.get_pixmap(dpi=150)
    preview_bytes = pix.tobytes("png") # Explicitly format as PNG
    
    output_doc.close()
    
    return output_buffer.getvalue(), preview_bytes

# --- STREAMLIT UI ---
st.set_page_config(page_title="Cert Generator", layout="wide")
st.title("🎓 Certificate Generator")

if not os.path.exists(TEMPLATE_FILENAME):
    st.error(f"⚠️ Error: '{TEMPLATE_FILENAME}' not found.")
    st.stop()

# SIDEBAR CONFIG
st.sidebar.header("Configuration")
creator = st.sidebar.selectbox("Certificate Creator", list(TEAM.keys()))

if not os.path.exists(TEAM[creator]):
    st.sidebar.warning(f"⚠️ Missing Sig File: {TEAM[creator]}")

# TABS
tab1, tab2 = st.tabs(["👤 Single Certificate", "👥 Batch Generation"])
today_str = datetime.today().strftime('%d-%b-%Y')
idx_map = {"Monitoring": "Monitoring", "EasyMap": "EasyMap"}

def get_template_index(mode, signer_name):
    # Adjust based on your PDF structure
    is_andrea = (signer_name == "Andrea Bondi")
    if mode == "Monitoring":
        return 4 if is_andrea else 3
    elif mode == "EasyMap":
        return 9
    return 3

# SINGLE MODE
with tab1:
    col1, col2 = st.columns([1, 1.5])
    with col1:
        with st.form("single_form"):
            s_name = st.text_input("Employee Name", placeholder="Mario Rossi")
            s_date = st.text_input("Date", value=today_str)
            s_type = st.selectbox("Type", list(idx_map.keys()))
            s_submit = st.form_submit_button("Generate & Preview")
    
    with col2:
        if s_submit and s_name:
            t_idx = get_template_index(s_type, creator)
            try:
                pdf_bytes, preview_img = generate_pdf(TEMPLATE_FILENAME, t_idx, s_name, s_date, creator)
                
                st.subheader("Preview")
                st.image(preview_img, caption=f"Certificate for {s_name}", use_container_width=True)
                
                st.download_button("⬇️ Download PDF", pdf_bytes, f"{s_name}_Cert.pdf", "application/pdf")
                
            except Exception as e:
                st.error(f"Error: {e}")

# BATCH MODE
with tab2:
    with st.form("batch_form"):
        b_names = st.text_area("List of Names", height=150)
        c1, c2 = st.columns(2)
        with c1: b_date = st.text_input("Date", value=today_str, key="bd")
        with c2: b_type = st.selectbox("Type", list(idx_map.keys()), key="bt")
        b_submit = st.form_submit_button("Generate Batch")
    
    if b_submit and b_names:
        names = [n.strip() for n in b_names.split('\n') if n.strip()]
        t_idx = get_template_index(b_type, creator)
        if names:
            zip_buffer = io.BytesIO()
            with st.spinner(f"Processing {len(names)} certificates..."):
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for name in names:
                        # Ignore preview in batch
                        pdf_bytes, _ = generate_pdf(TEMPLATE_FILENAME, t_idx, name, b_date, creator)
                        zf.writestr(f"{name.replace(' ', '_')}_Certificate.pdf", pdf_bytes)
            st.success(f"✅ Created {len(names)} certificates!")
            st.download_button("📦 Download ZIP", zip_buffer.getvalue(), "Certificates.zip", "application/zip")
