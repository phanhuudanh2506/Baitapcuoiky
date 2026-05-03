import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os
import cv2
from PIL import Image
import pytesseract
import docx
import PyPDF2
import json
from datetime import datetime

# ================= CẤU HÌNH GIAO DIỆN =================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# Sidebar
SB_BG          = "#0D1F15"
SB_BTN_HOVER   = "#12291C"
SB_BTN_ACTIVE  = "#1A4A2C"
SB_ACCENT      = "#16A34A"
SB_ACCENT2     = "#4ADE80"

# Nội dung
PAGE_BG        = "#142B1E"
CARD_BG        = "#1A3526"
CARD_BORDER    = "#224A32"

# Chữ
TXT_WHITE      = "#F0FFF4"
TXT_MUTED      = "#4D7A5A"
TXT_ACCENT     = "#4ADE80"

# Menu Navigation
navigate_items = [
    {"id": "home", "icon": "🏠", "label": "HOME", "description": "Trang chủ & Thống kê"},
    {"id": "checker", "icon": "🔍", "label": "CHECKER", "description": "Kiểm tra 2 văn bản"},
    {"id": "compare", "icon": "📂", "label": "COMPARE FILES", "description": "Quét thư mục đối chiếu"},
    {"id": "history", "icon": "🕐", "label": "HISTORY", "description": "Lịch sử kiểm tra"},
    {"id": "help", "icon": "❓", "label": "HELP", "description": "Hướng dẫn sử dụng"}
]

# ================= CÁC HÀM XỬ LÝ LÕI ĐỘC LẬP (Không dùng Class / Staticmethod) =================
STOPWORDS = {"là", "của", "và", "các", "những", "một", "cho", "đến", "trong", "có", "được", "với", "tại", "theo"}
HISTORY_FILE = "history.json"

def extract_text(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.txt':
            with open(path, 'r', encoding='utf-8') as f: return f.read()
        elif ext == '.docx':
            doc = docx.Document(path)
            return "\n".join([p.text for p in doc.paragraphs])
        elif ext == '.pdf':
            text = ""
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages: 
                    text += (page.extract_text() or "") + "\n"
            return text
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không đọc được file: {e}")
    return None

def opencv_preprocess(image_path):
    img = cv2.imread(image_path)
    if img is None: return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    processed = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    temp_file = "temp_ocr.png"
    cv2.imwrite(temp_file, processed)
    return temp_file

def preprocess_words(text):
    words = re.findall(r'\b\w+\b', text.lower())
    return [w for w in words if w not in STOPWORDS]

def get_similarity(words1, words2, n=2):
    if not words1 or not words2: return 0, set()
    s1 = set([tuple(words1[i:i+n]) for i in range(len(words1)-n+1)])
    s2 = set([tuple(words2[i:i+n]) for i in range(len(words2)-n+1)])
    if not s1 or not s2: return 0, set()
    inter = s1.intersection(s2)
    return (len(inter) / len(s1.union(s2))) * 100, inter

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_history(record):
    hist = load_history()
    hist.insert(0, record) # Thêm vào đầu danh sách
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=4)

class Base_Page(ctk.CTkFrame):
    def __init__(self, master, title, subtitle, icon, app_ref, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=PAGE_BG, **kwargs)
        self.app_ref = app_ref
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=CARD_BG)
        header.pack(fill="x")
        h_inner = ctk.CTkFrame(header, fg_color="transparent")
        h_inner.pack(fill="x", padx=32, pady=18)
        ctk.CTkLabel(h_inner, text=icon, width=48, height=48, font=("Arial", 26), fg_color="#252D40", corner_radius=12).pack(side="left", padx=(0, 16))
        t_col = ctk.CTkFrame(h_inner, fg_color="transparent")
        t_col.pack(side="left", fill="y")
        ctk.CTkLabel(t_col, text=title, font=("Arial Black", 18, "bold"), text_color=TXT_WHITE, anchor="w").pack(fill="x")
        ctk.CTkLabel(t_col, text=subtitle, font=("Arial", 12), text_color=TXT_MUTED, anchor="w").pack(fill="x")
        self.body = ctk.CTkFrame(self, fg_color=PAGE_BG)
        self.body.pack(fill="both", expand=True, padx=20, pady=20)
        self.build_body()
    def build_body(self): pass

