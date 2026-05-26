import streamlit as st
import pandas as pd
import tempfile
import zipfile
import os
from PIL import Image, ImageDraw, ImageFont

st.set_page_config(page_title="EAN13 Barcode", layout="centered")
st.title("EAN-13 Barcode Generator")

L_CODE = {
    '0': '0001101', '1': '0011001', '2': '0010011',
    '3': '0111101', '4': '0100011', '5': '0110001',
    '6': '0101111', '7': '0111011', '8': '0110111',
    '9': '0001011'
}
G_CODE = {
    '0': '0100111', '1': '0110011', '2': '0011011',
    '3': '0100001', '4': '0011101', '5': '0111001',
    '6': '0000101', '7': '0010001', '8': '0001001',
    '9': '0010111'
}
R_CODE = {
    '0': '1110010', '1': '1100110', '2': '1101100',
    '3': '1000010', '4': '1011100', '5': '1001110',
    '6': '1010000', '7': '1000100', '8': '1001000',
    '9': '1110100'
}
FIRST_DIGIT_PATTERN = {
    '0': 'LLLLLL', '1': 'LLGLGG', '2': 'LLGGLG',
    '3': 'LLGGGL', '4': 'LGLLGG', '5': 'LGGLLG',
    '6': 'LGGGLL', '7': 'LGLGLG', '8': 'LGLGGL',
    '9': 'LGGLGL'
}


def calc_check_digit(code12):
    digits = [int(d) for d in code12]
    total  = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits))
    return (10 - (total % 10)) % 10


def encode_ean13(full_code):
    first   = full_code[0]
    pattern = FIRST_DIGIT_PATTERN[first]
    bits    = '101'
    for i, digit in enumerate(full_code[1:7]):
        bits += L_CODE[digit] if pattern[i] == 'L' else G_CODE[digit]
    bits += '01010'
    for digit in full_code[7:13]:
        bits += R_CODE[digit]
    bits += '101'
    return bits


def fit_font(text, max_width, font_path, start_size=30):
    for size in range(start_size, 5, -1):
        try:
            font = ImageFont.truetype(font_path, size)
        except:
            font = ImageFont.load_default()
        bbox = font.getbbox(text)
        if (bbox[2] - bbox[0]) <= max_width:
            return font, size
    return ImageFont.load_default(), 8


def draw_barcode(full_code,
                 bar_width=2,
                 bar_height=60,
                 guard_extra=15,
                 quiet_zone=20,
                 font_shrink=3,
                 text_y_offset=2):

    bits = encode_ean13(full_code)

    lg_start  = quiet_zone + 0  * bar_width
    lg2_start = quiet_zone + 3  * bar_width
    lg2_end   = quiet_zone + 45 * bar_width
    rg_start  = quiet_zone + 50 * bar_width

    group_w = lg2_end - lg2_start

    # หา font path (Windows / Linux)
    font_candidates = [
        "arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    font_path = None
    for candidate in font_candidates:
        if os.path.exists(candidate):
            font_path = candidate
            break

    _, fsize = fit_font("000000", group_w - 2, font_path or "arial.ttf", start_size=30)
    fsize    = max(6, fsize - font_shrink)

    try:
        font  = ImageFont.truetype(font_path, fsize)
        font1 = ImageFont.truetype(font_path, fsize)
    except:
        font  = ImageFont.load_default()
        font1 = font

    bbox_t = font.getbbox("0")
    font_h = bbox_t[3] - bbox_t[1]

    total_bar_h = bar_height + guard_extra
    margin_top  = 8
    total_w     = quiet_zone * 2 + len(bits) * bar_width
    total_h     = margin_top + total_bar_h + font_h + text_y_offset + 4

    img  = Image.new("RGB", (total_w, total_h), "white")
    draw = ImageDraw.Draw(img)

    guard_positions = set(range(0, 3)) | set(range(45, 50)) | set(range(92, 95))
    x = quiet_zone
    for i, bit in enumerate(bits):
        if bit == '1':
            h = bar_height + (guard_extra if i in guard_positions else 0)
            draw.rectangle(
                [x, margin_top, x + bar_width - 1, margin_top + h],
                fill="black"
            )
        x += bar_width

    y_text = margin_top + bar_height + text_y_offset

    g1   = full_code[0]
    g1_w = font1.getbbox(g1)[2] - font1.getbbox(g1)[0]
    g1_x = (lg_start - g1_w) // 2
    draw.text((g1_x, y_text), g1, fill="black", font=font1)

    g2   = full_code[1:7]
    g2_w = font.getbbox(g2)[2] - font.getbbox(g2)[0]
    g2_x = lg2_start + (group_w - g2_w) // 2
    draw.text((g2_x, y_text), g2, fill="black", font=font)

    g3   = full_code[7:13]
    g3_w = font.getbbox(g3)[2] - font.getbbox(g3)[0]
    g3_x = rg_start + (group_w - g3_w) // 2
    draw.text((g3_x, y_text), g3, fill="black", font=font)

    return img


def generate_barcode(value, folder):
    code = (
        str(value)
        .replace(",", "")
        .replace(".0", "")
        .strip()
    )
    if not code.isdigit():
        return None
    if len(code) > 12:
        code = code[:12]
    code = code.zfill(12)

    check     = calc_check_digit(code)
    full_code = code + str(check)

    img = draw_barcode(
        full_code,
        bar_width=2,
        bar_height=60,
        guard_extra=15,
        quiet_zone=20,
        font_shrink=3,
        text_y_offset=2,
    )

    out_path = os.path.join(folder, full_code + ".png")
    img.save(out_path, dpi=(300, 300))
    return out_path


# ----------------
# UI
# ----------------
uploaded = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])

if uploaded:
    df = pd.read_excel(uploaded)
    st.success("Upload สำเร็จ")

    column = st.selectbox("เลือกคอลัมน์", df.columns)

    if st.button("สร้างบาร์โค้ด"):
        temp    = tempfile.mkdtemp()
        images  = []
        skipped = []

        for row in df[column]:
            try:
                img = generate_barcode(row, temp)
                if img:
                    images.append(img)
                else:
                    skipped.append(str(row))
            except Exception as e:
                skipped.append(f"{row} ({e})")

        if skipped:
            st.warning(f"ข้ามค่าเหล่านี้: {', '.join(skipped)}")

        st.subheader("Preview")
        for img in images[:4]:
            st.image(img, width=350)

        zip_path = os.path.join(temp, "barcode.zip")
        with zipfile.ZipFile(zip_path, "w") as z:
            for f in images:
                z.write(f, os.path.basename(f))

        st.success(f"สร้างเสร็จแล้ว {len(images)} บาร์โค้ด")
        with open(zip_path, "rb") as f:
            st.download_button("Download ZIP", f, "barcode.zip")