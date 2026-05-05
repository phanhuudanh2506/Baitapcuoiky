import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os
from PIL import Image
import pytesseract
import docx
import PyPDF2
from datetime import datetime
import threading
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
from difflib import SequenceMatcher

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

SB_BG        = "#0D1F15"
SB_BTN_HOVER = "#12291C"
SB_BTN_ACTIVE= "#1A4A2C"
SB_ACCENT    = "#16A34A"
SB_ACCENT2   = "#4ADE80"
PAGE_BG      = "#142B1E"
CARD_BG      = "#1A3526"
CARD_BORDER  = "#224A32"
TXT_WHITE    = "#F0FFF4"
TXT_MUTED    = "#4D7A5A"
TXT_ACCENT   = "#4ADE80"

LEVELS = {
    "Nguy hiểm": {"bar":"#E24B4A","badge_bg":"#4A1A1A","badge_txt":"#FF8080","min":50},
    "Cần chú ý": {"bar":"#EF9F27","badge_bg":"#3A2800","badge_txt":"#FFC060","min":30},
    "Chú ý nhẹ": {"bar":"#97C459","badge_bg":"#1A3A10","badge_txt":"#A0E060","min":15},
    "An toàn":   {"bar":"#4ADE80","badge_bg":"#0A2A18","badge_txt":"#4ADE80","min":0 },
}

HISTORY_FILE = "history.txt"

def load_history():
    hist = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip("\n").split("\t")
                if len(parts) == 4:
                    hist.append({"timestamp":parts[0],"mode":parts[1],
                                 "similarity":parts[2],"detail":parts[3]})
    return hist

def save_history(record):
    hist = load_history()
    hist.insert(0, record)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for r in hist:
            detail = str(r["detail"]).replace("\t"," ").replace("\n"," ")
            f.write(f"{r['timestamp']}\t{r['mode']}\t{r['similarity']}\t{detail}\n")

STOPWORDS = {"là","của","và","các","những","một","cho","đến","trong",
             "có","được","với","tại","theo","the","is","in","of","and","to","a"}

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

def preprocess_words(text: str) -> list:
    words = re.findall(r"\b\w+\b", text.lower())
    return [w for w in words if w not in STOPWORDS]

def get_similarity(words1, words2, n=2):
    if not words1 or not words2: return 0, set()
    s1 = set([tuple(words1[i:i+n]) for i in range(len(words1)-n+1)])
    s2 = set([tuple(words2[i:i+n]) for i in range(len(words2)-n+1)])
    if not s1 or not s2: return 0, set()
    inter = s1.intersection(s2)
    return (len(inter) / len(s1.union(s2))) * 100, inter

def compute_similarity(text_a: str, text_b: str) -> float:
    a = " ".join(preprocess_words(text_a))
    b = " ".join(preprocess_words(text_b))
    if not a or not b:
        return 0.0
    jac, _ = get_similarity(preprocess_words(text_a), preprocess_words(text_b))
    jac /= 100
    seq = SequenceMatcher(None, a[:5000], b[:5000]).ratio()
    try:
        vec = TfidfVectorizer(ngram_range=(1,2))
        mat = vec.fit_transform([a, b])
        cos = sk_cosine(mat[0:1], mat[1:2])[0][0]
    except:
        cos = jac
    return round((cos*0.5 + jac*0.3 + seq*0.2) * 100, 2)

def get_level(score: float) -> dict:
    for name, info in LEVELS.items():
        if score >= info["min"]:
            return {"name": name, **info}
    return {"name": "An toàn", **LEVELS["An toàn"]}

navigate_items = [
    {"id":"checker","icon":"🔍","label":"CHECKER",      "description":"Kiểm tra 2 văn bản"},
    {"id":"compare","icon":"📂","label":"COMPARE FILES","description":"So sánh 1 file với nhiều file"},
    {"id":"history","icon":"🕐","label":"HISTORY",      "description":"Lịch sử kiểm tra"},
]

