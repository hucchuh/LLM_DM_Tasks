from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures_cn"
OUT.mkdir(exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 120
plt.rcParams["savefig.dpi"] = 220

COLORS = ["#235789", "#0f766e", "#d97706", "#7c3aed", "#b42318", "#64748b"]
LANG_COLORS = {
    "中性": "#334155",
    "温暖": "#0f766e",
    "承诺": "#2563eb",
    "道歉": "#d97706",
    "温暖承诺": "#0f766e",
    "道歉解释": "#d97706",
}


def load_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def polish(ax, title: str, ylabel: str | None = None, xlabel: str | None = None) -> None:
    ax.set_title(title, fontsize=18, weight="bold", pad=14)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=14)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=14)
    ax.tick_params(axis="both", labelsize=12)
    ax.grid(axis="y", alpha=0.22, linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def add_bar_labels(ax, bars, fmt="{:.2f}", fontsize=10) -> None:
    for bar in bars:
        height = bar.get_height()
        y = height + (0.8 if abs(height) > 1 else 0.03)
        if height < 0:
            y = height - (0.8 if abs(height) > 1 else 0.03)
            va = "top"
        else:
            va = "bottom"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            y,
            fmt.format(height),
            ha="center",
            va=va,
            fontsize=fontsize,
            color="#17202a",
        )


