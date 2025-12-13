import fitz  # PyMuPDF
import os

def create_certificate():
    # --- CONFIGURATION ---
    input_file = "Onboarding Certificate [CR team].pdf"
    output_file = "Mario_Rossi_Onboarding_Certificate.pdf"
    
    # Data to fill
    employee_name = "Mario Rossi"
    date_text = "12-Dec-2025"
    
    # Template 1 is on Page 4 (index 3)
    page_index = 3 
    # ---------------------

    if not os.path.exists(input_file):
        print(f"Error: Could not find '{input_file}'.")
        return

    try:
        doc = fitz.open(input_file)
        page = doc[page_index]

        # Format: (Placeholder, New Text, Font Size, Is Bold?)
        replacements = [
            ("[Employee Name]", employee_name, 12, True),
            ("DD-MMM-YYYY", date_text, 12, False)
        ]

        for placeholder, new_value, f_size, is_bold in replacements:
            instances = page.search_for(placeholder)
            
            if instances:
                for rect in instances:
                    # White-out the old text
                    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
                    
                    # Insert new text
                    insert_point = fitz.Point(rect.x0, rect.y1 - 2)
                    
                    # FIX: Use 'hebo' for Bold, 'helv' for Regular
                    current_font = "hebo" if is_bold else "helv"
                    
                    page.insert_text(
                        insert_point, 
                        new_value, 
                        fontsize=f_size, 
                        fontname=current_font, 
                        color=(0, 0, 0)
                    )
                    print(f"Replaced '{placeholder}' with '{new_value}'")
            else:
                print(f"Warning: Could not find '{placeholder}'")

        output_doc = fitz.open()
        output_doc.insert_pdf(doc, from_page=page_index, to_page=page_index)
        output_doc.save(output_file)
        output_doc.close()
        
        print(f"Success! Saved: {output_file}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    create_certificate()