class Navigate_Buttons(ctk.CTkFrame):
    def __init__(self, master, item, command, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=10, **kwargs)
        self.item = item; self.command = command; self.active = False
        self.build(); self.bind_all_children(self)

    def build(self):
        self.grid_columnconfigure(2, weight=1)
        self.bar = ctk.CTkLabel(self, text="", width=4, height=44,
                                fg_color="transparent", corner_radius=2)
        self.bar.grid(row=0, column=0, padx=(6,0), pady=6)
        self.icon_label = ctk.CTkLabel(self, text=self.item["icon"],
                                       font=("Arial",24), width=36, height=44,
                                       text_color=TXT_MUTED)
        self.icon_label.grid(row=0, column=1, padx=(8,4), pady=6)
        tf = ctk.CTkFrame(self, fg_color="transparent")
        tf.grid(row=0, column=2, sticky="w", padx=(4,12), pady=6)
        self.lbl_name = ctk.CTkLabel(tf, text=self.item["label"],
                                     font=("Arial",14,"bold"),
                                     text_color=TXT_MUTED, anchor="w")
        self.lbl_name.pack(fill="x")
        self.lbl_desc = ctk.CTkLabel(tf, text=self.item["description"],
                                     font=("Arial",11), text_color=TXT_MUTED, anchor="w")
        self.lbl_desc.pack(fill="x")

    def set_active(self, active):
        self.active = active
        if active:
            self.configure(fg_color=SB_BTN_ACTIVE)
            self.bar.configure(fg_color=SB_ACCENT)
            self.lbl_name.configure(text_color=TXT_WHITE, font=("Arial",13,"bold"))
            self.icon_label.configure(text_color=SB_ACCENT2)
        else:
            self.configure(fg_color="transparent")
            self.bar.configure(fg_color="transparent")
            self.lbl_name.configure(text_color=TXT_MUTED, font=("Arial",13))
            self.icon_label.configure(text_color=TXT_MUTED)

    def bind_all_children(self, w):
        w.bind("<Button-1>", self.on_click)
        w.bind("<Enter>", self.on_enter)
        w.bind("<Leave>", self.on_leave)
        for c in w.winfo_children(): self.bind_all_children(c)

    def on_click(self, event=None):  self.command(self.item["id"])
    def on_enter(self, event=None):
        if not self.active: self.configure(fg_color=SB_BTN_HOVER)
    def on_leave(self, event=None):
        if not self.active: self.configure(fg_color="transparent")

class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_navigate, **kwargs):
        super().__init__(master, width=230, corner_radius=0, fg_color=SB_BG, **kwargs)
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self.buttons = {}
        self.build()

    def build(self):
        ctk.CTkLabel(self, text="MENU", font=("Arial Black",24,"bold"),
                     text_color="#FFFFFF", anchor="w").pack(fill="x", padx=40, pady=(20,15))
        nf = ctk.CTkFrame(self, fg_color="transparent")
        nf.pack(fill="x", padx=8)
        for item in navigate_items:
            btn = Navigate_Buttons(nf, item=item, command=self.on_navigate)
            btn.pack(fill="x", pady=2)
            self.buttons[item["id"]] = btn
        ctk.CTkFrame(self, fg_color="transparent").pack(fill="both", expand=True)

    def set_active(self, page_id):
        for pid, btn in self.buttons.items():
            btn.set_active(pid == page_id)

class Base_Page(ctk.CTkFrame):
    def __init__(self, master, title, subtitle, icon, app_ref, **kwargs):
        super().__init__(master, corner_radius=0, fg_color=PAGE_BG, **kwargs)
        self.app_ref = app_ref
        hdr = ctk.CTkFrame(self, corner_radius=0, fg_color=CARD_BG)
        hdr.pack(fill="x")
        hi = ctk.CTkFrame(hdr, fg_color="transparent")
        hi.pack(fill="x", padx=32, pady=18)
        ctk.CTkLabel(hi, text=icon, width=48, height=48,
                     font=("Arial",30), fg_color="transparent",
                     corner_radius=12).pack(side="left", padx=(0,16))
        tc = ctk.CTkFrame(hi, fg_color="transparent")
        tc.pack(side="left", fill="y")
        ctk.CTkLabel(tc, text=title, font=("Arial",20,"bold"),
                     text_color=TXT_WHITE, anchor="w").pack(fill="x")
        ctk.CTkLabel(tc, text=subtitle, font=("Arial",14,"bold"),
                     text_color=TXT_MUTED, anchor="w").pack(fill="x")
        self.body = ctk.CTkFrame(self, fg_color=PAGE_BG)
        self.body.pack(fill="both", expand=True, padx=20, pady=20)
        self.build_body()

    def build_body(self): pass

