from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
SUMMARY = OUT / "summary.json"
REPORT = OUT / "report.html"
FIG = OUT / "figures_cn"

PARTNER_ORDER = ["stable_cooperator", "predictable_opportunist", "random_opportunist"]
CONTROL_ORDER = ["controllable_stake", "fixed_high_stake", "random_stake"]

PARTNER_LABELS = {
    "stable_cooperator": "稳定合作者",
    "predictable_opportunist": "可预测机会主义者",
    "random_opportunist": "随机机会主义者",
}

CONTROL_LABELS = {
    "controllable_stake": "可控赌注",
    "fixed_high_stake": "固定高赌注",
    "random_stake": "随机赌注",
}

STAKE_LABELS = {"low": "低赌注", "medium": "中赌注", "high": "高赌注"}
CONTROL_COLORS = {
    "controllable_stake": "#0f766e",
    "fixed_high_stake": "#b42318",
    "random_stake": "#64748b",
}


def get_font() -> str:
    candidates = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["font.sans-serif"] = candidates
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 120
    plt.rcParams["savefig.dpi"] = 230
    return candidates[0]


def cell(summary: dict, partner: str, control: str) -> dict:
    return summary["by_partner_control"].get(f"{partner} / {control}", {})


def val(summary: dict, partner: str, control: str, metric: str) -> float:
    value = cell(summary, partner, control).get(metric)
    return 0.0 if value is None else float(value)


def add_bar_labels(ax, bars, offset: float, size: int = 16) -> None:
    for bar in bars:
        value = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + offset,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=size,
            fontweight="semibold",
            color="#17202a",
        )


def grouped_bar(summary: dict, metric: str, ylabel: str, title: str, filename: str, ylim: tuple[float, float]) -> None:
    x = list(range(len(PARTNER_ORDER)))
    width = 0.24
    fig, ax = plt.subplots(figsize=(14.5, 8.2))
    for i, control in enumerate(CONTROL_ORDER):
        values = [val(summary, partner, control, metric) for partner in PARTNER_ORDER]
        positions = [p + (i - 1) * width for p in x]
        bars = ax.bar(
            positions,
            values,
            width=width,
            label=CONTROL_LABELS[control],
            color=CONTROL_COLORS[control],
            edgecolor="white",
            linewidth=1.4,
        )
        add_bar_labels(ax, bars, (ylim[1] - ylim[0]) * 0.018)

    ax.set_xticks(x)
    ax.set_xticklabels([PARTNER_LABELS[p] for p in PARTNER_ORDER], fontsize=17)
    ax.set_ylabel(ylabel, fontsize=18)
    ax.set_title(title, fontsize=24, fontweight="bold", pad=20)
    ax.set_ylim(*ylim)
    ax.tick_params(axis="y", labelsize=15)
    ax.legend(ncols=3, loc="upper center", bbox_to_anchor=(0.5, 1.02), fontsize=16, frameon=False)
    ax.grid(axis="y", color="#d8dee6", alpha=0.55)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / filename, bbox_inches="tight")
    plt.close(fig)


def make_premium(summary: dict) -> None:
    premium = summary["controllability_premium"]
    values = [
        float(premium[p].get("controllable_minus_fixed_high") or 0)
        for p in PARTNER_ORDER
    ]
    colors = ["#235789", "#0f766e", "#64748b"]
    fig, ax = plt.subplots(figsize=(12.8, 7.8))
    bars = ax.bar([PARTNER_LABELS[p] for p in PARTNER_ORDER], values, color=colors, width=0.58)
    ax.axhline(0, color="#17202a", linewidth=1.1)
    ax.set_ylim(-0.2, max(values) + 0.55)
    ax.set_ylabel("可控性溢价：可控赌注 WTP - 固定高赌注 WTP", fontsize=18)
    ax.set_title("图3：可控性本身有价值，尤其放大可预测机会主义者的入场价值", fontsize=23, fontweight="bold", pad=20)
    ax.tick_params(axis="x", labelsize=17)
    ax.tick_params(axis="y", labelsize=15)
    ax.grid(axis="y", color="#d8dee6", alpha=0.55)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    add_bar_labels(ax, bars, 0.06, size=17)
    fig.tight_layout()
    fig.savefig(FIG / "v5_controllability_premium_cn.png", bbox_inches="tight")
    plt.close(fig)


