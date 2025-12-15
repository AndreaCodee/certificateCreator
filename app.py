import streamlit as st
import fitz  # PyMuPDF
import io
import os
import zipfile
from datetime import datetime

# --- CONFIGURATION ---
TEMPLATE_FILENAME = "Onboarding Certificate [CR team].pdf"

# 1. DEFINE TEAM MEMBERS
# Keys must match the dropdown names exactly
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
    Determines which page to use based on the Mode (Monitoring/EasyMap)
    and who is signing (Andrea = Single, Others = Double).
    """
    is_andrea = (signer_name == "Andrea Bondi")
    
    if mode == "Monitoring":
        # [cite_start]If Andrea, use Page 5 (Index 4) [cite: 66] - Single Signer
        # [cite_start]If Others, use Page 4 (Index 3) [cite: 48] - Double Signer
        return 4 if is_andrea else 3
    elif mode == "EasyMap":
        # [cite_start]Page 10 (Index 9) [cite: 121] is the EasyMap template.
        # It has 2 signatures by default. If Andrea does it alone, we might need logic to 
        # wipe the second signature, but for now we stick to the requested 2-signer logic.
        return 9
    return 3

def generate_pdf(filename, template_idx, emp_name, date_str, creator_name):
    doc = fitz.open(filename)
    page = doc[template_idx]
    
    # --- PART 1: FILL EMPLOYEE NAME & DATE ---
    
    # [cite_start]Analyze alignment using "We acknowledge that" [cite: 35]
    ref_phrase = "We acknowledge that"
    ref_instances = page.search_for(ref_phrase)
    ref_y = None
    ref_height = 12 
    if ref_instances:
        ref_rect = ref_instances[0]
        ref_y = ref_rect.y1
        ref_height = ref_rect.height

    # Text Replacements (Name & Date)
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
    # 1. We identify the two "Slots" on the PDF by searching for the original names.
    #    [cite_start]- Slot 1 (Left) is "Andrea Bondi"[cite: 48].
    #    [cite_start]- Slot 2 (Right) is "Laura Carrera Nieto"[cite: 49].
    # 2. We wipe both slots clean.
    # 3. We fill them based on the logic:
    #    - If Creator == Andrea: Fill Slot 1 only (Single template uses only Andrea).
    #    - If Creator != Andrea: Fill Left with Andrea, Right with Creator.

    # Search for placeholder names to find coordinates
    slot_left_instances = page.search_for("Andrea Bondi")
    slot_right_instances = page.search_for("Laura Carrera Nieto")
    
    # Prepare the list of signatures to insert
    sigs_to_place = []

    # CASE A: ANDREA (Single Signer)
    if creator_name == "Andrea Bondi":
        # [cite_start]In the 1-signer template (Page 5), "Andrea Bondi" is the only name[cite: 66].
        if slot_left_instances:
            base_rect = slot_left_instances[0]
            sigs_to_place.append({
                "rect": base_rect,
                "data": TEAM["Andrea Bondi"],
                "name_override": "Andrea Bondi"
            })
            
    # CASE B: OTHERS (Dual Signer)
    else:
        # We need two slots. 
        
        # Slot 1 (Left): ALWAYS Andrea Bondi
        if slot_left_instances:
            sigs_to_place.append({
                "rect": slot_left_instances[0], # The position where "Andrea" was
                "name_override": "Andrea Bondi",
                "data": TEAM["Andrea Bondi"]     
            })
            
        # Slot 2 (Right): The Creator
        # Note: We replace whoever is in the right slot (Laura) with the Creator
        if slot_right_instances:
            sigs_to_place.append({
                "rect": slot_right_instances[0], 
                "name_override": creator_name,  # Put Creator Name here
                "data": TEAM[creator_name]      # Creator Details
            })
        elif not slot_right_instances and template_idx == 9: 
             # [cite_start]Fallback: If we are on EasyMap Page 10[cite: 121], right slot is Laura.
             # If exact text search fails (due to formatting), we might skip, but usually it works.
             pass

    # --- EXECUTE SIGNATURE REPLACEMENT ---
    
    for sig in sigs_to_place:
        base_rect = sig["rect"]
        data = sig["data"]
        display_name = sig["name_override"]
        
        # 1. Define Cleaning Zone (Wipe old name, title, and signature space)
        # We go up 50px to catch the signature, down 20px for title
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
    # Sidebar Configuration
    st.sidebar.header("Configuration")
    
    # 1. Who is creating this?
    creator = st.sidebar.selectbox("Certificate Creator", list(TEAM.keys()))
    
    # 2. Check for signature file
    sig_status = "✅ Found" if os.path.exists(TEAM[creator]["file"]) else "❌ Missing in Repo"
    st.sidebar.caption(f"Creator Sig: {sig_status}")

    # Tabs
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
            # Calculate template index based on creator + type
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
