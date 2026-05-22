from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
SUMMARY = OUT / "summary.json"
RESULTS = OUT / "results.json"
REPORT = OUT / "v6_report.html"
FIG = OUT / "figures_cn"

PARTNER_ORDER = ["honest_beneficial", "honest_costly", "dishonest_beneficial", "dishonest_costly"]
MODE_ORDER = ["sequential", "batch"]

PARTNER_LABELS = {
    "honest_beneficial": "诚实且有帮助",
    "honest_costly": "诚实但有代价",
    "dishonest_beneficial": "不诚实但有帮助",
    "dishonest_costly": "不诚实且有代价",
}

MODE_LABELS = {"sequential": "逐轮互动", "batch": "一次性历史"}
MODE_COLORS = {"sequential": "#0f766e", "batch": "#64748b"}
PARTNER_COLORS = {
    "honest_beneficial": "#235789",
    "honest_costly": "#7c3aed",
    "dishonest_beneficial": "#d97706",
    "dishonest_costly": "#b42318",
}


def setup_font() -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["savefig.dpi"] = 220


def fmt(value, digits: int = 2) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def honesty_payoff_stats() -> dict[str, object]:
    rows = json.loads(RESULTS.read_text(encoding="utf-8"))
    successful = [row for row in rows if not row.get("error")]
    seq_high_honesty = []
    seq_low_honesty = []
    metric_rows = []

    for row in successful:
        metrics = row.get("metrics") or {}
        if row["presentation_mode"] == "sequential" and metrics.get("actual_choice_win_rate") is not None:
            target = seq_high_honesty if row["target_honesty_rate"] > 0.5 else seq_low_honesty
            target.append(float(metrics["actual_choice_win_rate"]))

        needed = ["perceived_honesty", "perceived_helpfulness", "willingness_to_pay", "investment", "expected_return_tokens"]
        if all(metrics.get(key) is not None for key in needed):
            metric_rows.append(metrics)

    correlations: dict[str, dict[str, float | None]] = {}
    for outcome in ["willingness_to_pay", "investment", "expected_return_tokens"]:
        correlations[outcome] = {
            "honesty": corr([float(row["perceived_honesty"]) for row in metric_rows], [float(row[outcome]) for row in metric_rows]),
            "helpfulness": corr([float(row["perceived_helpfulness"]) for row in metric_rows], [float(row[outcome]) for row in metric_rows]),
        }

    return {
        "seq_high_honesty_choice_win": mean(seq_high_honesty),
        "seq_low_honesty_choice_win": mean(seq_low_honesty),
        "seq_high_honesty_n": len(seq_high_honesty),
        "seq_low_honesty_n": len(seq_low_honesty),
        "correlations": correlations,
    }


def cell(summary: dict, partner: str, mode: str) -> dict:
    return summary["by_partner_mode"].get(f"{partner} / {mode}", {})


def partner(summary: dict, partner_type: str) -> dict:
    return summary["by_partner"].get(partner_type, {})


def grouped_bar(summary: dict, metric: str, ylabel: str, title: str, filename: str, ylim: tuple[float, float]) -> None:
    x = list(range(len(PARTNER_ORDER)))
    width = 0.34
    fig, ax = plt.subplots(figsize=(14.5, 8.0))
    for i, mode in enumerate(MODE_ORDER):
        values = [cell(summary, p, mode).get(metric) or 0 for p in PARTNER_ORDER]
        positions = [pos + (i - 0.5) * width for pos in x]
        bars = ax.bar(positions, values, width=width, label=MODE_LABELS[mode], color=MODE_COLORS[mode])
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + (ylim[1] - ylim[0]) * 0.015,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=14,
                fontweight="semibold",
            )
    ax.set_xticks(x)
    ax.set_xticklabels([PARTNER_LABELS[p] for p in PARTNER_ORDER], fontsize=15)
    ax.set_ylabel(ylabel, fontsize=17)
    ax.set_title(title, fontsize=23, fontweight="bold", pad=18)
    ax.set_ylim(*ylim)
    ax.tick_params(axis="y", labelsize=14)
    ax.legend(ncols=2, loc="upper center", bbox_to_anchor=(0.5, 1.02), frameon=False, fontsize=15)
    ax.grid(axis="y", alpha=0.28)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / filename, bbox_inches="tight")
    plt.close(fig)


