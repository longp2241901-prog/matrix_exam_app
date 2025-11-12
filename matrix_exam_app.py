import streamlit as st
from groq import Groq
import os
import re
import random
from docx import Document
from docx.shared import RGBColor
import PyPDF2
from io import BytesIO
from docx import Document as DocReader
import copy
import zipfile
#=====================
# 🔓 Giải nén data.zip nếu chưa có thư mục data
if not os.path.exists("data"):
    if os.path.exists("data.zip"):
        with zipfile.ZipFile("data.zip", 'r') as zip_ref:
            zip_ref.extractall(".")
        print("✅ Đã giải nén data.zip")
    else:
        print("⚠️ Không tìm thấy data.zip")
# =========================
# 🧹 Hàm làm sạch nội dung trước khi Tex hóa
# =========================
def clean_text_for_tex(text: str) -> str:
    """Bỏ 'Câu 1.', 'A.', 'B.'... và làm gọn văn bản"""
    # Bỏ Câu 1., Câu 2.
    text = re.sub(r"C[âa]u\s*\d+\s*[.:]", "", text, flags=re.IGNORECASE)
    # Bỏ A. B. C. D. (trắc nghiệm)
    text = re.sub(r"\b[ABCDĐ]\s*\.", "", text)
    # Bỏ a) b) c) d) (đúng/sai)
    text = re.sub(r"\b[a-d]\)", "", text)
    # Làm gọn khoảng trắng
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


# =========================
# ⚙️ Cấu hình trang
# =========================
st.set_page_config(layout="wide")
#st.title("📝 Sinh đề kiểm tra từ ma trận (chuẩn ex_test)")
# =========================   
# 🧮 Thông tin ứng dụng & Tác giả (hiển thị đầu trang)
# =========================
st.markdown(
    """
    <div style='text-align: center; line-height: 1.6; margin-bottom: 20px;'>
        <img src="https://cdn-icons-png.flaticon.com/512/3523/3523063.png" width="55" style="margin-bottom: 5px;" />
        <h1 style="margin-bottom: 0;">SinhĐề+</h1>
        <p style="color: gray; font-size: 16px; margin-top: 4px;">
            Ứng dụng sinh đề kiểm tra tự động — <b>Phạm Tiến Long & Trương Thị Huỳnh Trang</b> (2025)
        </p>
        <p style="font-size: 15px; color: #555;">
            📞 Liên hệ hỗ trợ: <a href="tel:0396595129" style="text-decoration: none; color: #3366cc;">0396595129</a><br>
            ✉️ Email: <a href="mailto:longp2241901@gmail.com" style="text-decoration: none; color: #3366cc;">longp2241901@gmail.com</a>
        </p>
    </div>
    """,
    unsafe_allow_html=True
)



# =========================
# 🔑 Nhập API Key
# =========================
# =========================
# =========================
# 🔑 Nhập Groq API Key cá nhân
# =========================
st.markdown("### 🔐 Nhập key Groq API cá nhân")

# Ô nhập API key
user_api_key = st.text_input(
    "Nhập Groq API Key của bạn (bắt đầu bằng 'gsk_...')",
    type="password",
    help="Bạn cần có Groq API Key riêng để sử dụng. Lấy tại https://console.groq.com/keys",
)

# Hướng dẫn thêm
st.info(
    """
    💡 **Cách lấy Groq API Key:**
    1. Truy cập [https://console.groq.com/keys](https://console.groq.com/keys)
    2. Đăng nhập (hoặc tạo tài khoản miễn phí)
    3. Chọn **Create API Key**
    4. Sao chép key (dạng `gsk_...`) và dán vào ô trên.
    
    ⚠️ **Lưu ý giới hạn sử dụng:**
    - Mỗi API key có giới hạn ~100.000 token mỗi ngày (đếm cả input + output).  
    - Nếu vượt giới hạn, bạn sẽ thấy lỗi `Rate limit reached`.  
    - Sau khoảng **30–60 phút**, Groq sẽ tự động reset quota để bạn tiếp tục sử dụng.
    """,
    icon="ℹ️"
)

