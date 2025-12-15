import streamlit as st
import fitz  # PyMuPDF
import io
import os
import zipfile
from datetime import datetime

# --- CONFIGURATION ---
TEMPLATE_FILENAME = "Onboarding Certificate [CR team].pdf"

# 1. DEFINE TEAM MEMBERS
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

def get_template_index(mode, signer_name):
    """
    Selects the correct page.
    - Andrea (Single Mode) -> Page 5 (Index 4)
    - Others (Dual Mode)   -> Page 4 (Index 3)
    - EasyMap              -> Page 10 (Index 9)
    """
    is_andrea = (signer_name == "Andrea Bondi")
    
    if mode == "Monitoring":
        return 4 if is_andrea else 3
    elif mode == "EasyMap":
        return 9
    return 3

def generate_pdf(filename, template_idx, emp_name, date_str, creator_name):
    doc = fitz.open(filename)
    page = doc[template_idx]
    
    # --- PART 1: FILL EMPLOYEE NAME & DATE ---
    
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

    insertions = []

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
                    "x": rect.x0, "y": insert_y, "text": item["value"],
                    "size": f_size, "font": "hebo" if item["is_name"] else "helv",
                    "color": (1, 1, 1) # White text
                })

    # --- PART 2: HANDLE SIGNATURES ---
    
    # Logic:
    # A. If Creator is Andrea: DO NOTHING. 
    #    The template already has her signature (Single or Left slot).
    #
    # B. If Creator is NOT Andrea:
    #    1. Leave Left Slot (Andrea) ALONE.
    #    2. Find Right Slot (Laura).
    #    3. Wipe "Laura" and insert "Creator".

    sigs_to_place = []

    if creator_name != "Andrea Bondi":
        # We look for Laura to replace her with the Creator
        slot_right_instances = page.search_for("Laura Carrera Nieto")
        
        if slot_right_instances:
            # We found Laura's slot. Replace it with the Creator.
            sigs_to_place.append({
                "rect": slot_right_instances[0], 
                "name_override": creator_name,  
                "data": TEAM[creator_name]      
            })
        else:
             # Fallback: If we can't find "Laura" text (e.g. unexpected formatting),
             # we might try to hardcode coordinates, but usually text search is safest.
             pass

    # --- EXECUTE SIGNATURE REPLACEMENT ---
    
    for sig in sigs_to_place:
        base_rect = sig["rect"]
        data = sig["data"]
        display_name = sig["name_override"]
        
        # 1. Define Cleaning Zone (Wipe old name, title, and signature space)
        clean_rect = fitz.Rect(
            base_rect.x0 - 5,    
            base_rect.y0 - 50,   
            base_rect.x1 + 100,  
            base_rect.y1 + 20    
        )
        page.add_redact_annot(clean_rect)
        
        # 2. Add New Text Info
        # Name
        insertions.append({
            "x": base_rect.x0, "y": base_rect.y1 - 2, 
            "text": display_name, "size": 11, "font": "hebo", "color": (0, 0, 0)
        })
        # Title
        insertions.append({
            "x": base_rect.x0, "y": base_rect.y1 + 10, 
            "text": data["title"], "size": 9, "font": "helv", "color": (0.3, 0.3, 0.3)
        })
        
        # 3. Add Signature Image
        if os.path.exists(data["file"]):
            img_rect = fitz.Rect(base_rect.x0, base_rect.y0 - 45, base_rect.x0 + 100, base_rect.y0 - 5)
            sig["img_rect"] = img_rect
            sig["img_file"] = data["file"]

    # APPLY ERASING
    # This deletes [Employee Name] AND [Laura Carrera Nieto] (if applicable)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_IMAGE_NONE)

    # INSERT TEXT
    for insert in insertions:
        page.insert_text(
            fitz.Point(insert["x"], insert["y"]),
            insert["text"],
            fontsize=insert["size"],
            fontname=insert["font"],
            color=insert["color"]
        )

    # INSERT IMAGES
    for sig in sigs_to_place:
        if "img_file" in sig:
            page.insert_image(sig["img_rect"], filename=sig["img_file"])

    # OUTPUT
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
    
    # Check signature file only if it's NOT Andrea (since we don't need Andrea's file anymore)
    if creator != "Andrea Bondi":
        sig_file = TEAM[creator]["file"]
        sig_status = "✅ Found" if os.path.exists(sig_file) else "❌ Missing in Repo"
        st.sidebar.caption(f"Creator Sig: {sig_status}")

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
