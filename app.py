import collections
import io
import base64
import gc
import cv2
import numpy as np
import streamlit as st
from pptx import Presentation
from PIL import Image

st.set_page_config(page_title="Strict Image Matcher (90%-100%)", layout="wide", initial_sidebar_state="expanded")

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

st.title("🖼️ Strict 90%-100% Exact Image Matcher")

def get_thumbnail_base64(img, max_size=(300, 300)):
    thumb = img.copy()
    if thumb.mode in ("RGBA", "P"):
        thumb = thumb.convert("RGB")
    thumb.thumbnail(max_size)
    buffered = io.BytesIO()
    thumb.save(buffered, format="JPEG", quality=75)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

def pil_to_cv2(pil_img):
    if pil_img.mode in ("RGBA", "P"):
        pil_img = pil_img.convert("RGB")
    open_cv_image = np.array(pil_img)
    return cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)

def get_features(cv_img):
    orb = cv2.ORB_create(nfeatures=500)
    kp, des = orb.detectAndCompute(cv_img, None)
    return des

def compare_features(des1, des2):
    if des1 is None or des2 is None:
        return 0
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    # Strict matching distance filter
    good_matches = [m for m in matches if m.distance < 40]
    return len(good_matches)

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
                            cv_img = pil_to_cv2(img)
                            des = get_features(cv_img)
                            b64_str = get_thumbnail_base64(img)
                            
                            ppt_images.append({
                                "slide": slide_index + 1,
                                "img_num": img_count,
                                "descriptors": des,
                                "b64_img": b64_str
                            })
                    except Exception:
                        continue

        progress_bar.empty()
        status_text.empty()
        gc.collect()

        st.subheader("🔍 90%-100% Exact Match Result")

        if search_image_file is None:
            st.info("👈 Upload an image in the sidebar to search.")
        else:
            with Image.open(search_image_file) as target_img:
                target_cv = pil_to_cv2(target_img)
                target_des = get_features(target_cv)
                target_b64 = get_thumbnail_base64(target_img)
            
            matches = []
            for item in ppt_images:
                match_score = compare_features(target_des, item["descriptors"])
                
                # STRICT THRESHOLD: Sirf 40+ matched features wale (90%-100% match) accept honge
                if match_score >= 40:
                    matches.append((item, match_score))
            
            # Sort matches so highest score comes on top
            matches.sort(key=lambda x: x[1], reverse=True)

            if matches:
                st.success(f"**Exact 90%-100% Match Found!** Found in {len(matches)} location(s):")
                c1, c2 = st.columns([1, 5])
                with c1:
                    st.markdown(
                        f'<img src="{target_b64}" class="zoom-img" tabindex="0">', 
                        unsafe_allow_html=True
                    )

                with c2:
                    for match_item, score in matches:
                        st.write(f"• **Slide {match_item['slide']}** → Image #{match_item['img_num']} *(Match Score: {score} features)*")
            else:
                st.error("❌ Koi bhi **90%-100% exact match** nahi mila.")

    except Exception as e:
        st.error(f"Error processing file: {e}")
