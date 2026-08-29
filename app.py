import collections
import io
import streamlit as st
from pptx import Presentation
from PIL import Image
import imagehash

# Compact Page Layout
st.set_page_config(page_title="PPT Image Inspector", layout="wide", initial_sidebar_state="expanded")

# CSS styling for clean look
st.markdown("""
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 0rem;}
    [data-testid="stSidebar"] {padding-top: 0rem;}
    h1 {font-size: 1.8rem !important; margin-bottom: 0.5rem;}
    .stAlert {padding: 0.5rem 1rem; margin-bottom: 0.5rem;}
    </style>
""", unsafe_allow_html=True)

st.title("🖼️ PPT Image Duplicate & Search Tool")

# --- SIDEBAR (Controls) ---
with st.sidebar:
    st.header("⚙️ Controls")
    uploaded_file = st.file_uploader("1. PPTX File Upload", type=["pptx"])
    st.divider()
    search_image_file = st.file_uploader("2. Search Specific Image (Optional)", type=["jpg", "jpeg", "png", "webp"])

# --- MAIN DASHBOARD ---
if uploaded_file is None:
    st.info("👈 Please upload a PPTX file from the sidebar to start scanning.")
else:
    try:
        with st.spinner("Scanning PPT..."):
            prs = Presentation(uploaded_file)
            ppt_images = []

            for slide_index, slide in enumerate(prs.slides):
                img_count = 0
                for shape in slide.shapes:
                    if shape.shape_type == 13:
                        img_count += 1
                        try:
                            image_bytes = shape.image.blob
                            img = Image.open(io.BytesIO(image_bytes))
                            
                            # Original image for full view, small image for visual hashing
                            small_img = img.resize((128, 128))
                            img_hash = str(imagehash.average_hash(small_img))
                            
                            ppt_images.append({
                                "slide": slide_index + 1,
                                "img_num": img_count,
                                "hash": img_hash,
                                "original_image": img,
                                "small_image": small_img
                            })
                        except Exception:
                            continue

        # Tab layout for clean display
        tab1, tab2 = st.tabs(["📋 PPT Duplicates Report", "🔍 Specific Image Search"])

        # TAB 1: Duplicate Images Report
        with tab1:
            hashes = collections.defaultdict(list)
            for item in ppt_images:
                hashes[item["hash"]].append(item)
                
            duplicates_found = False
            for img_hash, locations in hashes.items():
                if len(locations) > 1:
                    duplicates_found = True
                    st.warning(f"**Duplicate Found** ({len(locations)} occurrences)")
                    
                    c1, c2 = st.columns([1.5, 3.5])
                    with c1:
                        # Displaying Thumbnail
                        st.image(locations[0]["original_image"], use_container_width=True)
                        
                        # Clickable Expander for Full Screen Large View
                        with st.expander("🔍 View Full Size Image"):
                            st.image(locations[0]["original_image"], use_container_width=True)

                    with c2:
                        for loc in locations:
                            st.write(f"• **Slide {loc['slide']}** → Image #{loc['img_num']}")
                    st.divider()

            if not duplicates_found:
                st.success("No internal duplicate images found in this PPT.")

        # TAB 2: Custom Search Result
        with tab2:
            if search_image_file is None:
                st.info("👈 Upload an image in the sidebar to search for it inside this PPT.")
            else:
                target_img = Image.open(search_image_file)
                target_small = target_img.resize((128, 128))
                target_hash = str(imagehash.average_hash(target_small))
                
                matches = [
                    item for item in ppt_images 
                    if (imagehash.hex_to_hash(target_hash) - imagehash.hex_to_hash(item["hash"])) <= 5
                ]
                
                if matches:
                    st.success(f"**Match Found!** Found in {len(matches)} location(s):")
                    c1, c2 = st.columns([1.5, 3.5])
                    with c1:
                        st.image(target_img, caption="Searched Image", use_container_width=True)
                        
                        # Clickable Expander for Full Screen Large View
                        with st.expander("🔍 View Full Size Image"):
                            st.image(target_img, use_container_width=True)

                    with c2:
                        for match in matches:
                            st.write(f"• **Slide {match['slide']}** → Image #{match['img_num']}")
                else:
                    st.error("This image was **NOT** found in the uploaded PPT.")

    except Exception as e:
        st.error(f"Error processing file: {e}")
