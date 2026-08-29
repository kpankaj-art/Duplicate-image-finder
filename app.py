import collections
import io
import base64
import streamlit as st
from pptx import Presentation
from PIL import Image
import imagehash

st.set_page_config(page_title="PPT Image Inspector", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS: Hide Streamlit header/footer and style controls
st.markdown("""
    <style>
    [data-testid="stToolbar"] {display: none !important;}
    footer {visibility: hidden !important;}
    .block-container {padding-top: 1.5rem; padding-bottom: 0rem;}
    h1 {font-size: 1.8rem !important; margin-bottom: 0.5rem;}
    .stAlert {padding: 0.5rem 1rem; margin-bottom: 0.5rem;}
    
    /* Image Lightbox Styling (Click to Full View) */
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

def get_image_as_base64(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

# --- TOP UPLOAD CONTROLS (MAIN SCREEN) ---
col_upload1, col_upload2 = st.columns(2)

with col_upload1:
    uploaded_file = st.file_uploader("1. PPTX File Upload Karein", type=["pptx"])

with col_upload2:
    search_image_file = st.file_uploader("2. Search Specific Image (Optional)", type=["jpg", "jpeg", "png", "webp"])

st.divider()

# --- MAIN DASHBOARD LOGIC ---
if uploaded_file is None:
    st.info("👆 Kripya upar diye gaye box me PPT file upload karein.")
else:
    try:
        with st.spinner("PPT scan ho rahi hai..."):
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
                        b64_img = get_image_as_base64(locations[0]["original_image"])
                        st.markdown(
                            f'<img src="{b64_img}" class="zoom-img" tabindex="0" title="Click to view full, Click away to close">', 
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
                st.info("👆 Upar optional image upload box me image daalein search karne ke liye.")
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
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        b64_target = get_image_as_base64(target_img)
                        st.markdown(
                            f'<img src="{b64_target}" class="zoom-img" tabindex="0" title="Click to view full, Click away to close">', 
                            unsafe_allow_html=True
                        )

                    with c2:
                        for match in matches:
                            st.write(f"• **Slide {match['slide']}** → Image #{match['img_num']}")
                else:
                    st.error("This image was **NOT** found in the uploaded PPT.")

    except Exception as e:
        st.error(f"Error processing file: {e}")
