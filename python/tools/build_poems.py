"""
build_poems.py —— 构建诗句数据文件（可以反复运行，结果稳定）
==============================================================
做的事情：
  1. 读取 data/poems_tang_original.json 里的唐诗底本（唐诗三百首）
  2. 清洗：去掉 "(明年一作：年年)" 这类校勘注；把塞了整段的长句拆成短句；过滤超长句
  3. 合并 extra_poems.py 里手工整理的补充数据
     （小学必背 / 宋词 / 五代词 / 诗经乐府 / 四季名篇 / 唐诗名篇 / 宋诗 / 补遗）
  4. 去重、排序、写出 data/poems.json
  5. 打印质量报告（总数、各类别句数、常用令字覆盖）

运行：python3 build_poems.py
"""
import json
import os
import re
from collections import Counter

from extra_poems import (PRIMARY_SCHOOL, SONG_CI, SONG_CI_EXTRA, CLASSICS, SEASONS,
                         TANG_CLASSICS, SONG_SHI, MORE_POEMS)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
DATA_FILE = os.path.join(BASE, "data", "poems.json")
BACKUP_FILE = os.path.join(BASE, "data", "poems_tang_original.json")
USER_FILE = os.path.join(BASE, "data", "user_poems.json")   # 玩家在界面里自己加的诗句


def load_user_poems():
    """读玩家自建的诗句。这些句子也要并进来，否则重跑构建就被"弄丢"了"""
    if not os.path.exists(USER_FILE):
        return []
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        print("user_poems.json 读不了，这次跳过")
        return []
    if not isinstance(data, list):
        return []

    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        line = str(item.get("句", "")).strip()
        if not line:
            continue
        out.append({
            "句": line,
            "作者": str(item.get("作者", "")).strip() or "佚名",
            "出处": str(item.get("出处", "")).strip() or "自编",
            "体裁": str(item.get("体裁", "")).strip() or "自编",
        })
    return out


def clean_line(text):
    """去掉括号注解和多余空格"""
    if not text:
        return ""
    text = re.sub(r"[（(][^）)]*[）)]", "", text)   # 去掉 (……) 注解
    # 底本里有些注解被切断了，只剩半个括号（"(猿"、"(中宵一作：终宵"），整段丢掉
    text = re.sub(r"[（(][^）)]*$", "", text)       # 去掉没闭合的 "(……"
    text = re.sub(r"[）)]", "", text)               # 去掉落单的 ")"
    text = re.split(r"一作", text)[0]                # 去掉 "一作：xxx" 尾巴
    text = text.replace(" ", "").replace("\u3000", "")
    text = re.sub(r"[A-Za-z]+", "", text)            # 去掉夹杂的英文
    return text.strip()


def split_long(line):
    """把塞了整首诗的长句按标点拆开

    规则（按优先级）：
      1. 长度 <= 14 字的，按原样保留（可能是"七言+逗号"或"五言+逗号"的完整一句）
      2. 更长的，先按句号/问号/叹号/分号切开成"段"
      3. 每段再按逗号切成"半句"，末尾补上逗号
    """
    if len(line) <= 14:
        return [line]
    parts = []
    for chunk in re.split(r"[。！？；]", line):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "，" in chunk:
            for s in chunk.split("，"):
                s = s.strip()
                if s:
                    parts.append(s + "，")
        else:
            parts.append(chunk)
    return parts


def normalize(records, keep_short=False):
    """清洗 + 拆分 + 去重，返回标准格式列表"""
    out, seen = [], set()
    for line, author, title, genre in records:
        line = clean_line(line)
        if not line:
            continue
        for seg in split_long(line):
            seg = clean_line(seg)
            min_len = 2 if keep_short else 5
            if len(seg) < min_len or len(seg) > 26:
                continue
            if "一作" in seg or "作者" in seg:
                continue
            if seg in seen:
                continue
            seen.add(seg)
            out.append({"句": seg, "作者": author, "出处": title, "体裁": genre})
    return out


def main():
    # 1) 读唐诗底本（第一次运行后，这个文件就是"原始唐诗"备份）
    if not os.path.exists(BACKUP_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            original = json.load(f)
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(original, f, ensure_ascii=False, indent=1)
        print("已备份唐诗底本 ->", os.path.basename(BACKUP_FILE))
    else:
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            original = json.load(f)

    tang_raw = [(p["句"], p["作者"], p["出处"], p.get("体裁", "唐诗")) for p in original]
    print("唐诗原始记录：", len(tang_raw))

    tang = normalize(tang_raw)
    print("唐诗清洗后：", len(tang), "（去掉注解、拆分长句、去重）")

    # 2) 合并补充数据
    extra = normalize(PRIMARY_SCHOOL + SONG_CI + SONG_CI_EXTRA + CLASSICS + SEASONS
                      + TANG_CLASSICS + SONG_SHI + MORE_POEMS, keep_short=True)
    print("补充数据：", len(extra),
          "（小学必背 / 宋词 / 五代词 / 诗经乐府 / 四季名篇 / 唐诗名篇 / 宋诗 / 补遗）")

    # 玩家在界面里自己添的句子，放在最后，不覆盖原名句
    user = load_user_poems()
    print("玩家自建：", len(user), "（data/user_poems.json）")

    # 3) 合并去重：唐诗优先，补充数据补充唐诗没有的，自建句最后
    merged, seen = [], set()
    for rec in tang + extra + user:
        if rec["句"] in seen:
            continue
        seen.add(rec["句"])
        merged.append(rec)

    # 4) 排序：按类别归拢，读起来整齐（自建句排在最后）
    order = {"小学必背": 0, "宋词": 1, "五代词": 2, "宋诗": 3,
             "诗经": 4, "汉乐府": 5, "建安": 6, "魏晋": 7,
             "唐诗名篇": 8, "自编": 10}
    merged.sort(key=lambda r: (order.get(r["体裁"], 9), len(r["句"])))

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)

    # 5) 质量报告
    print("\n" + "=" * 46)
    print("最终句数：", len(merged))
    print("体裁分布：")
    for k, v in Counter(r["体裁"] for r in merged).most_common():
        print("   %-6s %d 句" % (k, v))
    print("作者数：", len(set(r["作者"] for r in merged)))
    print("其中自建：", sum(1 for r in merged if r["体裁"] == "自编"), "句")
    print("\n常用令字覆盖：")
    words = "春 夏 秋 冬 山 水 云 花 月 风 雨 雪 江 天 日 夜 酒 家 人 心 国 树 鸟".split()
    short = []
    for w in words:
        n = sum(1 for r in merged if w in r["句"])
        flag = "⚠ 偏少" if n < 8 else ""
        if n < 8:
            short.append(w)
        print("   %s %3d 句 %s" % (w, n, flag))
    print("\n偏少的令字：", short if short else "无")
    print("=" * 46)


if __name__ == "__main__":
    main()
