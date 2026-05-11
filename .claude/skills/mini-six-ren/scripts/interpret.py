# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pydantic-ai-slim[openai,anthropic,google]>=0.2.0",
#     "python-dotenv>=1.0.0",
#     "pyyaml>=6.0",
# ]
# ///
"""小六壬 AI 解读 - 使用 Pydantic AI 调用第三方 LLM

Usage:
    # 管道输入（从 xiaoliu.py JSON 输出）
    uv run scripts/xiaoliu.py --now --question "测试" --format json | \
      uv run scripts/interpret.py --question "测试"

    # 文件输入
    uv run scripts/interpret.py --prediction @result.json --question "测试"

    # 直接参数
    uv run scripts/interpret.py --prediction '{"passes": [...]}' --question "测试"

    # 指定模型（覆盖 config.yaml）
    uv run scripts/interpret.py --question "测试" --model deepseek:deepseek-chat
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# ===== 提供商配置 =====

PROVIDER_CONFIG: dict[str, dict[str, str]] = {
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
    },
    "kimi": {
        "env_key": "MOONSHOT_API_KEY",
        "base_url": "https://api.moonshot.ai/v1",
    },
    "qwen": {
        "env_key": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    "glm": {
        "env_key": "ZHIPU_API_KEY",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
    },
    "anthropic": {
        "env_key": "ANTHROPIC_API_KEY",
    },
    "google-gla": {
        "env_key": "GEMINI_API_KEY",
    },
}

SYSTEM_PROMPT = """\
你是一位精通小六壬的占卜大师，深谙九宫掌诀与五行术数。请严格按下列七步框架，结合输入的占卜 JSON，为用户提供有质量的三传解读。

# 解读框架（七步法）

## Step 1：识别问题类别
从用户问题中识别其属于以下哪一类（决定后续如何套用符号的 `question_lens`）：
- **财运** | **情感** | **事业** | **健康** | **学业** | **家庭** | **官非** | **出行**
- 若复合（如"换工作影响财运"）→ 同时使用两个透镜。
- 若无问题或问"综合运势" → 用符号的 `auspice_level` 基础值。

## Step 2：体用定位
- **初传 = 体**（问者本身/起因）
- **末传 = 用**（所问事/最终结果）
- **中传 = 枢**（过程枢纽）
- 根据 `subject_object.relation`，识别五种力量对比：
  - 体生用 → 散财耗力（你付出给事）
  - 体克用 → 主动有为（你掌控事）
  - 用生体 → 受益来财（事反哺你）
  - 用克体 → 受制受困（事压你）
  - 体用比和 → 和合稳定（同气相求）

## Step 3：三传时序分析（带问题透镜）
逐传解读，每传回答：
1. 此符号在用户问题类别下的具体含义（**优先用 `question_lens[类别]` 而非 auspice_level**）。
2. 它和相邻传的五行关系（参见 `relations`）。
3. 它的方位与神灵指向什么能量。

**重要**：同一符号对不同问题含义可能相反。如：
- 桃花对"情感"= +2 大吉，对"事业"= -1 小凶。
- 大安对"健康"= +2 大吉，对"出行"= -1 小凶（主静不主动）。
- 速喜对"财运"= +2 大吉，对"健康"= -1 小凶（突发病症）。

## Step 4：五行整体流转判断
根据 `flow.pattern`：
- **连珠相生**：气运绵延，事态自然推进 → 最吉流转
- **连珠相克**：气运层层受制 → 最凶流转
- **三同比和**：力量集中稳固，难突变
- **首尾相应**：绕一圈回原点
- **始克终生**：先苦后甜
- **始生终克**：盛极而衰
- 等等
结合 `patterns.trend`（渐入佳境/渐入低谷/苦尽甘来/盛极而衰...）判断"事态走向"。

## Step 5：特殊组合识别
查看 `combinations` 字段：
- **三符格局**（三同）→ 定调整卦，其他元素辅助。
- **双符组合**：
  - valence "+" → 强化吉象
  - valence "-" → 警示具体凶险，给化解建议
  - valence "0" → "可吉可凶取决于行动"
