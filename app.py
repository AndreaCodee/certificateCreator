import streamlit as st
import fitz  # PyMuPDF
import io
import os
from datetime import datetime

# --- CONFIGURATION ---
TEMPLATE_FILENAME = "Onboarding Certificate [CR team].pdf"

# TEAM DEFINITIONS
TEAM = {
    "Andrea Bondi": {
        "title": "Customer Relations Manager",
        "file": "sig_andrea.png"
    },
    "Laura Carrera": {
        "title": "Customer Relations Lead",
        "file": "sig_laura.png"
    },
    "Tomislav Cicin-Karlov": {
        "title": "Customer Relations Specialist",
        "file": "sig_tomislav.png"
    },
    "Lisa Harrsen": {
        "title": "Customer Relations Specialist",
        "file": "sig_lisa.png"
    }
}

# DIMENSIONS
SIG_WIDTH = 120        
SIG_HEIGHT = 50        
BOTTOM_MARGIN_CM = 3.5 # Increased margin to ensure text doesn't fall off page

def cm_to_points(cm):
    return cm * 28.3465

def get_text_width(text, fontsize, fontname, page):
    """Calculates the width of a string in points to allow centering."""
    return fitz.getTextLength(text, fontname=fontname, fontsize=fontsize)

def get_template_index(mode):
    if mode == "Monitoring":
        return 2 
    elif mode == "EasyMap":
        return 4
    return 2

def generate_pdf(filename, template_idx, emp_name, date_str, creator_name):
    doc = fitz.open(filename)
    page = doc[template_idx]
    
    # 1. PAGE GEOMETRY
    page_w = page.rect.width
    page_h = page.rect.height
    
    # Calculate Y Positions
    # We build the block from bottom up: Title -> Name -> Signature
    base_y = page_h - cm_to_points(BOTTOM_MARGIN_CM)
    
    sig_y = base_y
    
    # Reduced gaps here (closer to image)
    name_y = sig_y + SIG_HEIGHT + 3    # Only 3px gap
    title_y = name_y + 11              # Tight spacing for title

    # --- PART 1: FILL EMPLOYEE DATA ---
    replacements = [
        {"placeholder": "[Employee Name]", "value": emp_name, "is_name": True},
        {"placeholder": "DD-MMM-YYYY", "value": date_str, "is_name": False}
    ]

    ref_instances = page.search_for("We acknowledge that")
    ref_y = ref_instances[0].y1 if ref_instances else None
    ref_h = ref_instances[0].height if ref_instances else 12

    for item in replacements:
        instances = page.search_for(item["placeholder"])
        if instances:
            for rect in instances:
                page.add_redact_annot(rect)
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_IMAGE_NONE)
                
                if item["is_name"] and ref_y:
                    f_size = ref_h * 0.95 
                    t_y = ref_y - 2 
                else:
                    f_size = rect.height * 0.9
                    t_y = rect.y1 - 2

                page.insert_text(
                    fitz.Point(rect.x0, t_y),
                    item["value"],
                    fontsize=f_size,
                    fontname="hebo" if item["is_name"] else "helv",
                    color=(1, 1, 1) # White
                )

    # --- PART 2: INSERT SIGNATURE BLOCKS ---
    blocks_to_insert = []
    
    def create_block(name, x_center):
        return {
            "name": name,
            "title": TEAM[name]["title"],
            "file": TEAM[name]["file"],
            "x": x_center - (SIG_WIDTH / 2),
            "center_x": x_center
        }

    if creator_name == "Andrea Bondi":
        blocks_to_insert.append(create_block("Andrea Bondi", page_w / 2))
    else:
        blocks_to_insert.append(create_block("Andrea Bondi", page_w * 0.25))
        blocks_to_insert.append(create_block(creator_name, page_w * 0.75))

    for block in blocks_to_insert:
        # A. Insert Signature Image
        if os.path.exists(block["file"]):
            rect = fitz.Rect(block["x"], sig_y, block["x"] + SIG_WIDTH, sig_y + SIG_HEIGHT)
            page.insert_image(rect, filename=block["file"])
        
        # B. Insert Centered Name
        name_w = fitz.get_text_length(block["name"], fontname="hebo", fontsize=10)
        name_x = block["center_x"] - (name_w / 2)
        
        page.insert_text(
            fitz.Point(name_x, name_y), 
            block["name"],
            fontsize=10,
            fontname="hebo", # Bold
            color=(0, 0, 0)
        )
        
        # C. Insert Centered Title
        title_w = fitz.get_text_length(block["title"], fontname="helv", fontsize=8)
        title_x = block["center_x"] - (title_w / 2)
        
        page.insert_text(
            fitz.Point(title_x, title_y),
            block["title"],
            fontsize=8,
            fontname="helv", # Regular
            color=(0.3, 0.3, 0.3)
        )

    # --- PART 3: OUTPUT ---
    output_buffer = io.BytesIO()
    output_doc = fitz.open()
    output_doc.insert_pdf(doc, from_page=template_idx, to_page=template_idx)
    output_doc.save(output_buffer)
    
    # Preview
    preview_page = output_doc[0]
    pix = preview_page.get_pixmap(dpi=150)
    preview_bytes = pix.tobytes("png")
    output_doc.close()
    
    return output_buffer.getvalue(), preview_bytes

# --- STREAMLIT UI ---
st.set_page_config(page_title="Cert Generator", layout="wide")
st.title("🎓 Certificate Generator")

if not os.path.exists(TEMPLATE_FILENAME):
    st.error(f"⚠️ Error: '{TEMPLATE_FILENAME}' not found.")
    st.stop()

# SIDEBAR
st.sidebar.header("Configuration")
creator = st.sidebar.selectbox("Certificate Creator", list(TEAM.keys()))

if not os.path.exists(TEAM[creator]["file"]):
    st.sidebar.warning(f"⚠️ Missing Sig: {TEAM[creator]['file']}")

# TABS
tab1, tab2 = st.tabs(["👤 Single Certificate", "👥 Batch Generation"])
today_str = datetime.today().strftime('%d-%b-%Y')

# SINGLE MODE
with tab1:
    col1, col2 = st.columns([1, 1.5])
    with col1:
        with st.form("single_form"):
            s_name = st.text_input("Employee Name", placeholder="Mario Rossi")
            s_date = st.text_input("Date", value=today_str)
            s_type = st.selectbox("Type", ["Monitoring", "EasyMap"])
            s_submit = st.form_submit_button("Generate & Preview")
    
    with col2:
        if s_submit and s_name:
            t_idx = get_template_index(s_type)
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
        with c2: b_type = st.selectbox("Type", ["Monitoring", "EasyMap"], key="bt")
        b_submit = st.form_submit_button("Generate Batch")
    
    if b_submit and b_names:
        names = [n.strip() for n in b_names.split('\n') if n.strip()]
        t_idx = get_template_index(b_type)
        if names:
            zip_buffer = io.BytesIO()
            with st.spinner(f"Processing {len(names)} certificates..."):
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for name in names:
                        pdf_bytes, _ = generate_pdf(TEMPLATE_FILENAME, t_idx, name, b_date, creator)
                        zf.writestr(f"{name.replace(' ', '_')}_Certificate.pdf", pdf_bytes)
            st.success(f"✅ Created {len(names)} certificates!")
            st.download_button("📦 Download ZIP", zip_buffer.getvalue(), "Certificates.zip", "application/zip")
