import streamlit as st
import fitz  # PyMuPDF
import io
import os
import zipfile
from datetime import datetime

# --- 1. CONFIGURATION ---
TEMPLATE_FILENAME = "Onboarding Certificate [CR team].pdf"

# COORDINATES (X, Y) - Adjust these to move signatures!
# (0,0 is top-left. Increasing Y moves down. Increasing X moves right.)
POS_SINGLE_SIG = {"x": 250, "y": 450}  # Where Andrea goes when alone
POS_LEFT_SIG   = {"x": 100, "y": 450}  # Where Andrea goes in 2-signer layout
POS_RIGHT_SIG  = {"x": 400, "y": 450}  # Where Creator goes in 2-signer layout
SIG_SIZE       = {"w": 180, "h": 70}   # Width/Height of the signature image

# TEAM DEFINITIONS
TEAM = {
    "Andrea Bondi":          "sig_andrea.png",
    "Laura Carrera":         "sig_laura.png",
    "Tomislav Cicin-Karlov": "sig_tomislav.png",
    "Lisa Harrsen":          "sig_lisa.png"
}

def get_template_index(mode, signer_name):
    """
    Selects the page index. 
    Adjust these indices if your 'Clean' template has different page numbers!
    """
    is_andrea = (signer_name == "Andrea Bondi")
    
    if mode == "Monitoring":
        # Usually Page 5 (Index 4) is for Single Signer layout
        # Usually Page 4 (Index 3) is for Double Signer layout
        return 4 if is_andrea else 3
    elif mode == "EasyMap":
        return 9 # Page 10
    return 3

def generate_pdf(filename, template_idx, emp_name, date_str, creator_name):
    doc = fitz.open(filename)
    page = doc[template_idx]
    
    # --- PART 1: FILL TEXT (Name & Date) ---
    
    # Analyze alignment
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
                # 1. Hide placeholder
                page.add_redact_annot(rect)
                
                # 2. Calculate position
                if item["is_name"] and ref_y:
                    f_size = ref_height * 0.95 
                    insert_y = ref_y - 2 
                else:
                    f_size = rect.height * 0.9
                    insert_y = rect.y1 - 2

                # 3. Insert Text
                # Note: We apply redaction first to clear the space
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

    # LOGIC A: Andrea (Single Signer)
    if creator_name == "Andrea Bondi":
        # Insert Andrea in the Single Position
        sigs_to_insert.append({
            "file": TEAM["Andrea Bondi"],
            "pos": POS_SINGLE_SIG
        })
        
    # LOGIC B: Others (Double Signer)
    else:
        # 1. Insert Andrea on LEFT (Always)
        sigs_to_insert.append({
            "file": TEAM["Andrea Bondi"],
            "pos": POS_LEFT_SIG
        })
        
        # 2. Insert Creator on RIGHT
        sigs_to_insert.append({
            "file": TEAM[creator_name],
            "pos": POS_RIGHT_SIG
        })

    # EXECUTE INSERTION
    for sig in sigs_to_insert:
        if os.path.exists(sig["file"]):
            # Create Rect: (x, y, x+w, y+h)
            x = sig["pos"]["x"]
            y = sig["pos"]["y"]
            rect = fitz.Rect(x, y, x + SIG_SIZE["w"], y + SIG_SIZE["h"])
            
            page.insert_image(rect, filename=sig["file"])
        else:
            print(f"Warning: Signature file {sig['file']} not found.")

    # SAVE
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
    
    # Check images
    if not os.path.exists(TEAM[creator]):
        st.sidebar.error(f"❌ Missing Image: {TEAM[creator]}")

    tab1, tab2 = st.tabs(["👤 Single Certificate", "👥 Batch Generation"])
    today_str = datetime.today().strftime('%d-%b-%Y')
    
    # Mode Selection Map
    idx_map = {"Monitoring": "Monitoring", "EasyMap": "EasyMap"}

    # --- SINGLE ---
    with tab1:
        with st.form("single_form"):
            s_name = st.text_input("Employee Name", placeholder="Mario Rossi")
            s_date = st.text_input("Date", value=today_str)
            s_type = st.selectbox("Certificate Type", list(idx_map.keys()))
            s_submit = st.form_submit_button("Generate PDF")
        
        if s_submit and s_name:
            # Get Page Index
            t_idx = get_template_index(s_type, creator)
            try:
                pdf_data = generate_pdf(TEMPLATE_FILENAME, t_idx, s_name, s_date, creator)
                st.success(f"✅ Generated for {s_name}")
                st.download_button("⬇️ Download PDF", pdf_data, f"{s_name.replace(' ', '_')}_Certificate.pdf", "application/pdf")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- BATCH ---
    with tab2:
        with st.form("batch_form"):
            b_names = st.text_area("List of Names", height=150)
            c1, c2 = st.columns(2)
            with c1: b_date = st.text_input("Date", value=today_str, key="bd")
            with c2: b_type = st.selectbox("Certificate Type", list(idx_map.keys()), key="bt")
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