class Checker_Page(Base_Page):
    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, icon="🔍",
                         title="Kiểm tra 2 Văn Bản",
                         subtitle="So sánh chi tiết mức độ trùng lặp giữa 2 văn bản",
                         app_ref=app_ref, **kwargs)

    def build_body(self):
        tc = ctk.CTkFrame(self.body, fg_color="transparent")
        tc.pack(fill="both", expand=True, pady=(0,10))
        self.txt_1 = self.create_text_column(tc, "VĂN BẢN GỐC / ĐỐI CHIẾU", side="left")
        self.txt_2 = self.create_text_column(tc, "VĂN BẢN CẦN KIỂM TRA", side="right")
        self.txt_1.tag_config("match", background="#b8860b", foreground="white")
        self.txt_2.tag_config("match", background="#b8860b", foreground="white")

        af = ctk.CTkFrame(self.body, fg_color="transparent")
        af.pack(fill="x", pady=10)
        self.lbl_result = ctk.CTkLabel(af, text="MỨC ĐỘ TƯƠNG ĐỒNG: 0%",
                                       font=("Arial",25,"bold"), text_color="#F3AA2C")
        self.lbl_result.pack(side="left", padx=20)
        ctk.CTkButton(af, text="BẮT ĐẦU SO SÁNH", font=("Arial",14,"bold"),
                      fg_color="#16A34A", hover_color="#15803D",
                      command=self.compare_action, height=40).pack(side="right", padx=10)
        ctk.CTkButton(af, text="XÓA TRẮNG", font=("Arial",14,"bold"),
                      fg_color="transparent", border_width=1.5,
                      border_color="#EF4444", text_color="#EF4444",
                      hover_color="#451a1a", command=self.clear_all, height=40
                      ).pack(side="right", padx=10)

    def create_text_column(self, parent, title, side):
        col = ctk.CTkFrame(parent, fg_color=CARD_BG, corner_radius=10)
        col.pack(side=side, fill="both", expand=True, padx=10)
        
        header = ctk.CTkFrame(col, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header, text=title, font=("Arial", 16, "bold"), text_color=TXT_WHITE).pack(side="left")
        
        ctk.CTkButton(header, text="🖼️Ảnh (OCR)",font=("Arial", 13,"bold"), width=90, fg_color="#9C7606",text_color="white", hover_color="#CA8A04", command=lambda: self.load_image(txt_area)).pack(side="right", padx=5)
        ctk.CTkButton(header, text="📄Chọn File",font=("Arial", 13,"bold"), width=90, fg_color="#013A96",text_color="white", hover_color="#2563EB", command=lambda: self.load_file(txt_area)).pack(side="right", padx=5)
        
        txt_area = ctk.CTkTextbox(col, font=("Arial", 15), wrap="word", fg_color="#000000", border_width=0)
        txt_area.pack(fill="both", expand=True, padx=10, pady=(0,10))
        return txt_area

    def load_file(self, widget):
        path = filedialog.askopenfilename(
            filetypes=[("Tài liệu","*.txt *.docx *.pdf")])
        if path:
            content = extract_text(path)
            if content:
                widget.delete("1.0", tk.END)
                widget.insert(tk.END, content)

    def load_image(self, widget):
            path = filedialog.askopenfilename(
                filetypes=[("Ảnh","*.jpg *.png *.jpeg")])
            if path:
                try:
                    text = pytesseract.image_to_string(
                        Image.open(path), lang="vie", config="--psm 6")
                    
                    widget.delete("1.0", tk.END)
                    widget.insert(tk.END, text.strip())
                except Exception as e:
                    messagebox.showerror("Lỗi OCR", f"Không thể đọc ảnh: {e}")

    def highlight(self, r1, r2):
        self.txt_1.tag_remove("match","1.0",tk.END)
        self.txt_2.tag_remove("match","1.0",tk.END)
        score, common = get_similarity(preprocess_words(r1), preprocess_words(r2))
        for ngram in common:
            phrase = " ".join(ngram)
            for w in [self.txt_1, self.txt_2]:
                idx = "1.0"
                while True:
                    idx = w._textbox.search(phrase, idx, stopindex=tk.END, nocase=True)
                    if not idx: break
                    end = f"{idx}+{len(phrase)}c"
                    w.tag_add("match", idx, end)
                    idx = end

    def compare_action(self):
        r1 = self.txt_1.get("1.0", tk.END).strip()
        r2 = self.txt_2.get("1.0", tk.END).strip()
        if not r1 or not r2:
            messagebox.showwarning("Thiếu văn bản",
                                   "Vui lòng nhập cả hai văn bản.")
            return
        sim = compute_similarity(r1, r2)
        self.lbl_result.configure(text=f"Mức độ tương đồng: {sim:.2f}%")
        self.highlight(r1, r2)
        save_history({"timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                      "mode": "Kiểm tra 2 File",
                      "similarity": f"{sim:.2f}%",
                      "detail": "So sánh 2 văn bản trực tiếp."})
        if "history" in self.app_ref.pages:
            self.app_ref.pages["history"].refresh()

    def clear_all(self):
        self.txt_1.delete("1.0", tk.END)
        self.txt_2.delete("1.0", tk.END)
        self.lbl_result.configure(text="MỨC ĐỘ TƯƠNG ĐỒNG: 0%")