class Home_Page(Base_Page):
    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, icon="🏠", title="Dashboard", subtitle="Hệ thống kiểm tra tương đồng văn bản", app_ref=app_ref, **kwargs)
    
    def build_body(self):
        welcome_lbl = ctk.CTkLabel(self.body, text="Chào mừng đến với Plagiarism Checker", font=("Arial", 22, "bold"), text_color=TXT_ACCENT)
        welcome_lbl.pack(pady=(20, 5))
        ctk.CTkLabel(self.body, text="Chọn một chức năng bên dưới để bắt đầu:", font=("Arial", 14), text_color=TXT_WHITE).pack(pady=(0, 30))

        # Container cho các phím tắt
        grid_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=40)
        grid_frame.grid_columnconfigure((0, 1), weight=1)

        # Danh sách các chức năng chính để làm nút bấm
        shortcuts = [
            {"id": "checker", "icon": "🔍", "label": "CHECKER", "desc": "So sánh 2 văn bản hoặc quét ảnh OCR."},
            {"id": "compare", "icon": "📂", "label": "COMPARE FILES", "desc": "Đối chiếu 1 file với cả thư mục."},
            {"id": "history", "icon": "🕐", "label": "HISTORY", "desc": "Xem lại các lần kiểm tra trước đây."},
            {"id": "help", "icon": "❓", "label": "HELP", "desc": "Hướng dẫn sử dụng chi tiết hệ thống."}
        ]

        row, col = 0, 0
        for item in shortcuts:
            card = self.create_shortcut_card(grid_frame, item)
            card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
            col += 1
            if col > 1:
                col = 0
                row += 1

    def create_shortcut_card(self, parent, item):
        # Thẻ Card
        card = ctk.CTkFrame(parent, fg_color=CARD_BG, border_color=CARD_BORDER, border_width=1, corner_radius=15, cursor="hand2")
        
        # Icon to
        lbl_icon = ctk.CTkLabel(card, text=item["icon"], font=("Arial", 40))
        lbl_icon.pack(pady=(25, 10))

        # Tên chức năng
        lbl_title = ctk.CTkLabel(card, text=item["label"], font=("Arial", 16, "bold"), text_color=TXT_ACCENT)
        lbl_title.pack()

        # Mô tả ngắn
        lbl_d = ctk.CTkLabel(card, text=item["desc"], font=("Arial", 11), text_color=TXT_MUTED, wraplength=220)
        lbl_d.pack(pady=(5, 25))

        # Hiệu ứng hover và sự kiện Click cho Card và tất cả thành phần bên trong
        def on_click(e): self.app_ref.navigate(item["id"])
        def on_enter(e): card.configure(border_color=SB_ACCENT, fg_color=SB_BTN_HOVER)
        def on_leave(e): card.configure(border_color=CARD_BORDER, fg_color=CARD_BG)

        for widget in [card, lbl_icon, lbl_title, lbl_d]:
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        return card
# ================= CÁC COMPONENT UI =================
class Navigate_Buttons(ctk.CTkFrame):
    def __init__(self, master, item: dict, command, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=10, **kwargs)
        self.item = item
        self.command = command
        self.active = False
        self.build()
        self.bind_all_children(self)

    def build(self):
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.bar = ctk.CTkLabel(self, text="", width=4, height=44, fg_color="transparent", corner_radius=2)
        self.bar.grid(row=0, column=0, padx=(6, 0), pady=6)

        self.icon_label = ctk.CTkLabel(self, text=self.item["icon"], font=("Arial", 20), width=36, height=44, text_color=TXT_MUTED)
        self.icon_label.grid(row=0, column=1, padx=(8, 4), pady=6)

        text_frame = ctk.CTkFrame(self, fg_color="transparent")
        text_frame.grid(row=0, column=2, sticky="w", padx=(4, 12), pady=6)

        self.lbl_name = ctk.CTkLabel(text_frame, text=self.item["label"], font=("Arial", 13), text_color=TXT_MUTED, anchor="w")
        self.lbl_name.pack(fill="x")

        self.lbl_desc = ctk.CTkLabel(text_frame, text=self.item["description"], font=("Arial", 10), text_color=TXT_MUTED, anchor="w")
        self.lbl_desc.pack(fill="x")

    def set_active(self, active: bool):
        self.active = active
        if active:
            self.configure(fg_color=SB_BTN_ACTIVE)
            self.bar.configure(fg_color=SB_ACCENT)
            self.lbl_name.configure(text_color=TXT_WHITE, font=("Arial", 13, "bold"))
            self.icon_label.configure(text_color=SB_ACCENT2)
        else:
            self.configure(fg_color="transparent")
            self.bar.configure(fg_color="transparent")
            self.lbl_name.configure(text_color=TXT_MUTED, font=("Arial", 13))
            self.icon_label.configure(text_color=TXT_MUTED)

    def bind_all_children(self, widget):
        widget.bind("<Button-1>", self.on_click)
        widget.bind("<Enter>", self.on_enter)
        widget.bind("<Leave>", self.on_leave)
        for child in widget.winfo_children():
            self.bind_all_children(child)

    def on_click(self, _=None): self.command(self.item["id"])
    def on_enter(self, _=None): 
        if not self.active: self.configure(fg_color=SB_BTN_HOVER)
    def on_leave(self, _=None): 
        if not self.active: self.configure(fg_color="transparent")

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate, **kwargs):
        super().__init__(master, width=230, corner_radius=0, fg_color=SB_BG, **kwargs)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self.buttons: dict[str, Navigate_Buttons] = {}
        self.build()

    def build(self):
        menu = ctk.CTkLabel(self, text="MENU", font=("Arial Black", 24, "bold"), text_color="#FFFFFF", anchor="w")
        menu.pack(fill="x", padx=40, pady=(20, 15))

        navigate_frame = ctk.CTkFrame(self, fg_color="transparent")
        navigate_frame.pack(fill="x", padx=8)
        for item in navigate_items:
            button = Navigate_Buttons(navigate_frame, item=item, command=self.on_navigate)
            button.pack(fill="x", pady=2)
            self.buttons[item["id"]] = button
        
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)
        ctk.CTkLabel(self, text="v1.0.0 • 2026", font=("Arial", 10), text_color=TXT_MUTED).pack(pady=(0, 15))

    def set_active(self, page_id: str):
        for pid, button in self.buttons.items():
            button.set_active(pid == page_id)

