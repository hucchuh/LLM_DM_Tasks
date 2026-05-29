from __future__ import annotations

import html
import json
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
V9B = ROOT.parent / "v9b_instruction_control" / "output" / "summary.json"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return "<p class='muted'>暂无结果。</p>"
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = []
        for key, _ in columns:
            value = row.get(key, "")
            cells.append(f"<td>{html.escape(str(value))}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def condition(summary: dict[str, Any], **filters: Any) -> dict[str, Any]:
    for row in summary["by_condition"]:
        if all(row.get(key) == value for key, value in filters.items()):
            return row
    raise KeyError(filters)


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def gap(high: dict[str, Any], low: dict[str, Any]) -> float:
    return round(float(high["mean_investment"]) - float(low["mean_investment"]), 3)


def make_report() -> None:
    summary = read_json(OUT / "summary.json", {})
    model = read_json(OUT / "model_results.json", {})
    v9b = read_json(V9B, {})

    corr = summary["diagnostic_correlations"]
    previous_payoff_r = corr["investment_vs_previous_payoff"]["r"]
    cumulative_return_r = corr["investment_vs_cumulative_return"]["r"]
    cumulative_truth_r = corr["investment_vs_cumulative_truth"]["r"]

    main_rows = []
    for ret in ["fair_high", "unfair_low"]:
        for instruction in ["standard", "explicit_orthogonality"]:
            high = condition(
                summary,
                block="main_partner_honesty",
                return_policy=ret,
                honesty_level="high",
                orthogonality_instruction=instruction,
                presentation_mode="sequential_trial",
            )
            low = condition(
                summary,
                block="main_partner_honesty",
                return_policy=ret,
                honesty_level="low",
                orthogonality_instruction=instruction,
                presentation_mode="sequential_trial",
            )
            main_rows.append(
                {
                    "return_policy": ret,
                    "instruction": instruction,
                    "high_honesty": high["mean_investment"],
                    "low_honesty": low["mean_investment"],
                    "high_minus_low": gap(high, low),
                    "high_payoff": high["mean_payoff"],
                    "low_payoff": low["mean_payoff"],
                }
            )

    control_rows = [
        {
            "control": "no statement",
            "fair_high": condition(
                summary,
                block="no_statement_control",
                return_policy="fair_high",
                presentation_mode="sequential_trial",
            )["mean_investment"],
            "unfair_low": condition(
                summary,
                block="no_statement_control",
                return_policy="unfair_low",
                presentation_mode="sequential_trial",
            )["mean_investment"],
            "interpretation": "baseline without verifiable statements",
        },
        {
            "control": "irrelevant truth, high",
            "fair_high": condition(
                summary,
                block="irrelevant_truth_control",
                return_policy="fair_high",
                honesty_level="high",
                presentation_mode="sequential_trial",
            )["mean_investment"],
            "unfair_low": condition(
                summary,
                block="irrelevant_truth_control",
                return_policy="unfair_low",
                honesty_level="high",
                presentation_mode="sequential_trial",
            )["mean_investment"],
            "interpretation": "truth is explicitly unrelated to the partner's cooperation",
        },
        {
            "control": "irrelevant truth, low",
            "fair_high": condition(
                summary,
                block="irrelevant_truth_control",
                return_policy="fair_high",
                honesty_level="low",
                presentation_mode="sequential_trial",
            )["mean_investment"],
            "unfair_low": condition(
                summary,
                block="irrelevant_truth_control",
                return_policy="unfair_low",
                honesty_level="low",
                presentation_mode="sequential_trial",
            )["mean_investment"],
            "interpretation": "tests whether factual truth is overgeneralized",
        },
        {
            "control": "cheap talk only",
            "fair_high": condition(
                summary,
                block="cheap_talk_only_control",
                return_policy="fair_high",
                presentation_mode="sequential_trial",
            )["mean_investment"],
            "unfair_low": condition(
                summary,
                block="cheap_talk_only_control",
                return_policy="unfair_low",
                presentation_mode="sequential_trial",
            )["mean_investment"],
            "interpretation": "supportive language without verifiable truth feedback",
        },
    ]

    explicit_diag = model.get("explicit_gap_diagnostics", {})
    paired_rows = explicit_diag.get("paired_seed_differences", [])
    model_1 = model.get("models", {}).get("main_tracker", {}).get("terms", [])
    model_2 = model.get("models", {}).get("main_instruction_categorical", {}).get("terms", [])

    def term(rows: list[dict[str, Any]], name: str) -> dict[str, Any]:
        for row in rows:
            if row["term"] == name:
                return row
        return {"coef": "", "cluster_se": "", "t": "", "p_normal_approx": ""}

    model_key_rows = [
        {"term": "previous payoff", **term(model_1, "previous_payoff_z")},
        {"term": "cumulative return", **term(model_1, "cumulative_return_rate_before_z")},
        {"term": "cumulative truth", **term(model_1, "cumulative_truth_rate_before_z")},
        {"term": "low honesty × explicit orthogonality", **term(model_2, "low_honesty × explicit_orthogonality")},
    ]

    v9b_rows = v9b.get("high_low_gaps", [])
    v9b_sentence = "V9b 尚未生成。"
    if v9b_rows:
        gaps = {row["instruction_type"]: row["high_minus_low"] for row in v9b_rows}
        v9b_sentence = (
            f"natural 条件的 high-low gap 为 {gaps.get('natural')}，"
            f"attention-control 为 {gaps.get('attention_control')}，"
            f"explicit orthogonality 为 {gaps.get('explicit_orthogonality')}。"
            "这说明 V9 的反转不是由 prompt 变长或更正式造成的，而是由“truth 与 return 无因果关系”这条内容造成的。"
        )

    phase_rows = []
    trial_rows = read_json(OUT / "results.json", [])
    explicit_trials = []
    for run in trial_rows:
        if run.get("error"):
            continue
        if run.get("block") != "main_partner_honesty":
            continue
        if run.get("return_policy") != "fair_high":
            continue
        if run.get("orthogonality_instruction") != "explicit_orthogonality":
            continue
        if run.get("presentation_mode") != "sequential_trial":
            continue
        for trial in run.get("trial_results", []):
            explicit_trials.append(
                {
                    "honesty": run["honesty_level"],
                    "trial": int(trial["trial"]),
                    "investment": int(trial["investment"]),
                    "payoff": int(trial["payoff"]),
                }
            )
    for phase, lo, hi in [("前 6 轮", 1, 6), ("中间 6 轮", 7, 12), ("后 6 轮", 13, 18)]:
        high_vals = [row["investment"] for row in explicit_trials if row["honesty"] == "high" and lo <= row["trial"] <= hi]
        low_vals = [row["investment"] for row in explicit_trials if row["honesty"] == "low" and lo <= row["trial"] <= hi]
        if high_vals and low_vals:
            phase_rows.append(
                {
                    "phase": phase,
                    "high_honesty": round(mean(high_vals), 3),
                    "low_honesty": round(mean(low_vals), 3),
                    "low_minus_high": round(mean(low_vals) - mean(high_vals), 3),
                }
            )

    prompt_excerpt = """Important rule: the truth or falsehood of the pre-decision statement has no causal relation to the partner's return policy. Return behavior is generated independently of statement truth."""

    report = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V9 学术报告</title>
  <style>
    :root {{
      --ink: #152033;
      --muted: #5d6a78;
      --line: #dbe3eb;
      --soft: #f3f6f9;
      --blue: #18395d;
      --accent: #9b3d35;
    }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", sans-serif;
      color: var(--ink);
      background: #f7f8fa;
    }}
    header {{
      background: #17375e;
      color: white;
      padding: 56px 7vw 64px;
    }}
    header p {{
      max-width: 1040px;
      color: #e8f0f7;
      font-size: 22px;
      line-height: 1.7;
    }}
    h1 {{
      margin: 0 0 18px;
      font-size: clamp(38px, 6vw, 68px);
      line-height: 1.08;
      letter-spacing: 0;
    }}
    h2 {{
      font-size: 30px;
      margin: 0 0 18px;
      letter-spacing: 0;
    }}
    h3 {{
      font-size: 22px;
      margin: 28px 0 10px;
    }}
    p, li {{
      font-size: 18px;
      line-height: 1.78;
    }}
    section {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 44px 7vw;
      background: white;
      border-bottom: 1px solid var(--line);
    }}
    .abstract {{
      font-size: 20px;
      background: #fbfcfd;
      border-left: 5px solid var(--blue);
      padding: 18px 22px;
    }}
    .claim {{
      background: #f7f2ef;
      border-left: 5px solid var(--accent);
      padding: 18px 22px;
      font-size: 19px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px 20px;
      background: #fff;
    }}
    .card strong {{
      display: block;
      font-size: 26px;
      margin-bottom: 4px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 18px 0 26px;
      font-size: 15px;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #eef3f8;
    }}
    code {{
      background: #eef2f6;
      padding: 2px 6px;
      border-radius: 5px;
    }}
    pre {{
      white-space: pre-wrap;
      background: var(--soft);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px 18px;
      font-size: 15px;
      line-height: 1.55;
    }}
    figure {{
      margin: 28px 0;
    }}
    figure img {{
      width: 100%;
      max-width: 960px;
      border: 1px solid var(--line);
      border-radius: 8px;
      display: block;
    }}
    figcaption, .muted {{
      color: var(--muted);
      font-size: 15px;
    }}
    @media (max-width: 860px) {{
      .grid {{ grid-template-columns: 1fr; }}
      section {{ padding: 34px 6vw; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>V9：当“诚实”被声明为无关时，模型还会如何投资？</h1>
    <p>一个关于大语言模型在重复信任互动中如何使用诚实性、收益反馈和因果说明的 API 实验报告。</p>
  </header>

  <section>
    <h2>摘要</h2>
    <p class="abstract">V8 发现，在返还政策匹配时，低诚实对象会让模型投资更少。V9 将这一现象扩展为更严格的主实验：同时操纵 partner 的事实诚实性、真实返还政策、是否给出显式因果说明，并加入 no-statement、irrelevant-truth 和 cheap-talk-only controls。MiniMax-M2.7 的完整 sequential 条件共完成 96 runs、1728 个 trial-level decisions。结果显示，模型最稳定地追踪上一轮收益和累计返还，而不是累计真实率；但在自然语境下，高诚实对象仍获得更高投资。最有意思的是，当 prompt 明确说明“陈述真假与返还策略无因果关系”时，fair/high return 中低诚实对象反而得到更高投资。V9b attention-control 进一步表明，这一反转并非由 prompt 变长或更正式造成，而更可能来自显式因果说明本身改变了模型的任务表征。</p>
  </section>

  <section>
    <h2>研究问题</h2>
    <p>这个实验不再笼统地问“模型是否信任诚实的人”。更准确的问题是：当一个对象的陈述真假、真实返还收益和任务规则被拆开时，模型的逐轮投资究竟由什么驱动？</p>
    <p>V9 关心三个层次。第一，模型是否主要追踪实际收益。第二，在没有额外说明的自然互动中，事实诚实性是否仍会被当作合作性的社会线索。第三，当任务明确声明诚实性与返还无因果关系时，模型是否会改变对诚实性线索的使用。</p>
    <p class="claim">当前最合适的故事不是“模型稳定奖励诚实”，也不是“模型完全只看收益”。更好的表述是：模型会在 prompt 语境中构建一个局部任务模型。自然语境下，可核验诚实性会被用作社会合作线索；显式因果说明则可能把模型从社会推断拉向收益探索。</p>
  </section>

  <section>
    <h2>实验设计</h2>
    <p>主实验使用逐轮重复投资任务。每一轮模型有 10 个 token，可选择向 Alex 投资 0 到 10 个整数 token。投资会被三倍交给 Alex，Alex 按预设返还比例返还。模型随后看到本轮投资、返还、payoff，以及陈述是否与实际值相符。</p>
    <div class="grid">
      <div class="card"><strong>96</strong><span>successful sequential runs</span></div>
      <div class="card"><strong>1728</strong><span>trial-level decisions</span></div>
      <div class="card"><strong>18</strong><span>trials per run</span></div>
    </div>
    <h3>主操纵</h3>
    <p>事实诚实性有两档：高诚实为 18 轮中 14 轮陈述为真，低诚实为 18 轮中 4 轮陈述为真。返还政策有两档：fair/high 的平均返还率为 0.60，unfair/low 的平均返还率为 0.20。instruction 有两档：standard 不说明陈述真假是否与返还有关；explicit orthogonality 明确说明二者没有因果关系。</p>
    <pre>{html.escape(prompt_excerpt)}</pre>
    <h3>Controls</h3>
    <p>No-statement control 用来估计没有可核验陈述时的 baseline。Irrelevant-truth control 将真假反馈明确设为与合作无关，用来检验模型是否把任何真假反馈都泛化为合作信号。Cheap-talk-only control 只有支持性语言、没有可核验真假反馈，用来估计漂亮话本身的作用。</p>
  </section>

  <section>
    <h2>因变量与分析</h2>
    <p>主因变量是每轮 <code>investment</code>。payoff 定义为：</p>
    <pre>payoff_t = 10 - investment_t + returned_tokens_t</pre>
    <p>需要特别注意：V9 匹配的是 <code>return_rate_t</code>，不是 realized payoff。只要模型自己的投资额不同，实际得到的 payoff 就会不同。因此，早期探索会影响后续证据；这也是解释 explicit 条件反转时必须保留的边界。</p>
  </section>

  <section>
    <h2>主要结果一：收益反馈主导投资</h2>
    <p>在完整 sequential 数据中，investment 与上一轮 payoff 的相关为 {previous_payoff_r}，与累计返还率的相关为 {cumulative_return_r}，与累计真实率的相关为 {cumulative_truth_r}。trial-level OLS 也给出同样方向：上一轮 payoff 是最稳定的 predictor。</p>
    {table(model_key_rows, [("term", "term"), ("coef", "coef"), ("cluster_se", "cluster SE"), ("t", "t"), ("p_normal_approx", "p")])}
  </section>

  <section>
    <h2>主要结果二：自然语境下仍有诚实性效应</h2>
    <p>在 standard 条件下，V9 与 V8 的方向一致：高诚实对象得到更高投资。这个结果不是压倒性的主效应，但说明 V8 的现象没有消失。</p>
    {table(main_rows, [("return_policy", "return policy"), ("instruction", "instruction"), ("high_honesty", "high honesty investment"), ("low_honesty", "low honesty investment"), ("high_minus_low", "high-low gap"), ("high_payoff", "high payoff"), ("low_payoff", "low payoff")])}
    <figure>
      <img src="figures/main_investment_by_honesty_return.png" alt="Main investment by honesty and return policy">
      <figcaption>主实验条件的平均投资。注意：explicit orthogonality 在 fair/high return 中产生了反向 gap。</figcaption>
    </figure>
  </section>

  <section>
    <h2>主要结果三：explicit orthogonality 不是中性说明</h2>
    <p>最值得深挖的结果出现在 fair/high return 条件。standard 条件下 high-low gap 为 +{fmt(main_rows[0]["high_minus_low"])}；explicit orthogonality 条件下 high-low gap 变为 {fmt(main_rows[1]["high_minus_low"])}。换言之，明确说明“陈述真假与返还无关”后，低诚实对象反而获得更高投资。</p>
    <p>这个结果不应被解释为“低诚实更可信”。更谨慎的解释是：显式因果说明取消了低诚实的社会惩罚，使模型更倾向于把互动对象看作一个需要通过投资来学习的收益过程。若低诚实条件更早开始探索，positive payoff 会被迅速放大；若高诚实条件早期持续投 0，则模型无法获得返还证据，形成 no-learning trap。</p>
    <p>在 fair/high + explicit 条件下，6 个 paired seeds 全部是 low honesty 投资更高；平均 low-minus-high 为 {explicit_diag.get("mean_low_minus_high")}，简单 sign test 双侧 p = {explicit_diag.get("sign_test_p_two_sided")}。</p>
    {table(paired_rows, [("seed", "seed"), ("high_mean", "high mean"), ("low_mean", "low mean"), ("low_minus_high", "low-high"), ("early_low_minus_high", "early low-high"), ("late_low_minus_high", "late low-high"), ("high_zero_trials", "high zero trials"), ("low_zero_trials", "low zero trials")])}
  </section>

  <section>
    <h2>意外结果：低诚实在 explicit 条件下更早探索</h2>
    <p>更细地看时间轨迹，explicit orthogonality 不只是改变最终平均投资。它在早期就改变了模型是否愿意探索。fair/high + explicit 条件中，低诚实组前 6 轮平均投资为 {phase_rows[0]["low_honesty"] if phase_rows else ""}，高诚实组只有 {phase_rows[0]["high_honesty"] if phase_rows else ""}。这个早期差异随后被收益反馈放大：一旦低诚实组的小额或中额投资获得正收益，模型会迅速加码；而高诚实组如果早期持续投 0，就无法观察到 partner 在真实投资下的返还表现。</p>
    {table(phase_rows, [("phase", "phase"), ("high_honesty", "high honesty investment"), ("low_honesty", "low honesty investment"), ("low_minus_high", "low-high")])}
    <p>这个结果的理论价值在于，它提示 explicit causal instruction 可能不只是“纠正”honesty bias。它还可能改变模型的探索态度：当模型被告知不诚实与返还无关时，低诚实不再是需要回避的社会风险，反而把任务推向“通过投资测试收益规则”的探索模式。</p>
    <p>因此，一个更有意思的机制假设是：<strong>orthogonalized dishonesty can increase exploration</strong>。也就是说，在明确的因果说明下，不诚实不再压低投资，反而可能提高早期探索和风险暴露。这个解释目前仍需谨慎，因为早期探索一旦产生正收益，会通过 payoff feedback 自我放大；但正因为如此，它值得成为下一版实验的核心对象。</p>
  </section>

  <section>
    <h2>Controls：排除几个朴素解释</h2>
    <p>Controls 的结果说明，这不是简单的“看到真话就多投”，也不是漂亮话可以轻易覆盖收益反馈。No-statement 条件下模型仍区分 fair/high 和 unfair/low；irrelevant truth 没有形成与 partner honesty 相同的稳定模式；cheap talk 可以抬高 fair/high 条件下的投资，但在低返还条件下仍明显降低。</p>
    {table(control_rows, [("control", "control"), ("fair_high", "fair/high investment"), ("unfair_low", "unfair/low investment"), ("interpretation", "interpretation")])}
    <figure>
      <img src="figures/control_investment.png" alt="Control investment">
      <figcaption>控制条件的平均投资。真实返还政策仍是最强的信息源。</figcaption>
    </figure>
  </section>

  <section>
    <h2>V9b：检验是不是 prompt 变长导致反转</h2>
    <p>为了检验 explicit 反转是否只是因为多了一段正式说明，我们补做了 V9b attention-control。Attention-control 同样加入一段正式说明，但不提 truth 与 return 的因果关系。</p>
    <p>{html.escape(v9b_sentence)}</p>
    {table(v9b_rows, [("instruction_type", "instruction"), ("high_investment", "high investment"), ("low_investment", "low investment"), ("high_minus_low", "high-low gap"), ("high_payoff", "high payoff"), ("low_payoff", "low payoff")])}
    <p>这使当前解释更清楚：explicit 反转不是 prompt 更长、语气更正式或额外注意力造成的，而是由因果说明本身改变了模型如何使用诚实性线索。</p>
  </section>

  <section>
    <h2>目前的理论解释</h2>
    <p>V9 支持一个较强但仍需验证的机制假设：模型会根据任务说明调节诚实性线索的因果地位。在自然语境下，诚实性被当作合作倾向的社会证据；在 explicit orthogonality 下，诚实性被声明为非诊断性，模型转而依赖收益探索。低诚实对象在这种语境下可能不再触发回避，反而更像一个“说话不准但收益规则待测试”的对象。这个解释能同时容纳两个现象：自然语境下的 honesty bias，以及正交说明后的 early exploration increase。</p>
    <p>可以用一个 causal-gated reinforcement learning model 来形式化这个想法。模型同时维护预期返还率 <code>μ_t</code>、诚实信念 <code>h_t</code>、诚实性是否诊断返还的 gate <code>d_t</code>、探索 bonus、风险厌恶和 choice temperature。关键参数是 <code>β_X</code>：在 explicit 条件下，低诚实是否额外提高探索倾向。</p>
  </section>

  <section>
    <h2>限制与下一步</h2>
    <p>当前结果仍有三个限制。第一，只完整解释了 sequential trial-by-trial；evidence-only 在 MiniMax-M2.7 上容易诱发长篇推理，没有纳入正式结论。第二，V9 控制了返还政策，但 realized payoff 会被模型自己的投资路径影响。第三，explicit 反转可能混有 early exploration 和 no-learning trap。</p>
    <p>下一步不应只是加大样本，而应做 forced-observation 或 forced-exploration 版本。最简单的设计是：前 3 轮让 high/low honesty 两组获得同等 payoff evidence，例如固定投资 5，或展示上一位参与者投资 10 后 Alex 的返还；之后只分析第 4 轮以后的自由投资。如果 explicit-low-honesty 优势消失，说明 V9 的反转主要来自早期探索差异；如果仍然存在，才更支持 explicit causal framing 改变了低诚实对象下的 exploration 或 risk attitude。</p>
  </section>

  <section>
    <h2>文件</h2>
    <p>数据文件：<code>output/trial_level_data.csv</code>；模型结果：<code>output/model_results.json</code>；V9b 追证报告：<code>../v9b_instruction_control/output/report.html</code>。</p>
  </section>
</body>
</html>
"""

    (OUT / "report.html").write_text(report, encoding="utf-8")
    print(f"Wrote {OUT / 'report.html'}")


if __name__ == "__main__":
    make_report()