class ResultRow(ctk.CTkFrame):
    BAR_W = 180
    BAR_H = 8

    def __init__(self, master, index, filename, score, **kwargs):
        super().__init__(master, fg_color="transparent",
                         corner_radius=0, **kwargs)
        self.score = score
        self.level = get_level(score)
        self.cur  = 0.0
        self.build(index, filename)

    def build(self, index, filename):
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text=f"{index}.", font=("Arial",11), text_color=TXT_MUTED, width=32, anchor="e").grid(row=0, column=0, padx=(8,4), pady=8)
        
        short = (filename[:30]+"…") if len(filename) > 30 else filename
        ctk.CTkLabel(self, text=f"📄 {short}", font=("Arial",12), text_color=TXT_WHITE, anchor="w").grid(row=0, column=1, sticky="ew", padx=(4,12), pady=8)
        
        bar_frame = ctk.CTkFrame(self, fg_color="transparent")
        bar_frame.grid(row=0, column=2, padx=(0,12), pady=8)
        bar_frame.grid_columnconfigure(0, weight=1)
        
        self.progressbar = ctk.CTkProgressBar(
            bar_frame, 
            width=self.BAR_W, 
            height=self.BAR_H,
            fg_color="#224A32",             
            progress_color=self.level["bar"], 
            corner_radius=0                 
        )
        self.progressbar.grid(row=0, column=0, padx=(0,8))
        self.progressbar.set(0)             
        
        self.pct = ctk.CTkLabel(bar_frame, text="0%", font=("Arial",12,"bold"), text_color=self.level["bar"], width=46, anchor="w")
        self.pct.grid(row=0, column=1)
        
        tk.Label(self, text=self.level["name"], font=("Arial",10), fg=self.level["badge_txt"], bg=self.level["badge_bg"], padx=8, pady=3, relief="flat").grid(row=0, column=3, padx=(0,12), pady=8)
        
        ctk.CTkFrame(self, height=1, fg_color=CARD_BORDER).grid(row=1, column=0, columnspan=4, sticky="ew")

    def animate(self, step=2.5):
        if self.cur < self.score:
            self.cur = min(self.cur + step, self.score)
            self.progressbar.set(self.cur / 100.0)
            self.pct.configure(text=f"{self.cur:.0f}%")
            self.after(16, self.animate)
        else:
            self.progressbar.set(self.score / 100.0)
            self.pct.configure(text=f"{self.score}%")