# Lưu key vào session
if user_api_key:
    st.session_state["api_key"] = user_api_key.strip()
    st.success("✅ API Key đã được lưu. Bạn có thể bắt đầu sử dụng ứng dụng.")
else:
    st.warning("🔑 Hãy nhập API Key để tiếp tục.")

# Nếu chưa có key thì dừng app
if "api_key" not in st.session_state:
    st.stop()

# Gán biến dùng chung cho toàn app
api_key = st.session_state["api_key"]



# =========================
# 🧠 Hàm tiện ích
# =========================
def get_sample_file(mon, lop, topic, dang_cauhoi, muc_do, dang):
    base_dir = "data"
    folder = os.path.join(base_dir, mon, lop, topic, dang_cauhoi, muc_do)
    filename = f"{dang}.txt"
    return os.path.join(folder, filename)

def split_ex_blocks(latex_text):
    """Tách từng câu hỏi \\begin{ex} ... \\end{ex}"""
    return re.findall(r"\\begin{ex}.*?\\end{ex}", latex_text, re.S)

# =========================
# 💾 Xuất LaTeX
# =========================
def export_latex_ex(all_questions, filename="output.tex"):
    latex_content = (
        "\\documentclass[12pt]{article}\n"
        "\\usepackage[utf8]{vietnam}\n"
        "\\usepackage{ex_test}\n"
        "\\begin{document}\n"
        "\\section*{Đề kiểm tra}\n"
    )
    latex_content += "\n\n".join(all_questions)
    latex_content += "\n\\end{document}"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(latex_content)
    return filename