class Base_Page(ctk.CTkFrame):
    def __init__(self, master, title, subtitle, icon, app_ref, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=PAGE_BG, **kwargs)
        self.app_ref = app_ref
        
        header = ctk.CTkFrame(self, corner_radius=0, fg_color=CARD_BG, border_width=0)
        header.pack(fill="x")

        header_inner_frame = ctk.CTkFrame(header, fg_color="transparent")
        header_inner_frame.pack(fill="x", padx=32, pady=18)

        header_inner = ctk.CTkLabel(header_inner_frame, text=icon, width=48, height=48, font=("Arial", 26), fg_color="#252D40", corner_radius=12)
        header_inner.pack(side="left", padx=(0, 16))

        title_column_frame = ctk.CTkFrame(header_inner_frame, fg_color="transparent")
        title_column_frame.pack(side="left", fill="y")

        ctk.CTkLabel(title_column_frame, text=title, font=("Arial Black", 18, "bold"), text_color=TXT_WHITE, anchor="w").pack(fill="x")
        ctk.CTkLabel(title_column_frame, text=subtitle, font=("Arial", 12), text_color=TXT_MUTED, anchor="w").pack(fill="x")

        ctk.CTkFrame(self, height=1, fg_color="#252D40").pack(fill="x")

        self.body = ctk.CTkFrame(self, fg_color=PAGE_BG)
        self.body.pack(fill="both", expand=True, padx=20, pady=20)
        self.build_body()

    def build_body(self): pass

# ================= CÁC TRANG CHỨC NĂNG =================

