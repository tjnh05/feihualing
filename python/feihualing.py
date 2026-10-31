"""
诗词飞花令 · 人机对战  ——  feihualing
====================================================
项目主页：https://github.com/你的用户名/feihualing
数据来源：chinese-poetry / 《唐诗三百首》（MIT 许可），
          另含手工整理的宋词名句与部编版小学必背古诗
运行方式：python3 feihualing.py
依赖：只用 Python 自带的 tkinter 和 json，不需要安装任何东西
"""

import json
import os
import random
import tkinter as tk
from tkinter import messagebox

# ============================================================
# 第一部分：读数据
# ============================================================
# __file__ 是这个 py 文件自己的路径，用它可以找到旁边的 data 文件夹
# 这样不管在哪个目录下运行程序，都能找到数据
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "poems.json")
USER_FILE = os.path.join(BASE_DIR, "data", "user_poems.json")   # 玩家自己添加的诗句

with open(DATA_FILE, "r", encoding="utf-8") as f:
    POEMS = json.load(f)          # POEMS 是一个列表，里面每个元素是一句诗

# 常用的令字：这些字在诗库里都至少有 8 句以上，保证每局都能玩起来
COMMON_WORDS = [
    "月", "花", "春", "山", "风", "江", "水", "云", "雨", "雪",
    "秋", "天", "日", "夜", "酒", "家", "心", "树", "鸟", "柳",
    "星", "舟", "竹", "夏", "冬",
]

# 颜色（游戏界面用）
C_PAPER = "#f6efe1"     # 纸张色
C_CARD = "#fffaf0"      # 卡片色
C_INK = "#2a2118"       # 墨色
C_INK2 = "#5b4a38"      # 淡墨
C_INK3 = "#8b7355"      # 更淡
C_RED = "#b23a2e"       # 朱砂红
C_JADE = "#3d6b5c"      # 青绿
C_GOLD = "#c99a3f"      # 金色
C_LINE = "#d9c9ae"      # 线

FONT_TITLE = ("Songti SC", 22, "bold")
FONT_LING = ("Songti SC", 40, "bold")
FONT_BODY = ("PingFang SC", 15)
FONT_SMALL = ("PingFang SC", 11)
FONT_BIG = ("PingFang SC", 20, "bold")


# ============================================================
# 第二部分：游戏规则（不含界面，纯逻辑）
# ============================================================

def find_lines(word):
    """找出所有含有某个字的诗句，返回一个列表"""
    result = []
    for poem in POEMS:
        if word in poem["句"]:
            result.append(poem)
    return result


def clean_text(text):
    """去掉空格和标点，方便比较。比如 '明月 光' 和 '明月光。' 视为一样"""
    bad_chars = " \u3000，。、；：！？,.;:!?\"'“”‘’（）()《》…—-·"
    for ch in bad_chars:
        text = text.replace(ch, "")
    return text


# ---------------- 玩家自己添加的诗句 ----------------
# 存在 data/user_poems.json 里，和内置诗库分开，重跑 build_poems.py 也不会被冲掉

# 添加诗句时可以选的类别
GENRES = [
    "自编", "唐诗名篇", "宋词", "小学必背", "诗经", "汉乐府",
    "五言绝句", "五言律诗", "五言古诗",
    "七言绝句", "七言律诗", "七言古诗", "乐府", "建安", "魏晋", "宋诗",
]


def load_user_poems():
    """读玩家自建的句子。文件不存在、或者里面写坏了，都当成空的，不影响开局"""
    if not os.path.exists(USER_FILE):
        return []
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []

    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        line = str(item.get("句", "")).strip()
        if not line:
            continue
        result.append({
            "句": line,
            "作者": str(item.get("作者", "")).strip() or "佚名",
            "出处": str(item.get("出处", "")).strip() or "自编",
            "体裁": str(item.get("体裁", "")).strip() or "自编",
        })
    return result


