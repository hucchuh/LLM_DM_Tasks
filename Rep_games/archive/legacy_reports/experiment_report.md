# Repeated Trust Game 实验报告

## 1. 研究问题

这组 pilot 想回答一个很具体的问题：

> 大模型在 repeated trust game 中形成信任判断时，主要追踪对方的实际行为收益，还是会进一步表征对方在不同情境下的行为模式？

我们把这个问题拆成两步：

1. **V1:** 当 partner type 的平均返还率自然不同，`trust_rating` 是否主要跟随 `observed return`？
2. **V2:** 当所有 partner type 的 `observed return` 被控制为相同值时，模型还能不能区分不同的 return pattern？

核心结论先放在前面：

> V1 显示 `trust_rating` 与 `observed return` 高度相关。V2 进一步显示，在平均返还率完全相同的情况下，模型仍然会根据 stake-specific return 和 recent trend 调整 `predicted return` 与投资行为。因此，模型不是只看语言，也不只是简单追踪总体平均收益；但目前 V2 的 probe 太直接，下一步需要用更有噪声、更隐蔽的 held-out prediction 来检验是否真的形成了 robust partner policy representation。

## 2. 实验协议

两个实验都使用 repeated investment game：

- 每轮模型面对同一个 partner。
- 模型拥有一定数量 tokens，可以选择投资。
- 投资金额会被 tripled 后交给 partner。
- partner 决定返还多少 tokens。
- 模型目标是最大化自身 tokens。

调用设置：

- Model: `MiniMax-M2.7`
- Endpoint: MiniMax Anthropic-compatible endpoint
- 输出格式: JSON
- V1 成功调用: `23 / 24`
- V2 成功调用: `36 / 36`

主要因变量：

- `trust_rating`: 模型对 partner 的总体信任评分，0-100。
- `predicted return`: 模型预测 partner 会返还 tripled investment 的比例。
- `investment`: 模型下一轮愿意投资多少。
- V2 中额外看 `high-low prediction gap`: predicted high-stake return minus predicted low-stake return。

## 3. V1: 自然差异条件

### 3.1 实验调节

V1 使用 6 类 partner type。不同类型同时改变语言线索和实际返还行为：

| Partner type | 操纵含义 |
|---|---|
| `honest_cooperator` | 友善承诺 + 稳定公平返还 |
| `charming_under_returner` | 友善语言 + 偏低返还 |
| `cautious_reliable` | 语言谨慎 + 稳定公平返还 |
| `strategic_opportunist` | 低赌注较合作，高赌注剥削 |
| `noisy_repairing` | 偶尔低返还，但后续真实补偿 |
| `apology_only_exploiter` | 低返还 + 道歉，但没有真实补偿 |

V1 的重点不是严格控制平均返还率，而是先看模型在自然差异条件下是否主要依赖行为证据。

### 3.2 V1 结果

| Partner type | N | Investment next | Trust rating | Predicted return | Observed return | High-stake return |
|---|---:|---:|---:|---:|---:|---:|
| `honest_cooperator` | 4/4 | 10.00 | 78.25 | 0.508 | 0.503 | 0.506 |
| `charming_under_returner` | 4/4 | 4.50 | 38.25 | 0.338 | 0.331 | 0.326 |
| `cautious_reliable` | 4/4 | 10.00 | 70.25 | 0.502 | 0.502 | 0.499 |
| `strategic_opportunist` | 4/4 | 8.50 | 51.00 | 0.480 | 0.400 | 0.236 |
| `noisy_repairing` | 4/4 | 10.00 | 68.75 | 0.497 | 0.481 | 0.481 |
| `apology_only_exploiter` | 3/4 | 1.67 | 27.67 | 0.287 | 0.283 | 0.272 |

V1 中最直接的结果是 `trust_rating` 与 `observed return` 高度相关：

- Trial level: `r = 0.878`, `n = 23`
- Partner-type mean level: `r = 0.992`, `n = 6`

图见：

- `Rep_games/output/figures/trust_vs_average_return_trials.png`
- `Rep_games/output/figures/trust_vs_average_return_by_type.png`

### 3.3 V1 解释

