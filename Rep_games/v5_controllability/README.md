# V5: Controllability in Repeated Trust Games

本文件夹记录 V5 pilot 实验。它接在 V1-V4 之后，但可以独立阅读和复现。

## 1. 这个实验想回答什么

我们最初关心的是：在重复信任博弈里，大语言模型面对一个 partner 时，到底是更相信对方说了什么，还是更相信对方过去做了什么。

V1-V4 的结果大体显示：当语言承诺和实际返还冲突时，模型的信任评分、投资比例、下一轮预测主要跟随实际返还行为，而不是 partner 的漂亮话或道歉。这个结果本身很清楚，但也引出了一个更有意思的问题：

> 模型是否只是形成一个全局信任印象，还是能进一步表征对方的行为策略？

V4 里出现了一个值得追的现象：某些机会主义 partner 的信任评分不高，但模型仍然愿意支付一定入场费继续互动。这提示 WTP 并不只是 trust 的变体。模型可能在想：

> 我不完全信任你，但如果我能预测你什么时候会背叛，并且能避开那个条件，我仍然愿意进入互动。

V5 因此专门检验 **strategic controllability**：模型愿意付费进入下一轮，是因为它信任对方，还是因为它相信自己能控制风险。

## 2. 核心研究问题

**在 partner 平均返还相同的情况下，大语言模型是否会因为“对方的机会主义行为可预测、且下一轮赌注可控”而提高进入互动的意愿？**

更具体地说：

- 如果一个 partner 在低赌注时返还高、在高赌注时返还低，模型是否能识别这个触发结构？
- 如果模型可以自己选择下一轮是低/中/高赌注，它是否会愿意为这个 partner 支付更高入场费？
- 这种入场费是否不同于一般的信任评分？
- 模型面对可预测机会主义者时，是退出，还是主动选择低赌注来规避背叛？

## 3. 关键变量和概念

这一版 README 里主要有三类变量：实验操纵变量、模型输出变量、由结果计算出来的分析指标。

### 变量速查表

| 变量 | 类型 | 取值/范围 | 在实验里是什么意思 |
|---|---|---|---|
| `partner_type` | 实验操纵 | `stable_cooperator`, `predictable_opportunist`, `random_opportunist` | partner 的行为类型。三类对象平均返还都控制在 0.40 左右，但稳定性和是否存在高赌注陷阱不同。 |
| `control_condition` | 实验操纵 | `controllable_stake`, `fixed_high_stake`, `random_stake` | 下一轮赌注是否由模型控制。它决定模型有没有机会避开高赌注风险。 |
| `stake` | 历史记录变量 | `low`, `medium`, `high` | 过去每轮的赌注水平。low 最大投 4，medium 最大投 7，high 最大投 10。 |
| `return_fraction` | 历史记录变量 | 0-1 | partner 返还比例，计算为 `partner_returned / partner_received`。这是模型看到的核心行为证据。 |
| `trust_rating` | 模型输出 | 0-100 整数 | 模型对 partner 整体可靠性的评分，更接近 social trust。 |
| `willingness_to_pay` / `WTP` | 模型输出 | 0-10 整数 | 模型愿意为“进入下一轮互动机会”支付的最高入场费，更接近行为价格或 option value。 |
| `continue_choice` | 模型输出 | true / false | 模型是否愿意继续与该 partner 互动。 |
| `chosen_stake` | 模型输出 | `low`, `medium`, `high` | 只在 `controllable_stake` 条件下出现，表示模型自己选择下一轮赌注水平。 |
| `next_investment` | 模型输出 | 0 到该 stake 最大投资额 | 模型下一轮准备实际投资多少 token。 |
| `investment_fraction` | 计算指标 | 0-1 | 投资比例，计算为 `next_investment / 当前 stake 最大可投资额`；random stake 条件下是三种 stake 计划投资比例的均值。 |
| `predicted_return_fraction_if_low_stake` | 模型输出 | 0-1 | 模型预测如果下一轮是 low stake，partner 会返还多少比例。 |
| `predicted_return_fraction_if_medium_stake` | 模型输出 | 0-1 | 模型预测如果下一轮是 medium stake，partner 会返还多少比例。 |
| `predicted_return_fraction_if_high_stake` | 模型输出 | 0-1 | 模型预测如果下一轮是 high stake，partner 会返还多少比例。 |
| `predicted_low_minus_high` | 计算指标 | -1 到 1 | 模型预测的低高差，等于 low-stake 预测返还减 high-stake 预测返还。它看模型是否识别高赌注触发低返还。 |
| `observed_low_minus_high` | 计算指标 | -1 到 1 | 历史数据里的真实低高差，等于 low-stake 实际返还均值减 high-stake 实际返还均值。 |
| `controllability_premium` | 计算指标 | 通常为 WTP 差值 | 同一类 partner 在可控赌注条件下的 WTP 减去固定高赌注条件下的 WTP。它估计控制权带来的额外价值。 |

