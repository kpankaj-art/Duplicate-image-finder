import collections
import io
import base64
import re
import gc
import streamlit as st
from pptx import Presentation
from PIL import Image
import imagehash
import pytesseract

st.set_page_config(page_title="PPT Dual Matcher (Geo + Visual)", layout="wide", initial_sidebar_state="expanded")

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

st.title("🖼️ PPT Geo-Tag & Visual Image Search Tool")

def get_thumbnail_base64(img, max_size=(300, 300)):
    thumb = img.copy()
    thumb.thumbnail(max_size)
    buffered = io.BytesIO()
    thumb.save(buffered, format="JPEG", quality=75)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

# 1. Geo-Tag Extractor (Reads Lat/Long via OCR)
def extract_geo_coordinates(img):
    try:
        w, h = img.size
        # Crop bottom 35% where GPS Camera overlay stamp exists
        stamp_area = img.crop((0, int(h * 0.65), w, h))
        text = pytesseract.image_to_string(stamp_area)
        
        # Regex search for Lat & Long patterns (e.g., Lat 28.723053°, Long 77.854382°)
        lat_match = re.search(r'Lat\s*([0-9]+\.[0-9]+)', text, re.IGNORECASE)
        long_match = re.search(r'Long\s*([0-9]+\.[0-9]+)', text, re.IGNORECASE)
        
        if lat_match and long_match:
            # Rounding to 4 decimal places for high precision matching
            lat = round(float(lat_match.group(1)), 4)
            lng = round(float(long_match.group(1)), 4)
            return f"{lat},{lng}"
    except Exception:
        pass
    return None

# 2. Visual Image Hasher (Ignores GPS overlay)
def get_visual_hash(img):
    w, h = img.size
    # Crop top 65% area to exclude GPS overlay
    cropped = img.crop((0, 0, w, int(h * 0.65)))
    small = cropped.resize((128, 128))
    return str(imagehash.phash(small))

with st.sidebar:
    st.header("⚙️ Controls")
    uploaded_file = st.file_uploader("1. PPTX File Upload", type=["pptx"])
    st.divider()
    search_image_file = st.file_uploader("2. Search Specific Image (Optional)", type=["jpg", "jpeg", "png", "webp"])

if uploaded_file is None:
    st.info("👈 Sidebar se PPTX file upload karein scanning start karne ke liye.")
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
                            geo_key = extract_geo_coordinates(img)
                            v_hash = get_visual_hash(img)
                            b64_str = get_thumbnail_base64(img)
                            
                            ppt_images.append({
                                "slide": slide_index + 1,
                                "img_num": img_count,
                                "geo": geo_key,
                                "hash": v_hash,
                                "b64_img": b64_str
                            })
                    except Exception:
                        continue

        progress_bar.empty()
        status_text.empty()
        gc.collect()

        tab1, tab2 = st.tabs(["📋 Duplicate Report", "🔍 Image / Geo Search"])

        # TAB 1: Duplicate Identification
        with tab1:
            geo_groups = collections.defaultdict(list)
            hash_groups = collections.defaultdict(list)
            
            for item in ppt_images:
                if item["geo"]:
                    geo_groups[item["geo"]].append(item)
                hash_groups[item["hash"]].append(item)

            duplicates_found = False
            processed_slides = set()

            # Geo-tag duplicates
            for geo, locations in geo_groups.items():
                if len(locations) > 1:
                    duplicates_found = True
                    st.warning(f"**Duplicate Geo-Tag Found** (Lat/Long: `{geo}`) — {len(locations)} occurrences")
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        st.markdown(f'<img src="{locations[0]["b64_img"]}" class="zoom-img" tabindex="0">', unsafe_allow_html=True)
                    with c2:
                        for loc in locations:
                            processed_slides.add((loc["slide"], loc["img_num"]))
                            st.write(f"• **Slide {loc['slide']}** → Image #{loc['img_num']}")
                    st.divider()

            if not duplicates_found:
                st.success("No duplicate images found.")

        # TAB 2: Custom Search (Geo + Visual Dual Verification)
        with tab2:
            if search_image_file is None:
                st.info("👈 Upload an image in sidebar to search.")
            else:
                with Image.open(search_image_file) as target_img:
                    target_geo = extract_geo_coordinates(target_img)
                    target_hash = get_visual_hash(target_img)
                    target_b64 = get_thumbnail_base64(target_img)
                
                matches = []
                match_type = ""

                # Step 1: Geo Matching (Highest Accuracy)
                if target_geo:
                    matches = [item for item in ppt_images if item["geo"] == target_geo]
                    if matches:
                        match_type = f"Matched via Geo-Coordinates (`{target_geo}`)"

                # Step 2: Fallback to Visual Matching if Geo fails
                if not matches:
                    matches = [
                        item for item in ppt_images 
                        if (imagehash.hex_to_hash(target_hash) - imagehash.hex_to_hash(item["hash"])) <= 2
                    ]
                    if matches:
                        match_type = "Matched via Visual Image Features"

                if matches:
                    st.success(f"**Match Found!** ({match_type}) in {len(matches)} location(s):")
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        st.markdown(f'<img src="{target_b64}" class="zoom-img" tabindex="0">', unsafe_allow_html=True)
                    with c2:
                        for match in matches:
                            st.write(f"• **Slide {match['slide']}** → Image #{match['img_num']}")
                else:
                    st.error("This image or Geo-location was **NOT** found in the uploaded PPT.")

    except Exception as e:
        st.error(f"Error processing file: {e}")