def save(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(OUT / name, bbox_inches="tight")
    plt.close(fig)


def v1_figures() -> None:
    summary = load_json("output/summary.json")
    rows = summary["by_partner_type"]
    order = [
        ("honest_cooperator", "稳定合作者"),
        ("cautious_reliable", "谨慎但可靠"),
        ("noisy_repairing", "真实修复者"),
        ("strategic_opportunist", "机会主义者"),
        ("charming_under_returner", "会说话但少返还"),
        ("apology_only_exploiter", "只道歉不修复"),
    ]
    labels = [label for _, label in order]
    trusts = [rows[key]["mean_trust_rating"] for key, _ in order]
    investments = [rows[key]["mean_investment_next"] for key, _ in order]
    returns = [rows[key]["mean_true_return_fraction"] for key, _ in order]

    fig, ax = plt.subplots(figsize=(11, 6.2))
    bars = ax.bar(labels, trusts, color=COLORS)
    ax.set_ylim(0, 100)
    polish(ax, "V1：信任评分主要跟随实际返还", "信任评分（0-100）")
    ax.tick_params(axis="x", labelrotation=18)
    add_bar_labels(ax, bars, "{:.1f}")
    save(fig, "v1_trust_by_partner_cn.png")

    fig, ax = plt.subplots(figsize=(11, 6.2))
    bars = ax.bar(labels, investments, color=COLORS)
    ax.set_ylim(0, 10.8)
    polish(ax, "V1：下一轮投资随对象可靠性变化", "下一轮投资（0-10）")
    ax.tick_params(axis="x", labelrotation=18)
    add_bar_labels(ax, bars, "{:.1f}")
    save(fig, "v1_investment_by_partner_cn.png")

    fig, ax = plt.subplots(figsize=(8.8, 6.2))
    ax.scatter(returns, trusts, s=90, color="#235789")
    for x, y, label in zip(returns, trusts, labels):
        ax.annotate(label, (x, y), xytext=(6, 5), textcoords="offset points", fontsize=11)
    coef = np.polyfit(returns, trusts, 1)
    xs = np.linspace(min(returns) - 0.01, max(returns) + 0.01, 100)
    ax.plot(xs, coef[0] * xs + coef[1], color="#d97706", linewidth=2)
    polish(ax, "V1：平均返还越高，信任评分越高", "信任评分（0-100）", "实际平均返还比例")
    save(fig, "v1_trust_vs_return_cn.png")

    results = load_json("output/results.json")
    fig, ax = plt.subplots(figsize=(8.8, 6.2))
    for idx, (key, label) in enumerate(order):
        subset = [r for r in results if r.get("partner_type") == key and not r.get("error")]
        xs = [r["true_mean_return_fraction"] for r in subset]
        ys = [r["metrics"]["trust_rating"] for r in subset]
        ax.scatter(xs, ys, s=72, color=COLORS[idx], label=label, alpha=0.88)
    ax.set_xlim(0.22, 0.54)
    ax.set_ylim(15, 88)
    polish(ax, "V1：逐个试次也呈现同一关系", "信任评分（0-100）", "该次历史中的平均返还比例")
    ax.legend(fontsize=10, ncols=2, frameon=False)
    save(fig, "v1_trial_return_trust_cn.png")


def v2_figures() -> None:
    summary = load_json("v2_average_control/output/summary.json")
    rows = summary["by_condition"]
    order = [
        ("stable_neutral", "稳定中性"),
        ("stable_warm", "稳定温暖"),
        ("high_stake_betrayal", "高赌注背叛"),
        ("high_stake_generous", "高赌注慷慨"),
        ("repairing_trend", "逐步修复"),
        ("declining_trend", "逐步恶化"),
    ]
    labels = [label for _, label in order]

    fig, ax = plt.subplots(figsize=(11, 6.2))
    vals = [rows[key]["global_trust_rating"] for key, _ in order]
    bars = ax.bar(labels, vals, color=COLORS)
    ax.set_ylim(0, 100)
    polish(ax, "V2：平均返还相同，信任仍然不同", "信任评分（0-100）")
    ax.tick_params(axis="x", labelrotation=18)
    add_bar_labels(ax, bars, "{:.1f}")
    save(fig, "v2_trust_by_condition_cn.png")

    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    x = np.arange(len(order))
    width = 0.25
    low = [rows[key]["predicted_return_low"] for key, _ in order]
    med = [rows[key]["predicted_return_medium"] for key, _ in order]
    high = [rows[key]["predicted_return_high"] for key, _ in order]
    ax.bar(x - width, low, width, label="低赌注", color="#0f766e")
    ax.bar(x, med, width, label="中赌注", color="#64748b")
    ax.bar(x + width, high, width, label="高赌注", color="#b42318")
    ax.set_ylim(0, 0.72)
    ax.set_xticks(x, labels, rotation=18, ha="right")
    polish(ax, "V2：模型能分辨不同赌注下的返还模式", "预计返还比例")
    ax.legend(fontsize=12, ncols=3)
    save(fig, "v2_conditional_predictions_cn.png")

    fig, ax = plt.subplots(figsize=(11, 6.2))
    vals = [rows[key]["predicted_high_minus_low"] for key, _ in order]
    bars = ax.bar(labels, vals, color=["#64748b", "#64748b", "#b42318", "#0f766e", "#0f766e", "#b42318"])
    ax.axhline(0, color="#17202a", linewidth=1)
    ax.set_ylim(-0.36, 0.36)
    polish(ax, "V2：高赌注相对低赌注的预期变化", "高赌注预计返还 - 低赌注预计返还")
    ax.tick_params(axis="x", labelrotation=18)
    add_bar_labels(ax, bars, "{:.2f}", fontsize=10)
    save(fig, "v2_high_low_gap_cn.png")


def v3_figures() -> None:
    summary = load_json("v3_noisy_policy/output/summary.json")
    cells = summary["by_cell"]
    behaviors = [
        ("stable_moderate", "稳定中等"),
        ("strategic_opportunist", "机会主义"),
        ("noisy_repairing", "逐步修复"),
        ("apology_only_exploiter", "只道歉不修复"),
    ]
    languages = [("neutral", "中性"), ("warm_promise", "温暖承诺"), ("apology_excuse", "道歉解释")]
    x = np.arange(len(behaviors))
    width = 0.24

    def grouped_bar(metric: str, title: str, ylabel: str, filename: str, ylim=None):
        fig, ax = plt.subplots(figsize=(12, 6.3))
        for idx, (lang_key, lang_label) in enumerate(languages):
            vals = [cells[f"{b_key} / {lang_key}"][metric] for b_key, _ in behaviors]
            ax.bar(x + (idx - 1) * width, vals, width, label=lang_label, color=LANG_COLORS[lang_label])
        if ylim:
            ax.set_ylim(*ylim)
        ax.set_xticks(x, [label for _, label in behaviors], rotation=10, ha="right")
        polish(ax, title, ylabel)
        ax.legend(fontsize=12, ncols=3)
        save(fig, filename)

    grouped_bar("trust_rating", "V3：信任评分主要由行为记录拉开", "信任评分（0-100）", "v3_trust_by_behavior_language_cn.png", (0, 100))
    grouped_bar("predicted_high_minus_low", "V3：模型识别高赌注是否更危险", "高赌注预计返还 - 低赌注预计返还", "v3_high_low_gap_cn.png", (-0.38, 0.30))

    fig, ax = plt.subplots(figsize=(8.8, 6.2))
    vals = [summary["by_language"][key]["trust_rating"] for key, _ in languages]
    bars = ax.bar([label for _, label in languages], vals, color=[LANG_COLORS[label] for _, label in languages])
    ax.set_ylim(0, 100)
    polish(ax, "V3：说法对信任有小幅影响", "信任评分（0-100）")
    add_bar_labels(ax, bars, "{:.1f}")
    save(fig, "v3_language_trust_cn.png")

    fig, ax = plt.subplots(figsize=(8.8, 6.2))
    vals = [summary["overall"]["behavior_weight"], summary["overall"]["message_weight"]]
    bars = ax.bar(["行为记录", "对方说法"], vals, color=["#0f766e", "#d97706"])
    ax.set_ylim(0, 100)
    polish(ax, "V3：模型自称更依赖行为记录", "自报权重（0-100）")
    add_bar_labels(ax, bars, "{:.1f}")
    save(fig, "v3_self_report_weight_cn.png")


def v4_figures() -> None:
    summary = load_json("v4_clean_wtp/output/summary.json")
    cells = summary["by_behavior_language"]
    behaviors = [
        ("deteriorating_exploiter", "逐步恶化"),
        ("noisy_repairing", "逐步修复"),
        ("stable_moderate", "稳定中等"),
        ("strategic_opportunist", "机会主义"),
    ]
    languages = [("neutral_filler", "中性"), ("warmth", "温暖"), ("promise", "承诺"), ("apology", "道歉")]
    x = np.arange(len(behaviors))
    width = 0.19

    def grouped_bar(metric: str, title: str, ylabel: str, filename: str, ylim=None):
        fig, ax = plt.subplots(figsize=(12, 6.3))
        for idx, (lang_key, lang_label) in enumerate(languages):
            vals = [cells[f"{b_key} / {lang_key}"][metric] for b_key, _ in behaviors]
            bars = ax.bar(x + (idx - 1.5) * width, vals, width, label=lang_label, color=LANG_COLORS[lang_label])
            if metric == "willingness_to_pay":
                for bar, val in zip(bars, vals):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        val + 0.08,
                        f"{val:.2f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        rotation=90,
                    )
        if ylim:
            ax.set_ylim(*ylim)
        ax.set_xticks(x, [label for _, label in behaviors], rotation=10, ha="right")
        polish(ax, title, ylabel)
        ax.legend(fontsize=12, ncols=4)
        save(fig, filename)

    grouped_bar("willingness_to_pay", "V4：愿意支付的入场费主要随行为记录变化", "愿意支付的入场费（0-10）", "v4_wtp_by_behavior_language_cn.png", (0, 5.2))
    grouped_bar("trust_rating", "V4：信任评分也主要由行为记录区分", "信任评分（0-100）", "v4_trust_by_behavior_language_cn.png", (0, 100))

    stake_rows = summary["by_behavior_next_stake"]
    stakes = [("low", "低赌注"), ("medium", "中赌注"), ("high", "高赌注")]
    fig, ax = plt.subplots(figsize=(12, 6.3))
    width2 = 0.24
    stake_colors = {"低赌注": "#0f766e", "中赌注": "#64748b", "高赌注": "#b42318"}
    for idx, (stake_key, stake_label) in enumerate(stakes):
        vals = [stake_rows[f"{b_key} / {stake_key}"]["investment_fraction"] for b_key, _ in behaviors]
        ax.bar(x + (idx - 1) * width2, vals, width2, label=stake_label, color=stake_colors[stake_label])
    ax.set_xticks(x, [label for _, label in behaviors], rotation=10, ha="right")
    ax.set_ylim(0, 1.08)
    polish(ax, "V4：下一轮投资比例反映具体风险判断", "投资比例")
    ax.legend(fontsize=12, ncols=3)
    save(fig, "v4_investment_by_behavior_stake_cn.png")

    fig, ax = plt.subplots(figsize=(8.8, 6.2))
    vals = [summary["by_language"][key]["willingness_to_pay"] for key, _ in languages]
    bars = ax.bar([label for _, label in languages], vals, color=[LANG_COLORS[label] for _, label in languages])
    ax.set_ylim(0, 3)
    polish(ax, "V4：说法本身的平均影响较小", "愿意支付的入场费（0-10）")
    add_bar_labels(ax, bars, "{:.2f}")
    save(fig, "v4_language_wtp_cn.png")


def main() -> None:
    v1_figures()
    v2_figures()
    v3_figures()
    v4_figures()
    print(f"saved figures to {OUT}")


if __name__ == "__main__":
    main()
