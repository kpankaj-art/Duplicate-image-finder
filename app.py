import collections
import io
import re
import os
import gdown
import streamlit as st
from pptx import Presentation
from PIL import Image
import imagehash

st.set_page_config(page_title="Large PPT Duplicate Finder", layout="wide")
st.title("PPT Duplicate Image Finder (Large Files / No Limit)")

st.subheader("Option 1: Direct File Upload (Max 200MB)")
uploaded_file = st.file_uploader("PPTX File Upload Karein", type=["pptx"])

st.subheader("Option 2: Google Drive Link (2GB+ Files Ke Liye)")
gdrive_url = st.text_input("PPT File Ka Public Google Drive Link Yahan Paste Karein:")

file_to_process = None

if uploaded_file is not None:
    file_to_process = uploaded_file
elif gdrive_url:
    if st.button("Drive File Process Karein"):
        with st.spinner("Google Drive se file download ho rahi hai..."):
            file_id = re.search(r'[-\w]{25,}', gdrive_url)
            if file_id:
                download_url = f'https://drive.google.com/uc?id={file_id.group(0)}'
                output_path = "temp_ppt.pptx"
                gdown.download(download_url, output_path, quiet=False)
                file_to_process = output_path
            else:
                st.error("Invalid Google Drive Link! Kripya 'Anyone with the link' access wali file ka link daalein.")

if file_to_process:
    st.info("Scanning chal rahi hai...")
    
    try:
        prs = Presentation(file_to_process)
        hashes = collections.defaultdict(list)

        for slide_index, slide in enumerate(prs.slides):
            img_count = 0
            for shape in slide.shapes:
                if shape.shape_type == 13:  # Picture
                    img_count += 1
                    try:
                        image_bytes = shape.image.blob
                        img = Image.open(io.BytesIO(image_bytes))
                        
                        small_img = img.resize((128, 128))
                        img_hash = str(imagehash.average_hash(small_img))
                        
                        hashes[img_hash].append({
                            "slide": slide_index + 1,
                            "img_num": img_count,
                            "image": small_img
                        })
                    except Exception:
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

    finally:
        if isinstance(file_to_process, str) and os.path.exists(file_to_process):
            os.remove(file_to_process)