def make_chosen_stake(summary: dict) -> None:
    fig, ax = plt.subplots(figsize=(12.8, 7.8))
    bottom = [0.0] * len(PARTNER_ORDER)
    colors = {"low": "#0f766e", "medium": "#64748b", "high": "#b42318"}

    for stake in ["low", "medium", "high"]:
        values = []
        for partner in PARTNER_ORDER:
            counts = cell(summary, partner, "controllable_stake").get("chosen_stake_counts", {})
            total = sum(counts.values()) or 1
            values.append(counts.get(stake, 0) / total)
        bars = ax.bar(
            [PARTNER_LABELS[p] for p in PARTNER_ORDER],
            values,
            bottom=bottom,
            label=STAKE_LABELS[stake],
            color=colors[stake],
            edgecolor="white",
            linewidth=1.3,
        )
        for bar, value, base in zip(bars, values, bottom):
            if value >= 0.12:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    base + value / 2,
                    f"{value:.0%}",
                    ha="center",
                    va="center",
                    fontsize=16,
                    color="white",
                    fontweight="bold",
                )
        bottom = [b + v for b, v in zip(bottom, values)]

    ax.set_ylim(0, 1)
    ax.set_ylabel("可控条件下的选择比例", fontsize=18)
    ax.set_title("图5：有控制权时，模型如何选择下一轮赌注大小", fontsize=23, fontweight="bold", pad=20)
    ax.tick_params(axis="x", labelsize=17)
    ax.tick_params(axis="y", labelsize=15)
    ax.legend(ncols=3, loc="upper center", bbox_to_anchor=(0.5, 1.02), fontsize=16, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIG / "v5_chosen_stake_cn.png", bbox_inches="tight")
    plt.close(fig)


def make_figures(summary: dict) -> None:
    get_font()
    FIG.mkdir(exist_ok=True)
    grouped_bar(
        summary,
        "willingness_to_pay",
        "愿意支付的入场费 WTP（0-10）",
        "图1：入场费显示模型愿意为“可控机会”付费",
        "v5_wtp_cn.png",
        (0, 3.2),
    )
    grouped_bar(
        summary,
        "trust_rating",
        "信任评分（0-100）",
        "图2：信任评分反映对对象整体可靠性的判断",
        "v5_trust_cn.png",
        (0, 100),
    )
    make_premium(summary)
    grouped_bar(
        summary,
        "predicted_low_minus_high",
        "预测低赌注返还 - 预测高赌注返还",
        "图4：模型是否识别“高赌注触发低返还”的结构",
        "v5_predicted_gap_cn.png",
        (-0.08, 0.38),
    )
    make_chosen_stake(summary)


def replace_css(html_text: str) -> str:
    replacements = {
        r"\.figure-grid \{[^}]+\}": ".figure-grid { display: grid; grid-template-columns: 1fr; gap: 34px; margin-top: 30px; }",
        r"\.figure \{[^}]+\}": ".figure { margin: 0; padding: 22px; }",
        r"\.figure img \{[^}]+\}": ".figure img { display: block; width: 100%; border-radius: 6px; border: 1px solid var(--line); }",
        r"figcaption \{[^}]+\}": "figcaption { margin-top: 18px; color: var(--ink); font-size: 18px; line-height: 1.72; }",
    }
    for pattern, replacement in replacements.items():
        html_text = re.sub(pattern, replacement, html_text)

    extra_css = """
    .figure-caption-title { display: block; margin-bottom: 7px; color: var(--blue); font-weight: 780; font-size: 20px; }
    .figure-caption-result { display: block; margin-top: 8px; color: var(--muted); }
    .figure-caption-implication { display: block; margin-top: 8px; }
"""
    if ".figure-caption-title" not in html_text:
        html_text = html_text.replace("    code { background: #eef2f7; border-radius: 4px; padding: 1px 5px; }\n", f"    code {{ background: #eef2f7; border-radius: 4px; padding: 1px 5px; }}\n{extra_css}")
    return html_text


