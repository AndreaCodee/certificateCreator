import streamlit as st
import fitz  # PyMuPDF
import io
import os
import zipfile
from datetime import datetime

# --- CONFIGURATION ---
TEMPLATE_FILENAME = "Onboarding Certificate [CR team].pdf"

# TEAM DEFINITIONS
# Make sure these filenames match your uploaded files EXACTLY!
TEAM = {
    "Andrea Bondi":          "sig_andrea.png",
    "Laura Carrera":         "sig_laura.png",
    "Tomislav Cicin-Karlov": "sig_tomislav.png",
    "Lisa Harrsen":          "sig_lisa.png"
}

def generate_pdf(filename, template_idx, emp_name, date_str, creator_name, pos_config):
    doc = fitz.open(filename)
    page = doc[template_idx]
    
    # --- PART 1: FILL TEXT (Name & Date) ---
    ref_phrase = "We acknowledge that"
    ref_instances = page.search_for(ref_phrase)
    ref_y = None
    ref_height = 12 
    if ref_instances:
        ref_rect = ref_instances[0]
        ref_y = ref_rect.y1
        ref_height = ref_rect.height

    replacements = [
        {"placeholder": "[Employee Name]", "value": emp_name, "is_name": True},
        {"placeholder": "DD-MMM-YYYY", "value": date_str, "is_name": False}
    ]

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

                # Apply redaction immediately to clear space
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_IMAGE_NONE)
                
                page.insert_text(
                    fitz.Point(rect.x0, insert_y),
                    item["value"],
                    fontsize=f_size,
                    fontname="hebo" if item["is_name"] else "helv",
                    color=(1, 1, 1) # White
                )

    # --- PART 2: INSERT SIGNATURE IMAGES ---
    
    sigs_to_insert = []
    
    # Get coordinates from user sliders
    y_pos = pos_config["y_pos"]
    
    # 1. ANDREA (Single Mode)
    if creator_name == "Andrea Bondi":
        sigs_to_insert.append({
            "file": TEAM["Andrea Bondi"],
            "x": pos_config["x_single"] # Center/Single Position
        })
        
    # 2. OTHERS (Dual Mode)
    else:
        # Andrea on LEFT
        sigs_to_insert.append({
            "file": TEAM["Andrea Bondi"],
            "x": pos_config["x_left"]
        })
        # Creator on RIGHT
        sigs_to_insert.append({
            "file": TEAM[creator_name],
            "x": pos_config["x_right"]
        })

    # Execute Insertion
    for sig in sigs_to_insert:
        if os.path.exists(sig["file"]):
            # Define Box: x, y, x+width, y+height
            # We use the sliders for X and Y
            rect = fitz.Rect(
                sig["x"], 
                y_pos, 
                sig["x"] + pos_config["width"], 
                y_pos + pos_config["height"]
            )
            page.insert_image(rect, filename=sig["file"])

    # Output
    output_buffer = io.BytesIO()
    output_doc = fitz.open()
    output_doc.insert_pdf(doc, from_page=template_idx, to_page=template_idx)
    output_doc.save(output_buffer)
    output_doc.close()
    
    return output_buffer.getvalue()

# --- STREAMLIT UI ---
st.set_page_config(page_title="Cert Generator", layout="wide") # Wide layout for side-by-side view
st.title("🎓 Certificate Generator")

# Check Template
if not os.path.exists(TEMPLATE_FILENAME):
    st.error(f"⚠️ Error: '{TEMPLATE_FILENAME}' not found.")
    st.stop()

# --- SIDEBAR: CONFIGURATION & CALIBRATION ---
st.sidebar.header("1. Creator")
creators = list(TEAM.keys())
creator = st.sidebar.selectbox("Who is creating this?", creators)

# Check Image
sig_file = TEAM[creator]
if os.path.exists(sig_file):
    st.sidebar.success(f"✅ Sig Found: {sig_file}")
else:
    st.sidebar.error(f"❌ Missing: {sig_file}")
    st.sidebar.info("Please upload the .png file to the repo.")

st.sidebar.markdown("---")
st.sidebar.header("2. Position Calibration")
st.sidebar.info("Adjust these sliders to move the signature.")

# Default values are guesses - Adjust them in the app!
pos_config = {
    "y_pos":    st.sidebar.slider("Vertical Position (Y)", 300, 600, 450, help="Higher number = Lower on page"),
    "x_single": st.sidebar.slider("Single Sig (X)", 0, 600, 250, help="Horizontal pos for Andrea alone"),
    "x_left":   st.sidebar.slider("Left Sig (X)", 0, 400, 100, help="Horizontal pos for Left signature"),
    "x_right":  st.sidebar.slider("Right Sig (X)", 200, 800, 400, help="Horizontal pos for Right signature"),
    "width":    st.sidebar.slider("Image Width", 50, 300, 180),
    "height":   st.sidebar.slider("Image Height", 20, 150, 70)
}

# --- MAIN AREA ---
tab1, tab2 = st.tabs(["👤 Single Certificate", "👥 Batch Generation"])
today_str = datetime.today().strftime('%d-%b-%Y')
idx_map = {"Monitoring": "Monitoring", "EasyMap": "EasyMap"}

def get_template_index(mode, signer_name):
    # Adjust these indices if your new template has different pages!
    is_andrea = (signer_name == "Andrea Bondi")
    if mode == "Monitoring":
        return 4 if is_andrea else 3
    elif mode == "EasyMap":
        return 9
    return 3

# SINGLE MODE
with tab1:
    col1, col2 = st.columns([1, 2])
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
                pdf_data = generate_pdf(TEMPLATE_FILENAME, t_idx, s_name, s_date, creator, pos_config)
                
                st.success("✅ Generated! If position is wrong, adjust sliders on the left.")
                
                # Download
                st.download_button("⬇️ Download PDF", pdf_data, f"{s_name}_Cert.pdf", "application/pdf")
                
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
                        pdf_bytes = generate_pdf(TEMPLATE_FILENAME, t_idx, name, b_date, creator, pos_config)
                        zf.writestr(f"{name.replace(' ', '_')}_Certificate.pdf", pdf_bytes)
            st.success(f"✅ Created {len(names)} certificates!")
            st.download_button("📦 Download ZIP", zip_buffer.getvalue(), "Certificates.zip", "application/zip")