# =========================
# 💾 Xuất Word
# =========================
def export_word_ex(all_questions, filename="output.docx"):
    from docx import Document
    from docx.shared import RGBColor, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    doc.add_heading("Đề kiểm tra", 0)
    questions = []
    for q in all_questions:
        questions.extend(split_ex_blocks(q))

    # --- Tách câu theo loại ---
    mc_questions = []      # \choice
    tf_questions = []      # \choiceTF
    short_questions = []   # \shortans

    for q in questions:
        if "\\choice" in q and not "\\choiceTF" in q:
            mc_questions.append(q)
        elif "\\choiceTF" in q:
            tf_questions.append(q)
        elif "\\shortans" in q:
            short_questions.append(q)

    section_map = [
        ("PHẦN I – TRẮC NGHIỆM 4 LỰA CHỌN", mc_questions),
        ("PHẦN II – TRẮC NGHIỆM ĐÚNG SAI", tf_questions),
        ("PHẦN III – TRẢ LỜI NGẮN", short_questions)
    ]

    ques_counter = 1
    for title, qlist in section_map:
        if not qlist:
            continue

        # Tiêu đề section
        p_title = doc.add_paragraph()
        run_title = p_title.add_run(title)
        run_title.bold = True
        run_title.font.size = Pt(14)
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph("")  # thêm 1 dòng trống

        for q in qlist:
            # ===== Nội dung câu hỏi =====
            noi_dung_match = re.search(
                r"\\begin\{ex\}([\s\S]*?)(?=\\choice|\\choiceTF|\\shortans|\\loigiai|\\end\{ex\})",
                q, re.MULTILINE,
            )
            noi_dung = noi_dung_match.group(1).strip() if noi_dung_match else q
            noi_dung = noi_dung.replace("\\\\", "\n").replace("\r", "")

            p = doc.add_paragraph()
            run_q = p.add_run(f"Câu {ques_counter}. ")
            run_q.bold = True
            p.add_run(noi_dung)

            dap_an = None

            # ===== Trắc nghiệm nhiều lựa chọn =====
            if "\\choice" in q and not "\\choiceTF" in q:
                lc_block = re.search(r"\\choice(.*?)(?=\\loigiai|\\end{ex})", q, re.S)
                if lc_block:
                    lines = lc_block.group(1).splitlines()
                    options = []
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        is_true = "\\True" in line
                        line = line.replace("\\True", "").strip("{} ")
                        options.append((line, is_true))
                    for j, (opt, is_true) in enumerate(options):
                        label = chr(65 + j) + "."
                        p_opt = doc.add_paragraph()
                        run = p_opt.add_run(f"{label} {opt}")
                        if is_true:
                            run.bold = True
                            run.underline = True
                            run.font.color.rgb = RGBColor(255, 0, 0)
                            dap_an = chr(65 + j)

            # ===== Đúng / Sai =====
            elif "\\choiceTF" in q:
                tf_block = re.search(r"\\choiceTF(.*?)(?=\\loigiai|\\end{ex})", q, re.S)
                if tf_block:
                    lines = tf_block.group(1).splitlines()
                    tf_ans = ""
                    idx_tf = 0
                    for line in lines:
                        line = line.strip("{} \t")
                        if not line:
                            continue
                        is_true = "\\True" in line
                        clean_line = line.replace("\\True", "").strip()
                        label = f"{chr(97 + idx_tf)})"
                        p_opt = doc.add_paragraph()
                        run = p_opt.add_run(f"{label} {clean_line}")
                        if is_true:
                            run.bold = True
                            run.underline = True
                            run.font.color.rgb = RGBColor(255, 0, 0)
                        tf_ans += "Đ" if is_true else "S"
                        idx_tf += 1
                    dap_an = tf_ans

            # ===== Trả lời ngắn =====
            elif "\\shortans" in q:
                sa_block = re.search(r"\\shortans\{(.*?)\}", q)
                if sa_block:
                    doc.add_paragraph("Trả lời ngắn: ............")
                    dap_an = sa_block.group(1).strip()

            # ===== Lời giải =====
            loi_giai_match = re.search(r"\\loigiai\{([\s\S]*?)(?=\\end\{ex\})", q)
            if loi_giai_match:
                loi_giai = loi_giai_match.group(1).strip()
                loi_giai = loi_giai.replace("\\\\", "\n").strip()
                if loi_giai.endswith("}"):
                    loi_giai = loi_giai[:-1].rstrip()

                p_lg = doc.add_paragraph()
                run_lg = p_lg.add_run("Lời giải: ")
                run_lg.bold = True
                if dap_an:
                    p_lg.add_run(f"Đáp án: {dap_an}. {loi_giai}")
                else:
                    p_lg.add_run(loi_giai)
            else:
                if dap_an:
                    p_lg = doc.add_paragraph()
                    run_lg = p_lg.add_run("Lời giải: ")
                    run_lg.bold = True
                    p_lg.add_run(f"Đáp án: {dap_an}.")

            ques_counter += 1

    doc.save(filename)
    return filename




# =========================
# ⚙️ Chế độ nhập dữ liệu
# =========================
mode = st.radio(
    "Chọn chế độ làm việc:",
    [
        "📂 Dùng dữ liệu có sẵn trong thư mục data",
        "✍️ Nhập câu hỏi mẫu thủ công",
        "📤 Kéo thả file PDF"
    ],
    horizontal=True
)

