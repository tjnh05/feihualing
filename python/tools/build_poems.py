"""
build_poems.py —— 构建诗句数据文件（可以反复运行，结果稳定）
==============================================================
做的事情：
  1. 读取 data/poems_tang_original.json 里的唐诗底本（唐诗三百首）
  2. 清洗：去掉 "(明年一作：年年)" 这类校勘注；把塞了整段的长句拆成短句；过滤超长句
  3. 合并 extra_poems.py 里手工整理的补充数据
     （整篇补全 / 小学必背 / 宋词 / 五代词 / 诗经乐府 / 四季名篇 / 唐诗名篇 / 宋诗 / 补遗）
  4. 按 TITLE_ALIAS、LINE_ALIAS、GENRE_FIX 三张表把简称篇名和错标的体裁改回来
  5. 去重、排序、写出 data/poems.json
  6. 打印质量报告（总数、各类别句数、常用令字覆盖）

运行：python3 build_poems.py
"""
import json
import os
import re
from collections import Counter

from extra_poems import (PRIMARY_SCHOOL, SONG_CI, SONG_CI_EXTRA, CLASSICS, SEASONS,
                         TANG_CLASSICS, SONG_SHI, MORE_POEMS, FULL_TEXTS)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
DATA_FILE = os.path.join(BASE, "data", "poems.json")
BACKUP_FILE = os.path.join(BASE, "data", "poems_tang_original.json")
USER_FILE = os.path.join(BASE, "data", "user_poems.json")   # 玩家在界面里自己加的诗句


# 早几块数据只写了词牌名（"念奴娇"），FULL_TEXTS 写的是带题目的小序（"念奴娇·赤壁怀古"）。
# 不归一的话，同一首词会被当成两篇：玩家看到《念奴娇》只有两句，完整的那首却挂在另一个名字下。
TITLE_ALIAS = {
    ("苏轼", "念奴娇"): "念奴娇·赤壁怀古",
    ("苏轼", "水调歌头"): "水调歌头·明月几时有",
    ("苏轼", "水龙吟"): "水龙吟·次韵章质夫杨花词",
    ("苏轼", "定风波"): "定风波·莫听穿林打叶声",
    ("苏轼", "卜算子"): "卜算子·黄州定慧院寓居作",
    ("苏轼", "蝶恋花"): "蝶恋花·春景",
    ("苏轼", "江城子"): "江城子·乙卯正月二十日夜记梦",
    ("苏轼", "浣溪沙"): "浣溪沙·游蕲水清泉寺",
    ("辛弃疾", "青玉案"): "青玉案·元夕",
    ("辛弃疾", "破阵子"): "破阵子·为陈同甫赋壮词以寄之",
    ("辛弃疾", "永遇乐"): "永遇乐·京口北固亭怀古",
    ("辛弃疾", "丑奴儿"): "丑奴儿·书博山道中壁",
    ("辛弃疾", "菩萨蛮"): "菩萨蛮·书江西造口壁",
    ("辛弃疾", "清平乐"): "清平乐·村居",
    ("辛弃疾", "南乡子"): "南乡子·登京口北固亭有怀",
    ("辛弃疾", "贺新郎"): "贺新郎·甚矣吾衰矣",
    ("辛弃疾", "西江月"): "西江月·夜行黄沙道中",
    ("李清照", "声声慢"): "声声慢·寻寻觅觅",
    ("李清照", "一剪梅"): "一剪梅·红藕香残玉簟秋",
    ("李清照", "醉花阴"): "醉花阴·薄雾浓云愁永昼",
    ("李清照", "武陵春"): "武陵春·风住尘香花已尽",
    ("柳永", "雨霖铃"): "雨霖铃·寒蝉凄切",
    ("柳永", "蝶恋花"): "蝶恋花·伫倚危楼风细细",
    ("柳永", "望海潮"): "望海潮·东南形胜",
    ("欧阳修", "蝶恋花"): "蝶恋花·庭院深深深几许",
    ("欧阳修", "玉楼春"): "玉楼春·尊前拟把归期说",
    ("欧阳修", "生查子"): "生查子·元夕",
    ("晏殊", "蝶恋花"): "蝶恋花·槛菊愁烟兰泣露",
    ("晏殊", "浣溪沙"): "浣溪沙·一曲新词酒一杯",
    ("晏几道", "临江仙"): "临江仙·梦后楼台高锁",
    ("晏几道", "鹧鸪天"): "鹧鸪天·彩袖殷勤捧玉钟",
    ("秦观", "鹊桥仙"): "鹊桥仙·纤云弄巧",
    ("秦观", "踏莎行"): "踏莎行·郴州旅舍",
    ("秦观", "浣溪沙"): "浣溪沙·漠漠轻寒上小楼",
    ("范仲淹", "苏幕遮"): "苏幕遮·怀旧",
    ("范仲淹", "渔家傲"): "渔家傲·秋思",
    ("周邦彦", "苏幕遮"): "苏幕遮·燎沉香",
    ("周邦彦", "少年游"): "少年游·并刀如水",
    ("周邦彦", "兰陵王"): "兰陵王·柳",
    ("姜夔", "扬州慢"): "扬州慢·淮左名都",
    ("姜夔", "踏莎行"): "踏莎行·燕燕轻盈",
    ("贺铸", "青玉案"): "青玉案·凌波不过横塘路",
    ("张先", "天仙子"): "天仙子·水调数声持酒听",
    ("蒋捷", "虞美人"): "虞美人·听雨",
    ("蒋捷", "一剪梅"): "一剪梅·舟过吴江",
    ("刘过", "唐多令"): "唐多令·芦叶满汀洲",
    ("岳飞", "满江红"): "满江红·怒发冲冠",
    ("陆游", "钗头凤"): "钗头凤·红酥手",
    ("李之仪", "卜算子"): "卜算子·我住长江头",
    ("黄庭坚", "清平乐"): "清平乐·春归何处",
    ("陈与义", "临江仙"): "临江仙·夜登小阁忆洛中旧游",
    ("朱敦儒", "相见欢"): "相见欢·金陵城上西楼",
    ("张孝祥", "念奴娇"): "念奴娇·过洞庭",
    ("陈亮", "水调歌头"): "水调歌头·送章德茂大卿使虏",
    ("李煜", "破阵子"): "破阵子·四十年来家国",
    ("李煜", "浪淘沙令"): "浪淘沙令·帘外雨潺潺",
    ("李煜", "虞美人"): "虞美人·春花秋月何时了",
    ("王昌龄", "出塞"): "出塞·秦时明月汉时关",
    ("李白", "宣州谢脁楼饯别校书叔云"): "宣州谢朓楼饯别校书叔云",
}

