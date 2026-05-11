---
name: mini-six-ren
description: "小六壬占卜系统 (Mini Six Ren Divination) - 中国传统占卜和命理分析。Use when the user asks for divination, fortune telling, or prediction using mini six ren (小六壬), or mentions keywords: 占卜、算卦、小六壬、三传、运势、占一卦、divination、fortune. Supports four input modes: numbers, date/time, Chinese characters (汉字笔画), and current time. Generates three-pass (三传) predictions with rich structured analysis: auspice grading, overall pattern, five-element flow, subject-object (体用) relation, special combinations, and timing/direction guidance. LLM interpretation follows a rigorous seven-step traditional framework."
---

# Mini Six Ren (小六壬占卜)

Chinese traditional divination based on the Nine-Palace hand technique (九宫掌诀). Generates three-pass (三传) predictions with multi-layer analysis, then provides AI-powered interpretation grounded in traditional methodology.

## Workflow

1. Determine input mode (numbers / datetime / Chinese chars / current time).
2. Run `scripts/xiaoliu.py --format json` to compute the prediction (now returns a rich analytical JSON — see "JSON Schema" below).
3. Check if `config.yaml` exists and has a `model` field:
   - **No config** (default): Display `ℹ️ 当前使用 Claude Code 内置模型解读。如需使用第三方模型，请创建 config.yaml`. Then perform the built-in LLM analysis following the "Seven-Step Interpretation Framework" below.
   - **Has config + API key**: Display `ℹ️ 当前使用 <model> 解读`. Pipe the prediction JSON into `scripts/interpret.py`:
     ```bash
     uv run scripts/xiaoliu.py --now --question "问题" --format json | \
       uv run scripts/interpret.py --question "问题"
     ```
   - **Has config, missing API key**: Display `⚠️ 请在 .env 中设置 <ENV_KEY>`. Fall back to built-in LLM analysis.
4. Format the final report using `assets/template.md`, filling all placeholders with the prediction JSON and the LLM analysis.

## Quick Start

```bash
# By three numbers
uv run scripts/xiaoliu.py --numbers 1,2,3 --question "今日运势" --format json

# By date/time (auto-converted to lunar month / day / hour-branch)
uv run scripts/xiaoliu.py --datetime "2025-07-15 10:30" --question "面试能成功吗" --format json

# By Chinese characters (uses stroke count)
uv run scripts/xiaoliu.py --chars "天地人" --question "感情运势" --format json

# By current time
uv run scripts/xiaoliu.py --now --question "今天适合出行吗" --format json
```

Use `--format json` for LLM analysis. Use `--format text` for direct human-readable display (already includes the analytical sections).

## Input Mode Selection

| User says | Mode | Example |
|---|---|---|
| gives 3 numbers | `--numbers` | `--numbers 3,5,7` |
| mentions a date/time | `--datetime` | `--datetime "2025-01-31 14:30"` |
| gives Chinese characters | `--chars` | `--chars "天地人"` |
| "用现在的时间" / "now" | `--now` | `--now` |
| no specific input | `--now` | default to current time |

## JSON Schema (key analytical fields)

The script now outputs a structured JSON with these top-level fields:

| Field | Purpose |
|---|---|
| `input` | Input mode metadata (mode, raw, lunar/hour for datetime modes, stroke_counts for chars) |
| `input_numbers` | The three step numbers used for 三传 computation |
| `passes` | The three passes; each has `position`, `role` (体/枢/用), `symbol` with `auspice`/`auspice_level`/`question_lens` |
| `relations` | Pairwise five-element relations between adjacent passes, with `meaning` |
| `subject_object` | 体用关系: subject (initial) vs object (final) — relation + interpretation |
| `flow` | Overall five-element flow pattern (连珠相生 / 连珠相克 / 三同比和 / 始克终生 / ... ) with explanation |
| `patterns` | `overall_pattern` (三吉/二吉一凶/...), `grade` (上上格..下下格), `trend` (渐入佳境/苦尽甘来/...), `auspice_score` |
| `combinations` | Detected special combinations (双符 / 三符格局) with valence |
| `timing_guidance` | Season, months, hours, directions (based on末传 element + 三传 auspice-sorted directions), favorable deities |
| `question` | Echo of the user's question |