def merge_user_poems():
    """把玩家自建的句子接进 POEMS：内置诗库优先，同一句只留一条"""
    have = set(clean_text(p["句"]) for p in POEMS)
    for poem in load_user_poems():
        key = clean_text(poem["句"])
        if key and key not in have:
            have.add(key)
            POEMS.append(poem)
    return len(POEMS)


def split_input(text):
    """把玩家输入的一段文字拆成一条一句：按 。！？； 和换行断开，标点留着"""
    text = (text or "").strip()
    if not text:
        return []

    out, cur = [], ""
    for ch in text:
        if ch in "。！？；":
            cur += ch
            out.append(cur.strip())
            cur = ""
        elif ch in "\r\n":
            if cur.strip():
                out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return [line for line in out if line]


def save_user_poems(new_poems):
    """把新句子追加写进 user_poems.json，返回是否写成功"""
    data = load_user_poems()
    data.extend(new_poems)
    try:
        os.makedirs(os.path.dirname(USER_FILE), exist_ok=True)
        with open(USER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        return True
    except OSError:
        return False


def add_poem(raw, author, title, genre):
    """添加诗句：校验 -> 写文件 -> 立刻并进内存里的 POEMS（当场就能接）

    返回 (成功加入的句子列表, 失败说明列表)"""
    lines = split_input(raw)
    if not lines:
        return [], ["先写一句诗吧"]

    author = (author or "").strip() or "佚名"
    title = (title or "").strip() or "自编"
    genre = genre or "自编"

    have = set(clean_text(p["句"]) for p in POEMS)
    added, errors = [], []
    for line in lines:
        if len(line) < 2:
            errors.append("「%s」太短了，至少 2 个字" % line)
            continue
        if len(line) > 26:
            errors.append("「%s」太长了，最多 26 字，请一句一句添加" % line)
            continue
        key = clean_text(line)
        if not key:
            errors.append("「%s」里没有能认的字" % line)
            continue
        if key in have:
            errors.append("「%s」诗库里已经有了" % line)
            continue
        have.add(key)
        poem = {"句": line, "作者": author, "出处": title, "体裁": genre}
        POEMS.append(poem)
        added.append(poem)

    if added and not save_user_poems(added):
        # 写盘失败就把内存里的也退回去，免得这次能玩、下次打开又没了
        for poem in added:
            POEMS.remove(poem)
        return [], ["写入 %s 失败，请检查文件权限" % os.path.basename(USER_FILE)]

    return added, errors


def source_text(poem):
    """拼出"作者《出处》· 类别"，让玩家知道这句来自唐诗还是宋词"""
    genre = poem.get("体裁", "")
    # 出处和类别重名时（比如自建的佚名《自编》）只写一遍，免得"自编·自编"
    if genre in ("小学必背", "宋词", "诗经", "汉乐府", "建安", "魏晋", "宋诗", "自编") \
            and genre != poem["出处"]:
        return "%s《%s》· %s" % (poem["作者"], poem["出处"], genre)
    return "%s《%s》" % (poem["作者"], poem["出处"])


merge_user_poems()


class Game:
    """一局游戏的所有状态和数据"""

    def __init__(self, word):
        self.word = word                    # 本局令字
        self.pool = find_lines(word)        # 所有可用的诗句
        self.used = []                      # 已经用过的句子
        self.score = 0                      # 我的分数
        self.streak = 0                     # 连击次数
        self.ai_count = 0                   # 电脑接了几句
        self.over = False                   # 是否结束

    def remaining(self):
        """还没被用过的诗句"""
        rest = []
        for poem in self.pool:
            if poem["句"] not in self.used:
                rest.append(poem)
        return rest

    def check(self, text):
        """判断玩家输入的诗句对不对
        返回 (是否正确, 说明文字, 找到的那句诗)"""
        if text.strip() == "":
            return False, "先写一句诗吧", None

        cleaned = clean_text(text)
        if self.word not in cleaned:
            return False, "这一句里没有「%s」字哦" % self.word, None

        # 在诗库里找这一句（玩家可能只写了半句，所以用"包含"来判断）
        found = None
        for poem in self.pool:
            if clean_text(poem["句"]) == cleaned:
                found = poem
                break
        if found is None and len(cleaned) >= 5:
            for poem in self.pool:
                if cleaned in clean_text(poem["句"]):
                    found = poem
                    break

        if found is None:
            return False, "诗库里暂时没有这一句，换一句试试", None
        if found["句"] in self.used:
            return False, "这一句已经用过了，不能重复接", None

        return True, "", found

    def player_answer(self, poem):
        """玩家答对后加分"""
        self.used.append(poem["句"])
        self.streak += 1
        gain = 10 + (self.streak - 1) * 2      # 连击越多分越高
        self.score += gain
        return gain

    def ai_answer(self):
        """电脑接一句。返回 (诗句, 是否成功)"""
        rest = self.remaining()
        if not rest:
            return None, False
        # 电脑有 12% 的概率"想不出来"，这样游戏才有输有赢
        if random.random() < 0.12 and len(rest) > 6:
            return None, False
        poem = random.choice(rest)
        self.used.append(poem["句"])
        self.ai_count += 1
        return poem, True


# ============================================================
# 第三部分：界面
# ============================================================

class App:
    def __init__(self, root):
        self.root = root
        root.title("诗词飞花令 · 人机对战")
        root.geometry("880x780")
        # 窗口不能被拖得太小，否则输入框和按钮会被挤没
        root.minsize(720, 600)
        root.configure(bg=C_PAPER)

        self.game = None

        # ---------- 顶部标题 ----------
        top = tk.Frame(root, bg=C_PAPER)
        top.pack(fill="x", padx=26, pady=(18, 8))

        seal = tk.Label(top, text="飞花\n令", bg=C_RED, fg="#fff8ec",
                        font=("Songti SC", 13, "bold"), width=4, height=2)
        seal.pack(side="left")

        titles = tk.Frame(top, bg=C_PAPER)
        titles.pack(side="left", padx=14)
        tk.Label(titles, text="诗词飞花令 · 人机对战", bg=C_PAPER, fg=C_INK,
                 font=FONT_TITLE).pack(anchor="w")
        self.count_label = tk.Label(titles, text="", bg=C_PAPER, fg=C_INK3, font=FONT_SMALL)
        self.count_label.pack(anchor="w", pady=(3, 0))
        self.refresh_count()

        # ---------- 令字区 ----------
        ling_box = tk.Frame(root, bg=C_CARD, highlightbackground=C_LINE, highlightthickness=1)
        ling_box.pack(fill="x", padx=26, pady=8)

        self.ling_char = tk.Label(ling_box, text="月", bg=C_CARD, fg=C_RED, font=FONT_LING,
                                  width=3, height=1, relief="solid", bd=2)
        self.ling_char.pack(side="left", padx=18, pady=14)

        info = tk.Frame(ling_box, bg=C_CARD)
        info.pack(side="left", fill="both", expand=True, pady=10)
        tk.Label(info, text="今日令字", bg=C_CARD, fg=C_INK, font=("PingFang SC", 13, "bold")).pack(anchor="w")
        self.ling_desc = tk.Label(info, text="", bg=C_CARD, fg=C_INK3, font=FONT_SMALL, justify="left")
        self.ling_desc.pack(anchor="w", pady=(4, 6))

        # 令字按钮：25 个字分三排显示
        btns = tk.Frame(info, bg=C_CARD)
        btns.pack(anchor="w")
        rows = []
        for r in range(3):
            f = tk.Frame(btns, bg=C_CARD)
            f.pack(anchor="w", pady=(0 if r == 0 else 3, 0))
            rows.append(f)
        for i, w in enumerate(COMMON_WORDS):
            parent = rows[0] if i < 9 else (rows[1] if i < 18 else rows[2])
            b = tk.Button(parent, text=w, font=("Songti SC", 14), width=2,
                          bg="#fffdf6", fg=C_INK2, relief="flat", cursor="hand2",
                          command=lambda w=w: self.new_game(w))
            b.pack(side="left", padx=2)

        # ---------- 计分区 ----------
        score_row = tk.Frame(root, bg=C_PAPER)
        score_row.pack(fill="x", padx=26)

        self.p_score = tk.Label(score_row, text="0 分", bg="#efe4d0", fg=C_INK, font=FONT_BIG)
        self.p_score.pack(side="left", expand=True, fill="x", padx=(0, 6), ipady=8)
        self.c_score = tk.Label(score_row, text="0 句", bg="#efe4d0", fg=C_INK, font=FONT_BIG)
        self.c_score.pack(side="left", expand=True, fill="x", padx=(6, 0), ipady=8)

        # ---------- 对话区 ----------
        # 注意：先不 pack，等下面输入区和底部按钮占好位置后再填充剩余空间，
        # 这样窗口再矮也不会把输入框挤出去
        self.dialog = tk.Text(root, height=10, bg=C_CARD, fg=C_INK, font=FONT_BODY,
                              relief="flat", highlightbackground=C_LINE, highlightthickness=1,
                              wrap="word", padx=14, pady=12, spacing1=4, spacing3=8)
        self.dialog.tag_config("me", foreground=C_JADE, font=("PingFang SC", 15, "bold"))
        self.dialog.tag_config("ai", foreground=C_INK, font=("PingFang SC", 15))
        self.dialog.tag_config("meta", foreground=C_INK3, font=("PingFang SC", 10))
        self.dialog.tag_config("sys", foreground=C_INK3, font=("PingFang SC", 11), justify="center")
        self.dialog.tag_config("err", foreground=C_RED, font=("PingFang SC", 14))
        self.dialog.config(state="disabled")

        # ---------- 输入区 ----------
        input_row = tk.Frame(root, bg=C_PAPER)

        self.entry = tk.Entry(input_row, font=FONT_BODY, bg="#fffdf7", fg=C_INK,
                              relief="flat", highlightbackground=C_LINE, highlightthickness=1)
        self.entry.pack(side="left", fill="x", expand=True, ipady=9)
        self.entry.bind("<Return>", lambda e: self.player_turn())

        self.send_btn = tk.Button(input_row, text="接 句", command=self.player_turn,
                                  bg=C_RED, fg="#fff8ec", font=("PingFang SC", 14, "bold"),
                                  relief="flat", width=8, cursor="hand2")
        self.send_btn.pack(side="left", padx=(10, 0), ipady=7)

        # ---------- 底部按钮 ----------
        bottom = tk.Frame(root, bg=C_PAPER)
        bottom.pack(side="bottom", fill="x", padx=26, pady=(8, 14))
        for text, cmd in [("给我提示", self.hint), ("换一局", lambda: self.new_game()),
                          ("添加诗句", self.add_dialog), ("退出", root.destroy)]:
            tk.Button(bottom, text=text, command=cmd, bg=C_PAPER, fg=C_INK2,
                      font=FONT_SMALL, relief="flat", cursor="hand2").pack(side="left", padx=(0, 14))

        # 底部固定件先占位（side="bottom" 从下往上叠），对话区最后吃掉剩余空间
        input_row.pack(side="bottom", fill="x", padx=26, pady=(6, 0))
        self.dialog.pack(side="top", fill="both", expand=True, padx=26, pady=10)

        self.new_game("月")

    # ---------------- 界面与小逻辑的连接 ----------------

    def write(self, text, tag="ai"):
        """往对话区写字"""
        self.dialog.config(state="normal")
        self.dialog.insert("end", text, tag)
        self.dialog.see("end")
        self.dialog.config(state="disabled")

    def new_game(self, word=None):
        """开始新的一局"""
        if word is None:
            word = random.choice(COMMON_WORDS)
        self.game = Game(word)

        self.ling_char.config(text=word)
        self.refresh_desc()
        self.entry.config(state="normal", textvariable=None)
        self.entry.delete(0, "end")
        self.send_btn.config(state="normal")

        self.dialog.config(state="normal")
        self.dialog.delete("1.0", "end")
        self.dialog.config(state="disabled")

        self.update_score()
        self.write("令字：「%s」　请先出句\n\n" % word, "sys")
        self.entry.focus_set()

    def refresh_count(self):
        """顶部副标题里的总句数（玩家添加诗句后会变）"""
        self.count_label.config(text="唐诗 + 宋词 + 小学必背 + 自建 · %d 句 · 离线运行" % len(POEMS))

    def refresh_desc(self):
        """令字下面的说明：本轮还有多少句可以接"""
        self.ling_desc.config(
            text="本轮诗句里必须含有「%s」字。诗库中有 %d 句可用，你说一句，电脑接一句。"
                 % (self.game.word, len(self.game.pool)))

    def absorb(self, poems):
        """新加的诗句马上参与当前这一局，返回其中含令字的句数"""
        if not self.game or self.game.over:
            return 0
        have = [p["句"] for p in self.game.pool]
        hit = 0
        for poem in poems:
            if self.game.word in poem["句"] and poem["句"] not in have:
                self.game.pool.append(poem)
                have.append(poem["句"])
                hit += 1
        if hit:
            self.refresh_desc()
        return hit

    def add_dialog(self):
        """「添加诗句」小窗：填好诗句后写进 data/user_poems.json，本局立刻生效"""
        win = tk.Toplevel(self.root)
        win.title("添加诗句")
        win.configure(bg=C_PAPER)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        box = tk.Frame(win, bg=C_PAPER)
        box.pack(fill="both", expand=True, padx=24, pady=20)

        tk.Label(box, text="添加诗句", bg=C_PAPER, fg=C_INK,
                 font=("Songti SC", 18, "bold")).pack(anchor="w")
        tk.Label(box, text="一句一行，也可以把整首贴进来（按 。！？； 自动拆句）。"
                           "作者、出处不填就记作「佚名《自编》」。",
                 bg=C_PAPER, fg=C_INK3, font=FONT_SMALL, justify="left",
                 wraplength=430).pack(anchor="w", pady=(5, 12))

        tk.Label(box, text="诗句", bg=C_PAPER, fg=C_INK2, font=FONT_SMALL).pack(anchor="w")
        lines = tk.Text(box, height=4, width=42, font=FONT_BODY, bg="#fffdf7", fg=C_INK,
                        relief="flat", highlightbackground=C_LINE, highlightthickness=1,
                        wrap="word", padx=8, pady=6)
        lines.pack(fill="x", pady=(4, 10))

        meta = tk.Frame(box, bg=C_PAPER)
        meta.pack(fill="x")
        entries = {}
        for col, (key, label, width) in enumerate([("作者", "作者", 10), ("出处", "出处", 16)]):
            cell = tk.Frame(meta, bg=C_PAPER)
            cell.grid(row=0, column=col, sticky="w", padx=(0, 12))
            tk.Label(cell, text=label, bg=C_PAPER, fg=C_INK2, font=FONT_SMALL).pack(anchor="w")
            ent = tk.Entry(cell, width=width, font=FONT_SMALL, bg="#fffdf7", fg=C_INK,
                           relief="flat", highlightbackground=C_LINE, highlightthickness=1)
            ent.pack(anchor="w", pady=(4, 0), ipady=5)
            entries[key] = ent

        genre_var = tk.StringVar(value=GENRES[0])
        cell = tk.Frame(meta, bg=C_PAPER)
        cell.grid(row=0, column=2, sticky="w")
        tk.Label(cell, text="类别", bg=C_PAPER, fg=C_INK2, font=FONT_SMALL).pack(anchor="w")
        picker = tk.OptionMenu(cell, genre_var, *GENRES)
        picker.config(font=FONT_SMALL, bg="#fffdf7", fg=C_INK, relief="flat",
                      highlightthickness=0, anchor="w", width=9)
        picker["menu"].config(font=FONT_SMALL)
        picker.pack(anchor="w", pady=(4, 0))

        tip = tk.Label(box, text="", bg=C_PAPER, fg=C_RED, font=FONT_SMALL,
                       justify="left", wraplength=430)
        tip.pack(anchor="w", pady=(10, 0))

        def submit(event=None):
            added, errors = add_poem(lines.get("1.0", "end"), entries["作者"].get(),
                                     entries["出处"].get(), genre_var.get())
            if added:
                self.refresh_count()
                hit = self.absorb(added)
                self.write("已收入诗库：%s\n" % "、".join(p["句"] for p in added), "sys")
                if hit:
                    self.write("　　其中 %d 句含「%s」，这一局就能接\n" % (hit, self.game.word), "meta")
                self.write("\n")
                lines.delete("1.0", "end")
            tip.config(text="\n".join(errors))
            if errors:
                lines.focus_set()
            else:
                win.destroy()

        btns = tk.Frame(box, bg=C_PAPER)
        btns.pack(fill="x", pady=(14, 0))
        tk.Button(btns, text="确认添加", command=submit, bg=C_RED, fg="#fff8ec",
                  font=("PingFang SC", 13, "bold"), relief="flat", cursor="hand2",
                  padx=14, pady=5).pack(side="right")
        tk.Button(btns, text="取消", command=win.destroy, bg="#efe4d0", fg=C_INK2,
                  font=FONT_SMALL, relief="flat", cursor="hand2",
                  padx=12, pady=6).pack(side="right", padx=(0, 8))

        win.bind("<Escape>", lambda e: win.destroy())
        win.bind("<Control-Return>", submit)
        lines.focus_set()

        # 小窗居中到主窗口
        win.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - win.winfo_width()) // 2
        y = self.root.winfo_rooty() + 90
        win.geometry("+%d+%d" % (max(x, 0), max(y, 0)))

    def update_score(self):
        s = self.game.score
        streak = "  连击 ×%d" % self.game.streak if self.game.streak > 1 else ""
        self.p_score.config(text="%d 分%s" % (s, streak))
        self.c_score.config(text="电脑 %d 句" % self.game.ai_count)

    def player_turn(self):
        if self.game.over:
            return
        text = self.entry.get()
        ok, msg, poem = self.game.check(text)

        if not ok:
            self.write("你：%s\n" % (text if text.strip() else "（空）"), "err")
            self.write("　　%s\n\n" % msg, "meta")
            return

        gain = self.game.player_answer(poem)
        self.write("你：" + poem["句"] + "\n", "me")
        self.write("　　%s　+%d 分\n\n" % (source_text(poem), gain), "meta")
        self.entry.delete(0, "end")
        self.update_score()

        # 用 after 延迟 0.7 秒再让电脑接，节奏更自然
        self.entry.config(state="disabled")
        self.send_btn.config(state="disabled")
        self.root.after(700, self.ai_turn)

    def ai_turn(self):
        if self.game.over:
            return
        poem, success = self.game.ai_answer()

        if not success:
            self.write("电脑一时想不出来……轮到你了\n\n", "sys")
            self.unlock()
            return

        self.write("电脑：" + poem["句"] + "\n", "ai")
        self.write("　　%s\n\n" % source_text(poem), "meta")
        self.update_score()
        self.unlock()

        if not self.game.remaining():
            self.finish("诗库见底了")

    def unlock(self):
        self.entry.config(state="normal")
        self.send_btn.config(state="normal")
        self.entry.focus_set()

    def hint(self):
        if self.game.over:
            return
        rest = self.game.remaining()
        if not rest:
            return
        p = random.choice(rest)
        head = p["句"][:3]
        self.write("提示：有一句是「%s……」（%s）\n\n" % (head, source_text(p)), "sys")

    def finish(self, why):
        self.game.over = True
        self.entry.config(state="disabled")
        self.send_btn.config(state="disabled")
        messagebox.showinfo(
            "本局结束",
            "令字「%s」\n\n你得了 %d 分，电脑接了 %d 句。\n%s"
            % (self.game.word, self.game.score, self.game.ai_count, why))


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