class Compare_Page(Base_Page):
    MAX_FILES = 30
    def __init__(self, master, app_ref, **kwargs):
        self.origin_path    = ""
        self.compare_paths  = []
        self.results        = []   
        self.row_widgets    = []  
        super().__init__(master, icon="📂", title="Compare Files", subtitle="So sánh 1 file gốc với tối đa 30 file khác", app_ref=app_ref, **kwargs)

    def build_body(self):
        self.build_upload_zone()
        self.build_result_table()

    def build_upload_zone(self):
        zone = ctk.CTkFrame(self.body, fg_color="transparent")
        zone.pack(fill="x", pady=(0, 10))
        zone.grid_columnconfigure(0, weight=1)
        zone.grid_columnconfigure(1, weight=1)
 
        left = ctk.CTkFrame(zone, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color=CARD_BORDER)
        left.grid(row=0, column=0, sticky="ew", padx=(0,8), ipady=6)

        ctk.CTkLabel(left, text="File gốc cần so sánh", font=("Arial",11), text_color=TXT_MUTED).pack(pady=(12,4))
        ctk.CTkLabel(left, text="📄", font=("Arial",32)).pack()

        self.origin_lbl = ctk.CTkLabel(left, text="Chưa chọn file", font=("Arial",12,"bold"), text_color=TXT_MUTED)
        self.origin_lbl.pack(pady=(4,4))

        ctk.CTkLabel(left, text=".txt / .docx / .pdf", font=("Arial",10), text_color=TXT_MUTED).pack()
        ctk.CTkButton(left, text="Chọn file gốc", font=("Arial",12,"bold"), fg_color=SB_ACCENT, hover_color="#15803D", corner_radius=8, height=34, command=self.pick_origin).pack(pady=(10,14), padx=20, fill="x")

        right = ctk.CTkFrame(zone, fg_color=CARD_BG, corner_radius=12,
                              border_width=1, border_color=CARD_BORDER)
        right.grid(row=0, column=1, sticky="ew", padx=(8,0), ipady=6)

        ctk.CTkLabel(right, text=f"Các file cần kiểm tra (tối đa {self.MAX_FILES})", font=("Arial",11), text_color=TXT_MUTED).pack(pady=(12,4))
        ctk.CTkLabel(right, text="📂", font=("Arial",32)).pack()

        self.files_lbl = ctk.CTkLabel(right, text="Chưa chọn file nào", font=("Arial",12,"bold"), text_color=TXT_MUTED)
        self.files_lbl.pack(pady=(4,4))

        ctk.CTkLabel(right, text="Ctrl+A để chọn tất cả", font=("Arial",10), text_color=TXT_MUTED).pack()
        ctk.CTkButton(right, text=f"Chọn tối đa {self.MAX_FILES} file", font=("Arial",12,"bold"), fg_color=SB_ACCENT, hover_color="#15803D", corner_radius=8, height=34, command=self.pick_compare).pack(pady=(10,14), padx=20, fill="x")

        self.compare_btn = ctk.CTkButton(self.body, text="▶  So sánh ngay", font=("Arial",14,"bold"), fg_color=SB_ACCENT, hover_color="#15803D", corner_radius=10, height=44, command=self.start_compare)
        self.compare_btn.pack(fill="x", pady=(0,10))
        
    def build_result_table(self):
        outer = ctk.CTkFrame(self.body, fg_color=CARD_BG, corner_radius=12, border_width=1, border_color=CARD_BORDER)
        outer.pack(fill="both", expand=True)

        top = ctk.CTkFrame(outer, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(10,0))
        ctk.CTkLabel(top, text="Kết quả so sánh",
                     font=("Arial",13,"bold"),
                     text_color=TXT_WHITE).pack(side="left")

        self.scroll = ctk.CTkScrollableFrame(outer, fg_color=CARD_BG, scrollbar_button_color=SB_ACCENT)
        self.scroll.pack(fill="both", expand=True)
        self.scroll.grid_columnconfigure(0, weight=1)

    def pick_origin(self):
        path = filedialog.askopenfilename(
            title="Chọn file gốc",
            filetypes=[("Văn bản","*.txt *.docx *.pdf"),("Tất cả","*.*")])
        if path:
            self.origin_path = path
            name = os.path.basename(path)
            short = (name[:26]+"…") if len(name)>26 else name
            self.origin_lbl.configure(text=short, text_color=TXT_ACCENT)

    def pick_compare(self):
        paths = filedialog.askopenfilenames(
            title=f"Chọn tối đa {self.MAX_FILES} file",
            filetypes=[("Văn bản","*.txt *.docx *.pdf"),("Tất cả","*.*")])
        if paths:
            self.compare_paths = list(paths[:self.MAX_FILES])
            self.files_lbl.configure(
                text=f"Đã chọn {len(self.compare_paths)} file",
                text_color=TXT_ACCENT)

    def start_compare(self):
        if not self.origin_path:
            messagebox.showwarning("Thiếu file","Vui lòng chọn file gốc.")
            return
        if not self.compare_paths:
            messagebox.showwarning("Thiếu file","Vui lòng chọn file để so sánh.")
            return
        self.compare_btn.configure(text="⏳ Đang so sánh...", state="disabled", fg_color="#4D7A5A")
        threading.Thread(target=self.run_compare, daemon=True).start()

    def run_compare(self):
        try:
            origin_text = extract_text(self.origin_path)
            if not origin_text:
                self.after(0, self.reset_btn)
                return
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Lỗi file gốc", str(e)))
            self.after(0, self.reset_btn)
            return

        results = []
        for path in self.compare_paths:
            try:
                text  = extract_text(path)
                score = compute_similarity(origin_text, text) if text else 0.0
                results.append((os.path.basename(path), score))
            except Exception:
                results.append((os.path.basename(path), 0.0))
        results.sort(key=lambda x: -x[1])
        self.results = results
        self.after(0, self.render_results)

    def render_results(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.row_widgets.clear()

        if not self.results:
            ctk.CTkLabel(self.scroll, text="Không có kết quả.",
                         text_color=TXT_MUTED).pack(pady=30)
            self.reset_btn()
            return

        for i, (name, score) in enumerate(self.results, start=1):
            row = ResultRow(self.scroll, index=i,
                            filename=name, score=score)
            row.pack(fill="x")

            row.after(i * 40, row.animate)
            self.row_widgets.append((row, get_level(score)["name"]))

        self.save_result()
        self.reset_btn()

    def save_result(self):
        if not self.results:
            return
        best_name, best_score = self.results[0]
        save_history({
            "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "mode": "Compare Files",
            "similarity": f"{best_score:.2f}%",
            "detail": f"Cao nhất: {best_name} ({best_score:.2f}%). "
                      f"Tổng {len(self.results)} file.",
        })
        if "history" in self.app_ref.pages:
            self.app_ref.pages["history"].refresh()

    def reset_btn(self):
        self.compare_btn.configure(text="▶  So sánh ngay",
                                     state="normal",
                                     fg_color=SB_ACCENT)

class History_Page(Base_Page):
    def __init__(self, master, app_ref, **kwargs):
        super().__init__(master, icon="🕐", title="History", subtitle="Lịch sử các lần kiểm tra trước đây", app_ref=app_ref, **kwargs)
        
    def build_body(self):
        self.sf = ctk.CTkScrollableFrame(self.body, fg_color="transparent")
        self.sf.pack(fill="both", expand=True)
        self.refresh()
        
    def refresh(self):
        for w in self.sf.winfo_children():
            w.destroy()
        data = load_history()
        if not data:
            ctk.CTkLabel(self.sf, text="Chưa có dữ liệu lịch sử.",
                         font=("Arial",14), text_color=TXT_MUTED).pack(pady=20)
            return
        for rec in data:
            card = ctk.CTkFrame(self.sf, fg_color=CARD_BG, corner_radius=10)
            card.pack(fill="x", pady=8, padx=10)
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=15, pady=(10,5))
            ctk.CTkLabel(top, text=rec["mode"], font=("Arial",14,"bold"),
                         text_color=TXT_WHITE).pack(side="left")
            ctk.CTkLabel(top, text=rec["timestamp"], font=("Arial",12),
                         text_color=TXT_MUTED).pack(side="right")
            bot = ctk.CTkFrame(card, fg_color="transparent")
            bot.pack(fill="x", padx=15, pady=(0,10))
            ctk.CTkLabel(bot, text=rec["detail"], font=("Arial",13),
                         text_color=TXT_MUTED).pack(side="left")
            ctk.CTkLabel(bot, text=f"Tỷ lệ: {rec['similarity']}",
                         font=("Arial",14,"bold"),
                         text_color="#F59E0B").pack(side="right")
            
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Plagiarism_Checker")
        self.geometry("1280x750")
        self.minsize(1000, 600)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.current = ""
        self.setup_layout()
        self.setup_pages()
        self.navigate("checker")

    def setup_layout(self):
        self.sidebar = Sidebar(self, on_navigate=self.navigate)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

    def setup_pages(self):
        self.pages = {
            "checker": Checker_Page(self, app_ref=self),
            "compare": Compare_Page(self, app_ref=self),
            "history": History_Page(self, app_ref=self),
        }
        for page in self.pages.values():
            page.grid(row=0, column=1, sticky="nsew")
            page.grid_remove()

    def navigate(self, page_id):
        if self.current and self.current in self.pages:
            self.pages[self.current].grid_remove()
        if page_id in self.pages:
            self.pages[page_id].grid()
            self.current = page_id
            if page_id == "history":
                self.pages["history"].refresh()
        self.sidebar.set_active(page_id)

App().mainloop()