class Checker_Page(Base_Page):
    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, icon="🔍", title="Kiểm tra 2 Văn Bản", subtitle="So sánh chi tiết mức độ trùng lặp giữa văn bản gốc và văn bản cần kiểm tra", app_ref=app_ref, **kwargs)
        
    def build_body(self):
        text_container = ctk.CTkFrame(self.body, fg_color="transparent")
        text_container.pack(fill="both", expand=True, pady=(0, 10))
        
        self.txt_1 = self.create_text_column(text_container, "VĂN BẢN GỐC / ĐỐI CHIẾU", side="left")
        self.txt_2 = self.create_text_column(text_container, "VĂN BẢN CẦN KIỂM TRA", side="right")

        self.txt_1.tag_config("match", background="#b8860b", foreground="white")
        self.txt_2.tag_config("match", background="#b8860b", foreground="white")

        action_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        action_frame.pack(fill="x", pady=10)

        self.lbl_result = ctk.CTkLabel(action_frame, text="Mức độ tương đồng: 0%", font=("Arial", 18, "bold"), text_color="#F59E0B")
        self.lbl_result.pack(side="left", padx=20)

        ctk.CTkButton(action_frame, text="BẮT ĐẦU SO SÁNH", font=("Arial", 14, "bold"), fg_color="#16A34A", hover_color="#15803D", command=self.compare_action, height=40).pack(side="right", padx=10)
        ctk.CTkButton(action_frame, text="Xóa Trắng", font=("Arial", 14), fg_color="transparent", border_width=1, border_color="#EF4444", text_color="#EF4444", hover_color="#451a1a", command=self.clear_all, height=40).pack(side="right", padx=10)

    def create_text_column(self, parent, title, side):
        col = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=10)
        col.pack(side=side, fill="both", expand=True, padx=10)
        
        header = ctk.CTkFrame(col, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text=title, font=("Arial", 14, "bold"), text_color=TXT_WHITE).pack(side="left")
        
        ctk.CTkButton(header, text="🖼️ Ảnh (OCR)", width=90, fg_color="#EAB308", text_color="black", hover_color="#CA8A04", command=lambda: self.load_image(txt_area)).pack(side="right", padx=5)
        ctk.CTkButton(header, text="📄 Chọn File", width=90, fg_color="#3B82F6", hover_color="#2563EB", command=lambda: self.load_file(txt_area)).pack(side="right", padx=5)
        
        txt_area = ctk.CTkTextbox(col, font=("Arial", 13), wrap="word", fg_color="#0F172A", border_color="#1E293B", border_width=1)
        txt_area.pack(fill="both", expand=True, padx=10, pady=(0,10))
        return txt_area

    def load_file(self, widget):
        path = filedialog.askopenfilename(filetypes=[("Tài liệu", "*.txt *.docx *.pdf")])
        if path:
            content = extract_text(path)
            if content:
                widget.delete("1.0", tk.END)
                widget.insert(tk.END, content)

    def load_image(self, widget):
        path = filedialog.askopenfilename(filetypes=[("Ảnh", "*.jpg *.png *.jpeg")])
        if path:
            cleaned_path = opencv_preprocess(path)
            if cleaned_path:
                text = pytesseract.image_to_string(Image.open(cleaned_path), lang='vie', config='--psm 6')
                widget.delete("1.0", tk.END)
                widget.insert(tk.END, text.strip())

    def highlight(self, r1, r2):
        self.txt_1.tag_remove("match", "1.0", tk.END)
        self.txt_2.tag_remove("match", "1.0", tk.END)
        _, common = get_similarity(preprocess_words(r1), preprocess_words(r2))
        
        for ngram in common:
            phrase = " ".join(ngram)
            for w in [self.txt_1, self.txt_2]:
                start_idx = "1.0"
                while True:
                    start_idx = w._textbox.search(phrase, start_idx, stopindex=tk.END, nocase=True)
                    if not start_idx: break
                    end_idx = f"{start_idx}+{len(phrase)}c"
                    w.tag_add("match", start_idx, end_idx)
                    start_idx = end_idx

    def compare_action(self):
        r1 = self.txt_1.get("1.0", tk.END).strip()
        r2 = self.txt_2.get("1.0", tk.END).strip()
        if r1 and r2:
            sim, _ = get_similarity(preprocess_words(r1), preprocess_words(r2))
            self.lbl_result.configure(text=f"Mức độ tương đồng: {sim:.2f}%")
            self.highlight(r1, r2)
            
            # Lưu lịch sử
            record = {
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "mode": "Kiểm tra 2 File",
                "similarity": f"{sim:.2f}%",
                "detail": "Đã thực hiện so sánh 2 văn bản độc lập."
            }
            save_history(record)
            if "history" in self.app_ref.pages:
                self.app_ref.pages["history"].refresh()

    def clear_all(self):
        self.txt_1.delete("1.0", tk.END)
        self.txt_2.delete("1.0", tk.END)
        self.lbl_result.configure(text="Mức độ tương đồng: 0%")