V1 支持一个清楚结论：

> 模型并不是简单被 friendly language、promise 或 apology 牵引；它的 `trust_rating` 很大程度跟随 partner 实际返还行为。

但是 V1 不能说明模型是否形成了结构化 partner policy。因为在 V1 中，不同 partner type 的 `observed return` 本身就不同。模型可能只是把所有历史行为压缩成一个 average return，然后用这个 average return 生成 `trust_rating`。

因此需要 V2。

## 4. V2: Average Return Control

### 4.1 实验调节

V2 的关键控制是：

```text
所有 partner type 的 observed return 都固定为 0.40
```

也就是说，V2 不再让平均返还率解释差异，而是只改变返还结构。

| Partner type | Observed return | Return pattern |
|---|---:|---|
| `honest_cooperator` | 0.40 | 稳定中等返还 + warm cooperative language |
| `cautious_reliable` | 0.40 | 稳定中等返还 + cautious neutral language |
| `strategic_opportunist` | 0.40 | low stake 高返还，high stake 低返还 |
| `strategic_opportunist_mirror` | 0.40 | low stake 低返还，high stake 高返还 |
| `noisy_repairing` | 0.40 | 前期低返还，后期真实补偿 |
| `apology_only_exploiter` | 0.40 | 前期高返还，后期逐步恶化 |

说明：`strategic_opportunist_mirror` 是 V2 新加的反向控制条件，用来检验模型是否真的区分 high-stake 和 low-stake 的方向性。

### 4.2 V2 结果

| Partner type | N | Trust rating | Observed return | Observed low | Observed high | Predicted low | Predicted high | High-low prediction gap |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `honest_cooperator` | 6/6 | 57.17 | 0.40 | 0.40 | 0.40 | 0.40 | 0.40 | 0.00 |
| `cautious_reliable` | 6/6 | 73.33 | 0.40 | 0.40 | 0.40 | 0.40 | 0.40 | 0.00 |
| `strategic_opportunist` | 6/6 | 49.17 | 0.40 | 0.55 | 0.25 | 0.55 | 0.25 | -0.30 |
| `strategic_opportunist_mirror` | 6/6 | 77.50 | 0.40 | 0.25 | 0.55 | 0.25 | 0.55 | +0.30 |
| `noisy_repairing` | 6/6 | 59.50 | 0.40 | 0.35 | 0.483 | 0.558 | 0.633 | +0.075 |
| `apology_only_exploiter` | 6/6 | 35.00 | 0.40 | 0.45 | 0.317 | 0.227 | 0.198 | -0.028 |

图见：

- `Rep_games/v2_average_control/output/figures/global_trust_by_condition.png`
- `Rep_games/v2_average_control/output/figures/conditional_return_predictions.png`
- `Rep_games/v2_average_control/output/figures/predicted_high_minus_low_by_condition.png`

### 4.3 V2 trend 说明

**图 1: Trust rating by partner type**

虽然所有 partner type 的 `observed return` 都是 0.40，`trust_rating` 仍然从 35.00 到 77.50 大幅变化。这说明 `trust_rating` 不只是 average return 的线性变换。它还会受到 recent trend、stake-specific return 以及 partner pattern 的影响。

**图 2: Predicted return by stake**

这是 V2 最关键的图。模型对 `strategic_opportunist` 给出：

```text
predicted low = 0.55
predicted high = 0.25
```

对 `strategic_opportunist_mirror` 给出：

```text
predicted low = 0.25
predicted high = 0.55
```

这说明在明确询问 low / medium / high stake 时，模型能够读出 stake-specific return pattern。

**图 3: High-low prediction gap**

这个指标总结模型是否区分 high stake 和 low stake：

- `strategic_opportunist`: gap = -0.30，说明模型预测 high stake 明显更差。
- `strategic_opportunist_mirror`: gap = +0.30，说明模型预测 high stake 明显更好。
- 稳定型 partner: gap = 0，说明模型预测不同 stake 下没有差别。

### 4.4 V2 解释

V2 修正了 V1 的简单解释。

V1 看起来像是：

```text
trust_rating ≈ f(observed average return)
```

