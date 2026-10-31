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
import subprocess
import tkinter as tk
from datetime import date
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

    if added:
        _YA_CACHE.clear()      # 池子变了，雅令的可行性要重新算

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

# ---------------- 主题限令 / 电脑人设 / 每日挑战 ----------------
THEME_ALL = "全部"
# 体裁字段是现成的，按主题归并即可。唐诗被拆成了好几种体裁，这里合起来算
THEMES = {
    THEME_ALL: None,
    "唐诗": {"五言绝句", "五言律诗", "五言古诗",
             "七言绝句", "七言律诗", "七言古诗", "乐府", "唐诗名篇"},
    "宋词": {"宋词", "宋诗"},
    "小学必背": {"小学必背"},
}
THEME_MIN = 4          # 某令字在主题下少于这么多句，就别硬开这一局

# 人设只约束电脑的选句范围，不影响玩家；顺便换个开场白
PERSONAS = {
    "默认": {},
    "李白": {"genres": THEMES["唐诗"], "greet": "酒来！且听某家吟一句。"},
    "易安": {"genres": {"宋词"}, "greet": "且听奴家慢慢道来。"},
    "蒙童": {"genres": {"小学必背"}, "greet": "先生，这首诗我也会背！"},
}
DEFAULT_PERSONA = "默认"

DAILY_FILE = os.path.join(BASE_DIR, "data", "daily.json")

# 桌面版音效直接放 macOS 自带的系统音，不额外下载文件
SOUND_FILES = {
    "ok": "/System/Library/Sounds/Tink.aiff",
    "miss": "/System/Library/Sounds/Basso.aiff",
    "challenge": "/System/Library/Sounds/Pop.aiff",
    "end": "/System/Library/Sounds/Glass.aiff",
}

_YA_CACHE = {}      # 雅令可行性缓存；玩家加了新诗就清掉重算


def theme_pool(word, theme=THEME_ALL):
    """某个令字的诗句池，按主题限令筛一遍"""
    pool = find_lines(word)
    kinds = THEMES.get(theme)
    if not kinds:
        return pool
    return [p for p in pool if p["体裁"] in kinds]


def _fnv1a(text):
    """把字符串碾成 32 位整数，两端算出来的值一样"""
    h = 2166136261
    for ch in text:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


class LcgRandom:
    """和网页版一字不差的伪随机数：每日挑战靠它复现同一局电脑行为"""

    def __init__(self, seed):
        self.state = (seed & 0x7FFFFFFF) or 1

    def next(self):
        self.state = (self.state * 1103515245 + 12345) & 0x7FFFFFFF
        return self.state

    def random(self):
        return self.next() / 2147483648.0

    def choice(self, seq):
        return seq[self.next() % len(seq)]

    def randint(self, a, b):
        return a + self.next() % (b - a + 1)


def persona_fits(name, theme):
    """人设得跟主题对得上：唐诗配李白、宋词配易安，配不上就等于白发一句开场白"""
    kinds = THEMES.get(theme)
    genres = PERSONAS.get(name, {}).get("genres")
    if not kinds or not genres:
        return True
    return bool(kinds & genres)


def daily_plan(key=None):
    """按日期算出一套固定的今日对局：同日同题，两端算法一致"""
    key = key or date.today().strftime("%Y-%m-%d")
    rnd = LcgRandom(_fnv1a(key))
    themes = list(THEMES.keys())
    personas = list(PERSONAS.keys())
    word, theme = COMMON_WORDS[0], THEME_ALL
    # 抽到的组合得真有句子可接，才作数；抽不中就一直重抽
    for _ in range(60):
        word = rnd.choice(COMMON_WORDS)
        theme = themes[rnd.next() % len(themes)]
        if len(theme_pool(word, theme)) >= THEME_MIN:
            break
    else:
        word, theme = rnd.choice(COMMON_WORDS), THEME_ALL
    # 抽到的人设跟主题不搭就换成搭得上的，抽的还是同一个随机数，种子不受影响
    fits = [n for n in personas if persona_fits(n, theme)]
    return {
        "key": key,
        "word": word,
        "theme": theme,
        "persona": rnd.choice(fits or personas),
        "seed": rnd.next(),
    }