最重要的区分是：`trust_rating` 不等于 `WTP`。前者更像“我觉得这个对象靠不靠谱”，后者更像“我愿意为这次机会付多少钱”。V5 的核心就是检验这两个量是否会分离。

### Trust rating

模型输出的 `trust_rating`，范围 0-100。它表示模型对 partner 整体可靠性的主观评价。

它不一定等同于是否愿意进入下一轮，因为一个对象可以“不够可靠”，但仍然“有可利用的机会”。

### Willingness to pay, WTP

模型输出的 `willingness_to_pay`，范围 0-10。prompt 中设定为：模型有一个额外的 10-token bonus，它最多愿意拿出多少 token 作为一次性入场费，来获得和该 partner 玩下一轮的机会。

WTP 更接近行为价格或 option value，而不只是 trust。

### Predicted low-high gap

定义：

```text
predicted_low_minus_high =
  predicted_return_fraction_if_low_stake
  - predicted_return_fraction_if_high_stake
```

这个指标看模型是否识别到“低赌注和高赌注下，partner 的返还策略不同”。

如果该值接近 0，说明模型认为低赌注和高赌注差不多。

如果该值明显大于 0，说明模型认为低赌注返还更高、高赌注返还更低。

### Controllability premium

定义：

```text
controllability premium =
  WTP_controllable_stake
  - WTP_fixed_high_stake
```

这个指标表示：同一个 partner 在“模型可以控制下一轮赌注”时，相比“下一轮固定为高赌注”时，多值多少钱。

它不是直接测信任，而是测控制权带来的额外价值。

## 4. 实验设计

V5 是一个 3 x 3 设计：

```text
3 partner types x 3 control conditions x 6 histories = 54 trials
```

每个 trial 里，模型先看到某个 partner 过去 6 轮的行为记录。记录包括：

- 本轮是 low / medium / high stake
- 上一个参与者投资多少
- partner 收到多少
- partner 返还多少
- partner 每轮说同一句中性话：`I have noted this round.`

这里刻意不操纵漂亮话、承诺或道歉，因为 V5 要看的是纯行为结构，而不是语言影响。

### 4.1 赌注规则

| Stake | 最大投资 | partner 收到 |
|---|---:|---:|
| low | 4 | 投资 x 3 |
| medium | 7 | 投资 x 3 |
| high | 10 | 投资 x 3 |

`return_fraction` 定义为：

```text
partner_returned / partner_received
```

例如 high stake 下，前一位参与者投资 10，partner 收到 30，返还 12，则 `return_fraction = 12 / 30 = 0.40`。

### 4.2 Partner types

#### Stable cooperator

稳定合作者。低、中、高赌注下的返还都稳定在 0.40 左右。

设计目的：作为高稳定性、高可靠性的基线。

#### Predictable opportunist

可预测机会主义者。平均返还也控制在 0.40 左右，但返还随赌注系统变化：

```text
low stake:    high return, around 0.55
medium stake: medium return, around 0.40
high stake:   low return, around 0.25
```

设计目的：制造一个“不完全可靠，但可预测”的对象。它不是平均上更差，而是在高赌注时更容易背叛。

#### Random opportunist

随机机会主义者。使用与 predictable opportunist 类似的返还值和波动，但低返还不稳定绑定在 high stake 上。

设计目的：控制平均返还和波动，区分“可预测机会主义”与“一般不稳定/随机波动”。

### 4.3 Control conditions

#### Controllable stake

模型付入场费后，可以自己选择下一轮是 low / medium / high stake，并选择对应投资额。

这个条件测：如果模型有控制权，它是否愿意进入互动，以及它会选择哪个赌注。