# 宋词块尾部混进了几首宋诗和古文，被当成了词；《滕王阁序》这类骈文也挂在唐诗名下。
# 用 {原标题: 正确体裁} 的形式，只改标错的那一条，同一篇里别的归类不动。
GENRE_FIX = {
    ("王安石", "梅花"): {"宋词": "宋诗"},
    ("王安石", "泊船瓜洲"): {"宋词": "宋诗"},
    ("王安石", "元日"): {"宋词": "宋诗"},
    ("王安石", "登飞来峰"): {"宋词": "宋诗"},
    ("文天祥", "过零丁洋"): {"宋词": "宋诗"},
    ("黄庭坚", "寄黄几复"): {"宋词": "宋诗"},
    ("晏殊", "寓意"): {"宋词": "宋诗"},
    ("范仲淹", "岳阳楼记"): {"宋词": "古文"},
    ("欧阳修", "醉翁亭记"): {"宋词": "古文"},
    ("王勃", "滕王阁序"): {"唐诗名篇": "古文"},
}


# 同名作品在底本里署"佚名"、补充数据里署了真名，按真名统一
AUTHOR_FIX = {
    ("佚名", "金缕衣"): "杜秋娘",
}

# 词牌名对得上一首、但底下挂了两首的那几处，只能按句子定归属。
# 李清照《如梦令》两首共用这一个词牌，底本里合成了一篇，这里按句拆回两首。
LINE_ALIAS = {
    ("李清照", "如梦令", "常记溪亭日暮，"): "如梦令·常记溪亭日暮",
    ("李清照", "如梦令", "沉醉不知归路。"): "如梦令·常记溪亭日暮",
    ("李清照", "如梦令", "兴尽晚回舟，"): "如梦令·常记溪亭日暮",
    ("李清照", "如梦令", "误入藕花深处。"): "如梦令·常记溪亭日暮",
    ("李清照", "如梦令", "惊起一滩鸥鹭。"): "如梦令·常记溪亭日暮",
    ("李清照", "如梦令", "昨夜雨疏风骤，"): "如梦令·昨夜雨疏风骤",
    ("李清照", "如梦令", "浓睡不消残酒。"): "如梦令·昨夜雨疏风骤",
    ("李清照", "如梦令", "应是绿肥红瘦。"): "如梦令·昨夜雨疏风骤",
}


