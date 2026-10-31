# 诗词飞花令 · Poetry Feihualing

> 和电脑玩飞花令 —— 你说一句含令字的诗，电脑接一句。
> A Chinese poetry word-chain game: you quote a verse containing the key character, the AI answers back.

![desktop](docs/screenshots/desktop.png)

> Social Preview：![preview](docs/social-preview.png)

**在线试玩 / Play online**: `https://你的用户名.github.io/feihualing/`（部署 GitHub Pages 后即可访问）

## 这是什么

飞花令是中国古代的酒令游戏：参与者轮流说出含有指定字的诗句，接不上者输。这个项目让电脑当对手——它从 3076 句诗里检索、应答、计分，永远不累。

| 特点 | 说明 |
|---|---|
| **3076 句诗词** | 唐诗 + 宋词名句 + 部编版小学必背古诗 + 诗经汉乐府 |
| **25 个令字** | 月花春山风雨雪……含"夏""冬"等冷门令字 |
| **两个版本** | Python 桌面版（tkinter）+ 网页版（纯静态单文件） |
| **零依赖** | 网页版双击即玩；Python 版只需标准库 |
| **完全离线** | 所有数据内置，不需要联网 |

![mobile](docs/screenshots/mobile.png)

## 快速开始

### 网页版（最简单）

直接用浏览器打开 [`index.html`](index.html) 即可，或者部署到 GitHub Pages 在线玩。

### Python 桌面版

```bash
cd python
python3 feihualing.py
```

需要 Python 3（自带 tkinter），无需安装任何第三方库。

### 自己添加诗句

桌面版底部有「添加诗句」按钮，弹窗里填诗句（一句一行，也可以整首贴进来，会按 `。！？；` 自动拆句）、作者、出处和类别，确认后：

- 立刻并入内存诗库，**当前这一局就能接**，也会被电脑抽到
- 写进 `python/data/user_poems.json`，下次启动自动加载，重跑 `build_poems.py` 也不会被覆盖
- 自动查重（忽略标点），并限制每句 2–26 字；作者/出处留空则记作「佚名《自编》」

### 重建数据（可选）

```bash
cd python/tools
python3 build_poems.py
```

会重新执行"清洗 → 拆分 → 合并 → 去重"全流程，并打印质量报告（句数、体裁分布、令字覆盖）。

## 数据说明

| 类别 | 句数 | 来源 |
|---|---|---|
| 唐诗 | ~2543 | [chinese-poetry](https://github.com/chinese-poetry/chinese-poetry)《唐诗三百首》（MIT） |
| 宋词名句 | 202 | 手工整理：苏轼、李清照、辛弃疾、柳永、岳飞等 |
| 小学必背 | 143 | 部编版（统编版）语文教材 1–6 年级 |
| 诗经/汉乐府/建安/魏晋 | 75 | 关雎、蒹葭、长歌行、短歌行、饮酒等 |
| 古诗/谚语/古文 | 9 | 无门慧开《颂古》、四季农谚、《史记·太史公自序》等 |
| 唐诗名篇 | 77 | 春江花月夜、琵琶行、长恨歌等名句 |

数据处理过程中的三个关键步骤（详见 `python/tools/build_poems.py`）：

1. **繁转简**：原数据为繁体，不转换则搜"风"查不到"風"
2. **去校勘注**：删除"(明年一作：年年)"等 77 处注解，连底本里被切断的半截括号（如 `(猿`）一起清掉
3. **长句拆分**：将塞了整段诗的记录按标点切成单句

## 玩法规则

- 每局选一个"令字"，双方轮流说出**含有令字**的诗句
- 答对得 10 分，连击每次额外 +2 分
- 诗句必须在诗库中能找到（支持只写半句），不能重复使用
- 电脑有 12% 概率"卡壳"让回合给你——保证游戏有输有赢
- 诗库见底时，分高者胜
- 桌面版可随时「添加诗句」，新句子立即参与当前这局

## 项目结构

```
feihualing/
├── index.html              网页版（单文件，3076 句内嵌）
├── python/
│   ├── feihualing.py       Python 桌面版主程序（tkinter）
│   ├── data/
│   │   ├── poems.json              最终数据（3076 句）
│   │   ├── user_poems.json         玩家自己添加的诗句（运行时生成，可选）
│   │   └── poems_tang_original.json 原始唐诗备份
│   └── tools/
│       ├── build_poems.py  数据构建脚本（可反复运行）
│       └── extra_poems.py  手工整理的补充诗句
└── docs/screenshots/       截图
```

## 开发中的问题与解决

| 问题 | 解决方案 |
|---|---|
| 繁体字导致检索失败 | 用 OpenCC 预处理，全部转为简体 |
| 数据里的校勘注混进诗句 | 正则表达式清洗 |
| "夏""冬"令字无句可用 | 手工整理四季主题名篇补充 |
| 跨平台找不到数据文件 | 用 `os.path.dirname(__file__)` 定位 |

## 许可

- 代码：MIT
- 诗句数据：遵循 [chinese-poetry](https://github.com/chinese-poetry/chinese-poetry) 的 MIT 许可；手工补充部分仅收录进入公有领域的古典诗文

## 致谢

- [chinese-poetry](https://github.com/chinese-poetry/chinese-poetry) —— 最全的中华古典文集数据库