# =========================
# 📂 Giao diện cũ - dùng data
# =========================
# =========================
# 📂 Giao diện cũ - dùng data (mở rộng thêm môn)
# =========================
if mode.startswith("📂"):
    def list_subfolders(path):
        return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))] if os.path.exists(path) else []
    def list_txt_files(path):
        return [f[:-4] for f in os.listdir(path) if f.endswith(".txt")] if os.path.exists(path) else []
    BASE_DIR = "data"
    st.markdown("## 🧩 Ma trận chọn câu hỏi")
    ALL_MON = sorted(list_subfolders(BASE_DIR)) if os.path.exists(BASE_DIR) else []
    
    if "configs" not in st.session_state:
        st.session_state.configs = [{"mon": "", "lop": "", "topic": "", "dang_cauhoi": "", "muc_do": "", "dang": "", "count": 1}]
    
    if st.button("➕ Thêm cấu hình"):
        st.session_state.configs.append({"mon": "", "lop": "", "topic": "", "dang_cauhoi": "", "muc_do": "", "dang": "", "count": 1})
        st.rerun()

    for idx, cfg in enumerate(list(st.session_state.configs)):
        cols = st.columns([1.2,1.2,1.6,1.4,1.4,1.6,0.9,0.8])
        
        # 🔹 Môn
        with cols[0]:
            mon_folders = list_subfolders(BASE_DIR)
            cfg["mon"] = st.selectbox("Môn", mon_folders, key=f"mon_{idx}") if mon_folders else ""
        
        # 🔹 Lớp
        with cols[1]:
            lops = list_subfolders(os.path.join(BASE_DIR, cfg["mon"])) if cfg["mon"] else []
            cfg["lop"] = st.selectbox("Lớp", lops, key=f"lop_{idx}") if lops else ""
        
        # 🔹 Chủ đề
        with cols[2]:
            topics = list_subfolders(os.path.join(BASE_DIR, cfg["mon"], cfg["lop"])) if cfg["lop"] else []
            cfg["topic"] = st.selectbox("Chủ đề", topics, key=f"topic_{idx}") if topics else ""
        
        # 🔹 Loại câu hỏi
        with cols[3]:
            dang_cauhoi = list_subfolders(os.path.join(BASE_DIR, cfg["mon"], cfg["lop"], cfg["topic"])) if cfg["topic"] else []
            cfg["dang_cauhoi"] = st.selectbox("Loại", dang_cauhoi, key=f"dang_{idx}") if dang_cauhoi else ""
        
        # 🔹 Mức độ
        with cols[4]:
            mucdos = list_subfolders(os.path.join(BASE_DIR, cfg["mon"], cfg["lop"], cfg["topic"], cfg["dang_cauhoi"])) if cfg["dang_cauhoi"] else []
            cfg["muc_do"] = st.selectbox("Mức độ", mucdos, key=f"mucdo_{idx}") if mucdos else ""
        
        # 🔹 Dạng
        with cols[5]:
            dang_files = list_txt_files(os.path.join(BASE_DIR, cfg["mon"], cfg["lop"], cfg["topic"], cfg["dang_cauhoi"], cfg["muc_do"])) if cfg["muc_do"] else []
            cfg["dang"] = st.selectbox("Dạng", dang_files, key=f"file_{idx}") if dang_files else ""
        
        # 🔹 Số lượng
        with cols[6]:
            cfg["count"] = st.number_input("Số lượng", 1, 50, cfg.get("count", 1), key=f"count_{idx}")
        
        # 🔹 Xóa cấu hình
        with cols[7]:
            if st.button("❌", key=f"remove_{idx}"):
                st.session_state.configs.pop(idx)
                st.rerun()


# =========================
# ✍️ Giao diện nhập tay
# =========================
elif mode.startswith("✍️"):
    st.markdown("## ✍️ Nhập nội dung câu hỏi mẫu (theo chuẩn ex_test)")
    user_input = st.text_area(
        "Nhập nội dung LaTeX của câu hỏi (\\begin{ex} ... \\end{ex}):",
        height=300,
        placeholder="""Ví dụ:
Dạng 4 lựa chọn: \\begin{ex} ... \\choice{A}{\\True B}{C}{D} \\loigiai{Giải thích...} \\end{ex}
Dạng đúng sai: \\begin{ex} ... \\choiceTF{a}{\\True b}{c}{\\True d} \\loigiai{Giải thích...} \\end{ex}
Dạng trả lời ngắn: \\begin{ex} ... \\shortans[oly]{đáp số}\\end{ex}
"""
    )
    so_luong_tu_nhap = st.number_input("Số lượng câu muốn sinh thêm:", 1, 50, 5)