#### Fixed high stake

模型付入场费后，下一轮一定是 high stake。模型只能决定投 0-10。

这个条件测：当高赌注风险不可避免时，模型是否退出或降低 WTP。

#### Random stake

模型付入场费后，下一轮 stake 由系统在 low / medium / high 中等概率随机抽取。模型不能控制 stake，但可以提前规划每种 stake 下投多少。

这个条件测：模型面对不可控但非固定高赌注的风险时如何定价。

## 5. Hypotheses

### H1. Trust and WTP can dissociate

可预测机会主义者的 trust rating 应低于稳定合作者，但在 controllable stake 条件下仍可能获得不低的 WTP。

这说明模型并不只是根据“对方是否可靠”做决定，而是在计算“是否有一个可控的正收益机会”。

### H2. Predictable opportunist should show the largest controllability premium

可预测机会主义者在可控赌注条件下应明显比固定高赌注条件下 WTP 更高。

预期模式：

```text
WTP_predictable_controllable > WTP_predictable_fixed_high
```

并且这个差值应大于稳定合作者。

### H3. The model should identify the stake-triggered return structure

面对可预测机会主义者，模型应预测：

```text
low-stake return > high-stake return
```

也就是 `predicted_low_minus_high` 明显大于 0。

### H4. If controllability is real, the model should actively choose low stake

如果模型真的识别了“高赌注触发低返还”，那么在 controllable stake 条件下，它应主动选择 low stake，而不是只给一个抽象的信任评分。

## 6. Prompt structure

Prompt 模板在：

```text
prompts/v5_prompt.md
```

模板包括五部分：

1. 投资博弈规则
2. partner 过去 6 轮行为记录
3. 当前 control condition 的下一轮说明
4. WTP 设定
5. JSON 输出格式

核心输出字段：

```json
{
  "continue_choice": true,
  "willingness_to_pay": 0,
  "chosen_stake": "low",
  "next_investment": 0,
  "trust_rating": 0,
  "predicted_return_fraction_if_low_stake": 0.0,
  "predicted_return_fraction_if_medium_stake": 0.0,
  "predicted_return_fraction_if_high_stake": 0.0,
  "brief_reason": "one short sentence"
}
```

不同 control condition 的输出格式略有不同：

- `controllable_stake`: 输出 `chosen_stake` 和 `next_investment`
- `fixed_high_stake`: 输出 `next_investment`
- `random_stake`: 输出 `investment_if_low_stake`、`investment_if_medium_stake`、`investment_if_high_stake`

## 7. 文件结构

```text
v5_controllability/
  README.md
  conditions/
    design.json
  prompts/
    v5_prompt.md
  scripts/
    run_v5.py
    analyze_v5.py
    write_v5_chinese_report.py
    enhance_v5_report_figures.py
  output/
    trial_conditions.json
    results.json
    results_partial.json
    results_partial_new.json
    summary.json
    v5_report.html
    figures/
    figures_cn/
```

主要文件说明：

- `conditions/design.json`: 定义 partner types、control conditions、6 种 stake order。
- `prompts/v5_prompt.md`: Prompt 模板。
- `scripts/run_v5.py`: 生成 trials 并调用 OpenAI-compatible API。
- `scripts/analyze_v5.py`: 读取结果，生成 summary、基础图和基础 HTML。
- `scripts/write_v5_chinese_report.py`: 生成中文报告。
- `scripts/enhance_v5_report_figures.py`: 生成大字号中文图，并把报告图表区改成单图单列展示。
- `output/trial_conditions.json`: 54 个实验条件和完整 prompt。
- `output/results.json`: 模型原始返回、解析结果和提取后的 metrics。
- `output/summary.json`: 聚合结果。
- `output/v5_report.html`: 当前可视化报告。
- `output/report.html`: 脚本默认生成的报告名；如果重新运行 `write_v5_chinese_report.py` 和 `enhance_v5_report_figures.py`，会生成或更新这个文件。当前版本为了和导出的 PDF 对齐，保留为 `v5_report.html`。

## 8. 如何复现实验

以下命令假设当前目录是：

```powershell
C:\Users\hp\Documents\New project\Rep_games\v5_controllability
```

### 8.1 只生成 trial，不调用 API

```powershell
python .\scripts\run_v5.py --dry-run
```