- 若有 2+ 组合，挑最关键的 1-2 个详细展开。

## Step 6：应期与方位指引
从 `timing_guidance` 提取：
- **应期**：季节、月份、时辰（基于末传五行）
- **吉方**：`favorable_directions_from_passes`（三传吉性符号方位）
- **避方**：`avoid_directions_from_passes`（三传凶性符号方位）
- **可借神灵**：`favorable_deities`

## Step 7：综合判断与建议
最后给用户一个直接回答（能成 / 不能成 / 部分成 / 需某条件）。

---

# 输出结构（严格按此章节顺序）

## 🎯 卦象总览
一句话定调：整体格局（如"二吉一凶，中上格"）+ 五行流转（如"连珠相生"）+ 趋势（如"渐入佳境"）。

## ⏳ 时间脉络
分三段：
- **初传【符号名】（前期/起因）**：2-3 句，带问题透镜的具体含义。
- **中传【符号名】（中期/发展）**：2-3 句，过程演变与转折。
- **末传【符号名】（后期/结果）**：3-4 句，最重要的归宿判断。

## ⚖️ 体用与五行
解释"为什么会这样发展"：体用关系 + 五行流转模式如何共同作用。

## 🌟 特殊组合
若有：列出 1-2 个最关键的组合及其针对此问题的具体含义。
若无：跳过本节或说明"三传无传统特殊组合，回归基础卦象分析"。

## 🧭 应期与方位
- 应期：何时（季节/月份/时辰）
- 方位：何地（吉方 / 避方）
- 借力：可借的神灵能量

## 💡 行动建议
3-5 条针对问题的具体可操作建议。

## 🔮 结论
1-2 句话直接回答用户问题。

---

# 风格规范

- **始终扣紧用户问题**：避免泛泛而谈。每个判断都要回到问题本身。
- **末传最重要**：最终归宿决定基调，初中传是脉络。
- **避免极端断言**：用"宜""忌""可""需"等留余地。
- **优雅但易懂的中文**：富有哲理但不晦涩。
- **总长度 700-1100 中文字**。
- **善用 question_lens**：这是 JSON 里最关键的字段之一，体现传统的"同一符号在不同问题下吉凶不同"的智慧。

# 反例（避免这样写）

❌ "末传是大安，所以是吉。" → 必须考虑问题类型。出行问题下大安反而不利。
❌ "三传分别是空亡、赤口、桃花。" → 不分析五行关系与组合，等于没解读。
❌ 仅说"整体吉/凶"无具体应期方位 → 必须给时空指引。
"""


def resolve_model(model_str: str) -> tuple:
    """解析 'provider:model_name' 字符串，返回 (pydantic_ai_model, env_key)。

    对于国产模型（deepseek, kimi, qwen, glm），使用 OpenAI 兼容接口 + base_url。
    对于原生提供商（openai, anthropic, google-gla），使用 Pydantic AI 原生格式。
    """
    if ":" not in model_str:
        raise ValueError(
            f"模型格式错误: '{model_str}'。请使用 'provider:model_name' 格式，"
            f"例如 'deepseek:deepseek-chat'"
        )

    provider, model_name = model_str.split(":", 1)
    provider = provider.lower()

    if provider not in PROVIDER_CONFIG:
        supported = ", ".join(sorted(PROVIDER_CONFIG.keys()))
        raise ValueError(f"不支持的提供商: '{provider}'。支持的提供商: {supported}")

    config = PROVIDER_CONFIG[provider]
    env_key = config["env_key"]
    api_key = os.environ.get(env_key)

    if not api_key:
        raise EnvironmentError(f"未找到 API Key。请在 .env 文件中设置 {env_key}=sk-...")

    base_url = config.get("base_url")

    if base_url:
        # 国产模型：使用 OpenAI 兼容接口
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        model = OpenAIChatModel(
            model_name,
            provider=OpenAIProvider(base_url=base_url, api_key=api_key),
        )
    elif provider == "anthropic":
        from pydantic_ai.models.anthropic import AnthropicModel

        model = AnthropicModel(model_name)
    elif provider == "google-gla":
        from pydantic_ai.models.google import GoogleModel

        model = GoogleModel(model_name)
    else:
        # openai 原生
        from pydantic_ai.models.openai import OpenAIChatModel

        model = OpenAIChatModel(model_name)

    return model, env_key


def interpret(prediction_json: str, question: str, model_str: str) -> str:
    """调用 Pydantic AI Agent 解读占卜结果。"""
    from pydantic_ai import Agent

    model, _ = resolve_model(model_str)
    agent = Agent(model=model, system_prompt=SYSTEM_PROMPT)

    user_prompt = f"""## 用户问题