# =========================
# 📤 Kéo thả Word / PDF
# =========================
else:
    st.markdown("## 📤 Kéo thả file PDF để đọc nội dung")
    st.info(
        """
        💡 **Hướng dẫn sử dụng:**
        - Ứng dụng chỉ hỗ trợ **file PDF**.
        - Nếu bạn có file **Word (.docx)** chứa đề gốc, vui lòng **chuyển sang PDF** trước khi tải lên.
        - Cách đơn giản nhất: Mở Word → Chọn **File → Save As → PDF**.
        - Sau khi tải lên PDF, hệ thống sẽ tự động đọc, làm sạch và Tex hóa nội dung.
        ⚠️ Mỗi lần xử lý, ứng dụng chỉ đọc **tối đa 2 trang đầu tiên của PDF** để đảm bảo tốc độ và độ chính xác.
        ⚠️ Bạn có thể dùng **khoảng 10–12 lần/ngày** trước khi đạt giới hạn token. Khi đạt giới hạn token hãy **chờ 30–60 phút** để tiếp tục.
        """,
        icon="ℹ️"
    )
    uploaded_file = st.file_uploader("📄 Kéo thả hoặc chọn file PDF tại đây", type=["pdf"])
    extracted_text = ""
#==========
    if uploaded_file:
        file_type = uploaded_file.name.split(".")[-1].lower()
        extracted_text = ""

        if file_type == "docx":
            doc = DocReader(uploaded_file)
            for para in doc.paragraphs:
                extracted_text += para.text + "\n"
        elif file_type == "pdf":
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            total_pages = len(pdf_reader.pages)

            # ✅ Cho phép người dùng chọn trang (ví dụ: "1,2" hoặc "5-6")
            page_input = st.text_input(
                f"Nhập số trang cần Tex hóa (1–{total_pages}, tối đa 2 trang):",
                value="1,2"
            )

            # 🔢 Hàm lấy danh sách trang từ chuỗi nhập
            def parse_page_input(text):
                pages = set()
                for part in text.split(","):
                    part = part.strip()
                    if "-" in part:
                        start, end = part.split("-")
                        pages.update(range(int(start), int(end) + 1))
                    elif part.isdigit():
                        pages.add(int(part))
                # Giới hạn tối đa 2 trang
                return sorted(list(pages))[:2]

            selected_pages = parse_page_input(page_input)
            selected_pages = [p for p in selected_pages if 1 <= p <= total_pages]

            if not selected_pages:
                st.warning("⚠️ Vui lòng nhập số trang hợp lệ (tối đa 2 trang).")
            else:
                st.info(f"📄 Đang đọc các trang: {', '.join(map(str, selected_pages))}")
                extracted_text = ""
                for p in selected_pages:
                    page = pdf_reader.pages[p - 1]
                    text = page.extract_text()
                    if text:
                        extracted_text += text + "\n"

        # 🔹 Làm sạch nội dung
        extracted_text = clean_text_for_tex(extracted_text)

        st.text_area("📜 Nội dung đọc được:", extracted_text, height=300)

    