def unify(rec, base_genre=None):
    """按上面几张表改写出处和体裁，返回新记录（不改原对象）

    base_genre 是底本里每篇的体裁：底本已经完整收录的名篇，补充数据里又按
    「唐诗名篇」摘了几句，这里统一回底本的体裁，免得同一首诗在诗库里出现两次。
    """
    key = (rec["作者"], rec["出处"])
    if key in AUTHOR_FIX:
        rec = dict(rec, 作者=AUTHOR_FIX[key])
        key = (rec["作者"], rec["出处"])
    line_key = (rec["作者"], rec["出处"], rec["句"])
    if line_key in LINE_ALIAS:
        rec = dict(rec, 出处=LINE_ALIAS[line_key])
    elif key in TITLE_ALIAS:
        rec = dict(rec, 出处=TITLE_ALIAS[key])
    fix = GENRE_FIX.get(key)
    if fix and rec["体裁"] in fix:
        rec = dict(rec, 体裁=fix[rec["体裁"]])
    elif rec["体裁"] == "唐诗名篇" and base_genre and key in base_genre:
        rec = dict(rec, 体裁=base_genre[key])
    return rec


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


def dedup_key(line):
    """去重用的键：去掉标点再比。

    同一句在不同数据块里可能收尾用逗号、也可能用句号（"劝君惜取少年时，" 和
    "劝君惜取少年时。"），不归一就会当成两句，游戏里问两遍。
    """
    return re.sub(r"[，。！？；、：,.!?;:　]", "", line)


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
            key = dedup_key(seg)
            if not key or key in seen:
                continue
            seen.add(key)
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
    # 底本里也有旧简称篇名和错标的体裁，先理顺一遍，下面的体裁统计才准
    tang = [unify(rec) for rec in tang]
    print("  理顺篇名体裁后：", len(tang))

    # 底本里同一篇可能挂着两种体裁（《游子吟》既标"乐府"又标"唐诗名篇"），
    # 挑句数最多的那个正经诗体，用来认出"补充数据摘句、底本其实已收全篇"的名篇
    genre_count = {}
    for rec in tang:
        genre_count.setdefault((rec["作者"], rec["出处"]), Counter())[rec["体裁"]] += 1
    base_genre = {}
    for key, counter in genre_count.items():
        for genre, _ in counter.most_common():
            if genre not in ("唐诗名篇", "小学必背", "自编"):
                base_genre[key] = genre
                break

    # 2) 合并补充数据。整篇的排在前面，摘句的只用来补整篇没覆盖到的句子
    extra = normalize(FULL_TEXTS + PRIMARY_SCHOOL + SONG_CI + SONG_CI_EXTRA + CLASSICS
                      + SEASONS + TANG_CLASSICS + SONG_SHI + MORE_POEMS, keep_short=True)
    print("补充数据：", len(extra),
          "（整篇 / 小学必背 / 宋词 / 五代词 / 诗经乐府 / 四季名篇 / 唐诗名篇 / 宋诗 / 补遗）")

    # 玩家在界面里自己添的句子，放在最后，不覆盖原名句
    user = load_user_poems()
    print("玩家自建：", len(user), "（data/user_poems.json）")

    # 3) 合并去重：唐诗优先，补充数据补充唐诗没有的，自建句最后
    #    先按归一表改写出处、体裁，再判重 —— 去重是先到先得，
    #    改写必须在判重之前，活下来的那条才会带上正确的篇名和体裁
    merged, seen = [], set()
    for rec in tang + extra + user:
        rec = unify(rec, base_genre)
        key = dedup_key(rec["句"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(rec)

    # 4) 排序：按类别归拢，读起来整齐（自建句排在最后）
    order = {"小学必背": 0, "宋词": 1, "五代词": 2, "宋诗": 3,
             "诗经": 4, "汉乐府": 5, "建安": 6, "魏晋": 7,
             "唐诗名篇": 8, "古文": 9, "自编": 10}
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