**Key field for question-aware interpretation**: `passes[i].symbol.question_lens` provides each symbol's auspice level (-2..+2) for each of 8 question categories (财运/情感/事业/健康/学业/家庭/官非/出行). Always prefer the lens value over the base `auspice_level` when the user's question category is identifiable.

## Seven-Step Interpretation Framework

When performing the built-in LLM analysis (Claude Code's own model, no third-party config), follow this rigorous seven-step traditional framework. (`scripts/interpret.py` embeds the same framework in its system prompt for third-party models.)

### Step 1: 识别问题类别 (Identify Question Category)

Map the user's question to one of 8 categories — this determines which `question_lens` index to use:

| 类别 | 关键词 |
|---|---|
| 财运 | 钱、财、生意、投资、加薪、奖金、买卖 |
| 情感 | 恋爱、感情、婚姻、对象、复合、分手 |
| 事业 | 工作、项目、升迁、跳槽、offer、面试 |
| 健康 | 病、手术、康复、检查、体检 |
| 学业 | 考试、升学、留学、论文、读书 |
| 家庭 | 家人、父母、子女、配偶、家事 |
| 官非 | 官司、诉讼、纠纷、法律 |
| 出行 | 出差、旅行、搬家、远行、调动 |

If no clear question or "综合运势": fall back to base `auspice_level`.

### Step 2: 体用定位 (Subject-Object Positioning)

- **初传 = 体** (problem原因 / 问者本身)
- **末传 = 用** (所问事 / 最终结果)
- **中传 = 枢** (过程枢纽)

Use `subject_object.interpretation` from the JSON.

### Step 3: 三传时序分析 (Sequential Analysis with Question Lens)

For each pass, answer:
1. **In this question category**, what does this symbol mean? — Use `question_lens[category]` from each pass's symbol.
2. **Five-element relation** with the adjacent pass — Use `relations[i].meaning`.
3. **Direction and deity** — what energy does this position channel?

**Critical**: the same symbol means different things across categories. Examples:
- 桃花 → 情感 +2 大吉, 事业 -1 小凶
- 大安 → 健康 +2 大吉, 出行 -1 小凶 (主静不主动)
- 速喜 → 财运 +2 大吉, 健康 -1 小凶 (突发病症)

### Step 4: 五行整体流转 (Overall Five-Element Flow)

Use `flow.pattern` + `flow.explanation` + `patterns.trend`:
- 连珠相生 → 气运绵延，最吉流转
- 连珠相克 → 层层受制，最凶流转
- 始克终生 → 先苦后甜
- 始生终克 → 盛极而衰
- 三同比和 → 力量集中难突变
- 等等

### Step 5: 特殊组合识别 (Detect Combinations)

Use `combinations` list:
- **三符格局** → defines the entire cast.
- **双符组合**: valence "+" 强化吉象 / "-" 警示凶险 / "0" 取决于行动
- If empty: skip; rely on basic analysis.

See [`references/combinations_reference.md`](references/combinations_reference.md) for detailed combination meanings.

### Step 6: 应期与方位 (Timing & Direction)

Use `timing_guidance`:
- **应期**: season, months, hours (based on末传 element)
- **吉方**: `favorable_directions_from_passes`
- **避方**: `avoid_directions_from_passes`
- **可借神灵**: `favorable_deities`

### Step 7: 综合判断与建议 (Synthesis & Advice)

Tie everything back to the user's specific question. Give a clear answer (能成 / 不能成 / 部分成 / 需某条件).

### Built-in LLM Output Structure

Generate analysis in **this exact section order** (matches `assets/template.md` placeholders):

1. **🎯 卦象总览** (`ai_overview`) — one paragraph: 整体格局 + 五行流转 + 趋势 (1-2 sentences定调)
2. **⏳ 时间脉络** (`ai_timeline`) — 三段：初传 / 中传 / 末传, each 2-4 sentences with question lens
3. **⚖️ 体用与五行** (`ai_subject_object_flow`) — explain "why事态如此走向": 体用关系 × 五行流转
4. **🌟 关键组合** (`ai_combinations`) — 1-2 most relevant combinations, or note that none formed
5. **🧭 应期与方位** (`ai_timing_direction`) — when / where / which deity to invoke
6. **💡 行动建议** (`ai_advice`) — 3-5 concrete actionable bullets
7. **🔮 结论** (`ai_conclusion`) — 1-2 sentences: direct answer to the question

### Style Guidelines

- 始终扣紧用户问题——never泛泛而谈。
- 末传最重要 (final pass = primary indicator).
- 避免极端断言——用"宜""忌""可""需"等留余地。
- Elegant, philosophical Chinese, but accessible.
- **Total length: 700-1100 中文字** for the LLM analysis portion.

## Report Output

After generating the prediction JSON and the LLM analysis, format using [`assets/template.md`](assets/template.md). Replace all `{{placeholder}}` variables with values from the script output and the LLM analysis.

### Key template variables

**From `xiaoliu.py` JSON output**:
- `{{timestamp}}`, `{{input_mode}}`, `{{input_data}}`, `{{input_numbers}}`, `{{question}}`
- `{{overall_pattern}}`, `{{grade}}`, `{{auspice_score}}`, `{{trend}}`, `{{trend_explanation_short}}`
- `{{flow_pattern}}`, `{{element_sequence}}`, `{{flow_explanation}}`
- Per pass: `{{first_name}}`, `{{first_element}}`, `{{first_auspice}}`, `{{first_level}}`, `{{first_description}}`, `{{first_interpretation}}`, `{{first_direction}}`, `{{first_deity}}`, `{{first_lens_value}}` (and `second_*`, `third_*` analogously)
- `{{relation_1_2}}`, `{{relation_2_3}}`, `{{relation_1_2_meaning}}`, `{{relation_2_3_meaning}}`
- `{{subject_object_relation}}`, `{{subject_object_interpretation}}`, `{{subject_object_summary}}`, `{{subject_object_relation_short}}`
- `{{primary_element}}`, `{{element_spirit}}`, `{{season}}`, `{{favorable_months}}`, `{{favorable_hours}}`, `{{element_directions}}`, `{{favorable_directions_from_passes}}`, `{{avoid_directions_from_passes}}`, `{{favorable_deities}}`, `{{favorable_colors}}`
- `{{#combinations}}...{{/combinations}}` block: iterates over the `combinations` array, each item has `{{combo_name}}`, `{{combo_type}}`, `{{combo_symbols}}`, `{{combo_meaning}}`. If empty, replace the whole loop with the note "本卦三传无形成传统特殊组合，回归基础卦象分析。"

**From LLM analysis** (you generate these strings):
- `{{ai_overview}}`, `{{ai_timeline}}`, `{{ai_subject_object_flow}}`, `{{ai_combinations}}`, `{{ai_timing_direction}}`, `{{ai_advice}}`, `{{ai_conclusion}}`
- For question-lens explanations: `{{first_lens_explanation}}`, `{{second_lens_explanation}}`, `{{third_lens_explanation}}` (brief 1-line explanation tying the lens value to the user's question)

## Third-Party Model Configuration (Optional)

By default, the skill uses Claude Code's built-in LLM for interpretation. To use a third-party model:

### Step 1: Create `config.yaml`

```yaml
# 格式: provider:model_name
model: deepseek:deepseek-chat
```

### Step 2: Set API Key in `.env`

```bash
DEEPSEEK_API_KEY=sk-...
```

### Supported Providers

| Provider prefix | API Key env var | Notes |
|---|---|---|
| `openai` | `OPENAI_API_KEY` | GPT series |
| `anthropic` | `ANTHROPIC_API_KEY` | Claude series |
| `google-gla` | `GEMINI_API_KEY` | Gemini series |
| `deepseek` | `DEEPSEEK_API_KEY` | DeepSeek |
| `kimi` | `MOONSHOT_API_KEY` | Moonshot Kimi |
| `qwen` | `DASHSCOPE_API_KEY` | Alibaba Qwen |
| `glm` | `ZHIPU_API_KEY` | Zhipu ChatGLM |

`interpret.py` embeds the same seven-step framework as a system prompt, so third-party models produce comparably structured output. To switch back to the built-in LLM, delete `config.yaml`.

## References

- [`references/symbols_reference.md`](references/symbols_reference.md) — 九宫符号详解 (按 8 类问题分化)
- [`references/interpretation_framework.md`](references/interpretation_framework.md) — 七步解读框架方法论
- [`references/combinations_reference.md`](references/combinations_reference.md) — 双符 / 三符特殊组合谱
- `examples/` — 三种输入方式示例