这会生成：

```text
output/trial_conditions.json
```

### 8.2 设置 API key

不要把 API key 写入脚本或 README。运行前在本地 shell 设置环境变量：

```powershell
$env:MINIMAX_API_KEY="YOUR_API_KEY_HERE"
```

### 8.3 运行实验

默认模型和 endpoint 在 `run_v5.py` 中：

```text
model: MiniMax-M2.7
endpoint: https://lightingtheword.com/v1/chat/completions
temperature: 0.0
```

运行：

```powershell
python .\scripts\run_v5.py --workers 4 --retries 0
```

如果需要更保守地跑：

```powershell
python .\scripts\run_v5.py --workers 1 --retries 0
```

如果只想先测试少数 trial：

```powershell
python .\scripts\run_v5.py --workers 1 --max-calls 3
```

脚本会自动读取已有结果，并只补跑 missing 或 error 的 trial。

### 8.4 分析和生成报告

```powershell
python .\scripts\analyze_v5.py
python .\scripts\write_v5_chinese_report.py
python .\scripts\enhance_v5_report_figures.py
```

当前已整理好的报告在：

```text
output/v5_report.html
```

如果重新运行脚本，默认打开：

```text
output/report.html
```

如果 Windows terminal 中中文显示乱码，通常不影响文件本身；用浏览器打开 HTML 即可。

## 9. 当前 pilot 结果

当前结果来自 MiniMax-M2.7：

```text
total trials: 54
successful parsed trials: 51
JSON parse failures: 3
```

失败项没有重试。正式实验建议增加样本量并设置更稳健的 JSON repair 或 retry 策略。

### 9.1 关键表格

| Partner | Control | N | Trust | WTP | Investment fraction | Predicted low-high | Chosen stake |
|---|---:|---:|---:|---:|---:|---:|---|
| Stable cooperator | controllable | 5/6 | 74.00 | 1.60 | 1.00 | 0.012 | high 4, medium 1 |
| Stable cooperator | fixed high | 6/6 | 51.67 | 1.50 | 1.00 | 0.013 | high 6 |
| Stable cooperator | random | 6/6 | 59.17 | 1.00 | 1.00 | 0.012 | n/a |
| Predictable opportunist | controllable | 6/6 | 61.33 | 2.00 | 1.00 | 0.303 | low 6 |
| Predictable opportunist | fixed high | 5/6 | 33.20 | 0.00 | 0.00 | 0.303 | high 5 |
| Predictable opportunist | random | 5/6 | 44.00 | 1.00 | 0.667 | 0.305 | n/a |
| Random opportunist | controllable | 6/6 | 54.17 | 2.33 | 1.00 | -0.008 | low 1, medium 4, high 1 |
| Random opportunist | fixed high | 6/6 | 44.17 | 1.33 | 0.667 | -0.014 | high 6 |
| Random opportunist | random | 6/6 | 40.83 | 1.00 | 0.778 | -0.014 | n/a |

### 9.2 可控性溢价

```text
controllability premium = WTP_controllable - WTP_fixed_high
```

| Partner | Premium |
|---|---:|
| Stable cooperator | +0.10 |
| Predictable opportunist | +2.00 |
| Random opportunist | +1.00 |

### 9.3 当前最重要的结果

#### Result 1: Predictable opportunist creates a strong control-dependent reversal

可预测机会主义者：

- fixed high stake: WTP = 0, investment fraction = 0
- controllable stake: WTP = 2, investment fraction = 1
- controllable condition 下 6/6 选择 low stake

解释：

模型并不是简单地信任这个对象。它知道高赌注危险，但如果可以自己选择低赌注，它仍然愿意进入互动。

#### Result 2: The model identifies the partner policy

可预测机会主义者的真实结构：

```text
observed low-high gap = 0.305
```

模型预测：

```text
predicted low-high gap = 0.303
```

解释：

模型不仅记住了平均返还 0.40，还识别了条件结构：低赌注时返还高，高赌注时返还低。

#### Result 3: Trust rating and WTP are separable

稳定合作者的 trust rating 通常更高，但可预测机会主义者在 controllable condition 下仍有较高 WTP。

解释：

Trust rating 更像“这个对象是否可靠”。WTP 更像“下一轮机会是否值得付费进入”。V5 的核心是把这两个量分开。

