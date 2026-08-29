import collections
import io
import base64
import gc
import streamlit as st
from pptx import Presentation
from PIL import Image
import imagehash

st.set_page_config(page_title="Exact Visual Matcher", layout="wide", initial_sidebar_state="expanded")

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

st.title("🖼️ PPT Visual-Only Exact Image Search")

# FIXED: Auto Convert RGBA/PNG to RGB before saving as JPEG
def get_thumbnail_base64(img, max_size=(300, 300)):
    thumb = img.copy()
    if thumb.mode in ("RGBA", "P"):
        thumb = thumb.convert("RGB")
    thumb.thumbnail(max_size)
    buffered = io.BytesIO()
    thumb.save(buffered, format="JPEG", quality=75)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

# Visual Feature Extraction (Ignores bottom 35% GPS Overlay)
def get_visual_fingerprint(img):
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    w, h = img.size
    # Crop top 65% area to exclude bottom map overlay
    clean_photo = img.crop((0, 0, w, int(h * 0.65)))
    
    # Calculate dual structural hashes for high precision
    d_hash = imagehash.dhash(clean_photo.resize((128, 128)))
    p_hash = imagehash.phash(clean_photo.resize((128, 128)))
    
    return d_hash, p_hash

with st.sidebar:
    st.header("⚙️ Controls")
    uploaded_file = st.file_uploader("1. PPTX File Upload", type=["pptx"])
    st.divider()
    search_image_file = st.file_uploader("2. Search Specific Image (Optional)", type=["jpg", "jpeg", "png", "webp"])

if uploaded_file is None:
    st.info("👈 Sidebar se PPTX file upload karein search start karne ke liye.")
else:
    try:
        prs = Presentation(uploaded_file)
        ppt_images = []
        
        total_slides = len(prs.slides)
        progress_bar = st.progress(0)
        status_text = st.empty()

        for slide_index, slide in enumerate(prs.slides):
            progress = (slide_index + 1) / total_slides
            progress_bar.progress(progress)
            status_text.text(f"Scanning Slide {slide_index + 1} of {total_slides}...")
            
            img_count = 0
            for shape in slide.shapes:
                if shape.shape_type == 13:
                    img_count += 1
                    try:
                        image_bytes = shape.image.blob
                        with Image.open(io.BytesIO(image_bytes)) as img:
                            d_hash, p_hash = get_visual_fingerprint(img)
                            b64_str = get_thumbnail_base64(img)
                            
                            ppt_images.append({
                                "slide": slide_index + 1,
                                "img_num": img_count,
                                "dhash": d_hash,
                                "phash": p_hash,
                                "b64_img": b64_str
                            })
                    except Exception:
                        continue

        progress_bar.empty()
        status_text.empty()
        gc.collect()

        tab1, tab2 = st.tabs(["📋 PPT Duplicates Report", "🔍 Search Specific Image"])

        # TAB 1: Internal Duplicates
        with tab1:
            hashes = collections.defaultdict(list)
            for item in ppt_images:
                hashes[str(item["dhash"])].append(item)
                
            duplicates_found = False
            for img_hash, locations in hashes.items():
                if len(locations) > 1:
                    duplicates_found = True
                    st.warning(f"**Duplicate Image Found** ({len(locations)} occurrences)")
                    
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        st.markdown(
                            f'<img src="{locations[0]["b64_img"]}" class="zoom-img" tabindex="0">', 
                            unsafe_allow_html=True
                        )

                    with c2:
                        for loc in locations:
                            st.write(f"• **Slide {loc['slide']}** → Image #{loc['img_num']}")
                    st.divider()

            if not duplicates_found:
                st.success("No duplicate images found in this PPT.")

        # TAB 2: Custom Image Search (Exact 95%+ Visual Filter)
        with tab2:
            if search_image_file is None:
                st.info("👈 Side menu me target image upload karein search ke liye.")
            else:
                with Image.open(search_image_file) as target_img:
                    target_dhash, target_phash = get_visual_fingerprint(target_img)
                    target_b64 = get_thumbnail_base64(target_img)
                
                matches = []
                for item in ppt_images:
                    diff_d = target_dhash - item["dhash"]
                    diff_p = target_phash - item["phash"]
                    
                    # Strict Visual Match Logic (Diff <= 1 means 95% to 100% same content)
                    if diff_d <= 1 and diff_p <= 2:
                        matches.append(item)
                
                if matches:
                    st.success(f"**Exact Visual Match Found!** Found in {len(matches)} location(s):")
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        st.markdown(
                            f'<img src="{target_b64}" class="zoom-img" tabindex="0">', 
                            unsafe_allow_html=True
                        )

                    with c2:
                        for match in matches:
                            st.write(f"• **Slide {match['slide']}** → Image #{match['img_num']}")
                else:
                    st.error("❌ Yeh image is PPT me **nahi mili**. (No 95%+ visual match found)")

    except Exception as e:
        st.error(f"Error processing file: {e}")