def critical_contrast(summary: dict) -> None:
    metrics = [
        ("perceived_honesty", "感知诚实", 100),
        ("perceived_helpfulness", "感知有帮助", 100),
        ("trust_rating", "信任评分", 100),
        ("willingness_to_pay", "WTP×10", 10),
        ("investment", "投资×10", 10),
    ]
    partners = ["honest_costly", "dishonest_beneficial"]
    x = list(range(len(metrics)))
    width = 0.34
    fig, ax = plt.subplots(figsize=(13.5, 7.6))
    for i, p in enumerate(partners):
        values = []
        for key, _, scale in metrics:
            value = partner(summary, p).get(key) or 0
            if scale == 10:
                value *= 10
            values.append(value)
        bars = ax.bar([pos + (i - 0.5) * width for pos in x], values, width=width, label=PARTNER_LABELS[p], color=PARTNER_COLORS[p])
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 1.3, f"{value:.1f}", ha="center", va="bottom", fontsize=13, fontweight="semibold")
    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label, _ in metrics], fontsize=15)
    ax.set_ylabel("统一到 0-100 量尺", fontsize=17)
    ax.set_ylim(0, 105)
    ax.set_title("图5：关键对照显示模型知道谁诚实，但行动更看谁有用", fontsize=23, fontweight="bold", pad=18)
    ax.legend(ncols=2, loc="upper center", bbox_to_anchor=(0.5, 1.02), frameon=False, fontsize=15)
    ax.grid(axis="y", alpha=0.28)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "v6_critical_contrast_cn.png", bbox_inches="tight")
    plt.close(fig)


def make_figures(summary: dict) -> None:
    setup_font()
    FIG.mkdir(exist_ok=True)
    grouped_bar(summary, "perceived_honesty", "感知诚实程度（0-100）", "图1：模型能识别 partner 是否诚实", "v6_perceived_honesty_cn.png", (0, 100))
    grouped_bar(summary, "perceived_helpfulness", "感知有帮助程度（0-100）", "图2：模型也能识别 partner 是否让自己获益", "v6_perceived_helpfulness_cn.png", (0, 100))
    grouped_bar(summary, "trust_rating", "信任评分（0-100）", "图3：最终信任并不只跟诚实走，也明显受收益牵引", "v6_trust_cn.png", (0, 100))
    grouped_bar(summary, "willingness_to_pay", "愿意支付的入场费 WTP（0-10）", "图4：WTP 更像进入机会的价格，强烈跟收益/有帮助程度走", "v6_wtp_cn.png", (0, 7.5))
    critical_contrast(summary)