#=======
        action = st.radio("Chọn hành động:", ["🧠 Tex hóa nội dung", "🚀 Sinh đề tương tự"], horizontal=True)

        if st.button("⚙️ Thực hiện"):
            client = Groq(api_key=api_key)
            if action.startswith("🧠"):
            #====
                prompt = f"""
Hãy chuyển văn bản sau đây thành định dạng LaTeX theo chuẩn ex_test.

Yêu cầu:
- Không thêm 'Câu 1.' hoặc 'Câu 2.'.
- Nếu có các lựa chọn trắc nghiệm (A., B., C., D.), hãy chuyển thành:
  \\choice
  {{đáp án 1}}
  {{đáp án 2}}
  {{đáp án 3}}
  {{đáp án 4}}
   (mỗi đáp án trên 1 dòng riêng)
- Nếu là bài đúng/sai, dùng:
  \\choiceTF
  {{mệnh đề 1}}
  {{mệnh đề 2}}
  {{mệnh đề 3}}
  {{mệnh đề 4}}
- Mỗi bài đặt trong \\begin{{ex}} ... \\end{{ex}}, có \\loigiai{{...}} ở cuối.
Văn bản cần xử lý:
{extracted_text}
⚠️ Chỉ trả về LaTeX thuần, không thêm lời giải thích.
"""
            else:
                prompt = f"""
Dưới đây là nội dung văn bản người dùng cung cấp:
{extracted_text}

Hãy sinh 5 câu hỏi tương tự (giống phong cách, chủ đề, độ dài).
Dạng LaTeX chuẩn ex_test:
- Dùng \\begin{{ex}} ... \\end{{ex}}
- Có \\loigiai{{...}} ở cuối
⚠️ Chỉ trả về LaTeX, không thêm chú thích nào khác.
"""
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    #model="llama-3.1-8b-instant",
                    temperature=0.7,
                )
                output = chat_completion.choices[0].message.content.strip()
                st.code(output, language="latex")
                # --- Bản vá lỗi Word trống ---
                st.session_state.all_questions = [output]
                st.session_state["pdf_generated_output"] = output  # giữ lại nội dung sinh từ PDF
                st.session_state["last_mode"] = "pdf"              # ghi nhớ nguồn dữ liệu
                # --- Kết thúc bản vá ---
                st.success("✅ Hoàn tất xử lý văn bản.")
            except Exception as e:
                st.error(f"Lỗi khi gọi Groq API: {e}")

# =========================
# 🚀 Sinh câu hỏi (2 chế độ đầu)
# =========================
col_gen = st.columns([1,1,1])
with col_gen[0]:
    submitted = st.button("🚀 Sinh câu hỏi")
with col_gen[1]:
    export_word_btn = st.button("⬇️ Xuất Word")
with col_gen[2]:
    export_tex_btn = st.button("⬇️ Xuất LaTeX")

if "all_questions" not in st.session_state:
    st.session_state.all_questions = []

if submitted and not mode.startswith("📤"):
    client = Groq(api_key=api_key)
    all_questions = []
    if mode.startswith("✍️"):
        if not user_input.strip():
            st.warning("⚠️ Vui lòng nhập ít nhất một câu hỏi mẫu.")
        else:
            prompt = f"""
Dưới đây là câu hỏi mẫu theo chuẩn ex_test:
{user_input}

Hãy sinh thêm {so_luong_tu_nhap} câu hỏi tương tự bằng tiếng Việt.
Yêu cầu:
- Giữ nguyên cấu trúc LaTeX (\\begin{{ex}} ... \\end{{ex}})
- Nếu câu mẫu có \\choiceTF thì sinh đúng dạng đó, nếu có \\shortans thì sinh tương ứng
- Mỗi câu có \\loigiai{{...}} ở cuối
⚠️ Chỉ trả về LaTeX, không thêm chú thích nào khác.
"""
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    #model="llama-3.1-8b-instant",
                    temperature=0.7,
                )
                output = chat_completion.choices[0].message.content.strip()
                all_questions.append(output)
                st.code(output, language="latex")
                st.success(f"✅ Đã sinh {so_luong_tu_nhap} câu từ nội dung nhập thủ công.")
            except Exception as e:
                st.error(f"Lỗi khi gọi Groq API: {e}")
    else:
        for cfg in st.session_state.configs:
            file_path = get_sample_file(cfg["mon"], cfg["lop"], cfg["topic"], cfg["dang_cauhoi"], cfg["muc_do"], cfg["dang"])
            if not os.path.exists(file_path):
                st.warning(f"❌ Không tìm thấy file: {file_path}")
                continue
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            cau_truc = "luôn dùng \\choiceTF" if "\\choiceTF" in content else ("luôn dùng \\shortans" if "\\shortans" in content else "luôn dùng \\choice")
            prompt = f"""
Đây là các câu hỏi mẫu theo chuẩn ex_test:
{content}
Hãy sinh {cfg['count']} câu hỏi tương tự bằng tiếng Việt.
Yêu cầu:
- Dùng \\begin{{ex}} ... \\end{{ex}}
- {cau_truc}
- Mỗi câu có \\loigiai{{...}}
- Nếu có hình tikz thì sinh code tikz phù hợp
⚠️ Chỉ trả về LaTeX, không thêm chữ nào khác.
"""
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    #model="llama-3.1-8b-instant",
                    temperature=0.7,
                )
                output = chat_completion.choices[0].message.content.strip()
                st.code(output, language="latex")
                all_questions.append(output)
                st.success(f"✅ Đã sinh {cfg['count']} câu từ file.")
            except Exception as e:
                st.error(f"Lỗi khi gọi Groq API: {e}")

    st.session_state.all_questions = all_questions