但 V2 显示：

```text
当 observed average return 被控制住后，模型仍然能使用 return structure。
```

因此更准确的解释是：

> 模型会使用 revealed returns 形成 trust judgment；但它并不一定只压缩成平均收益。在明确 probe 下，它可以提取 stake-specific 和 trend-based return pattern。

不过，这个结论需要谨慎。V2 的 probe 直接问了 low / medium / high stake 的 predicted return，因此模型可能只是做了 stake-specific average extraction，而不一定说明它真正形成了复杂的社会策略模型。

## 5. 总体结论

两轮实验合起来，当前最稳的 story 是：

1. LLM 的信任评分不是主要由 cheap talk 驱动，而是高度依赖实际返还行为。
2. 在自然差异条件下，`trust_rating` 与 `observed return` 几乎线性相关。
3. 当 average return 被控制后，模型仍然能区分不同的 return pattern，尤其是 `strategic_opportunist` 与 `strategic_opportunist_mirror`。
4. 目前最好的 probe 不是 global `trust_rating`，而是 conditional `predicted return`。

一句话版本：

> LLM trust updating is strongly behavior-based, but not reducible to average payoff; under explicit probing, the model can recover stake-dependent return patterns.

## 6. 当前局限

1. **V2 任务过于干净。**  
   `strategic_opportunist` 的 low/high pattern 非常明显，模型可能只是读取条件均值。

2. **Probe 太直接。**  
   直接问 low / medium / high stake，等于提示模型 stake 是关键变量。

3. **样本量仍然是 pilot level。**  
   V1 每类约 4 个 trial，V2 每类 6 个 trial，只能看趋势。

4. **只跑了一个模型。**  
   目前结果不能说明这是 LLM 普遍规律，还是 MiniMax-M2.7 的特定行为。

5. **还没有和简单统计模型比较。**  
   下一步必须比较 overall mean、stake-specific mean、recency-weighted mean、message-only model 等 baseline。

## 7. Next Step

### 7.1 V3: Noisy Policy Inference

把 V2 的 return pattern 加噪声，避免模型直接抄条件均值。

例如：

- `strategic_opportunist`: low stake around 0.50-0.60，high stake around 0.18-0.32。
- `strategic_opportunist_mirror`: low stake around 0.18-0.32，high stake around 0.50-0.60。
- 保持 overall average return 相同。

核心问题：

> 在有噪声、不完全证据的条件下，模型是否仍然能恢复 partner type？

### 7.2 Held-out Prediction

不要让模型看完整 8 轮后直接解释。改成：

1. 给模型前 6 轮。
2. 让它预测第 7/8 轮不同 stake 下的 return。
3. 和真实生成规则比较。

这样可以区分：

- 回读历史 pattern；
- 预测未见 trial；
- 泛化 partner policy。

### 7.3 Baseline Model Comparison

把 LLM 输出与简单模型比较：

| Baseline | 解释 |
|---|---|
| Overall mean | 只看总体平均返还 |
| Stake-specific mean | 分别计算 low / medium / high 平均返还 |
| Recency-weighted mean | 更重视最近几轮 |
| Message-only model | 只根据语言类型预测 |
| Hybrid model | observed return + stake + recency + message |

如果 LLM 只等同于 stake-specific mean，那么 story 会比较弱。  
如果 LLM 在 noisy / sparse evidence 下优于简单均值模型，或者出现系统偏差，就更值得发展。

### 7.4 Multi-model Replication

下一步至少比较：

- MiniMax-M2.7
- GPT 系列
- Claude 系列
- Gemini 系列
- 开源模型，如 Qwen / Llama

关键看：

- 是否都 behavior-based；
- 是否都能识别 stake-dependent pattern；
- 是否在 apology / repair / recent deterioration 上表现不同。

### 7.5 Human Comparison

如果想往更高层次期刊推进，需要加入人类对照：

> 人类和 LLM 是否都用 observed return 更新 trust？在人类能识别策略性 partner 的条件下，LLM 是否也能识别？

这会把故事从 “LLM behavioral probing” 推到 “human-like social inference vs machine shortcut”。

