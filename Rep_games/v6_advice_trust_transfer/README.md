# V6: Advice-to-Trust Transfer

V6 解决 V4/V5 暴露出来的一个问题：当 prompt 以完整 history 表格的形式呈现时，模型容易把 partner 当成固定策略机器人，任务变成拟合返还函数，而不是社会信任更新。

这一版把任务改成“同一个 partner 先在信息建议任务中建立声誉，再进入 trust/WTP 决策”。核心问题是：

> 当同一个 partner 的诚实程度和带来的收益被分开操纵时，LLM 最终的 social trust 和 willingness to pay 是否会走向不同机制？

## Design

```text
4 partner types x 2 presentation modes x 8 seeds = 64 runs
```

每个 sequential run 内含 12 个 trial-by-trial advice interactions，最后再做 1 次 trust/WTP probe。

每个 batch run 直接阅读同样结构的 12 轮历史，最后做同样的 trust/WTP probe。

## Partner types

| Partner type | Factual honesty | Recommendation payoff | 关键含义 |
|---|---:|---:|---|
| `honest_beneficial` | 高 | 高 | 说真话，也推荐赢钱的选项 |
| `honest_costly` | 高 | 低 | 说真话，但推荐会输钱的选项 |
| `dishonest_beneficial` | 低 | 高 | 常说假话，但推荐反而能赢钱 |
| `dishonest_costly` | 低 | 低 | 常说假话，也推荐输钱的选项 |

这里的 honesty 指 partner 的事实陈述是否为真，例如 “I checked the left card; it is 7.”

Recommendation payoff 指如果采纳 partner 推荐的那张卡，是否会赢。

## Why this version matters

V4/V5 的 trust game history 容易让模型做数值模式识别。V6 换成 advice task 后，模型面对的是一个社会对象的两个可分离属性：

- 它是否诚实。
- 它是否让我获得收益。

如果模型只做 payoff maximization，它会更喜欢 `dishonest_beneficial`。

如果模型形成 social trust representation，它应更信任 `honest_costly`。

如果 `trust_rating` 主要跟 honesty 走，而 `WTP` 同时受 payoff 影响，就支持我们的主线：

> social trust 和 willingness to pay 是可分离的机制。

## Files

```text
v6_advice_trust_transfer/
  README.md
  conditions/design.json
  prompts/
    sequential_trial_prompt.md
    sequential_final_prompt.md
    batch_final_prompt.md
  scripts/
    run_v6.py
    analyze_v6.py
  output/
    run_conditions.json
    results.json
    summary.json
    report.html
```

## Run

Set the API key in the shell, do not write it into files:

```powershell
$env:MINIMAX_API_KEY="YOUR_KEY"
```

Dry run:

```powershell
python .\scripts\run_v6.py --dry-run
```

Full run:

```powershell
python .\scripts\run_v6.py --workers 16
python .\scripts\analyze_v6.py
```

The script parallelizes across runs. Within each sequential run, the 12 advice trials are kept in order so the model can update from the accumulating interaction history.
