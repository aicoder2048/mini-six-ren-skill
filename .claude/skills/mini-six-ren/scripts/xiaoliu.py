# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "lunardate>=0.2.0",
# ]
# ///
"""小六壬占卜核心算法 - Mini Six Ren Divination Engine

提供:
- 三传计算（九宫掌诀基础算法）
- 吉凶分级（每个符号 -2..+2 等级，并按 8 类问题分化）
- 整体格局判断（三吉/二吉一凶/.../三凶 与 上上格..下下格）
- 五行流转模式识别（连珠相生 / 连珠相克 / 比和 / 首尾相应 / 始生终克 / ...）
- 体用关系分析（初传=体、末传=用，含传统财源/受制/反哺判断）
- 特殊符号组合识别（双符组合 + 三符特殊格局）
- 应期与方位指引（基于末传五行 + 三传吉凶方位汇总）

Usage:
    uv run scripts/xiaoliu.py --numbers 1,2,3 --question "今日运势" --format json
    uv run scripts/xiaoliu.py --datetime "2025-01-31 14:30" --question "面试"
    uv run scripts/xiaoliu.py --chars "天地人" --question "感情"
    uv run scripts/xiaoliu.py --now --question "出行宜否"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ===== 九宫格符号数据 =====
# auspice_level: -2..+2
#   +2 = 大吉  +1 = 小吉  0 = 中性  -1 = 小凶  -2 = 大凶
SYMBOLS_DATA = [
    {
        "name": "大安",
        "element": "木",
        "description": "长期、缓慢、稳定",
        "interpretation": "求安稳，大安最吉；求变化，大安不吉",
        "direction": "正东",
        "deity": "三清",
        "order": 1,
        "auspice": "吉",
        "auspice_level": 2,
    },
    {
        "name": "留连",
        "element": "木",
        "description": "停止、反复、复杂",
        "interpretation": "想挽留，留连是吉；否则不吉",
        "direction": "东南",
        "deity": "文昌",
        "order": 2,
        "auspice": "中",
        "auspice_level": 0,
    },
    {
        "name": "速喜",
        "element": "火",
        "description": "惊喜、快速、突然",
        "interpretation": "意想不到的好事！如需稳定，则可能是惊吓",
        "direction": "正南",
        "deity": "雷祖",
        "order": 3,
        "auspice": "吉",
        "auspice_level": 2,
    },
    {
        "name": "赤口",
        "element": "金",
        "description": "争斗、凶恶、伤害",
        "interpretation": "最凶最恶，吵架、打架、斗争、官司、肉体受伤",
        "direction": "正西",
        "deity": "将帅",
        "order": 4,
        "auspice": "凶",
        "auspice_level": -2,
    },
    {
        "name": "小吉",
        "element": "水",
        "description": "起步、不多、尚可",
        "interpretation": "不完美，成中有缺，适合起步，碰上小吉都有阻碍",
        "direction": "正北",
        "deity": "真武",
        "order": 5,
        "auspice": "吉",
        "auspice_level": 1,
    },
    {
        "name": "空亡",
        "element": "土",
        "description": "失去、虚伪、空想",
        "interpretation": "先得再失，尤忌金钱事。现实之事遇空亡很差，虚幻之事遇空亡很好",
        "direction": "中间",
        "deity": "玉皇",
        "order": 6,
        "auspice": "凶",
        "auspice_level": -2,
    },
    {
        "name": "病符",
        "element": "土",
        "description": "病态、异常、治疗",
        "interpretation": "病态+治疗=病符，先有病才需治疗，过程不好受",
        "direction": "西南",
        "deity": "后土",
        "order": 7,
        "auspice": "凶",
        "auspice_level": -1,
    },
    {
        "name": "桃花",
        "element": "土",
        "description": "欲望、牵绊、异性",
        "interpretation": "人际关系，往往和欲望、异性有关。除谈恋爱外，桃花都是不好的",
        "direction": "东北",
        "deity": "城隍",
        "order": 8,
        "auspice": "中",
        "auspice_level": 0,
    },
    {
        "name": "天德",
        "element": "金",
        "description": "贵人、长辈、上司老板、高远",
        "interpretation": "求人办事，靠人成事！让贵人来帮你",
        "direction": "西北",
        "deity": "紫薇",
        "order": 9,
        "auspice": "吉",
        "auspice_level": 2,
    },
]

# 8 类常见问题（用于按问题类型分化符号吉凶）
QUESTION_TYPES = ["财运", "情感", "事业", "健康", "学业", "家庭", "官非", "出行"]

# 每个符号在不同问题类型上的吉凶倾向 -2..+2
# 例：桃花对"情感"是+2大吉，对"事业"是-1小凶，体现了"除恋爱外桃花都不好"的传统判断
SYMBOL_QUESTION_VALENCE = {
    "大安": {"财运":  1, "情感":  2, "事业":  1, "健康":  2, "学业":  1, "家庭":  2, "官非":  2, "出行": -1},
    "留连": {"财运": -1, "情感":  1, "事业": -1, "健康": -1, "学业":  0, "家庭":  0, "官非":  0, "出行": -1},
    "速喜": {"财运":  2, "情感":  2, "事业":  2, "健康": -1, "学业":  1, "家庭":  1, "官非":  1, "出行":  2},
    "赤口": {"财运": -2, "情感": -2, "事业": -2, "健康": -2, "学业": -1, "家庭": -2, "官非": -2, "出行": -2},
    "小吉": {"财运":  1, "情感":  0, "事业":  1, "健康":  0, "学业":  1, "家庭":  0, "官非":  0, "出行":  0},
    "空亡": {"财运": -2, "情感": -1, "事业": -2, "健康": -1, "学业": -1, "家庭": -1, "官非": -1, "出行": -2},
    "病符": {"财运": -1, "情感": -1, "事业": -1, "健康": -2, "学业": -1, "家庭": -1, "官非": -1, "出行": -1},
    "桃花": {"财运":  0, "情感":  2, "事业": -1, "健康":  0, "学业":  0, "家庭":  0, "官非":  0, "出行":  0},
    "天德": {"财运":  1, "情感":  1, "事业":  2, "健康":  1, "学业":  1, "家庭":  1, "官非":  2, "出行":  1},
}

# ===== 五行生克与关系含义 =====
WUXING_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_OVERCOMES = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

RELATION_MEANINGS = {
    "生": "前者生后者，顺势推进、自然演化",
    "克": "前者克后者，形成压制、需克服阻碍",
    "被生": "前者被后者生，得到反哺、外力扶助",
    "被克": "前者被后者克，受到压制、形势不利",
    "同": "同属一行，比和加力、稳固难变",
    "无": "五行无直接关系",
}

# 五行对应的应期与方位指引
ELEMENT_GUIDANCE = {
    "木": {
        "season": "春季",
        "months": "农历正月、二月（寅、卯月）",
        "hours": "寅时(03-05)、卯时(05-07)",
        "directions": ["正东", "东南"],
        "colors": "青、绿",
        "spirit": "生发之气；宜开创、播种、起步、伸张",
    },
    "火": {
        "season": "夏季",
        "months": "农历四月、五月（巳、午月）",
        "hours": "巳时(09-11)、午时(11-13)",
        "directions": ["正南"],
        "colors": "红、紫",
        "spirit": "升腾之气；宜发布、展示、推进、表达",
    },
    "土": {
        "season": "四季月（三、六、九、十二月交节前后）",
        "months": "农历三、六、九、十二月（辰、未、戌、丑月）",
        "hours": "辰时(07-09)、未时(13-15)、戌时(19-21)、丑时(01-03)",
        "directions": ["中央", "西南", "东北"],
        "colors": "黄、棕",
        "spirit": "厚载之气；宜沉淀、巩固、储蓄、修整",
    },
    "金": {
        "season": "秋季",
        "months": "农历七月、八月（申、酉月）",
        "hours": "申时(15-17)、酉时(17-19)",
        "directions": ["正西", "西北"],
        "colors": "白、银",
        "spirit": "收敛之气；宜决断、收割、整顿、肃清",
    },
    "水": {
        "season": "冬季",
        "months": "农历十月、十一月（亥、子月）",
        "hours": "亥时(21-23)、子时(23-01)",
        "directions": ["正北"],
        "colors": "黑、深蓝",
        "spirit": "潜藏之气；宜谋划、积蓄、休养、深思",
    },
}

# ===== 双符特殊组合 =====
# valence: "+" 吉性  "-" 凶性  "0" 中性/转化
COMBINATIONS_2 = {
    # 三大吉之间
    frozenset(["大安", "天德"]): {"name": "安德相辅", "meaning": "贵人扶持稳定，事有靠山可依", "valence": "+"},
    frozenset(["大安", "速喜"]): {"name": "安喜相会", "meaning": "稳中有喜，渐进有成", "valence": "+"},
    frozenset(["速喜", "天德"]): {"name": "喜从天降", "meaning": "贵人带喜，事来如风", "valence": "+"},
    # 大吉配小吉
    frozenset(["大安", "小吉"]): {"name": "渐入安境", "meaning": "由小成至大稳，循序渐进", "valence": "+"},
    frozenset(["小吉", "速喜"]): {"name": "小成速达", "meaning": "起步顺遂，喜事相承", "valence": "+"},
    frozenset(["小吉", "天德"]): {"name": "贵人小成", "meaning": "贵人扶持，渐积小成", "valence": "+"},
    # 解凶 / 转化
    frozenset(["天德", "病符"]): {"name": "贵人医治", "meaning": "病灾有解，难处有人援助", "valence": "+"},
    frozenset(["天德", "赤口"]): {"name": "贵人解争", "meaning": "争斗中有调停者，凶象可化解", "valence": "0"},
    frozenset(["天德", "空亡"]): {"name": "贵援落空", "meaning": "求贵无门，外援空缺", "valence": "-"},
    frozenset(["留连", "速喜"]): {"name": "缠中得喜", "meaning": "反复纠缠中迎来转机", "valence": "+"},
    frozenset(["留连", "天德"]): {"name": "困中遇援", "meaning": "纠缠困境中得贵人解围", "valence": "+"},
    # 桃花相关
    frozenset(["速喜", "桃花"]): {"name": "喜花相会", "meaning": "情缘速至，异性带来喜事", "valence": "+"},
    frozenset(["大安", "桃花"]): {"name": "情归稳定", "meaning": "情感趋稳，宜定不宜变", "valence": "+"},
    frozenset(["赤口", "桃花"]): {"name": "情斗纠葛", "meaning": "情感纷争，异性口舌之祸", "valence": "-"},
    frozenset(["留连", "桃花"]): {"name": "情缠不解", "meaning": "感情牵绊难断，纠葛持续", "valence": "0"},
    frozenset(["空亡", "桃花"]): {"name": "情空花谢", "meaning": "情缘虚幻，桃花落空", "valence": "-"},
    frozenset(["病符", "桃花"]): {"name": "情伤病扰", "meaning": "情感纠葛带来病忧或心伤", "valence": "-"},
    # 病符相关
    frozenset(["大安", "病符"]): {"name": "安抚病情", "meaning": "病势趋稳但需长期调养", "valence": "0"},
    frozenset(["速喜", "病符"]): {"name": "喜中带病", "meaning": "喜事中夹病灾，乐极生悲之兆", "valence": "-"},
    frozenset(["留连", "病符"]): {"name": "病滞难解", "meaning": "病灾纠缠，过程漫长", "valence": "-"},
    frozenset(["病符", "空亡"]): {"name": "病虚两亡", "meaning": "病情虚浮难定，求医如缘木", "valence": "-"},
    frozenset(["赤口", "病符"]): {"name": "斗中受伤", "meaning": "争斗中身心受损，病由争起", "valence": "-"},
    # 凶组合
    frozenset(["赤口", "空亡"]): {"name": "刑耗交加", "meaning": "争斗中破财损物，亦可破而后立", "valence": "-"},
    frozenset(["大安", "赤口"]): {"name": "静中起波", "meaning": "稳定中突遇冲突，需防意外争端", "valence": "-"},
    frozenset(["大安", "空亡"]): {"name": "安转空寂", "meaning": "看似稳实则空，需警惕表象", "valence": "-"},
    frozenset(["速喜", "空亡"]): {"name": "喜事虚浮", "meaning": "喜来如风去亦如风，难以持久", "valence": "-"},
    frozenset(["留连", "赤口"]): {"name": "缠斗反复", "meaning": "纠缠不清，争执反复", "valence": "-"},
    frozenset(["留连", "空亡"]): {"name": "缠空相侵", "meaning": "反复折腾终归虚无", "valence": "-"},
    frozenset(["小吉", "空亡"]): {"name": "小成转空", "meaning": "初有小成终归虚无", "valence": "-"},
    frozenset(["小吉", "赤口"]): {"name": "小成受阻", "meaning": "初有小成被冲突打断", "valence": "-"},
}

# ===== 三符特殊格局 =====
TRIPLE_PATTERNS = {
    "大安": {"name": "三安格", "meaning": "极静停滞之象。求安稳最佳，求变动最忌；事如止水，需主动破局"},
    "速喜": {"name": "三喜格", "meaning": "喜悦连绵或虚惊重重；视所问事性质而定，凡事来得快也去得快"},
    "赤口": {"name": "三口格", "meaning": "争端激化至极。需警惕刑伤口舌；亦有否极泰来之意，破而后立"},
    "空亡": {"name": "三空格", "meaning": "极虚之象。实事难成，虚事（修行、艺术、构想）反易立"},
    "天德": {"name": "三德格", "meaning": "贵人云集，事必有助；亦戒过度依赖外力而失主见"},
    "留连": {"name": "三连格", "meaning": "极度缠绕，进退两难；需斩断牵绊方可前进"},
    "病符": {"name": "三病格", "meaning": "病难深重，须长期调理；亦警示积劳积患"},
    "桃花": {"name": "三桃格", "meaning": "情缘极盛或情劫深重；视问题而定，桃运浓烈"},
    "小吉": {"name": "三小吉格", "meaning": "积小成大，循序渐进；不宜冒进，宜稳扎稳打"},
}


# ===== 核心计算 =====

def get_relation(e1: str, e2: str) -> str:
    """判断两个五行元素之间的关系"""
    if WUXING_GENERATES.get(e1) == e2:
        return "生"
    elif WUXING_OVERCOMES.get(e1) == e2:
        return "克"
    elif WUXING_GENERATES.get(e2) == e1:
        return "被生"
    elif WUXING_OVERCOMES.get(e2) == e1:
        return "被克"
    elif e1 == e2:
        return "同"
    else:
        return "无"


def calculate_symbol(start_position: int, steps: int) -> dict:
    """计算符号位置：从start_position开始，走steps步"""
    normalized = steps % 9
    if normalized == 0:
        normalized = 9
    end_position = (start_position + normalized - 1) % 9
    return SYMBOLS_DATA[end_position]


def enrich_symbol(symbol: dict) -> dict:
    """给符号附加 question_lens（各问题类型的吉凶倾向）。"""
    return {**symbol, "question_lens": SYMBOL_QUESTION_VALENCE.get(symbol["name"], {})}


# ===== 分析层 =====

def analyze_subject_object(first: dict, last: dict) -> dict:
    """体用分析：初传=体（问者起因/本身），末传=用（所问事/最终结果）。

    传统判断：
    - 体生用：我付出能量给事 — 散财耗力（事可成但费力）
    - 体克用：我能掌控此事 — 主动有为（吉象）
    - 用生体：事反哺于我 — 来财来缘（受益）
    - 用克体：事压制于我 — 受制受困（凶象）
    - 体用比和：同气相求 — 平稳但缺变数
    """
    e_subject = first["element"]
    e_object = last["element"]
    relation = get_relation(e_subject, e_object)

    interpretations = {
        "生": "体生用 — 你主动付出投入，事虽可成但需消耗心力（散财耗力之兆）",
        "克": "体克用 — 你能掌控此事，事在己手（主动有为之兆）",
        "被生": "用生体 — 此事反哺你身，外力相助、来财来缘（受益之兆）",
        "被克": "用克体 — 此事压制你身，外部压力大、被动受困（受制之兆）",
        "同": "体用比和 — 你与此事同气相求，平稳推进但缺少变数（和合稳定之兆）",
        "无": "体用无直接生克关系 — 各自独立，事态发展全凭自身努力",
    }
    return {
        "subject_name": first["name"],
        "subject_element": e_subject,
        "object_name": last["name"],
        "object_element": e_object,
        "relation": relation,
        "interpretation": interpretations[relation],
    }


def analyze_flow(elements: list[str]) -> dict:
    """五行整体流转模式判断。

    识别模式：
    - 三同比和：三传同气
    - 连珠相生：E1→E2→E3 全为生
    - 连珠相克：E1→E2→E3 全为克
    - 首尾相应：E1==E3 但 E2 不同
    - 先比和后变化 / 先变化后比和
    - 始生终克 / 始克终生
    - 生克交杂（其余）
    """
    e1, e2, e3 = elements
    r12 = get_relation(e1, e2)
    r23 = get_relation(e2, e3)
    sequence = f"{e1} → {e2} → {e3}"

    if e1 == e2 == e3:
        pattern = "三同比和"
        explanation = "三传同气，力量集中而稳固；事态走向单一，难有突变"
    elif r12 == "生" and r23 == "生":
        pattern = "连珠相生"
        explanation = "三传连环相生，气运绵延不绝；事态自然推进，前景顺遂"
    elif r12 == "克" and r23 == "克":
        pattern = "连珠相克"
        explanation = "三传连环相克，气运层层受制；事态步步受阻，需主动破局"
    elif e1 == e3 and e1 != e2:
        pattern = "首尾相应"
        explanation = "首末同气，中间换形；事态绕一圈回归原点，过程曲折但归宿明确"
    elif e1 == e2 and e2 != e3:
        pattern = "先比和后变化"
        explanation = "前期同气积蓄，后期发生转变；变化集中于末段"
    elif e2 == e3 and e1 != e2:
        pattern = "先变化后比和"
        explanation = "前期转折发力，后期归于同气；起承转合明显，末段稳定"
    elif r12 == "生" and r23 == "克":
        pattern = "始生终克"
        explanation = "开局顺势推进，末段反受压制；事至将成而遇阻力"
    elif r12 == "克" and r23 == "生":
        pattern = "始克终生"
        explanation = "开局艰难受阻，末段转为顺势；先苦后甜，需熬过初期"
    else:
        pattern = "生克交杂"
        explanation = "三传五行关系混杂；事态起伏多变，无定向规律"

    return {
        "sequence": sequence,
        "elements": [e1, e2, e3],
        "relation_first_to_second": r12,
        "relation_second_to_third": r23,
        "pattern": pattern,
        "explanation": explanation,
    }


def analyze_patterns(passes: list[dict]) -> dict:
    """整体格局与趋势判断。"""
    levels = [p["symbol"]["auspice_level"] for p in passes]
    auspices = [p["symbol"]["auspice"] for p in passes]

    auspice_count = {"吉": 0, "中": 0, "凶": 0}
    for a in auspices:
        auspice_count[a] += 1
    auspice_score = sum(levels)

    j, z, x = auspice_count["吉"], auspice_count["中"], auspice_count["凶"]
    if j == 3:
        overall, grade = "三吉", "上上格"
    elif j == 2 and x == 0:
        overall, grade = "二吉一中", "上格"
    elif j == 2 and x == 1:
        overall, grade = "二吉一凶", "中上格"
    elif j == 1 and z == 2:
        overall, grade = "一吉二中", "中平格"
    elif j == 1 and z == 1 and x == 1:
        overall, grade = "一吉一中一凶", "中平格"
    elif j == 1 and x == 2:
        overall, grade = "一吉二凶", "中下格"
    elif z == 3:
        overall, grade = "三中", "中平格"
    elif z == 2 and x == 1:
        overall, grade = "二中一凶", "中下格"
    elif z == 1 and x == 2:
        overall, grade = "一中二凶", "下格"
    elif x == 3:
        overall, grade = "三凶", "下下格"
    else:
        overall, grade = f"{j}吉{z}中{x}凶", "中平格"

    l1, l2, l3 = levels
    if l1 == l2 == l3 == 0:
        trend = "始终平淡"
        trend_explanation = "运势平稳如水，无大喜大悲；事态发展全看自身行动"
    elif l1 < l2 < l3:
        trend = "渐入佳境"
        trend_explanation = "运势逐步上扬，越往后越顺；后期发力为佳"
    elif l1 > l2 > l3:
        trend = "渐入低谷"
        trend_explanation = "运势逐步下行，需把握前期良机；后期宜守不宜攻"
    elif all(l >= 1 for l in levels):
        trend = "始终顺遂"
        trend_explanation = "全程顺利，无明显阻碍；可大胆推进"
    elif all(l <= -1 for l in levels):
        trend = "始终困顿"
        trend_explanation = "全程不利，需暂避锋芒；待天时再动"
    elif l2 < l1 and l2 < l3:
        trend = "先抑后扬"
        trend_explanation = "中期遇挫但末段反弹；过程需熬过低谷"
    elif l2 > l1 and l2 > l3:
        trend = "先扬后抑"
        trend_explanation = "中期最盛但末段衰退；需见好就收"
    elif l1 < 0 <= l3:
        trend = "苦尽甘来"
        trend_explanation = "初凶末吉，过程虽难终有所成"
    elif l1 > 0 >= l3:
        trend = "盛极而衰"
        trend_explanation = "初吉末凶，看似顺利末段反转，宜留退路"
    else:
        trend = "起伏不定"
        trend_explanation = "运势波动不定，难有定数；随机应变为宜"

    return {
        "auspice_count": auspice_count,
        "auspice_score": auspice_score,
        "auspice_levels": levels,
        "overall_pattern": overall,
        "grade": grade,
        "trend": trend,
        "trend_explanation": trend_explanation,
    }


def detect_combinations(passes: list[dict]) -> list[dict]:
    """识别特殊符号组合（双符 + 三符）。"""
    names = [p["symbol"]["name"] for p in passes]
    found = []

    # 三符格局（三同）
    if names[0] == names[1] == names[2]:
        tp = TRIPLE_PATTERNS.get(names[0])
        if tp:
            found.append({
                "type": "三符格局",
                "symbols": [names[0], names[0], names[0]],
                "name": tp["name"],
                "meaning": tp["meaning"],
                "valence": "0",  # 三同既可大吉也可大凶，视符号性质
            })
        return found  # 三同时不再列双符

    # 双符组合（去重所有 pair）
    seen = set()
    for i, j in [(0, 1), (1, 2), (0, 2)]:
        a, b = names[i], names[j]
        if a == b:
            continue
        key = frozenset([a, b])
        if key in seen:
            continue
        seen.add(key)
        combo = COMBINATIONS_2.get(key)
        if combo:
            found.append({
                "type": "双符组合",
                "symbols": [a, b],
                "name": combo["name"],
                "meaning": combo["meaning"],
                "valence": combo["valence"],
            })
    return found


def compute_timing_guidance(passes: list[dict]) -> dict:
    """基于末传五行的应期方位指引，并汇总三传吉/凶方位。"""
    last_symbol = passes[-1]["symbol"]
    primary_element = last_symbol["element"]
    guidance = ELEMENT_GUIDANCE.get(primary_element, {})

    favorable_dirs: list[str] = []
    avoid_dirs: list[str] = []
    favorable_deities: list[str] = []
    for p in passes:
        s = p["symbol"]
        if s["auspice_level"] >= 1:
            favorable_dirs.append(s["direction"])
            favorable_deities.append(s["deity"])
        elif s["auspice_level"] <= -1:
            avoid_dirs.append(s["direction"])

    return {
        "primary_element": primary_element,
        "season": guidance.get("season", ""),
        "favorable_months": guidance.get("months", ""),
        "favorable_hours": guidance.get("hours", ""),
        "element_directions": guidance.get("directions", []),
        "favorable_colors": guidance.get("colors", ""),
        "element_spirit": guidance.get("spirit", ""),
        "favorable_directions_from_passes": list(dict.fromkeys(favorable_dirs)),
        "avoid_directions_from_passes": list(dict.fromkeys(avoid_dirs)),
        "favorable_deities": list(dict.fromkeys(favorable_deities)),
    }


# ===== 主流程 =====

def generate_prediction(num1: int, num2: int, num3: int) -> dict:
    """核心算法：根据三个数字生成三传占卜结果与完整分析。"""
    first = calculate_symbol(0, num1)
    second = calculate_symbol((num1 - 1) % 9, num2)
    third = calculate_symbol((num1 + num2 - 2) % 9, num3)

    r1 = get_relation(first["element"], second["element"])
    r2 = get_relation(second["element"], third["element"])

    passes = [
        {"position": "初传（前期）", "role": "体（问者起因）", "symbol": enrich_symbol(first), "index": 0},
        {"position": "中传（中期）", "role": "枢（过程发展）", "symbol": enrich_symbol(second), "index": 1},
        {"position": "末传（后期）", "role": "用（所问结果）", "symbol": enrich_symbol(third), "index": 2},
    ]

    relations = [
        {
            "from": first["name"],
            "to": second["name"],
            "from_element": first["element"],
            "to_element": second["element"],
            "relation": r1,
            "meaning": RELATION_MEANINGS[r1],
        },
        {
            "from": second["name"],
            "to": third["name"],
            "from_element": second["element"],
            "to_element": third["element"],
            "relation": r2,
            "meaning": RELATION_MEANINGS[r2],
        },
    ]

    return {
        "input_numbers": [num1, num2, num3],
        "passes": passes,
        "relations": relations,
        "subject_object": analyze_subject_object(first, third),
        "flow": analyze_flow([first["element"], second["element"], third["element"]]),
        "patterns": analyze_patterns(passes),
        "combinations": detect_combinations(passes),
        "timing_guidance": compute_timing_guidance(passes),
    }


# ===== 汉字笔画数据 =====
# strokes.json 由 Unicode Unihan 数据库 (kTotalStrokes) 一次性离线生成，
# 覆盖 102K+ 个 CJK 字符的真实笔画。
HOUR_NAMES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

_STROKES_CACHE: dict | None = None


def _load_strokes_data() -> dict:
    """懒加载 strokes.json（与本脚本同目录）。"""
    global _STROKES_CACHE
    if _STROKES_CACHE is not None:
        return _STROKES_CACHE
    strokes_file = Path(__file__).resolve().parent / "strokes.json"
    if strokes_file.exists():
        _STROKES_CACHE = json.loads(strokes_file.read_text(encoding="utf-8"))
    else:
        _STROKES_CACHE = {}
    return _STROKES_CACHE


def get_stroke_count(char: str) -> int:
    """获取单个汉字真实笔画数。

    优先查 Unihan 数据库（strokes.json）；极罕见字（非 CJK 或数据缺失）回落到
    Unicode 码点取模兜底，确保不报错。
    """
    strokes = _load_strokes_data()
    if char in strokes:
        return strokes[char]
    return (ord(char) % 20) + 1


def chars_to_numbers(chars: str) -> list[int]:
    """将汉字转换为笔画数列表（取前三个字）"""
    chars = chars[:3]
    return [get_stroke_count(c) for c in chars if "一" <= c <= "鿿"]


def datetime_to_numbers(dt: datetime) -> tuple[list[int], dict]:
    """将日期时间转换为三个数字（月、日、时辰），同时返回转换元数据。"""
    try:
        from lunardate import LunarDate
        lunar = LunarDate.fromSolarDate(dt.year, dt.month, dt.day)
        lunar_month = lunar.month
        lunar_day = lunar.day
        lunar_str = f"农历{lunar.year}年{lunar.month}月{lunar.day}日"
    except Exception:
        lunar_month = dt.month
        lunar_day = dt.day
        lunar_str = "（农历转换失败，使用公历）"

    # 时辰：23-1点=子时(1), 1-3点=丑时(2), ... 21-23点=亥时(12)
    hour_branch = ((dt.hour + 1) // 2) % 12 + 1
    hour_name = HOUR_NAMES[hour_branch - 1] + "时"

    meta = {
        "solar": dt.strftime("%Y-%m-%d %H:%M"),
        "lunar": lunar_str,
        "lunar_month": lunar_month,
        "lunar_day": lunar_day,
        "hour_branch": hour_branch,
        "hour_name": hour_name,
    }
    return [lunar_month, lunar_day, hour_branch], meta


# ===== 输入解析与格式化 =====

def parse_input(args) -> tuple[list[int], dict]:
    """根据命令行参数解析输入，返回 (三数字, input_metadata)。"""
    if args.numbers:
        parts = args.numbers.split(",")
        if len(parts) != 3:
            print("错误: 请输入恰好3个数字，逗号分隔", file=sys.stderr)
            sys.exit(1)
        nums = [int(p.strip()) for p in parts]
        return nums, {"mode": "numbers", "raw": args.numbers}

    if args.datetime:
        dt = datetime.strptime(args.datetime, "%Y-%m-%d %H:%M")
        nums, dt_meta = datetime_to_numbers(dt)
        return nums, {"mode": "datetime", "raw": args.datetime, **dt_meta}

    if args.chars:
        nums = chars_to_numbers(args.chars)
        if len(nums) < 3:
            print("错误: 请输入至少3个汉字", file=sys.stderr)
            sys.exit(1)
        nums = nums[:3]
        return nums, {
            "mode": "chars",
            "raw": args.chars,
            "stroke_counts": nums,
        }

    if args.now:
        dt = datetime.now()
        nums, dt_meta = datetime_to_numbers(dt)
        return nums, {"mode": "now", "raw": dt.strftime("%Y-%m-%d %H:%M"), **dt_meta}

    print("错误: 必须提供一种输入方式", file=sys.stderr)
    sys.exit(1)


def format_text_output(result: dict) -> str:
    """格式化为可读的文本输出。"""
    lines = []
    lines.append("=" * 64)
    lines.append("              小六壬三传占卜结果")
    lines.append("=" * 64)

    inp = result.get("input", {})
    mode_desc = {
        "numbers": "数字起卦",
        "datetime": "日期时间起卦",
        "chars": "汉字笔画起卦",
        "now": "当前时间起卦",
    }.get(inp.get("mode", ""), inp.get("mode", ""))
    lines.append(f"  起卦方式: {mode_desc}")
    lines.append(f"  输入数据: {inp.get('raw', '')}")
    if inp.get("lunar"):
        lines.append(f"  农历对照: {inp['lunar']} {inp.get('hour_name', '')}")
    if inp.get("stroke_counts"):
        lines.append(f"  汉字笔画: {inp['stroke_counts']}")
    lines.append(f"  起卦三数: {result['input_numbers']}")
    if result.get("question"):
        lines.append(f"  求问事项: {result['question']}")
    lines.append("-" * 64)

    # 卦象速读
    p = result["patterns"]
    so = result["subject_object"]
    flow = result["flow"]
    lines.append("【卦象速读】")
    lines.append(f"  整体格局: {p['overall_pattern']}（{p['grade']}）  总评分: {p['auspice_score']:+d}")
    lines.append(f"  五行流转: {flow['pattern']}  ( {flow['sequence']} )")
    lines.append(f"  趋势走向: {p['trend']} — {p['trend_explanation']}")
    lines.append(f"  体用关系: {so['interpretation']}")
    lines.append("-" * 64)

    # 三传详解
    lines.append("【三传详解】")
    for pp in result["passes"]:
        s = pp["symbol"]
        lines.append("")
        lines.append(f"  ◆ {pp['position']}  [{pp['role']}]")
        lines.append(f"    符号: 【{s['name']}】  五行: {s['element']}  方位: {s['direction']}  神灵: {s['deity']}")
        lines.append(f"    吉凶: {s['auspice']} ({s['auspice_level']:+d})")
        lines.append(f"    含义: {s['description']}")
        lines.append(f"    解释: {s['interpretation']}")
    lines.append("")
    lines.append("-" * 64)

    # 五行流转
    lines.append("【五行流转】")
    for r in result["relations"]:
        lines.append(f"  {r['from']}({r['from_element']}) —{r['relation']}→ {r['to']}({r['to_element']})")
        lines.append(f"    {r['meaning']}")
    lines.append(f"  整体: {flow['explanation']}")

    # 特殊组合
    combos = result.get("combinations", [])
    if combos:
        lines.append("-" * 64)
        lines.append("【特殊组合】")
        for c in combos:
            lines.append(f"  ◆ 【{c['name']}】 ({c['type']}: {' + '.join(c['symbols'])})")
            lines.append(f"    {c['meaning']}")

    # 应期与方位
    tg = result.get("timing_guidance", {})
    if tg:
        lines.append("-" * 64)
        lines.append("【应期与方位指引】")
        lines.append(f"  末传五行: {tg['primary_element']} — {tg.get('element_spirit', '')}")
        lines.append(f"  应期季节: {tg.get('season', '')}")
        lines.append(f"  应期月份: {tg.get('favorable_months', '')}")
        lines.append(f"  吉利时辰: {tg.get('favorable_hours', '')}")
        if tg.get("element_directions"):
            lines.append(f"  五行方位: {'、'.join(tg['element_directions'])}")
        if tg.get("favorable_directions_from_passes"):
            lines.append(f"  三传吉方: {'、'.join(tg['favorable_directions_from_passes'])}")
        if tg.get("avoid_directions_from_passes"):
            lines.append(f"  避忌方位: {'、'.join(tg['avoid_directions_from_passes'])}")
        if tg.get("favorable_deities"):
            lines.append(f"  可借神灵: {'、'.join(tg['favorable_deities'])}")
        if tg.get("favorable_colors"):
            lines.append(f"  吉利色彩: {tg['favorable_colors']}")

    lines.append("=" * 64)
    return "\n".join(lines)


def format_json_output(result: dict) -> str:
    """格式化为 JSON 输出。"""
    return json.dumps(result, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="小六壬占卜 - Mini Six Ren Divination")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--numbers", "-n", help="三个数字，逗号分隔 (例: 1,2,3)")
    group.add_argument("--datetime", "-d", help="日期时间 (例: 2025-01-31 14:30)")
    group.add_argument("--chars", "-c", help="三个汉字 (例: 天地人)")
    group.add_argument("--now", action="store_true", help="使用当前时间占卜")
    parser.add_argument("--question", "-q", help="求问事项")
    parser.add_argument("--format", "-f", choices=["text", "json"], default="text", help="输出格式")
    args = parser.parse_args()

    nums, input_meta = parse_input(args)
    result = generate_prediction(*nums)

    # 注入输入元数据与问题
    result_with_meta = {
        "input": input_meta,
        **result,
    }
    if args.question:
        result_with_meta["question"] = args.question

    if args.format == "json":
        print(format_json_output(result_with_meta))
    else:
        print(format_text_output(result_with_meta))


if __name__ == "__main__":
    main()
