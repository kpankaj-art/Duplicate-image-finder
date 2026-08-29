import collections
import io
import streamlit as st
from pptx import Presentation
from PIL import Image
import imagehash

st.set_page_config(page_title="PPT Image Finder", layout="wide")

st.title("PPT Duplicate Image Finder (Up to 2GB)")
st.write("Apni heavy PPT file direct upload karein aur duplicate images scan karein.")

# 1. Main PPT Upload Box (Top)
uploaded_file = st.file_uploader("PPTX File Upload Karein", type=["pptx"])

st.divider()

# 2. Optional Single Image Search Box (Bottom)
st.subheader("🔍 Specific Image Finder (Optional)")
st.write("Agar aapko PPT me koi alag se specific image dhoondni hai, toh use niche upload karein:")

search_image_file = st.file_uploader(
    "Specific Image Upload Karein (Optional)", 
    type=["jpg", "jpeg", "png", "webp"],
    key="single_img_search"
)

# Process Logic
if uploaded_file is not None:
    st.info("PPT scan ho rahi hai, kripya thoda wait karein...")
    
    try:
        prs = Presentation(uploaded_file)
        ppt_images = []

        # Extract all images from PPT
        for slide_index, slide in enumerate(prs.slides):
            img_count = 0
            for shape in slide.shapes:
                if shape.shape_type == 13:  # Picture shape
                    img_count += 1
                    try:
                        image_bytes = shape.image.blob
                        img = Image.open(io.BytesIO(image_bytes))
                        small_img = img.resize((128, 128))
                        img_hash = str(imagehash.average_hash(small_img))
                        
                        ppt_images.append({
                            "slide": slide_index + 1,
                            "img_num": img_count,
                            "hash": img_hash,
                            "image": small_img
                        })
                    except Exception:
                        continue

        # SECTION A: Specific Single Image Search (If uploaded)
        if search_image_file is not None:
            st.divider()
            st.subheader("🎯 Specific Image Search Result:")
            
            target_img = Image.open(search_image_file)
            target_small = target_img.resize((128, 128))
            target_hash = str(imagehash.average_hash(target_small))
            
            matches = []
            for item in ppt_images:
                hash_diff = imagehash.hex_to_hash(target_hash) - imagehash.hex_to_hash(item["hash"])
                if hash_diff <= 5:  # Similarity Threshold
                    matches.append(item)
            
            if matches:
                st.success(f"Haan! Ye Image PPT me mili hai ({len(matches)} jagah par):")
                
                col_target, col_found = st.columns([1, 3])
                with col_target:
                    st.image(target_img, caption="Aapki Uploaded Image", width=150)
                
                with col_found:
                    for match in matches:
                        st.write(f"• **Slide {match['slide']}** ki **Image #{match['img_num']}** me hai.")
            else:
                st.error("Ye Image di gayi PPT me kisi bhi slide par NAHI mili.")

        # SECTION B: Overall PPT Duplicate Scan
        st.divider()
        st.subheader("📋 PPT Internal Duplicates Report:")
        
        hashes = collections.defaultdict(list)
        for item in ppt_images:
            hashes[item["hash"]].append(item)
            
        duplicates_found = False
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
            st.success("PPT me aapas me koi duplicate image nahi mili.")

    except Exception as e:
        st.error(f"File process karne me dikkat aayi: {e}")