class Compare_Page(Base_Page):
    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, icon="📂", title="Compare Files in Folder", subtitle="So sánh văn bản mục tiêu với hàng loạt file trong thư mục", app_ref=app_ref, **kwargs)
        
    def build_body(self):
        top_frame = ctk.CTkFrame(self.body, fg_color=CARD_BG, corner_radius=10)
        top_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        top_header = ctk.CTkFrame(top_frame, fg_color="transparent")
        top_header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top_header, text="VĂN BẢN CẦN KIỂM TRA", font=("Arial", 14, "bold"), text_color=TXT_WHITE).pack(side="left")
        ctk.CTkButton(top_header, text="📄 Chọn File", width=100, command=self.load_target).pack(side="right")
        
        self.txt_target = ctk.CTkTextbox(top_frame, font=("Arial", 13), wrap="word", fg_color="#0F172A")
        self.txt_target.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        bot_frame = ctk.CTkFrame(self.body, fg_color=CARD_BG, corner_radius=10)
        bot_frame.pack(fill="both", expand=True)

        bot_header = ctk.CTkFrame(bot_frame, fg_color="transparent")
        bot_header.pack(fill="x", padx=10, pady=10)
        self.lbl_best_match = ctk.CTkLabel(bot_header, text="KẾT QUẢ KHỚP NHẤT (Văn bản đối chiếu)", font=("Arial", 14, "bold"), text_color=TXT_ACCENT)
        self.lbl_best_match.pack(side="left")
        
        ctk.CTkButton(bot_header, text="📁 Chọn Thư Mục & Quét", width=150, fg_color="#16A34A", hover_color="#15803D", command=self.check_folder).pack(side="right")
        
        self.txt_best = ctk.CTkTextbox(bot_frame, font=("Arial", 13), wrap="word", fg_color="#0F172A")
        self.txt_best.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.txt_target.tag_config("match", background="#b8860b", foreground="white")
        self.txt_best.tag_config("match", background="#b8860b", foreground="white")

    def load_target(self):
        path = filedialog.askopenfilename(filetypes=[("Tài liệu", "*.txt *.docx *.pdf")])
        if path:
            content = extract_text(path)
            if content:
                self.txt_target.delete("1.0", tk.END)
                self.txt_target.insert(tk.END, content)

    def check_folder(self):
        target = self.txt_target.get("1.0", tk.END).strip()
        if not target:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập/chọn văn bản cần kiểm tra trước!")
            return
            
        folder = filedialog.askdirectory()
        if not folder: return
        
        w_target = preprocess_words(target)
        max_sim, best_match, best_content = 0, "", ""

        for file in os.listdir(folder):
            if file.lower().endswith(('.txt', '.docx', '.pdf')):
                content = extract_text(os.path.join(folder, file))
                if content:
                    sim, _ = get_similarity(preprocess_words(content), w_target)
                    if sim > max_sim:
                        max_sim, best_match, best_content = sim, file, content

        if best_match:
            self.txt_best.delete("1.0", tk.END)
            self.txt_best.insert(tk.END, best_content)
            self.lbl_best_match.configure(text=f"KHỚP NHẤT: {best_match} - Tương đồng: {max_sim:.2f}%")
            self.highlight(best_content, target)
            
            record = {
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "mode": "Quét Thư Mục",
                "similarity": f"{max_sim:.2f}%",
                "detail": f"Trùng lặp lớn nhất với file: {best_match}"
            }
            save_history(record)
            if "history" in self.app_ref.pages:
                self.app_ref.pages["history"].refresh()
        else:
            messagebox.showinfo("Thông báo", "Không tìm thấy file hợp lệ trong thư mục này.")

    def highlight(self, r1, r2):
        self.txt_best.tag_remove("match", "1.0", tk.END)
        self.txt_target.tag_remove("match", "1.0", tk.END)
        _, common = get_similarity(preprocess_words(r1), preprocess_words(r2))
        
        for ngram in common:
            phrase = " ".join(ngram)
            for w in [self.txt_best, self.txt_target]:
                start_idx = "1.0"
                while True:
                    start_idx = w._textbox.search(phrase, start_idx, stopindex=tk.END, nocase=True)
                    if not start_idx: break
                    end_idx = f"{start_idx}+{len(phrase)}c"
                    w.tag_add("match", start_idx, end_idx)
                    start_idx = end_idx