# =========================
# 💾 Xuất file
# =========================
if export_word_btn:
    # --- Dự phòng cho trường hợp sinh từ PDF ---
    if st.session_state.get("all_questions"):
        data_to_export = st.session_state["all_questions"]
    elif st.session_state.get("pdf_generated_output"):
        data_to_export = [st.session_state["pdf_generated_output"]]
    else:
        data_to_export = []

    if data_to_export:
        word_file = export_word_ex(data_to_export, "de_kiem_tra.docx")
        with open(word_file, "rb") as f:
            st.download_button("⬇️ Tải Word", f, file_name="de_kiem_tra.docx")
    else:
        st.warning("⚠️ Không có dữ liệu để xuất Word. Vui lòng sinh đề trước.")

#-----
if export_tex_btn and st.session_state.all_questions:
    tex_file = export_latex_ex(st.session_state.all_questions, "de_kiem_tra.tex")
    with open(tex_file, "rb") as f:
        st.download_button("⬇️ Tải LaTeX", f, file_name="de_kiem_tra.tex")

# =========================
# 👀 Preview

st.markdown("## 🎲 Tạo mã đề trộn tự động")

num_versions = st.number_input("Số mã đề muốn tạo", 1, 10, 3)
mix_questions = st.button("🔀 Trộn và tạo mã đề")

# =========================
# 🧩 Hàm phụ trợ
# =========================
def shuffle_choices(q_text):
    """Trộn ngẫu nhiên các lựa chọn \\choice{} trong 1 câu hỏi"""
    pattern = r"\\choice(.*?)(?=\\loigiai|\\end\{ex\})"
    match = re.search(pattern, q_text, re.S)
    if not match:
        return q_text, None  # không có lựa chọn

    block = match.group(1)
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    clean_lines = []
    for l in lines:
        is_true = "\\True" in l
        l = l.replace("\\True", "").strip("{} ")
        clean_lines.append((l, is_true))

    random.shuffle(clean_lines)
    new_block = "\\choice\n" + "\n".join(
        "{" + (("\\True " if is_true else "") + l) + "}" for l, is_true in clean_lines
    )

    q_text_new = q_text.replace(match.group(0), new_block)
    new_answer = chr(65 + [i for i, (_, is_true) in enumerate(clean_lines) if is_true][0])
    return q_text_new, new_answer


def classify_question(q_text):
    """Xác định loại câu hỏi: 4 lựa chọn, đúng sai, trả lời ngắn"""
    if "\\choiceTF" in q_text:
        return "TF"
    elif "\\choice" in q_text:
        return "MC"
    elif "\\shortans" in q_text:
        return "SA"
    else:
        return "OTHER"