def result_rows(summary: dict) -> str:
    rows = []
    for p in PARTNER_ORDER:
        item = partner(summary, p)
        rows.append(
            "<tr>"
            f"<td>{PARTNER_LABELS[p]}</td>"
            f"<td class='num'>{item.get('n_success', 0)}/{item.get('n_total', 0)}</td>"
            f"<td class='num'>{fmt(item.get('observed_honesty_rate'))}</td>"
            f"<td class='num'>{fmt(item.get('observed_recommendation_win_rate'))}</td>"
            f"<td class='num'>{fmt(item.get('perceived_honesty'))}</td>"
            f"<td class='num'>{fmt(item.get('perceived_helpfulness'))}</td>"
            f"<td class='num'>{fmt(item.get('trust_rating'))}</td>"
            f"<td class='num'>{fmt(item.get('willingness_to_pay'))}</td>"
            f"<td class='num'>{fmt(item.get('investment'))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def mode_rows(summary: dict) -> str:
    rows = []
    for p in PARTNER_ORDER:
        for mode in MODE_ORDER:
            item = cell(summary, p, mode)
            rows.append(
                "<tr>"
                f"<td>{PARTNER_LABELS[p]}</td>"
                f"<td>{MODE_LABELS[mode]}</td>"
                f"<td class='num'>{item.get('n_success', 0)}/{item.get('n_total', 0)}</td>"
                f"<td class='num'>{fmt(item.get('perceived_honesty'))}</td>"
                f"<td class='num'>{fmt(item.get('perceived_helpfulness'))}</td>"
                f"<td class='num'>{fmt(item.get('trust_rating'))}</td>"
                f"<td class='num'>{fmt(item.get('willingness_to_pay'))}</td>"
                f"<td class='num'>{fmt(item.get('investment'))}</td>"
                f"<td class='num'>{fmt(item.get('follow_recommendation_rate'))}</td>"
                f"<td class='num'>{fmt(item.get('actual_choice_win_rate'))}</td>"
                "</tr>"
            )
    return "\n".join(rows)


def write_report(summary: dict, payoff_stats: dict[str, object]) -> None:
    hb = partner(summary, "honest_beneficial")
    hc = partner(summary, "honest_costly")
    db = partner(summary, "dishonest_beneficial")
    dc = partner(summary, "dishonest_costly")
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V6：诚实声誉能否迁移到信任与付费决策？</title>
  <style>
    :root {{
      --ink: #17202a;
      --muted: #5d6878;
      --soft: #f6f8fb;
      --line: #d9e0e8;
      --blue: #235789;
      --teal: #0f766e;
      --orange: #d97706;
      --red: #b42318;
      --shadow: 0 12px 24px rgba(20, 36, 56, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; color: var(--ink); line-height: 1.72; background: #fff; }}
    .hero {{ padding: 58px 28px 50px; color: #fff; background: linear-gradient(120deg, #111827, #235789); }}
    .wrap {{ width: min(1180px, 100%); margin: 0 auto; }}
    .eyebrow {{ color: rgba(255,255,255,.76); margin: 0 0 12px; }}
    h1 {{ margin: 0; max-width: 1050px; font-size: clamp(34px, 5vw, 62px); line-height: 1.08; letter-spacing: 0; }}
    .hero .lead {{ max-width: 980px; margin-top: 22px; color: rgba(255,255,255,.9); font-size: 20px; }}
    section {{ padding: 48px 28px; }}
    section.band {{ background: var(--soft); }}
    h2 {{ margin: 0 0 14px; font-size: clamp(26px, 3vw, 38px); line-height: 1.18; }}
    h3 {{ margin: 22px 0 8px; font-size: 21px; }}
    p {{ margin: 0 0 14px; }}
    .lead {{ max-width: 980px; color: var(--muted); font-size: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(235px, 1fr)); gap: 16px; margin-top: 20px; }}
    .box, .metric-card, figure {{ background: #fff; border: 1px solid var(--line); border-radius: 8px; box-shadow: var(--shadow); }}
    .box {{ padding: 18px; }}
    .metric-card {{ padding: 18px; }}
    .metric-card span {{ display: block; color: var(--blue); font-size: 32px; font-weight: 780; line-height: 1; margin-bottom: 7px; }}
    .metric-card strong {{ display: block; margin-bottom: 6px; }}
    .metric-card p {{ color: var(--muted); margin: 0; font-size: 14px; }}
    .callout {{ margin: 18px 0; padding: 15px 16px; border-left: 4px solid var(--teal); background: #f1faf8; border-radius: 0 8px 8px 0; }}
    .warning {{ border-left-color: var(--orange); background: #fff7ed; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }}
    th, td {{ border: 1px solid var(--line); padding: 9px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #eef3f8; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    figure {{ margin: 28px 0; padding: 18px; }}
    figure img {{ display: block; width: 100%; border-radius: 6px; border: 1px solid var(--line); }}
    figcaption {{ margin-top: 16px; font-size: 18px; line-height: 1.7; }}
    figcaption strong {{ display: block; color: var(--blue); margin-bottom: 6px; font-size: 20px; }}
    code {{ background: #eef2f7; padding: 1px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="wrap">
      <p class="eyebrow">V6 advice-to-trust transfer · MiniMax-M2.7 · {summary['overall']['n_success']}/{summary['overall']['n_total']} successful runs</p>
      <h1>诚实声誉能否迁移到信任与付费决策？</h1>
      <p class="lead">V6 把 V4/V5 的 trust-game history 改成逐轮信息建议任务：同一个 partner 先表现出“诚实/不诚实”和“有帮助/有代价”，随后进入一次投资互动。目标是看模型能不能把 factual honesty 和 instrumental payoff 分开，并检验 social trust 与 willingness to pay 是否可分离。</p>
    </div>
  </header>

  <main>
    <section>
      <div class="wrap">
        <h2>为什么做 V6</h2>
        <p class="lead">为了避免任务变成简单的返还函数拟合，V6 不再直接呈现 partner 的返还历史。V4/V5 的 history prompt 中，返还比例高度结构化，模型容易把 partner 当作固定策略系统来估计，而不是在互动中形成社会信任判断。V6 借鉴 Bellucci et al. 2019 的思路，让同一个对象先在 advice task 中通过“是否说真话”和“建议是否带来收益”形成声誉，再迁移到 trust/WTP 决策。</p>
        <div class="grid">
          <div class="box">
            <h3>核心问题</h3>
            <p>模型能不能区分“这个人说真话”和“这个人让我赚钱”？如果能区分，最终 trust 和 WTP 又分别更跟哪一个走？</p>
          </div>
          <div class="box">
            <h3>关键对照</h3>
            <p><code>honest_costly</code> 诚实但没帮助；<code>dishonest_beneficial</code> 不诚实但有帮助。前者更像道德可信，后者更像工具性有用。</p>
          </div>
          <div class="box">
            <h3>呈现方式</h3>
            <p>sequential 是 12 轮逐轮互动；batch 是一次性读同样 12 轮历史。这个对照专门回应“trial-by-trial 是否比一次性 history 更像社会学习”。</p>
          </div>
        </div>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        <h2>实验设计</h2>
        <p class="lead">完整设计为 4 种 partner × 2 种呈现方式 × 8 个 seed，共 64 个 run。当前成功解析 60 个，其中 sequential 32/32 全部成功，batch 28/32 成功。</p>
        <table>
          <thead>
            <tr><th>Partner 类型</th><th>真实诚实率</th><th>推荐获胜率</th><th>解释</th></tr>
          </thead>
          <tbody>
            <tr><td>诚实且有帮助</td><td>0.75</td><td>0.75</td><td>说真话，推荐也常让模型赢。</td></tr>
            <tr><td>诚实但有代价</td><td>0.75</td><td>0.25</td><td>说真话，但推荐常让模型输。</td></tr>
            <tr><td>不诚实但有帮助</td><td>0.25</td><td>0.75</td><td>经常说假话，但推荐常让模型赢。</td></tr>
            <tr><td>不诚实且有代价</td><td>0.25</td><td>0.25</td><td>经常说假话，推荐也常让模型输。</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="wrap">
        <h2>总体结果</h2>
        <div class="grid">
          <div class="metric-card"><span>{summary['overall']['n_success']}/{summary['overall']['n_total']}</span><strong>成功 run</strong><p>4 个 batch run 仍因 JSON/空响应失败，sequential 全部成功。</p></div>
          <div class="metric-card"><span>{fmt(summary['overall']['trust_rating'])}</span><strong>平均信任评分</strong><p>所有条件合并后的 trust rating。</p></div>
          <div class="metric-card"><span>{fmt(summary['overall']['willingness_to_pay'])}</span><strong>平均 WTP</strong><p>0-10 的入场费评分。</p></div>
          <div class="metric-card"><span>{fmt(summary['overall']['n_api_calls'], 0)}</span><strong>成功解析 API 调用</strong><p>sequential run 内部包含 12 轮互动 + final probe。</p></div>
        </div>
        <table>
          <thead>
            <tr><th>Partner</th><th class="num">N</th><th class="num">真实诚实率</th><th class="num">推荐获胜率</th><th class="num">感知诚实</th><th class="num">感知有帮助</th><th class="num">信任</th><th class="num">WTP</th><th class="num">投资</th></tr>
          </thead>
          <tbody>{result_rows(summary)}</tbody>
        </table>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        <h2>结果图</h2>
        <figure>
          <img src="figures_cn/v6_perceived_honesty_cn.png" alt="感知诚实">
          <figcaption><strong>图1：模型能识别谁更诚实。</strong>诚实条件下的 perceived honesty 明显高于不诚实条件。尤其是 <code>honest_costly</code> 的感知诚实仍然很高，说明模型并没有因为它让自己输钱，就完全否认它的 factual honesty。</figcaption>
        </figure>
        <figure>
          <img src="figures_cn/v6_perceived_helpfulness_cn.png" alt="感知有帮助">
          <figcaption><strong>图2：模型也能识别谁更有帮助。</strong>beneficial 条件的 perceived helpfulness 明显高于 costly 条件。这说明操纵是成功的：模型把“诚实”和“有帮助”分成了两个维度。</figcaption>
        </figure>
        <figure>
          <img src="figures_cn/v6_trust_cn.png" alt="信任评分">
          <figcaption><strong>图3：最终 trust rating 并不只是 moral honesty。</strong><code>dishonest_beneficial</code> 的信任评分高于 <code>honest_costly</code>。这说明在投资互动语境中，模型的 trust rating 被“这个人是否让我获益”强烈牵引，而不是纯粹代表诚实声誉。</figcaption>
        </figure>
        <figure>
          <img src="figures_cn/v6_wtp_cn.png" alt="WTP">
          <figcaption><strong>图4：WTP 更像工具性机会价格。</strong>WTP 排序基本跟 helpfulness / payoff 走：诚实且有帮助最高，不诚实但有帮助也较高；诚实但有代价明显低，不诚实且有代价最低。这支持 WTP 与 social honesty 可分离。</figcaption>
        </figure>
        <figure>
          <img src="figures_cn/v6_critical_contrast_cn.png" alt="关键对照">
          <figcaption><strong>图5：关键对照是 V6 最有价值的结果。</strong><code>honest_costly</code> 被模型识别为更诚实，但它的 trust、WTP 和投资都低于 <code>dishonest_beneficial</code>。换句话说，模型知道谁诚实，但在后续投资决策中更愿意选择“虽然不诚实、但对我有用”的对象。</figcaption>
        </figure>
      </div>
    </section>

    <section>
      <div class="wrap">
        <h2>Honesty 会不会影响最终收益？</h2>
        <p class="lead">这里要区分两件事：一是诚实信息是否会让模型在前面的 advice task 中实际赢得更多；二是后续进入投资互动时，模型的 WTP 和 investment 是否仍然主要由 honesty 驱动。</p>
        <div class="grid">
          <div class="box">
            <h3>Nature Communications 2019</h3>
            <p>Bellucci et al. 的设计并不是让“诚实”直接等于“给出赢钱建议”。他们试图把 adviser 的 honesty 和 trial outcome 分开：诚实 adviser 只是如实报告自己看到的牌，不保证总是指向赢家。行为结果上，参与者在 honest adviser 条件下确实得到稍多正反馈：约 63.5%，dishonest adviser 约 56.7%。但后续 trust game 的投资和前面赚到多少钱并不显著相关，所以作者主张迁移过去的是 honesty-based trust，而不是简单的 payoff repayment。</p>
          </div>
          <div class="box">
            <h3>V6 的对应结果</h3>
            <p>在 V6 的 sequential 条件中，高诚实 partner 下模型实际选择赢的比例为 {fmt(payoff_stats["seq_high_honesty_choice_win"], 3)}，低诚实 partner 下为 {fmt(payoff_stats["seq_low_honesty_choice_win"], 3)}。方向上类似：honesty 可以让前期互动更容易产生正反馈。但这还不是严格复现，因为 V6 同时显式操纵了 recommendation payoff / helpfulness。</p>
          </div>
          <div class="box">
            <h3>关键差异</h3>
            <p>V6 的最终付费和投资更像是被 helpfulness/payoff 牵引，而不是由 honesty 单独决定。也就是说，模型可以识别谁更诚实，但在要不要付费进入互动、投多少钱时，它更看重“这个对象是否让我获益”。</p>
          </div>
        </div>
        <table>
          <thead>
            <tr><th>最终变量</th><th class="num">与 perceived honesty 的相关</th><th class="num">与 perceived helpfulness 的相关</th><th>解释</th></tr>
          </thead>
          <tbody>
            <tr><td>WTP</td><td class="num">{fmt(payoff_stats["correlations"]["willingness_to_pay"]["honesty"], 3)}</td><td class="num">{fmt(payoff_stats["correlations"]["willingness_to_pay"]["helpfulness"], 3)}</td><td>付费意愿更接近“机会是否有用”的价格。</td></tr>
            <tr><td>Investment</td><td class="num">{fmt(payoff_stats["correlations"]["investment"]["honesty"], 3)}</td><td class="num">{fmt(payoff_stats["correlations"]["investment"]["helpfulness"], 3)}</td><td>实际投资也更强地跟随 helpfulness。</td></tr>
            <tr><td>Expected return</td><td class="num">{fmt(payoff_stats["correlations"]["expected_return_tokens"]["honesty"], 3)}</td><td class="num">{fmt(payoff_stats["correlations"]["expected_return_tokens"]["helpfulness"], 3)}</td><td>模型预期返还几乎直接受收益线索牵引。</td></tr>
          </tbody>
        </table>
        <div class="callout">
          <p><strong>对当前结果的保守解释：</strong>V6 可以说明模型会同时提取 honesty 和 payoff，并且 honesty 在逐轮信息任务中可能间接提高实际表现；但它还没有证明“在 previous payoff 被严格控制后，honesty 仍然独立预测后续 costly trust”。如果要更接近 Bellucci et al. 2019 的主张，下一版需要把 realized payoff 控制住，再检验 honesty 是否仍能预测 WTP / investment。</p>
          <p class="small">参考：<a href="https://www.nature.com/articles/s41467-019-13261-8">Bellucci et al., 2019, Nature Communications</a>。</p>
        </div>
      </div>
    </section>

    <section>
      <div class="wrap">
        <h2>Sequential vs Batch</h2>
        <p class="lead">这版结果没有支持“逐轮互动一定更容易产生 moral social trust”。相反，逐轮互动让模型更直接经历输赢，因此 costly partner 的信任和 WTP 更低。尤其是 sequential 条件下，<code>honest_costly</code> 的 perceived honesty 仍高，但 trust 和 WTP 很低。</p>
        <table>
          <thead>
            <tr><th>Partner</th><th>呈现方式</th><th class="num">N</th><th class="num">感知诚实</th><th class="num">感知有帮助</th><th class="num">信任</th><th class="num">WTP</th><th class="num">投资</th><th class="num">跟随推荐率</th><th class="num">实际胜率</th></tr>
          </thead>
          <tbody>{mode_rows(summary)}</tbody>
        </table>
        <div class="callout">
          <p><strong>解释：</strong>sequential 不只是“更社会”，它也更像亲身经历 reward/punishment。模型在逐轮互动中会学会不再跟随 costly partner，即便这个 partner 很诚实。因此 trial-by-trial 可能增强的是 experienced utility，而不是纯粹的社会信任。</p>
        </div>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        <h2>目前结论</h2>
        <div class="grid">
          <div class="box">
            <h3>1. 操纵成功</h3>
            <p>模型明确区分了 honesty 和 helpfulness：perceived honesty 跟真实诚实率走，perceived helpfulness 跟推荐获胜率走。</p>
          </div>
          <div class="box">
            <h3>2. Trust 被收益污染</h3>
            <p>最终投资语境中的 trust rating 不是纯 moral trust，而是混合了“此人是否诚实”和“此人是否对我有用”。</p>
          </div>
          <div class="box">
            <h3>3. WTP 更像机会价值</h3>
            <p>WTP 基本跟 helpfulness/reward 走。它不是诚实声誉的简单延伸，而更接近“我愿不愿意为这次互动机会付费”。</p>
          </div>
          <div class="box">
            <h3>4. 关键 story</h3>
            <p>模型知道 <code>honest_costly</code> 更诚实，却更愿意投资 <code>dishonest_beneficial</code>。这比 V4 更清楚地显示 social honesty 与 costly choice 的分离。</p>
          </div>
        </div>
        <div class="callout warning">
          <p><strong>局限：</strong>当前还有 4 个 batch run 失败；另外 final probe 把 trust 放在 investment game 语境里，模型可能把 trust 理解为“预期会不会返还/对我有没有用”，而不是纯粹道德信任。下一版可以把 final probe 拆成 moral trust、competence/helpfulness、willingness-to-pay 三个独立问题，且顺序随机化。</p>
        </div>
      </div>
    </section>
  </main>
</body>
</html>"""
    REPORT.write_text(html, encoding="utf-8", newline="\n")


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    payoff_stats = honesty_payoff_stats()
    make_figures(summary)
    write_report(summary, payoff_stats)
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
