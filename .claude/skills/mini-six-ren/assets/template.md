# 🔮 小六壬占卜报告

> **占卜时间**: {{timestamp}}
> **起卦方式**: {{input_mode}}
> **输入数据**: {{input_data}}
> **起卦三数**: {{input_numbers}}
> **求问事项**: {{question}}

---

## 🎯 卦象速读

| | **整体格局** | **五行流转** | **趋势走向** | **体用关系** |
|---|---|---|---|---|
| | {{overall_pattern}}（{{grade}}） | {{flow_pattern}} | {{trend}} | {{subject_object_relation_short}} |
| | 总评分 **{{auspice_score}}** | {{element_sequence}} | {{trend_explanation_short}} | {{subject_object_summary}} |

---

## 📊 三传详解

| | 初传（前期） | → | 中传（中期） | → | 末传（后期） |
|---|:---:|:---:|:---:|:---:|:---:|
| **角色** | 体（问者起因） | | 枢（过程发展） | | 用（所问结果） |
| **符号** | 【{{first_name}}】 | | 【{{second_name}}】 | | 【{{third_name}}】 |
| **五行** | {{first_element}} | {{relation_1_2}} | {{second_element}} | {{relation_2_3}} | {{third_element}} |
| **吉凶** | {{first_auspice}}（{{first_level}}） | | {{second_auspice}}（{{second_level}}） | | {{third_auspice}}（{{third_level}}） |
| **方位** | {{first_direction}} | | {{second_direction}} | | {{third_direction}} |
| **神灵** | {{first_deity}} | | {{second_deity}} | | {{third_deity}} |

### 符号详解

**初传 —【{{first_name}}】（{{first_element}}）** — 体 · {{first_auspice}}{{first_level_signed}}
- **含义**: {{first_description}}
- **解释**: {{first_interpretation}}
- **此问题透镜**: {{first_lens_value}} — {{first_lens_explanation}}

**中传 —【{{second_name}}】（{{second_element}}）** — 枢 · {{second_auspice}}{{second_level_signed}}
- **含义**: {{second_description}}
- **解释**: {{second_interpretation}}
- **此问题透镜**: {{second_lens_value}} — {{second_lens_explanation}}

**末传 —【{{third_name}}】（{{third_element}}）** — 用 · {{third_auspice}}{{third_level_signed}}
- **含义**: {{third_description}}
- **解释**: {{third_interpretation}}
- **此问题透镜**: {{third_lens_value}} — {{third_lens_explanation}}

---

## 🌊 五行流转

**流转图**：{{first_name}}（{{first_element}}）─{{relation_1_2}}→ {{second_name}}（{{second_element}}）─{{relation_2_3}}→ {{third_name}}（{{third_element}}）

- {{first_name}}（{{first_element}}） **{{relation_1_2}}** {{second_name}}（{{second_element}}）：{{relation_1_2_meaning}}
- {{second_name}}（{{second_element}}） **{{relation_2_3}}** {{third_name}}（{{third_element}}）：{{relation_2_3_meaning}}

**整体流转**：**{{flow_pattern}}** — {{flow_explanation}}

---

## ⚖️ 体用关系

**体**（你 / 起因）= 初传【{{first_name}}】{{first_element}}
**用**（所问事 / 结果）= 末传【{{third_name}}】{{third_element}}

**关系**：{{subject_object_relation}}
**解读**：{{subject_object_interpretation}}

---

## 🌟 特殊组合
<!-- 如 combinations 字段为空，本节改为：本卦三传无形成传统特殊组合，回归基础卦象分析。 -->

{{#combinations}}
- **【{{combo_name}}】**（{{combo_type}}: {{combo_symbols}}）— {{combo_meaning}}
{{/combinations}}

---

## 🧭 应期与方位指引

| | 内容 |
|---|---|
| **末传五行** | {{primary_element}} — {{element_spirit}} |
| **应期季节** | {{season}} |
| **应期月份** | {{favorable_months}} |
| **吉利时辰** | {{favorable_hours}} |
| **五行方位** | {{element_directions}} |
| **三传吉方** | {{favorable_directions_from_passes}} |
| **避忌方位** | {{avoid_directions_from_passes}} |
| **可借神灵** | {{favorable_deities}} |
| **吉利色彩** | {{favorable_colors}} |

---

## 🤖 智慧解读

> 求问事项：**{{question}}**

### 🎯 卦象总览

{{ai_overview}}

### ⏳ 时间脉络

{{ai_timeline}}

### ⚖️ 体用与五行

{{ai_subject_object_flow}}

### 🌟 关键组合

{{ai_combinations}}

### 🧭 应期与方位

{{ai_timing_direction}}

### 💡 行动建议

{{ai_advice}}

### 🔮 结论

{{ai_conclusion}}

---

*本报告由小六壬占卜系统生成，仅供参考娱乐。传承中华文化，弘扬传统智慧。*