# =========================
# 🚀 Trộn đề
# =========================
if mix_questions and st.session_state.all_questions:
    all_q = "\n".join(st.session_state.all_questions)
    questions = split_ex_blocks(all_q)

    os.makedirs("tmp", exist_ok=True)

    word_files, tex_files = [], []

    for ver in range(1, int(num_versions) + 1):
        q_copy = copy.deepcopy(questions)
        random.shuffle(q_copy)

        # --- Phân loại câu hỏi ---
        q_mc = [q for q in q_copy if classify_question(q) == "MC"]
        q_tf = [q for q in q_copy if classify_question(q) == "TF"]
        q_sa = [q for q in q_copy if classify_question(q) == "SA"]

        # Trộn thứ tự trong từng nhóm
        random.shuffle(q_mc)
        random.shuffle(q_tf)
        random.shuffle(q_sa)

        mixed_questions = []
        answer_key = []

        # --- Phần I: Trắc nghiệm 4 lựa chọn ---
        mixed_questions.append("\\section*{Phần I – Trắc nghiệm 4 lựa chọn}")
        for i, q in enumerate(q_mc, 1):
            q_new, ans = shuffle_choices(q)
            mixed_questions.append(q_new)
            if ans:
                answer_key.append(f"Câu {i}: {ans}")
            else:
                answer_key.append(f"Câu {i}: ---")

        # --- Phần II: Trắc nghiệm đúng sai ---
        start_tf = len(answer_key) + 1
        mixed_questions.append("\\section*{Phần II – Trắc nghiệm đúng sai}")
        for j, q in enumerate(q_tf, start=start_tf):
            mixed_questions.append(q)
            match = re.findall(r"\\True|\\False", q)
            if match:
                key = " / ".join(match)
                answer_key.append(f"Câu {j}: {key}")
            else:
                answer_key.append(f"Câu {j}: ---")

        # --- Phần III: Trả lời ngắn ---
        start_sa = len(answer_key) + 1
        mixed_questions.append("\\section*{Phần III – Trả lời ngắn}")
        for k, q in enumerate(q_sa, start=start_sa):
            mixed_questions.append(q)
            sa = re.search(r"\\shortans\{(.*?)\}", q)
            if sa:
                answer_key.append(f"Câu {k}: {sa.group(1).strip()}")
            else:
                answer_key.append(f"Câu {k}: ---")

        # --- Xuất Word và LaTeX ---
        de_file = f"tmp/De_so_{ver}.docx"
        dap_an_file = f"tmp/Dapan_so_{ver}.docx"
        export_word_ex(mixed_questions, de_file)

        doc_ans = Document()
        doc_ans.add_heading(f"ĐÁP ÁN - MÃ ĐỀ {ver}", 0)
        for line in answer_key:
            doc_ans.add_paragraph(line)
        doc_ans.save(dap_an_file)
        word_files += [de_file, dap_an_file]

        tex_file = f"tmp/De_so_{ver}.tex"
        export_latex_ex(mixed_questions, tex_file)
        dap_an_tex = f"tmp/Dapan_so_{ver}.txt"
        with open(dap_an_tex, "w", encoding="utf-8") as f:
            f.write("\n".join(answer_key))
        tex_files += [tex_file, dap_an_tex]

    # --- Đóng gói ZIP ---
    word_zip = "tmp/De_Word.zip"
    tex_zip = "tmp/De_LaTeX.zip"
    with zipfile.ZipFile(word_zip, "w") as zipf:
        for f in word_files:
            zipf.write(f, os.path.basename(f))
    with zipfile.ZipFile(tex_zip, "w") as zipf:
        for f in tex_files:
            zipf.write(f, os.path.basename(f))

    # Lưu để không mất khi rerun
    st.session_state.word_zip = word_zip
    st.session_state.tex_zip = tex_zip

    st.success(f"✅ Đã tạo {num_versions} mã đề và đáp án thành công!")


# =========================
# 💾 Nút tải file ZIP
# =========================
if "word_zip" in st.session_state and os.path.exists(st.session_state.word_zip):
    with open(st.session_state.word_zip, "rb") as f:
        st.download_button("⬇️ Tải tất cả file Word (.zip)", f, file_name="De_Word.zip")

if "tex_zip" in st.session_state and os.path.exists(st.session_state.tex_zip):
    with open(st.session_state.tex_zip, "rb") as f:
        st.download_button("⬇️ Tải tất cả file LaTeX (.zip)", f, file_name="De_LaTeX.zip")


    st.success(f"✅ Đã tạo {num_versions} mã đề và đáp án thành công!")

# =========================
if st.session_state.all_questions:
    st.markdown("### Xem trước (5 câu đầu)")
    for q in st.session_state.all_questions[:5]:
        st.code(q, language="latex")



