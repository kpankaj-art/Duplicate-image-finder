import collections
import io
import streamlit as st
from pptx import Presentation
from PIL import Image
import imagehash

st.set_page_config(page_title="Large PPT Duplicate Finder", layout="wide")

st.title("PPT Duplicate Image Finder (Up to 2GB)")
st.write("Apni heavy PPT file upload karein aur duplicate images scan karein.")

# 2GB upload limit set karne ke baad file uploader
uploaded_file = st.file_uploader("PPTX File Upload Karein", type=["pptx"])

if uploaded_file is not None:
    st.info("File badi hone ke karan scanning me thoda time lag sakta hai, kripya wait karein...")
    
    prs = Presentation(uploaded_file)
    hashes = collections.defaultdict(list)

    for slide_index, slide in enumerate(prs.slides):
        img_count = 0
        for shape in slide.shapes:
            if shape.shape_type == 13:  # Picture shape
                img_count += 1
                try:
                    image_bytes = shape.image.blob
                    img = Image.open(io.BytesIO(image_bytes))
                    
                    # Memory bachane ke liye image resize karke hash calculate karna
                    small_img = img.resize((128, 128))
                    img_hash = str(imagehash.average_hash(small_img))
                    
                    info = {
                        "slide": slide_index + 1,
                        "img_num": img_count,
                        "image": small_img
                    }
                    hashes[img_hash].append(info)
                except Exception as e:
                    continue

    duplicates_found = False
    st.subheader("Results:")

    for img_hash, locations in hashes.items():
        if len(locations) > 1:
            duplicates_found = True
            st.warning(f"Duplicate Image Mili! ({len(locations)} baar repeat hui hai)")
            
            col_img, col_details = st.columns([1, 3])
            with col_img:
                st.image(locations[0]["image"], caption="Duplicate Photo", width=150)
            
            with col_details:
                for loc in locations:
                    st.write(f"• **Slide {loc['slide']}** ki **Image #{loc['img_num']}**")
            st.divider()

    if not duplicates_found:
        st.success("Kisi bhi slide me koi duplicate image nahi mili.")