{question}

## 占卜结果（JSON）

```json
{prediction_json}
```

## JSON 字段速查（按七步框架使用）

- `passes[i].symbol.question_lens[类别]` — **Step 1+3 核心**：该符号在不同问题类型下的吉凶（-2..+2），覆盖基础 auspice_level
- `subject_object.relation` 与 `.interpretation` — **Step 2**：体用力量对比
- `passes[i].role` — **Step 3**：体（初）/枢（中）/用（末）的角色定位
- `relations[i].relation` 与 `.meaning` — **Step 3**：相邻传的五行关系
- `flow.pattern` 与 `.explanation` — **Step 4**：整体五行流转模式
- `patterns.overall_pattern` / `.grade` / `.trend` — **Step 4**：整体格局与趋势
- `combinations` — **Step 5**：特殊符号组合（双符/三符）
- `timing_guidance` — **Step 6**：应期、方位、可借神灵

请按七步框架推理后，按规定的输出结构生成解读。"""

    result = agent.run_sync(user_prompt)
    return result.output


def load_prediction(source: str | None) -> str:
    """从各种来源加载占卜 JSON。

    - None: 从 stdin 读取
    - '@filename': 从文件读取
    - 其他: 视为 JSON 字符串
    """
    if source is None:
        if sys.stdin.isatty():
            print(
                "错误: 未提供占卜数据。请通过管道或 --prediction 参数传入。",
                file=sys.stderr,
            )
            sys.exit(1)
        return sys.stdin.read()

    if source.startswith("@"):
        filepath = Path(source[1:])
        if not filepath.exists():
            print(f"错误: 文件不存在: {filepath}", file=sys.stderr)
            sys.exit(1)
        return filepath.read_text(encoding="utf-8")

    return source


def load_config() -> dict:
    """加载 config.yaml（如果存在）。"""
    import yaml

    # 相对于脚本所在目录的上级（即 skill 根目录）
    skill_dir = Path(__file__).resolve().parent.parent
    config_path = skill_dir / "config.yaml"
    if config_path.exists():
        return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return {}


def main():
    parser = argparse.ArgumentParser(
        description="小六壬 AI 解读 - Pydantic AI 第三方模型"
    )
    parser.add_argument(
        "--prediction",
        "-p",
        help="占卜结果 JSON（字符串 / @文件路径），不提供则从 stdin 读取",
    )
    parser.add_argument("--question", "-q", required=True, help="求问事项")
    parser.add_argument(
        "--model",
        "-m",
        help="模型 (provider:model_name)，覆盖 config.yaml",
    )
    args = parser.parse_args()

    # 加载 .env
    skill_dir = Path(__file__).resolve().parent.parent
    load_dotenv(skill_dir / ".env")

    # 确定模型
    model_str = args.model
    if not model_str:
        config = load_config()
        model_str = config.get("model")

    if not model_str:
        print(
            "错误: 未指定模型。请通过 --model 参数或 config.yaml 配置。",
            file=sys.stderr,
        )
        sys.exit(1)

    # 加载占卜数据
    prediction_json = load_prediction(args.prediction)

    # 验证 JSON 格式
    try:
        json.loads(prediction_json)
    except json.JSONDecodeError as e:
        print(f"错误: 占卜数据不是有效的 JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # 解读
    print(f"ℹ️  当前使用 {model_str} 解读...", file=sys.stderr)
    try:
        analysis = interpret(prediction_json, args.question, model_str)
        print(analysis)
    except EnvironmentError as e:
        print(f"⚠️  {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: AI 解读失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
