import collections
import io
import base64
import gc
import streamlit as st
from pptx import Presentation
from PIL import Image
import imagehash

st.set_page_config(page_title="PPT Image Inspector", layout="wide", initial_sidebar_state="expanded")

# Custom CSS: Hide Toolbar & Permanent Sidebar
st.markdown("""
    <style>
    [data-testid="stToolbar"] {display: none !important;}
    footer {visibility: hidden !important;}
    
    [data-testid="stSidebarCollapseButton"] {display: none !important;}
    button[title="Collapse sidebar"] {display: none !important;}
    
    .block-container {padding-top: 1.5rem; padding-bottom: 0rem;}
    [data-testid="stSidebar"] {padding-top: 0rem;}
    h1 {font-size: 1.8rem !important; margin-bottom: 0.5rem;}
    .stAlert {padding: 0.5rem 1rem; margin-bottom: 0.5rem;}
    
    .zoom-img {
        width: 120px;
        border-radius: 5px;
        cursor: pointer;
        transition: transform 0.25s ease;
    }
    .zoom-img:focus {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) scale(5);
        max-width: 80vw;
        max-height: 80vh;
        z-index: 99999;
        box-shadow: 0 0 20px rgba(0,0,0,0.8);
        outline: none;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🖼️ PPT Image Duplicate & Search Tool")

# Optimized Base64 Helper for Thumbnail
def get_thumbnail_base64(img, max_size=(300, 300)):
    thumb = img.copy()
    thumb.thumbnail(max_size)
    buffered = io.BytesIO()
    thumb.save(buffered, format="JPEG", quality=75)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Controls")
    uploaded_file = st.file_uploader("1. PPTX File Upload", type=["pptx"])
    st.divider()
    search_image_file = st.file_uploader("2. Search Specific Image (Optional)", type=["jpg", "jpeg", "png", "webp"])

# --- MAIN DASHBOARD LOGIC ---
if uploaded_file is None:
    st.info("👈 Please upload a PPTX file from the sidebar to start scanning.")
else:
    try:
        prs = Presentation(uploaded_file)
        ppt_images = []
        
        total_slides = len(prs.slides)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for slide_index, slide in enumerate(prs.slides):
            # Update Progress Bar
            progress = (slide_index + 1) / total_slides
            progress_bar.progress(progress)
            status_text.text(f"Scanning Slide {slide_index + 1} of {total_slides}...")
            
            img_count = 0
            for shape in slide.shapes:
                if shape.shape_type == 13: # Picture shape
                    img_count += 1
                    try:
                        image_bytes = shape.image.blob
                        with Image.open(io.BytesIO(image_bytes)) as img:
                            # Downsample image for hash calculation to save RAM
                            small_img = img.resize((64, 64))
                            img_hash = str(imagehash.average_hash(small_img))
                            
                            # Store low-res base64 string directly to avoid memory leak
                            b64_str = get_thumbnail_base64(img)
                            
                            ppt_images.append({
                                "slide": slide_index + 1,
                                "img_num": img_count,
                                "hash": img_hash,
                                "b64_img": b64_str
                            })
                    except Exception:
                        continue

        progress_bar.empty()
        status_text.empty()
        
        # Free memory
        gc.collect()

        tab1, tab2 = st.tabs(["📋 PPT Duplicates Report", "🔍 Specific Image Search"])

        # TAB 1: Duplicates Report
        with tab1:
            hashes = collections.defaultdict(list)
            for item in ppt_images:
                hashes[item["hash"]].append(item)
                
            duplicates_found = False
            for img_hash, locations in hashes.items():
                if len(locations) > 1:
                    duplicates_found = True
                    st.warning(f"**Duplicate Found** ({len(locations)} occurrences)")
                    
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        st.markdown(
                            f'<img src="{locations[0]["b64_img"]}" class="zoom-img" tabindex="0" title="Click to view full, Click away to close">', 
                            unsafe_allow_html=True
                        )

                    with c2:
                        for loc in locations:
                            st.write(f"• **Slide {loc['slide']}** → Image #{loc['img_num']}")
                    st.divider()

            if not duplicates_found:
                st.success("No internal duplicate images found in this PPT.")

        # TAB 2: Custom Search
        with tab2:
            if search_image_file is None:
                st.info("👈 Upload an image in the sidebar to search for it inside this PPT.")
            else:
                with Image.open(search_image_file) as target_img:
                    target_small = target_img.resize((64, 64))
                    target_hash = str(imagehash.average_hash(target_small))
                    target_b64 = get_thumbnail_base64(target_img)
                
                matches = [
                    item for item in ppt_images 
                    if (imagehash.hex_to_hash(target_hash) - imagehash.hex_to_hash(item["hash"])) <= 5
                ]
                
                if matches:
                    st.success(f"**Match Found!** Found in {len(matches)} location(s):")
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        st.markdown(
                            f'<img src="{target_b64}" class="zoom-img" tabindex="0" title="Click to view full, Click away to close">', 
                            unsafe_allow_html=True
                        )

                    with c2:
                        for match in matches:
                            st.write(f"• **Slide {match['slide']}** → Image #{match['img_num']}")
                else:
                    st.error("This image was **NOT** found in the uploaded PPT.")

    except Exception as e:
        st.error(f"Error processing file: {e}")
