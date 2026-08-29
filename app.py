import collections
import io
from PIL import Image
import imagehash
from pptx import Presentation
import streamlit as st

st.set_page_config(page_title="PPT Duplicate Image Finder", layout="wide")

st.title("PPT Duplicate Image Finder")
st.write("Apni PPT file upload karein aur jaanchein ki kis slide ki konsi image duplicate hai.")

uploaded_file = st.file_uploader("PPTX File Upload Karein", type=["pptx"])

if uploaded_file is not None:
    st.info("File scan ho rahi hai, kripya thoda wait karein...")
    
    prs = Presentation(uploaded_file)
    hashes = collections.defaultdict(list)

    # Scanning images across slides
    for slide_index, slide in enumerate(prs.slides):
        img_count = 0
        for shape in slide.shapes:
            if shape.shape_type == 13:  # Picture shape
                img_count += 1
                image_bytes = shape.image.blob
                img = Image.open(io.BytesIO(image_bytes))
                
                # Image visual hash calculation
                img_hash = str(imagehash.average_hash(img))
                
                info = {
                    "slide": slide_index + 1,
                    "img_num": img_count,
                    "image": img
                }
                hashes[img_hash].append(info)

    # Reporting results
    duplicates_found = False
    st.subheader("Results:")

    for img_hash, locations in hashes.items():
        if len(locations) > 1:
            duplicates_found = True
            st.warning(f"Duplicate Image Mili! ({len(locations)} baar repeat hui hai)")
            
            # Show the thumbnail of the duplicate image
            col_img, col_details = st.columns([1, 3])
            with col_img:
                st.image(locations[0]["image"], caption="Duplicate Image", width=150)
            
            with col_details:
                for loc in locations:
                    st.write(f"• **Slide {loc['slide']}** ki **Image #{loc['img_num']}**")
            st.divider()

    if not duplicates_found:
        st.success("Badhai ho! Kisi bhi slide me koi duplicate image nahi mili.")