def load_daily_records():
    """读本地存的每日战绩"""
    if not os.path.exists(DAILY_FILE):
        return {}
    try:
        with open(DAILY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_daily_record(key, record):
    """记下今日战绩，只留更好的那一次"""
    data = load_daily_records()
    old = data.get(key)
    if isinstance(old, dict) and old.get("lines", 0) >= record.get("lines", 0):
        return old
    data[key] = record
    try:
        os.makedirs(os.path.dirname(DAILY_FILE), exist_ok=True)
        with open(DAILY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
    return record


def play_sound(kind):
    """放一声系统音效。播不出来就算了，不能影响游戏"""
    path = SOUND_FILES.get(kind)
    if not path or not os.path.exists(path):
        return
    try:
        subprocess.Popen(["afplay", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


# 电脑难度：slip = 想不出来的概率，bad = 故意说错的概率，delay = 思考多久（毫秒）
LEVELS = {
    "初出茅庐": {"slip": 0.26, "bad": 0.20, "delay": 900},
    "旗鼓相当": {"slip": 0.12, "bad": 0.12, "delay": 700},
    "出口成章": {"slip": 0.04, "bad": 0.05, "delay": 450},
}
DEFAULT_LEVEL = "旗鼓相当"

LIVES = 3          # 一局可以漏接几次
HINTS = 3          # 一局可以要几次提示
HINT_COST = 5      # 每次提示扣几分
CHALLENGE_BONUS = 15   # 抓到电脑出错加几分
CHALLENGE_COST = 10    # 冤枉电脑扣几分
ROUNDS_TO_WIN = 2      # 三局两胜

# ---------------- 雅令（正宗玩法，可选）----------------
YA_MAX_POS = 3         # 令字位置最多递进到第 3 字
YA_MIN_POOL = 8        # 某个字位至少要有这么多句，才敢要求它
AUTHOR_MIN = 12        # 作者少于这么多位的令字，不启用"同一诗人不重复"
TIME_LIMIT = 20        # 限时模式每回合几秒


def ya_info(word, theme=THEME_ALL):
    """算出某个令字在雅令下能递进到第几字、作者够不够多

    第 n 轮要求"令字排在第 n 字或更后"，某个字位的句子不够多就降级，
    最少降到 1（等于不递进）。冷门的「夏」全库只有 10 句，第 2 字往后
    只剩 6 句，只能留在第 1 轮。主题限令会缩池子，所以按主题分开算。
    """
    key = (word, theme)
    if key in _YA_CACHE:
        return _YA_CACHE[key]

    pool = theme_pool(word, theme)
    counts = {}
    for n in (1, 2, 3):
        counts[n] = sum(1 for p in pool if clean_text(p["句"]).find(word) + 1 >= n)

    max_pos = 1
    for n in (2, 3):
        if counts[n] >= YA_MIN_POOL:
            max_pos = n

    authors = len({p["作者"] for p in pool})
    info = {
        "max_pos": max_pos,
        "counts": counts,
        "authors": authors,
        "author_ok": authors >= AUTHOR_MIN,
    }
    _YA_CACHE[key] = info
    return info


class Game:
    """一局游戏的所有状态和数据"""

    def __init__(self, word, level=DEFAULT_LEVEL, ya_ling=False, timed=False,
                 theme=THEME_ALL, persona=DEFAULT_PERSONA, two_player=False, seed=None):
        self.word = word                    # 本局令字
        self.theme = theme                  # 主题限令：只在这个体裁里接
        self.persona = persona              # 电脑人设：只影响它自己的选句
        self.two_player = two_player        # 双人同机：甲乙轮流，不跟电脑打
        # 每日挑战传 seed 进来，电脑的卡壳/说错就变成可复现的固定序列
        self.rnd = LcgRandom(seed) if seed is not None else random
        self.pool = theme_pool(word, theme)  # 所有可用的诗句
        self.used = []                      # 已经用过的句子（存去标点的写法，同句不同标点算一句）
        self.used_poems = []                # 用过的句子（完整记录，电脑"重复"失误要用）
        self.score = 0                      # 我的分数（双人模式不看这个）
        self.streak = 0                     # 连击次数
        self.ai_count = 0                   # 电脑接了几句
        self.ai_score = 0                   # 电脑的分数
        self.lives = LIVES                  # 还能漏接几次
        self.hints = HINTS                  # 还能要几次提示
        self.slips = 0                      # 电脑被抓到几次错
        self.level = level                  # 本局电脑难度
        self.ya_ling = ya_ling              # 是否启用雅令（字位递进 + 同一诗人不重复）
        self.timed = timed                  # 是否限时
        info = ya_info(word, theme)
        self.max_pos = info["max_pos"] if ya_ling else 1   # 本令字最多递进到第几字
        self.author_ok = info["author_ok"] if ya_ling else False
        self.round_no = 1                   # 本局第几轮（我答对几句 + 1）
        self.used_authors = set()           # 已经接过的诗人
        self.time_left = TIME_LIMIT         # 限时模式剩余秒数
        self.ai_bad = False                 # 电脑刚说的这一句有没有问题
        self.ai_bad_reason = ""             # 问题在哪：漏字 / 重复 / 位置不对
        self.challenged = False             # 这一句是否已经质疑过
        self.over = False                   # 是否结束

        # 双人同机：甲乙各自一套分、命、提示次数
        self.turn = 0                       # 0 = 甲，1 = 乙
        self.p_scores = [0, 0]
        self.p_lives = [LIVES, LIVES]
        self.p_hints = [HINTS, HINTS]
        self.p_lines = [0, 0]               # 各自接了几句

    def need_pos(self):
        """这一轮令字至少要排在第几个字（1 = 不限）"""
        if not self.ya_ling:
            return 1
        return min(self.round_no, self.max_pos)

    def pos_of(self, text):
        """令字在这句里排第几（从 1 数），没有就返回 0"""
        return clean_text(text).find(self.word) + 1

    def playable(self, for_ai=False):
        """还没用过、并且过得了本局规则（字位 / 诗人不重复）的句子
        for_ai=True 表示这是给电脑挑的，再按人设筛一遍体裁"""
        need = self.need_pos()
        out = []
        for poem in self.pool:
            if clean_text(poem["句"]) in self.used:
                continue
            if need > 1 and self.pos_of(poem["句"]) < need:
                continue
            if self.author_ok and poem["作者"] in self.used_authors:
                continue
            out.append(poem)
        return self.persona_pool(out) if for_ai else out

    def persona_pool(self, rest):
        """按人设缩窄电脑的选句范围；缩完一句不剩就不限体裁，免得它哑火"""
        kinds = PERSONAS.get(self.persona, {}).get("genres")
        if not kinds:
            return rest
        picked = [p for p in rest if p["体裁"] in kinds]
        return picked or rest

    def my_score(self):
        """当前该接的这一方有多少分"""
        return self.p_scores[self.turn] if self.two_player else self.score

    def my_lives(self):
        return self.p_lives[self.turn] if self.two_player else self.lives

    def my_hints(self):
        return self.p_hints[self.turn] if self.two_player else self.hints

    def add_score(self, delta):
        """加分扣分都走这里，双人模式下落在当前这一方头上"""
        if self.two_player:
            self.p_scores[self.turn] = max(0, self.p_scores[self.turn] + delta)
        else:
            self.score = max(0, self.score + delta)

    def dual_result(self):
        """双人同机收局：命先丢光的输，命都在就比分数
        返回 0 = 甲胜，1 = 乙胜，None = 平"""
        a, b = self.p_lives
        if a <= 0 and b > 0:
            return 1
        if b <= 0 and a > 0:
            return 0
        if a <= 0 and b <= 0:
            return None
        sa, sb = self.p_scores
        if sa == sb:
            return None
        return 0 if sa > sb else 1

    def mark_used(self, poem):
        """记下这句的诗人，禁则要用"""
        self.used_authors.add(poem["作者"])

    def remaining(self):
        """还没被用过的诗句"""
        rest = []
        for poem in self.pool:
            if clean_text(poem["句"]) not in self.used:
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
        if clean_text(found["句"]) in self.used:
            return False, "这一句已经用过了，不能重复接", None

        # 雅令：字位递进 + 诗人不重复
        need = self.need_pos()
        if need > 1 and self.pos_of(found["句"]) < need:
            return False, "这一轮令字要排在第 %d 字或更后，这句排在第 %d 字" % (
                need, self.pos_of(found["句"])), None
        if self.author_ok and found["作者"] in self.used_authors:
            return False, "「%s」的诗已经接过了，换个人的" % found["作者"], None

        return True, "", found

    def player_answer(self, poem):
        """玩家答对后加分"""
        self.used.append(clean_text(poem["句"]))
        self.used_poems.append(poem)
        self.mark_used(poem)
        self.round_no += 1
        if self.two_player:
            # 两人轮流接，每人每句都是 10 分；换人之后连击从头算
            self.streak = 0
            self.p_scores[self.turn] += 10
            self.p_lines[self.turn] += 1
            self.turn = 1 - self.turn          # 换人接
            return 10
        self.streak += 1
        gain = 10 + (self.streak - 1) * 2      # 连击越多分越高
        self.score += gain
        return gain

    def wrong_answer(self, rest):
        """故意编一句错的给玩家抓：位置不对 / 重复 / 漏字"""
        need = self.need_pos()
        if need > 1:
            early = [p for p in self.pool
                     if self.pos_of(p["句"]) < need and clean_text(p["句"]) not in self.used]
            if early and self.rnd.random() < 0.4:
                return self.rnd.choice(early), "位置不对"
        if self.used_poems and self.rnd.random() < 0.5:
            return self.rnd.choice(self.used_poems), "重复"
        others = [p for p in POEMS if self.word not in p["句"]]
        return self.rnd.choice(others), "漏字"

    def ai_answer(self):
        """电脑接一句。返回 (诗句, 是否成功)
        电脑可能"想不出来"（直接放行），也可能故意说错（漏字 / 重复 / 位置不对），留给玩家抓"""
        self.ai_bad = False
        self.ai_bad_reason = ""
        self.challenged = False

        rest = self.playable(for_ai=True)
        if not rest:
            return None, False

        conf = LEVELS.get(self.level, LEVELS[DEFAULT_LEVEL])
        # 难度越低越容易卡壳。能接的句子太少时不再卡壳，免得直接死局
        if self.rnd.random() < conf["slip"] and len(rest) > 3:
            return None, False

        # 故意说错：这样玩家才有"抓错"的机会。说错的句子不进 used，也不算电脑得分
        if self.rnd.random() < conf["bad"]:
            poem, self.ai_bad_reason = self.wrong_answer(rest)
            self.ai_bad = True
            self.ai_count += 1
            return poem, True

        poem = self.rnd.choice(rest)
        self.used.append(clean_text(poem["句"]))
        self.used_poems.append(poem)
        self.mark_used(poem)
        self.ai_count += 1
        self.ai_score += 10
        return poem, True

    def use_hint(self):
        """用一次提示：扣分、连击清零。返回 (要提示的句子, 说明)"""
        if self.over:
            return None, "本局已经结束了"
        if self.my_hints() <= 0:
            return None, "本局的提示用完了"
        rest = self.playable()
        if not rest:
            return None, "没有可以提示的句子了"
        if self.two_player:
            self.p_hints[self.turn] -= 1
        else:
            self.hints -= 1
        self.add_score(-HINT_COST)
        self.streak = 0
        return self.rnd.choice(rest), ""

    def miss(self):
        """漏接一次：少一条命，返回这一方剩余命数"""
        self.streak = 0
        if self.two_player:
            who = self.turn
            self.p_lives[who] -= 1
            self.turn = 1 - who            # 换人接着接
            return self.p_lives[who]
        self.lives -= 1
        return self.lives

    def challenge(self):
        """质疑电脑刚说的一句。返回 (是否抓对, 说明, 分数变化)；已质疑过返回 (None, 说明, 0)"""
        if self.challenged:
            return None, "这一句已经质疑过了", 0
        self.challenged = True

        if not self.ai_bad:
            self.add_score(-CHALLENGE_COST)
            self.streak = 0
            return False, "这句其实没问题，冤枉电脑扣 %d 分" % CHALLENGE_COST, -CHALLENGE_COST

        self.slips += 1
        self.streak += 1
        self.add_score(CHALLENGE_BONUS)
        reason = self.ai_bad_reason or "这一句不对"
        return True, "抓到问题：%s，加 %d 分" % (reason, CHALLENGE_BONUS), CHALLENGE_BONUS


# ============================================================
# 第三部分：界面
# ============================================================

class App:
    def __init__(self, root):
        self.root = root
        root.title("诗词飞花令 · 人机对战")
        root.geometry("880x780")
        # 窗口不能被拖得太小，否则输入框和按钮会被挤没
        # 宽度下限要容得下令字按钮那一排（9 个）+ 右侧三个下拉
        root.minsize(800, 680)
        root.configure(bg=C_PAPER)

        self.game = None
        self.timer_id = None     # 限时模式的 after 句柄
        self.fx_ids = []         # 动效的 after 句柄，换局时一次性清掉
        self.daily = None        # 正在打的每日挑战，不在挑战里就是 None
        self.round_no = 1        # 这是第几局
        self.my_rounds = 0       # 我赢了几局
        self.ai_rounds = 0       # 电脑赢了几局

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

        # 右上角：三局两胜的总比分
        self.match_label = tk.Label(top, text="", bg=C_PAPER, fg=C_INK2,
                                    font=("PingFang SC", 12, "bold"))
        self.match_label.pack(side="right", anchor="n", pady=(6, 0))

        # 每日挑战入口：同一天、两台机器抽到的是同一道题
        self.daily_btn = tk.Button(top, text="每日挑战", command=self.toggle_daily,
                                   bg=C_GOLD, fg="#fff8ec", font=("PingFang SC", 12, "bold"),
                                   relief="flat", cursor="hand2", padx=12, pady=4)
        self.daily_btn.pack(side="right", anchor="n", padx=(0, 14), pady=(2, 0))

        # ---------- 令字区 ----------
        ling_box = tk.Frame(root, bg=C_CARD, highlightbackground=C_LINE, highlightthickness=1)
        ling_box.pack(fill="x", padx=26, pady=8)

        self.ling_char = tk.Label(ling_box, text="月", bg=C_CARD, fg=C_RED, font=FONT_LING,
                                  width=3, height=1, relief="solid", bd=2)
        self.ling_char.pack(side="left", padx=18, pady=14)

        info = tk.Frame(ling_box, bg=C_CARD)
        info.pack(side="left", fill="both", expand=True, pady=10)
        self.ling_title = tk.Label(info, text="今日令字", bg=C_CARD, fg=C_INK,
                                   font=("PingFang SC", 13, "bold"))
        self.ling_title.pack(anchor="w")
        self.ling_desc = tk.Label(info, text="", bg=C_CARD, fg=C_INK3, font=FONT_SMALL,
                                  justify="left", wraplength=350)
        self.ling_desc.pack(anchor="w", pady=(4, 6))

        # 令字按钮：25 个字分三排显示
        btns = tk.Frame(info, bg=C_CARD)
        btns.pack(anchor="w")
        rows = []
        for r in range(3):
            f = tk.Frame(btns, bg=C_CARD)
            f.pack(anchor="w", pady=(0 if r == 0 else 3, 0))
            rows.append(f)
        word_btns = []             # 每日挑战里题面固定，这些按钮要锁上
        for i, w in enumerate(COMMON_WORDS):
            parent = rows[0] if i < 9 else (rows[1] if i < 18 else rows[2])
            b = tk.Button(parent, text=w, font=("Songti SC", 14), width=2,
                          bg="#fffdf6", fg=C_INK2, relief="flat", cursor="hand2",
                          command=lambda w=w: self.new_game(w))
            b.pack(side="left", padx=2)
            word_btns.append(b)
        self.word_btns = word_btns

        # 令字区右侧：难度 / 人设 / 主题三个下拉 + 四个开关
        opt_box = tk.Frame(ling_box, bg=C_CARD)
        # 先 pack 右边定宽的部分，中间那列才能安心吃掉剩下的空间；
        # 反过来的话窗口一窄，这几个下拉会被推出窗口外
        opt_box.pack(side="right", padx=16, pady=12, before=info)

        self.level_var = tk.StringVar(value=DEFAULT_LEVEL)
        self.persona_var = tk.StringVar(value=DEFAULT_PERSONA)
        self.theme_var = tk.StringVar(value=THEME_ALL)
        self.pickers = []          # 每日挑战时要把这三个下拉锁上
        opts = (("难度", self.level_var, list(LEVELS.keys()), self.change_level),
                ("人设", self.persona_var, list(PERSONAS.keys()), self.change_persona),
                ("主题", self.theme_var, list(THEMES.keys()), self.change_rules))
        for row, (label, var, items, cmd) in enumerate(opts):
            tk.Label(opt_box, text=label, bg=C_CARD, fg=C_INK3, font=FONT_SMALL) \
                .grid(row=row, column=0, sticky="e", padx=(0, 6), pady=2)
            picker = tk.OptionMenu(opt_box, var, *items, command=cmd)
            picker.config(font=("PingFang SC", 12), bg="#fffdf6", fg=C_INK2,
                          relief="flat", highlightthickness=0, anchor="w", width=7)
            picker["menu"].config(font=FONT_SMALL)
            picker.grid(row=row, column=1, sticky="w", pady=2)
            self.pickers.append(picker)

        # 玩法开关：勾了就按雅令 / 限时的规矩打，双人同机、音效另算
        self.ya_var = tk.BooleanVar(value=False)
        self.time_var = tk.BooleanVar(value=False)
        self.two_var = tk.BooleanVar(value=False)
        self.sound_var = tk.BooleanVar(value=True)
        rules = tk.Frame(opt_box, bg=C_CARD)
        rules.grid(row=3, column=0, columnspan=2, sticky="e", pady=(4, 0))
        self.switches = []         # 前三个在每日挑战里要锁上，音效不锁
        for text, var, cmd in (("雅令", self.ya_var, self.change_rules),
                               ("限时", self.time_var, self.change_rules),
                               ("双人", self.two_var, self.change_rules),
                               ("音效", self.sound_var, self.change_sound)):
            cb = tk.Checkbutton(rules, text=text, variable=var, command=cmd,
                                bg=C_CARD, fg=C_INK2, font=FONT_SMALL, relief="flat",
                                activebackground=C_CARD, activeforeground=C_INK,
                                selectcolor="#fffdf6", highlightthickness=0,
                                cursor="hand2")
            cb.pack(side="left")
            self.switches.append(cb)

        # ---------- 计分区 ----------
        score_row = tk.Frame(root, bg=C_PAPER)
        score_row.pack(fill="x", padx=26)

        self.me_box = tk.Frame(score_row, bg="#efe4d0",
                               highlightthickness=2, highlightbackground=C_LINE)
        self.me_box.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.p_score = tk.Label(self.me_box, text="0 分", bg="#efe4d0", fg=C_INK, font=FONT_BIG)
        self.p_score.pack(pady=(4, 0))
        p_sub_row = tk.Frame(self.me_box, bg="#efe4d0")
        p_sub_row.pack(pady=(0, 4))
        self.p_sub = tk.Label(p_sub_row, text="", bg="#efe4d0", fg=C_INK3, font=FONT_SMALL)
        self.p_sub.pack(side="left")
        self.clock_label = tk.Label(p_sub_row, text="", bg="#efe4d0", fg=C_INK3, font=FONT_SMALL)
        self.clock_label.pack(side="left")

        self.ai_box = tk.Frame(score_row, bg="#efe4d0",
                               highlightthickness=2, highlightbackground=C_LINE)
        self.ai_box.pack(side="left", expand=True, fill="x", padx=(6, 0))
        self.c_score = tk.Label(self.ai_box, text="0 分", bg="#efe4d0", fg=C_INK, font=FONT_BIG)
        self.c_score.pack(pady=(4, 0))
        self.c_sub = tk.Label(self.ai_box, text="", bg="#efe4d0", fg=C_INK3, font=FONT_SMALL)
        self.c_sub.pack(pady=(0, 4))

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

        self.hint_btn = tk.Button(bottom, text="提示 3/3", command=self.hint, bg=C_PAPER,
                                  fg=C_INK2, font=FONT_SMALL, relief="flat", cursor="hand2")
        self.hint_btn.pack(side="left", padx=(0, 14))

        # 电脑说完话才能点，抓它的漏字/重复
        self.challenge_btn = tk.Button(bottom, text="它有错", command=self.challenge, bg=C_PAPER,
                                       fg=C_RED, font=FONT_SMALL, relief="flat", cursor="hand2",
                                       state="disabled")
        self.challenge_btn.pack(side="left", padx=(0, 14))

        for text, cmd in [("漏接", self.give_up), ("换令字", self.restart_round),
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

    # ---------------- 音效与动效 ----------------

    def beep(self, kind):
        """放一声系统音；音效关着就什么都不做"""
        if self.sound_var.get():
            play_sound(kind)

    def flush_fx(self):
        """换局时把没跑完的动效掐掉，免得改到下一局的界面"""
        for fid in self.fx_ids:
            try:
                self.root.after_cancel(fid)
            except tk.TclError:
                pass
        self.fx_ids = []

    def flash_ling(self):
        """令字跳两下：先涨大变成金色，再缩回朱红"""
        steps = [(54, C_GOLD), (46, C_RED), (40, C_RED)]

        def step(i=0):
            if i >= len(steps):
                return
            size, color = steps[i]
            self.ling_char.config(font=("Songti SC", size, "bold"), fg=color)
            if i + 1 < len(steps):
                self.fx_ids.append(self.root.after(120, lambda: step(i + 1)))

        step()

    def pulse_score(self, owner=0):
        """答对时把这一方的分数放大一下，给点手感"""
        label = self.c_score if owner else self.p_score
        steps = [26, 23, 20]

        def step(i=0):
            if i >= len(steps):
                return
            label.config(font=("PingFang SC", steps[i], "bold"))
            if i + 1 < len(steps):
                self.fx_ids.append(self.root.after(110, lambda: step(i + 1)))

        step()

    def new_game(self, word=None):
        """开始新的一局"""
        if word is None:
            word = random.choice(COMMON_WORDS)
        self.stop_timer()
        self.flush_fx()
        g = self.game = Game(
            word, self.level_var.get(), self.ya_var.get(), self.time_var.get(),
            theme=self.theme_var.get(), persona=self.persona_var.get(),
            two_player=self.two_var.get(),
            seed=self.daily["seed"] if self.daily else None)   # 每日挑战要复现同一套电脑行为

        self.ling_char.config(text=word, font=FONT_LING, fg=C_RED)
        self.refresh_desc()
        self.entry.config(state="normal", textvariable=None)
        self.entry.delete(0, "end")
        self.send_btn.config(state="normal")
        self.hint_btn.config(state="normal", text="提示 %d/%d" % (g.my_hints(), HINTS))
        self.challenge_btn.config(state="disabled")

        self.dialog.config(state="normal")
        self.dialog.delete("1.0", "end")
        self.dialog.config(state="disabled")

        self.update_score()
        self.refresh_match()
        if self.daily:
            self.write("今日挑战　令字「%s」\n" % word, "sys")
        elif g.two_player:
            self.write("第 %d 局　令字「%s」　甲先出句\n" % (self.round_no, word), "sys")
        else:
            self.write("第 %d 局　令字「%s」　请先出句\n" % (self.round_no, word), "sys")

        note = []
        if g.ya_ling:
            note.append("雅令")
        if g.timed:
            note.append("限时 %d 秒" % TIME_LIMIT)
        if g.theme != THEME_ALL:
            note.append("主题「%s」" % g.theme)
        if g.two_player:
            note.append("双人同机")
        elif g.persona != DEFAULT_PERSONA:
            note.append("对手「%s」" % g.persona)
        if note:
            self.write("本局启用：%s\n" % " · ".join(note), "sys")
        greet = PERSONAS.get(g.persona, {}).get("greet")
        if greet and not g.two_player:
            self.write("%s：%s\n" % ("电脑" if g.persona == DEFAULT_PERSONA else g.persona, greet), "sys")
        self.write("\n")

        self.flash_ling()
        self.entry.focus_set()
        self.start_timer()

    def change_rules(self, *args):
        """切换玩法（雅令 / 限时 / 双人 / 主题）：规则变了只能重开本局，总比分保留"""
        g = self.game
        if g is None or self.daily:
            return
        want = (self.ya_var.get(), self.time_var.get(), self.two_var.get(), self.theme_var.get())
        have = (g.ya_ling, g.timed, g.two_player, g.theme)
        if want == have:
            return
        theme = want[3]
        if theme != g.theme and len(theme_pool(g.word, theme)) < THEME_MIN:
            # 换个主题就没句子可接了，别让玩家开局就卡死
            messagebox.showinfo("主题限令", "「%s」在%s里只有 %d 句，接不下去。换个主题吧。"
                                % (g.word, theme, len(theme_pool(g.word, theme))))
            self.theme_var.set(g.theme)
            return
        if not messagebox.askyesno("切换玩法", "换规则要从头打这一局，总比分保留。确定吗？"):
            self.ya_var.set(g.ya_ling)          # 取消就把勾选退回去
            self.time_var.set(g.timed)
            self.two_var.set(g.two_player)
            self.theme_var.set(g.theme)
            return
        self.new_game(g.word)

    def change_persona(self, value):
        """换电脑人设：只影响它自己挑什么体裁，本局立刻生效，不用重开"""
        g = self.game
        if g is None:
            return
        g.persona = value
        greet = PERSONAS.get(value, {}).get("greet")
        if greet and not g.two_player and not g.over:
            self.write("%s：%s\n\n" % (value, greet), "sys")

    def change_sound(self):
        """开关音效，顺手放一声让人知道生效了"""
        if self.sound_var.get():
            play_sound("ok")

    def set_controls(self, on):
        """每日挑战期间把题面相关的控件锁上，免得题目被改掉"""
        state = "normal" if on else "disabled"
        for picker in self.pickers:
            picker.config(state=state)
        for cb in self.switches[:3]:
            cb.config(state=state)
        for b in self.word_btns:
            b.config(state=state)

    def toggle_daily(self):
        """进出每日挑战"""
        if self.daily:
            self.daily = None
            self.set_controls(True)
            self.daily_btn.config(text="每日挑战")
            self.round_no, self.my_rounds, self.ai_rounds = 1, 0, 0
            self.refresh_match()
            self.new_game()
            return

        plan = daily_plan()
        self.daily = plan
        # 控件先跟题面走，再锁上：同一天打开，题目都一样
        self.ya_var.set(False)
        self.time_var.set(False)
        self.two_var.set(False)
        self.theme_var.set(plan["theme"])
        self.persona_var.set(plan["persona"])
        self.set_controls(False)
        self.daily_btn.config(text="退出挑战")
        self.round_no, self.my_rounds, self.ai_rounds = 1, 0, 0
        self.new_game(plan["word"])

    def refresh_match(self):
        """右上角的总比分；每日挑战时改显示今日最佳"""
        if self.daily:
            best = load_daily_records().get(self.daily["key"], {}).get("lines", 0)
            self.match_label.config(text="今日挑战 %s　最佳 %d 句"
                                    % (self.daily["key"][5:], best))
            return
        self.match_label.config(text="第 %d 局　%d : %d" % (self.round_no, self.my_rounds, self.ai_rounds))

    def change_level(self, value):
        """切难度：立刻对本局生效"""
        if self.game:
            self.game.level = value
        self.write("电脑难度：「%s」\n\n" % value, "sys")

    def refresh_count(self):
        """顶部副标题里的总句数（玩家添加诗句后会变）"""
        self.count_label.config(text="唐诗 + 宋词 + 小学必背 + 自建 · %d 句 · 离线运行" % len(POEMS))

    def refresh_desc(self):
        """令字下面的说明：本轮的字位要求、还剩多少句能接"""
        g = self.game
        can = len(g.playable())
        title = "今日令字"
        if g.theme != THEME_ALL:
            title += " · %s" % g.theme
        if g.two_player:
            title += " · 轮到%s" % ("甲" if g.turn == 0 else "乙")
        elif self.daily:
            title += " · " + self.daily["key"][5:]
        self.ling_title.config(text=title)

        if not g.ya_ling:
            text = "含「%s」字即可，现在能接 %d 句。" % (g.word, can)
        else:
            parts = []
            if g.max_pos <= 1:
                parts.append("「%s」句少，字位不递进。" % g.word)
            elif g.need_pos() > 1:
                parts.append("令字要排在第 %d 字或更后。" % g.need_pos())
            else:
                parts.append("首轮不限字位，之后逐轮后挪（最多第 %d 字）。" % g.max_pos)
            if g.author_ok:
                parts.append("同一诗人只接一句。")
            parts.append("现在能接 %d 句。" % can)
            text = "雅令：" + "".join(parts)
        self.ling_desc.config(text=text)

    # ---------------- 限时模式 ----------------

    def start_timer(self):
        """玩家回合开始倒计时；没开限时就不动"""
        self.stop_timer()
        g = self.game
        if g is None or g.over or not g.timed:
            return
        self.timer_id = self.root.after(1000, self.tick)

    def stop_timer(self):
        if self.timer_id is not None:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

    def tick(self):
        """每秒掉一格，掉光算漏接"""
        self.timer_id = None
        g = self.game
        if g is None or g.over or not g.timed:
            return
        g.time_left -= 1
        if g.time_left <= 0:
            self.update_score()
            self.write("时间到！这一轮算漏接\n\n", "err")
            self.give_up()
            return
        self.update_score()
        self.timer_id = self.root.after(1000, self.tick)

    def absorb(self, poems):
        """新加的诗句马上参与当前这一局，返回其中含令字的句数"""
        if not self.game or self.game.over:
            return 0
        have = [clean_text(p["句"]) for p in self.game.pool]
        hit = 0
        for poem in poems:
            key = clean_text(poem["句"])
            if self.game.word in poem["句"] and key not in have:
                self.game.pool.append(poem)
                have.append(key)
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

    def hearts(self, lives):
        """把剩下几条命画成实心/空心桃心"""
        lives = max(lives, 0)
        return "♥" * lives + "♡" * (LIVES - lives)

    def update_score(self):
        g = self.game
        if g.two_player:
            # 甲乙各一张卡，轮到谁谁描红边
            self.p_score.config(text="%d 分" % g.p_scores[0])
            self.c_score.config(text="%d 分" % g.p_scores[1])
            self.p_sub.config(text="甲 · %s · 接 %d 句" % (self.hearts(g.p_lives[0]), g.p_lines[0]))
            self.c_sub.config(text="乙 · %s · 接 %d 句" % (self.hearts(g.p_lives[1]), g.p_lines[1]))
            self.me_box.config(highlightbackground=C_RED if g.turn == 0 else C_LINE)
            self.ai_box.config(highlightbackground=C_RED if g.turn == 1 else C_LINE)
        else:
            streak = "连击 ×%d · " % g.streak if g.streak > 1 else ""
            self.p_score.config(text="%d 分" % g.score)
            self.p_sub.config(text="%s漏接 %s" % (streak, self.hearts(g.lives)))
            self.c_score.config(text="%d 分" % g.ai_score)
            self.c_sub.config(text="电脑 · 接 %d 句 · 失误 %d 次" % (g.ai_count, g.slips))
            self.me_box.config(highlightbackground=C_LINE)
            self.ai_box.config(highlightbackground=C_LINE)
        # 倒计时只在轮到人接的时候显示，最后 5 秒变红
        running = g.timed and str(self.entry.cget("state")) == "normal"
        self.clock_label.config(
            text="　⏱ %ds" % max(g.time_left, 0) if running else "",
            fg=C_RED if running and g.time_left <= 5 else C_INK3)

    def who(self, player=None):
        """该谁接：单人模式是「你」，双人同机分甲、乙"""
        g = self.game
        idx = g.turn if player is None else player
        if not g.two_player:
            return "你"
        return "甲" if idx == 0 else "乙"

    def player_turn(self):
        g = self.game
        if g.over:
            return
        text = self.entry.get()
        ok, msg, poem = g.check(text)

        if not ok:
            g.streak = 0                      # 接错就把连击断掉
            self.update_score()
            self.write("%s：%s\n" % (self.who(), text if text.strip() else "（空）"), "err")
            self.write("　　%s\n\n" % msg, "meta")
            return

        who = g.turn
        gain = g.player_answer(poem)
        self.write(self.who(who) + "：" + poem["句"] + "\n", "me")
        self.write("　　%s　+%d 分\n\n" % (source_text(poem), gain), "meta")
        self.beep("ok")
        self.pulse_score(who)
        self.entry.delete(0, "end")
        # 先把输入锁上再刷分数，倒计时的秒数才会跟着收掉
        self.entry.config(state="disabled")
        self.send_btn.config(state="disabled")
        self.challenge_btn.config(state="disabled")
        self.stop_timer()
        self.update_score()
        self.refresh_desc()          # 轮次变了，字位要求跟着变

        if g.two_player:
            # 双人同机：稍停一下就让另一方接着接，没有电脑的事
            self.root.after(400, self.unlock)
            return
        # 用 after 延迟一下再让电脑接，节奏更自然（难度越高想得越快）
        self.root.after(LEVELS.get(g.level, LEVELS[DEFAULT_LEVEL])["delay"], self.ai_turn)

    def ai_turn(self):
        g = self.game
        self.stop_timer()
        if g.over:
            return
        # 合规的句子接光了，这局没法往下走
        if not g.playable():
            self.finish("诗库见底了")
            return
        poem, success = g.ai_answer()

        if not success:
            self.write("电脑一时想不出来……轮到你了\n\n", "sys")
            self.update_score()
            self.unlock()
            return

        self.write("电脑：" + poem["句"] + "\n", "ai")
        self.write("　　%s\n\n" % source_text(poem), "meta")
        self.update_score()
        self.unlock()
        # 给玩家一个"抓错"的机会：抓对了有奖，冤枉它要扣分
        self.challenge_btn.config(state="normal")

    def unlock(self):
        self.entry.config(state="normal")
        self.send_btn.config(state="normal")
        self.entry.focus_set()
        # 玩家回合重新开始计时
        self.game.time_left = TIME_LIMIT
        # 双人同机换人后，提示次数是各算各的，按钮得跟着换
        left = self.game.my_hints()
        self.hint_btn.config(state="normal" if left > 0 else "disabled",
                             text="提示 %d/%d" % (left, HINTS))
        self.update_score()
        self.refresh_desc()          # 双人模式下"轮到谁"写在这里
        self.start_timer()

    def hint(self):
        g = self.game
        if g.over:
            return
        p, msg = g.use_hint()
        if p is None:
            self.write("提示：%s\n\n" % msg, "sys")
            self.hint_btn.config(state="disabled")
            return
        self.write("提示：有一句是「%s……」（%s）　-%d 分\n\n"
                   % (p["句"][:3], source_text(p), HINT_COST), "sys")
        left = g.my_hints()
        self.hint_btn.config(text="提示 %d/%d" % (left, HINTS))
        if left <= 0:
            self.hint_btn.config(state="disabled")
        self.update_score()

    def challenge(self):
        """点「它有错」：抓电脑的漏字 / 重复答句"""
        g = self.game
        if g.over:
            return
        ok, msg, delta = g.challenge()
        if ok is None:
            self.write("　　%s\n\n" % msg, "meta")
            return

        if ok:
            self.write("%s：这句有问题！\n" % self.who(), "me")
            self.write("　　%s　+%d 分\n\n" % (msg, delta), "meta")
            self.beep("challenge")
        else:
            self.write("%s：这句有问题！\n" % self.who(), "err")
            self.write("　　%s\n\n" % msg, "meta")

        self.challenge_btn.config(state="disabled")
        self.update_score()
        self.entry.focus_set()

    def give_up(self):
        """漏接：少一条命，然后换人接着接"""
        g = self.game
        if g.over:
            return
        # 电脑还在想、或者换人还没交接完的时候不算漏接，免得连点几下把命扣光
        if str(self.entry.cget("state")) == "disabled":
            return
        self.stop_timer()
        who = self.who()
        left = g.miss()
        self.write("%s：接不上了……（漏接一次，还剩 %d 次）\n\n" % (who, max(left, 0)), "err")
        self.beep("miss")
        self.entry.delete(0, "end")
        self.update_score()

        if g.two_player:
            # 任一方命丢光就收局，剩下的交给 finish 判谁赢
            if min(g.p_lives) <= 0:
                self.finish("%s的命用光了" % who)
                return
            self.entry.config(state="disabled")
            self.send_btn.config(state="disabled")
            self.challenge_btn.config(state="disabled")
            self.root.after(400, self.unlock)
            return

        if left <= 0:
            self.finish("三次漏接")
            return
        self.entry.config(state="disabled")
        self.send_btn.config(state="disabled")
        self.challenge_btn.config(state="disabled")
        self.root.after(500, self.ai_turn)

    def restart_round(self):
        """中途换令字：本局算认输，进下一局"""
        g = self.game
        if not g or g.over:
            return
        lose = ("算%s输" % self.who()) if g.two_player else "算你输"
        if not messagebox.askyesno("换令字", "现在换令字，这一局%s，确定吗？" % lose):
            return
        self.finish("主动换令字", forced_lose=True)

    def finish(self, why, forced_lose=False):
        g = self.game
        g.over = True
        self.stop_timer()
        self.flush_fx()
        self.entry.config(state="disabled")
        self.send_btn.config(state="disabled")
        self.challenge_btn.config(state="disabled")
        self.hint_btn.config(state="disabled")
        self.beep("end")

        if self.daily:
            self.finish_daily(why)
            return
        if g.two_player:
            self.finish_dual(why, forced_lose)
            return

        # 命还在就比分数；漏接光了或者主动换令字，直接判负
        my_win = (not forced_lose) and g.lives > 0 and g.score >= g.ai_score
        if my_win:
            self.my_rounds += 1
        else:
            self.ai_rounds += 1
        self.refresh_match()

        detail = ("%s\n令字「%s」\n\n你 %d 分　电脑 %d 分\n%s\n\n三局两胜　你 %d : %d 电脑"
                  % ("本局你胜" if my_win else "本局电脑胜", g.word,
                     g.score, g.ai_score, why, self.my_rounds, self.ai_rounds))
        messagebox.showinfo("第 %d 局结束" % self.round_no, detail)

        if self.my_rounds >= ROUNDS_TO_WIN or self.ai_rounds >= ROUNDS_TO_WIN:
            champion = ("这场对决你赢了！" if self.my_rounds > self.ai_rounds
                        else "这场对决电脑赢了。")
            if messagebox.askyesno("比赛结束", "%s\n\n再来一场？" % champion):
                self.round_no = 1
                self.my_rounds = 0
                self.ai_rounds = 0
                self.new_game()
            else:
                self.root.destroy()
            return

        self.round_no += 1
        self.new_game()

    def finish_dual(self, why, forced_lose=False):
        """双人同机收局：先丢光命的输，命都在就比分数；主动换令字的那方算输"""
        g = self.game
        winner = g.dual_result()
        if forced_lose:
            winner = 1 - g.turn      # 主动换令字的一方认输
        if winner is None:
            head = "平局"
        else:
            head = "%s胜" % ("甲" if winner == 0 else "乙")
        detail = ("本局%s\n令字「%s」\n\n甲 %d 分（接 %d 句）\n乙 %d 分（接 %d 句）\n%s"
                  % (head, g.word, g.p_scores[0], g.p_lines[0], g.p_scores[1], g.p_lines[1], why))
        messagebox.showinfo("本局结束", detail)
        self.round_no += 1
        self.new_game()          # 换个令字接着来

    def finish_daily(self, why):
        """每日挑战收局：成绩存本地，只留今天最好的那次"""
        g = self.game
        plan = self.daily
        lines = max(g.round_no - 1, 0)      # 每答对一句 round_no 就 +1
        record = {"lines": lines, "score": g.score, "ai": g.ai_score,
                  "word": plan["word"], "theme": plan["theme"], "why": why}
        old = load_daily_records().get(plan["key"], {})
        best = save_daily_record(plan["key"], record)
        best_lines = best.get("lines", lines)

        detail = ("今日挑战结束\n令字「%s」　主题「%s」\n\n你接 %d 句　%d 分\n电脑 %d 分\n%s\n\n"
                  "今日最佳：%d 句"
                  % (plan["word"], plan["theme"], lines, g.score, g.ai_score, why, best_lines))
        if lines > old.get("lines", 0):
            detail += "　（刷新纪录）"
        self.refresh_match()
        messagebox.showinfo("今日挑战", detail)
        self.new_game(plan["word"])          # 同一道题还能再打，只记最好的那次


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