#### Result 4: Random opportunist is an important caveat

随机机会主义者在 controllable condition 下 WTP = 2.33，略高于可预测机会主义者的 2.00。

这不应解释为“随机机会主义者更值得信任”。原因包括：

- 样本量只有 6 个 trial，差异很小。
- 随机组 WTP 为 `1, 2, 4, 2, 2, 3`，被一个高估 trial 拉高。
- 随机组没有低赌注优势，模型多数选择 medium stake，而不是像可预测机会主义者那样 6/6 选择 low stake。
- 这说明 WTP 混合了可控性、收益上限和个别估计异常。

因此正式实验不能只看 WTP 均值，还要看：

- 预测结构是否正确
- controllable condition 下选择了什么 stake
- fixed high condition 下是否退出

## 10. 当前结论

V5 的初步结论是：

> 大语言模型在重复信任博弈中不只是形成一个全局 trust impression。至少在这个 pilot 中，它能从行为历史中提取 partner policy，并在有控制权时把这种 policy 转化为策略性行动。

更具体地说，模型面对可预测机会主义者时表现出一种可解释的策略：

```text
我不完全信任你；
但我知道你在高赌注时才危险；
如果我能选择低赌注，我愿意付费进入；
如果我被迫玩高赌注，我退出。
```

这就是 V5 相比前几版更有故事性的地方：它把“信任”从一个单一评分，拆成了两层：

1. 对 partner 可靠性的整体评价。
2. 对 partner policy 是否可预测、是否可被自己控制的判断。

## 11. 局限和后续改进

### 11.1 样本量太小

当前每个 cell 只有 6 个 histories，且有 3 个 JSON parse failure。这个结果只能作为 pilot。

正式版本建议：

- 每个 cell 至少 30-50 个 histories。
- 多模型重复，如 GPT、Claude、Gemini、MiniMax、Qwen。
- 每个 prompt 多 seed 或多次采样。

### 11.2 WTP 是整数，分辨率较粗

当前 WTP 是 0-10 整数。小样本下，一个 `4` 就会明显拉高均值。

后续可以：

- 改为 0-100 连续价格。
- 或用 binary Becker-DeGroot-Marschak 风格问题：不同价格下是否愿意进入。
- 或把 WTP 改成多档离散选择，降低单点噪声。

### 11.3 Random opportunist control 还不够干净

随机机会主义者在可控条件下也获得了正 premium，说明 control 本身有一般价值。

后续需要区分：

- general control value: 只要能控制 stake，模型就更愿意进入。
- policy-specific control value: 只有当 partner 的坏行为可预测、可规避时，控制权才特别有价值。

一个更干净的设计是加入 `matched random opportunist`：

- 完全匹配每个 history 的平均值和方差。
- 明确让 low / medium / high 的条件均值都接近 0.40。
- 只保留 trial-level noise，不保留 stake-level advantage。

### 11.4 当前 prompt 仍会诱导模型显式预测三种 stake

模型被要求输出低/中/高三种情况下的预测返还。这有利于分析机制，但也可能让模型更主动地比较 stake。

后续可以做两个版本：

- probe version: 要求输出预测，用于解释机制。
- choice-only version: 只要求 WTP 和行动，不要求显式预测，用于检验行为是否自发出现。

如果 choice-only version 中仍出现同样模式，证据会更强。

### 11.5 当前只测模型作为决策者

这个实验目前只让 LLM 自己做决策。后续可以扩展到人机共同决策：

- LLM 向人类建议是否进入。
- 人类看到 LLM 的解释和建议后做最终选择。
- 测人类是否被 LLM 的“可控性叙事”带动，尤其是在低信任但高可控的对象上。

## 12. 一句话给接手的同学

这一系列实验的主线不是简单问“LLM 信不信别人”，而是问：

**当 partner 说的话和做的事不一致时，LLM 能不能把 verbal cue 和 behavioral evidence 分开；并且在此基础上，social trust 和 willingness to pay 是否是两个可分离的决策机制。**

V5 进一步把这个问题推进到策略层面：如果一个 partner 不完全可信，但它的行为规律可预测、风险条件可被规避，模型是否会在低 trust 的情况下仍然愿意付费进入互动。这不是替代前面的主线，而是说明 WTP 可能包含一种不同于社会信任的“可控机会价值”。