def figure_block() -> str:
    return """
        <div class="figure-grid">
          <figure class="figure">
            <img src="figures_cn/v5_wtp_cn.png" alt="V5 入场费结果">
            <figcaption>
              <span class="figure-caption-title">图1：入场费不是单纯的信任，而是对下一轮机会的定价。</span>
              <span class="figure-caption-result">结果上，可预测机会主义者在“可控赌注”条件下的平均 WTP 为 2.00；同一个对象一旦进入“固定高赌注”条件，WTP 降到 0。稳定合作者在三个条件下都没有这种断崖式变化；随机机会主义者也会因为可控性获得更高 WTP，但没有形成同样清楚的低赌注策略。</span>
              <span class="figure-caption-implication">这说明模型不是简单地“喜欢”或“信任”机会主义者。更贴切的解释是：当它能控制赌注大小时，它愿意买入一个可以被利用的机会；当它被迫进入高赌注时，它知道这个机会主义者会变危险，于是退出。</span>
            </figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v5_trust_cn.png" alt="V5 信任评分结果">
            <figcaption>
              <span class="figure-caption-title">图2：信任评分仍然保留了对“这个对象靠不靠谱”的整体判断。</span>
              <span class="figure-caption-result">结果上，稳定合作者整体信任评分最高；可预测机会主义者在固定高赌注下信任最低。可控赌注会提高可预测机会主义者的评分，但它仍然不是稳定合作者那种无条件可靠对象。</span>
              <span class="figure-caption-implication">这张图提醒我们，trust rating 和 WTP 不是同一个心理量。trust rating 更像整体可靠性评价；WTP 更像“是否值得进入下一轮”的行动价格。V5 的价值正在于把这两者分开：模型可以不完全信任一个对象，但仍然愿意为可控互动付费。</span>
            </figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v5_controllability_premium_cn.png" alt="V5 可控性溢价">
            <figcaption>
              <span class="figure-caption-title">图3：可控性溢价显示“我能控制局面”本身有价值。</span>
              <span class="figure-caption-result">这里的可控性溢价定义为：可控赌注条件下的 WTP 减去固定高赌注条件下的 WTP。可预测机会主义者的溢价最大，为 +2.00；稳定合作者几乎没有溢价，只有 +0.10；随机机会主义者也有 +1.00。</span>
              <span class="figure-caption-implication">最关键的比较不是“机会主义者 WTP 是否高”，而是“同一个机会主义者在可控和不可控时差多少”。这个差值说明模型在付费购买控制权。不过随机机会主义者也有正溢价，意味着控制权有一般吸引力；后续正式实验需要进一步区分一般 control value 和针对可预测机会主义的特殊策略价值。</span>
            </figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v5_predicted_gap_cn.png" alt="V5 预测低高赌注差异">
            <figcaption>
              <span class="figure-caption-title">图4：模型确实识别了可预测机会主义者的“触发规则”。</span>
              <span class="figure-caption-result">低-高预测差表示模型预测“低赌注返还”比“高赌注返还”高多少。可预测机会主义者的预测差约为 +0.303，几乎贴近真实结构；稳定合作者和随机机会主义者接近 0。</span>
              <span class="figure-caption-implication">这张图是机制证据。没有它，图1 的 WTP 差异可能只是一般风险偏好或随机波动；有了它，我们可以说模型不仅记住了平均返还，还表征了 partner policy：这个对象在什么条件下会合作、在什么条件下会背叛。</span>
            </figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v5_chosen_stake_cn.png" alt="V5 可控条件下的赌注选择">
            <figcaption>
              <span class="figure-caption-title">图5：真正的行为证据是模型在可控时如何下注。</span>
              <span class="figure-caption-result">只看可控赌注条件，模型面对可预测机会主义者时 6/6 选择低赌注；面对稳定合作者时主要选择高赌注；面对随机机会主义者时选择更分散。</span>
              <span class="figure-caption-implication">这直接对应你刚才提到的机制：“我赌我能猜到多高的赌注会触发你的低返还。”模型不是盲目冒险，也不是只看漂亮话；它在有控制权时主动把互动推到对自己有利的低赌注区域。这也是 V5 最适合继续展开成论文 story 的部分。</span>
            </figcaption>
          </figure>
        </div>"""


def patch_report() -> None:
    html_text = REPORT.read_text(encoding="utf-8")
    html_text = replace_css(html_text)
    pattern = re.compile(
        r"\s*<div class=\"figure-grid\">\s*"
        r"<figure class=\"figure\">.*?</figure>\s*"
        r"<figure class=\"figure\">.*?</figure>\s*"
        r"<figure class=\"figure\">.*?</figure>\s*"
        r"<figure class=\"figure\">.*?</figure>\s*"
        r"<figure class=\"figure\">.*?</figure>\s*"
        r"</div>",
        re.DOTALL,
    )
    html_text, count = pattern.subn(figure_block(), html_text, count=1)
    if count != 1:
        raise RuntimeError("Could not find the five-figure block in report.html")
    REPORT.write_text(html_text, encoding="utf-8")


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    make_figures(summary)
    patch_report()
    print(f"Updated {REPORT}")
    print(f"Generated figures in {FIG}")


if __name__ == "__main__":
    main()