class History_Page(Base_Page):
    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, icon="🕐", title="History", subtitle="Lịch sử các lần kiểm tra trước đây", app_ref=app_ref, **kwargs)
        
    def build_body(self):
        self.scrollable_frame = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self.scrollable_frame.pack(fill="both", expand=True)
        self.refresh()

    def refresh(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        history_data = load_history()
        
        if not history_data:
            ctk.CTkLabel(self.scrollable_frame, text="Chưa có dữ liệu lịch sử.", font=("Arial", 14), text_color=TXT_MUTED).pack(pady=20)
            return

        for record in history_data:
            card = ctk.CTkFrame(self.scrollable_frame, fg_color=CARD_BG, corner_radius=10)
            card.pack(fill="x", pady=8, padx=10)
            
            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=15, pady=(10, 5))
            
            ctk.CTkLabel(top_row, text=record["mode"], font=("Arial", 14, "bold"), text_color=TXT_WHITE).pack(side="left")
            ctk.CTkLabel(top_row, text=record["timestamp"], font=("Arial", 12), text_color=TXT_MUTED).pack(side="right")
            
            bot_row = ctk.CTkFrame(card, fg_color="transparent")
            bot_row.pack(fill="x", padx=15, pady=(0, 10))
            
            ctk.CTkLabel(bot_row, text=record["detail"], font=("Arial", 13), text_color=TXT_MUTED).pack(side="left")
            ctk.CTkLabel(bot_row, text=f"Tỷ lệ: {record['similarity']}", font=("Arial", 14, "bold"), text_color="#F59E0B").pack(side="right")


class Help_Page(Base_Page):
    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, icon="❓", title="Help & Tutorials", subtitle="Hướng dẫn sử dụng công cụ hiệu quả nhất", app_ref=app_ref, **kwargs)
        
    def build_body(self):
        textbox = ctk.CTkTextbox(self.body, font=("Arial", 14), fg_color=CARD_BG, text_color=TXT_WHITE, wrap="word")
        textbox.pack(fill="both", expand=True)
        
        help_text = """HƯỚNG DẪN SỬ DỤNG HỆ THỐNG KIỂM TRA ĐẠO VĂN

1. Trang Checker (Kiểm tra 2 file):
- Dùng để so sánh trực tiếp văn bản cần kiểm tra với một văn bản gốc duy nhất.
- Bấm "Chọn File" để tải file định dạng .txt, .pdf, .docx.
- Hoặc bấm "Ảnh (OCR)" để tải hình ảnh (cần cài đặt Tesseract), hệ thống sẽ trích xuất chữ viết trong ảnh.
- Nhấn "Bắt đầu so sánh". Các cụm từ giống nhau sẽ được bôi đậm (Highlight vàng) trên màn hình.

2. Trang Compare Files (Quét Thư Mục):
- Nhập hoặc chọn file văn bản cần kiểm tra ở khung phía trên.
- Nhấn "Chọn Thư Mục & Quét" ở khung dưới. Hệ thống sẽ quét toàn bộ các file (.txt, .docx, .pdf) trong thư mục đó.
- File nào có mức độ trùng lặp cao nhất sẽ được hiển thị ra màn hình cùng tỷ lệ phần trăm cụ thể.

3. Lịch sử (History):
- Mỗi lần bạn nhấn so sánh hoặc quét thư mục, kết quả sẽ tự động lưu lại đây.
- Bạn có thể xem lại chi tiết thời gian quét, thể loại kiểm tra và tỷ lệ trùng lặp.

LƯU Ý: Để kết quả OCR (quét ảnh) tốt nhất, hãy sử dụng ảnh có độ phân giải cao và nền giấy rõ ràng.
"""
        textbox.insert("1.0", help_text)
        textbox.configure(state="disabled")

# ================= CLASS CHÍNH (APP) =================
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Plagiarism Checker Toàn Diện")
        self.geometry("1280x750")
        
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.current: str = ""
        self.setup_layout()
        self.setup_pages()
        self.navigate("home")

    def setup_layout(self):
        self.sidebar = Sidebar(self, on_navigate=self.navigate)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

    def setup_pages(self):
        self.pages: dict[str, Base_Page] = {
            "home"   : Home_Page(self, app_ref=self),
            "checker": Checker_Page(self, app_ref=self),
            "compare": Compare_Page(self, app_ref=self),
            "history": History_Page(self, app_ref=self),
            "help"   : Help_Page(self, app_ref=self)
        }
        for page in self.pages.values():
            page.grid(row=0, column=1, sticky="nsew")
            page.grid_remove()

    def navigate(self, page_id: str):
        if self.current and self.current in self.pages:
            self.pages[self.current].grid_remove()
        if page_id in self.pages:
            self.pages[page_id].grid()
            self.current = page_id
            
            if page_id == "history":
                self.pages["history"].refresh()
                
        self.sidebar.set_active(page_id)

if __name__ == "__main__":
    app = App()
    app.mainloop()