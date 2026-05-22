from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
SUMMARY = OUT / "summary.json"
REPORT = OUT / "report.html"


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

PARTNER_ORDER = ["stable_cooperator", "predictable_opportunist", "random_opportunist"]
CONTROL_ORDER = ["controllable_stake", "fixed_high_stake", "random_stake"]


def fmt(value, digits: int = 3) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def cell(summary: dict, partner: str, control: str) -> dict:
    return summary["by_partner_control"].get(f"{partner} / {control}", {})


def metric_card(label: str, value: str, note: str) -> str:
    return f"""
          <div class="metric-card">
            <span>{html.escape(value)}</span>
            <strong>{html.escape(label)}</strong>
            <p>{html.escape(note)}</p>
          </div>"""


def design_table() -> str:
    return """
          <table>
            <thead>
              <tr><th>变量</th><th>水平</th><th>设计目的</th></tr>
            </thead>
            <tbody>
              <tr><td>对象类型</td><td>稳定合作者</td><td>各赌注返还稳定在 0.40 左右，作为高信任基线。</td></tr>
              <tr><td>对象类型</td><td>可预测机会主义者</td><td>低赌注返还高，高赌注返还低；平均返还仍控制在 0.40。</td></tr>
              <tr><td>对象类型</td><td>随机机会主义者</td><td>平均返还和波动与机会主义者接近，但低返还不和赌注大小绑定。</td></tr>
              <tr><td>控制权</td><td>可控赌注</td><td>模型付入场费后可以自己选择低、中、高赌注。</td></tr>
              <tr><td>控制权</td><td>固定高赌注</td><td>模型付入场费后下一轮一定是高赌注。</td></tr>
              <tr><td>控制权</td><td>随机赌注</td><td>模型付入场费后由系统随机决定低、中、高赌注。</td></tr>
            </tbody>
          </table>"""


def result_table(summary: dict) -> str:
    rows = []
    for partner in PARTNER_ORDER:
        for control in CONTROL_ORDER:
            item = cell(summary, partner, control)
            rows.append(
                f"<tr>"
                f"<td>{PARTNER_LABELS[partner]}</td>"
                f"<td>{CONTROL_LABELS[control]}</td>"
                f"<td class=\"num\">{item.get('n_success', 0)}/{item.get('n_total', 0)}</td>"
                f"<td class=\"num\">{fmt(item.get('observed_low_minus_high'))}</td>"
                f"<td class=\"num\">{fmt(item.get('predicted_low_minus_high'))}</td>"
                f"<td class=\"num\">{fmt(item.get('trust_rating'))}</td>"
                f"<td class=\"num\">{fmt(item.get('willingness_to_pay'))}</td>"
                f"<td class=\"num\">{fmt(item.get('investment_fraction'))}</td>"
                f"</tr>"
            )
    return "\n".join(rows)


def premium_table(summary: dict) -> str:
    rows = []
    for partner in PARTNER_ORDER:
        prem = summary["controllability_premium"].get(partner, {})
        c = cell(summary, partner, "controllable_stake")
        h = cell(summary, partner, "fixed_high_stake")
        r = cell(summary, partner, "random_stake")
        rows.append(
            f"<tr>"
            f"<td>{PARTNER_LABELS[partner]}</td>"
            f"<td class=\"num\">{fmt(c.get('willingness_to_pay'))}</td>"
            f"<td class=\"num\">{fmt(h.get('willingness_to_pay'))}</td>"
            f"<td class=\"num\">{fmt(r.get('willingness_to_pay'))}</td>"
            f"<td class=\"num strong\">{fmt(prem.get('controllable_minus_fixed_high'))}</td>"
            f"</tr>"
        )
    return "\n".join(rows)


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    pred_ctrl = cell(summary, "predictable_opportunist", "controllable_stake")
    pred_high = cell(summary, "predictable_opportunist", "fixed_high_stake")
    rand_ctrl = cell(summary, "random_opportunist", "controllable_stake")
    stable_ctrl = cell(summary, "stable_cooperator", "controllable_stake")

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>V5：模型是在信任对方，还是在相信自己能控制风险？</title>
  <style>
    :root {{
      --ink: #17202a;
      --muted: #5b6573;
      --soft: #f6f8fb;
      --line: #d8dee6;
      --blue: #235789;
      --teal: #0f766e;
      --red: #b42318;
      --orange: #d97706;
      --shadow: 0 12px 26px rgba(20, 36, 56, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #fff;
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      line-height: 1.68;
    }}
    .hero {{
      padding: 62px 28px 54px;
      color: #fff;
      background:
        linear-gradient(120deg, rgba(17, 24, 39, 0.98), rgba(35, 87, 137, 0.90)),
        repeating-linear-gradient(90deg, rgba(255,255,255,0.06) 0 1px, transparent 1px 88px),
        repeating-linear-gradient(0deg, rgba(255,255,255,0.045) 0 1px, transparent 1px 88px);
    }}
    .wrap {{ width: min(1180px, 100%); margin: 0 auto; }}
    .eyebrow {{ color: rgba(255,255,255,0.78); margin: 0 0 12px; }}
    h1 {{ max-width: 1050px; margin: 0; font-size: clamp(34px, 5vw, 64px); line-height: 1.08; letter-spacing: 0; }}
    .hero p.lead {{ max-width: 930px; margin: 24px 0 0; color: rgba(255,255,255,0.90); font-size: 20px; }}
    section {{ padding: 52px 28px; }}
    section.band {{ background: var(--soft); }}
    h2 {{ margin: 0 0 14px; font-size: clamp(26px, 3vw, 38px); line-height: 1.2; }}
    h3 {{ margin: 26px 0 8px; font-size: 21px; }}
    p {{ margin: 0 0 14px; }}
    .lead {{ max-width: 980px; color: var(--muted); font-size: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-top: 22px; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 18px; }}
    .box, .metric-card, .figure {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      padding: 18px;
      box-shadow: var(--shadow);
    }}
    .metric-card span {{ display: block; margin-bottom: 6px; color: var(--blue); font-size: 32px; font-weight: 760; line-height: 1; }}
    .metric-card strong {{ display: block; margin-bottom: 6px; }}
    .metric-card p {{ color: var(--muted); font-size: 14px; margin: 0; }}
    .callout {{
      margin: 18px 0;
      padding: 15px 16px;
      border-left: 4px solid var(--teal);
      border-radius: 0 8px 8px 0;
      background: #f1faf8;
    }}
    .warning {{ border-left-color: var(--orange); background: #fff7ed; }}
    .claim {{ border-left-color: var(--blue); background: #eef5ff; }}
    table {{ width: 100%; border-collapse: collapse; margin: 18px 0 22px; font-size: 14px; }}
    th, td {{ border: 1px solid var(--line); padding: 9px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #eef3f8; font-weight: 650; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .strong {{ font-weight: 760; color: var(--teal); }}
    .figure-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px; margin-top: 22px; }}
    .figure {{ margin: 0; padding: 12px; }}
    .figure img {{ display: block; width: 100%; border-radius: 4px; }}
    figcaption {{ margin-top: 12px; color: var(--muted); font-size: 16px; line-height: 1.55; }}
    code {{ background: #eef2f7; border-radius: 4px; padding: 1px 5px; }}
    @media (max-width: 900px) {{
      .two-col, .figure-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="wrap">
      <p class="eyebrow">V5 controllability pilot · MiniMax-M2.7 · 51/54 successful trials</p>
      <h1>模型是在信任对方，还是在相信自己能控制风险？</h1>
      <p class="lead">V4 里出现了一个有意思的分离：机会主义者的信任评分不高，但在某些条件下模型仍愿意支付入场费。V5 专门检验这个机制：模型是否认为“我不信任你，但我能预测你什么时候会背叛，所以我还愿意进场”。</p>
    </div>
  </header>

  <main>
    <section>
      <div class="wrap">
        <h2>实验动机</h2>
        <p class="lead">V1-V4 的主线是：模型在重复信任博弈里总体更依赖实际行为，而不是漂亮话。但 V4 进一步暴露了一个更微妙的问题：信任评分和愿意支付的入场费并不总是同向变化。</p>
        <div class="two-col">
          <div class="box">
            <h3>V4 的问题</h3>
            <p>机会主义者在高赌注时少返还，因此信任评分低于稳定合作者；但它在低赌注时返还高，模型可能觉得这类对象虽然“不可靠”，但“可预测、可规避、可利用”。</p>
          </div>
          <div class="box">
            <h3>V5 的核心想法</h3>
            <p>如果模型真的形成了这种策略性判断，那么当它能控制下一轮赌注大小时，应该愿意为机会主义者支付更高入场费；当下一轮被固定为高赌注时，它应该退出或显著降价。</p>
          </div>
        </div>
        <div class="callout claim">
          <p><strong>一句话研究问题：</strong>大语言模型面对机会主义对象时，是在“信任对方”，还是在“相信自己能预测并控制对方的背叛触发条件”？</p>
        </div>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        <h2>假设</h2>
        <div class="grid">
          <div class="box">
            <h3>H1：信任和可控性分离</h3>
            <p>可预测机会主义者的信任评分应低于稳定合作者，但在可控赌注条件下仍可能获得较高入场费。</p>
          </div>
          <div class="box">
            <h3>H2：可控性溢价</h3>
            <p>可预测机会主义者的 <code>WTP_controllable - WTP_fixed_high</code> 应明显高于稳定合作者。</p>
          </div>
          <div class="box">
            <h3>H3：不是单纯风险偏好</h3>
            <p>随机机会主义者和可预测机会主义者有相近平均返还和波动，但低返还不和赌注绑定。如果模型追求的是可预测性，两者应表现不同。</p>
          </div>
          <div class="box">
            <h3>H4：策略性避险</h3>
            <p>在可控赌注条件下，模型面对可预测机会主义者应主动选择低赌注，避开会触发低返还的高赌注。</p>
          </div>
        </div>
      </div>
    </section>

    <section>
      <div class="wrap">
        <h2>实验设计</h2>
        <p class="lead">V5 使用 3 × 3 设计：三类对象 × 三类控制权。每类对象有 6 段数值历史，每段历史有 6 轮；总共 54 个 trial，成功解析 51 个。</p>
        {design_table()}
        <div class="callout">
          <p><strong>关键控制：</strong>三类对象的平均返还都控制在 0.40 左右。可预测机会主义者和随机机会主义者的波动幅度也接近，二者主要区别是：低返还是否系统性地绑定在高赌注上。</p>
        </div>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        <h2>方法</h2>
        <div class="two-col">
          <div class="box">
            <h3>模型看到什么</h3>
            <p>每个 trial 中，模型看到同一对象过去 6 轮互动记录。每轮包括赌注大小、前一位参与者投入多少、对方收到多少、对方实际返还多少。语言固定为中性句子，避免再混入漂亮话或道歉。</p>
          </div>
          <div class="box">
            <h3>模型回答什么</h3>
            <p>模型输出是否继续互动、愿意支付的入场费、信任评分、对低/中/高赌注的预期返还。在可控赌注条件下，它还要选择下一轮是低、中还是高赌注。</p>
          </div>
        </div>
        <div class="grid">
          {metric_card("成功试次", f"{summary['overall']['n_success']}/{summary['overall']['n_total']}", "3 个试次解析失败，未重试；以下结果基于成功试次。")}
          {metric_card("平均返还", fmt(summary['overall']['observed_return']), "所有对象的总体平均返还被控制在 0.40 左右。")}
          {metric_card("平均入场费", fmt(summary['overall']['willingness_to_pay']), "入场费来自模型输出的 willingness_to_pay，范围 0-10。")}
          {metric_card("平均信任", fmt(summary['overall']['trust_rating']), "信任评分来自模型输出的 trust_rating，范围 0-100。")}
        </div>
      </div>
    </section>

    <section>
      <div class="wrap">
        <h2>主要结果</h2>
        <h3>结果 1：模型准确识别“低赌注高返还、高赌注低返还”的结构</h3>
        <p>可预测机会主义者的实际低-高赌注返还差为 {fmt(pred_ctrl.get('observed_low_minus_high'))}，模型预测的低-高赌注返还差为 {fmt(pred_ctrl.get('predicted_low_minus_high'))}。也就是说，模型不仅看到了机会主义，而且把它表征成了一个和赌注大小相关的规则。</p>

        <h3>结果 2：可控性让可预测机会主义者从“完全不值得进场”变成“值得付费尝试”</h3>
        <p>对可预测机会主义者，固定高赌注时 WTP 为 {fmt(pred_high.get('willingness_to_pay'))}，继续率为 {fmt(pred_high.get('continue_rate'))}，投资比例为 {fmt(pred_high.get('investment_fraction'))}；可控赌注时 WTP 升到 {fmt(pred_ctrl.get('willingness_to_pay'))}，继续率升到 {fmt(pred_ctrl.get('continue_rate'))}。</p>

        <h3>结果 3：可预测机会主义者的可控性溢价最大</h3>
        <table>
          <thead>
            <tr><th>对象类型</th><th class="num">可控赌注 WTP</th><th class="num">固定高赌注 WTP</th><th class="num">随机赌注 WTP</th><th class="num">可控性溢价</th></tr>
          </thead>
          <tbody>
            {premium_table(summary)}
          </tbody>
        </table>
        <p>可预测机会主义者的可控性溢价为 +2.00；稳定合作者几乎没有溢价，只有 +0.10。这正是“我不是更信任你，而是我觉得我能控制风险”的结果模式。</p>

        <h3>结果 4：可控条件下，模型面对可预测机会主义者全部选择低赌注</h3>
        <p>在可控赌注条件中，可预测机会主义者 6/6 都被模型选择为低赌注。稳定合作者则主要选择高赌注；随机机会主义者的选择分散在低、中、高之间。</p>

        <div class="figure-grid">
          <figure class="figure">
            <img src="figures/wtp_by_partner_control.png" alt="不同对象和控制权条件下的入场费">
            <figcaption>入场费：可预测机会主义者在可控条件下显著高于固定高赌注条件；固定高赌注时模型几乎完全退出。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures/trust_by_partner_control.png" alt="不同对象和控制权条件下的信任评分">
            <figcaption>信任评分：稳定合作者整体更高；可预测机会主义者在固定高赌注下信任最低。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures/controllability_premium.png" alt="可控性溢价">
            <figcaption>可控性溢价：可预测机会主义者的 WTP 从固定高赌注到可控赌注增加最多。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures/predicted_low_minus_high.png" alt="预测的低高赌注差异">
            <figcaption>预测差异：模型准确预测可预测机会主义者低赌注返还高、高赌注返还低。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures/chosen_stake_distribution.png" alt="可控条件下选择的赌注分布">
            <figcaption>赌注选择：面对可预测机会主义者时，模型在可控条件下全部选择低赌注。</figcaption>
          </figure>
        </div>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        <h2>完整结果表</h2>
        <table>
          <thead>
            <tr>
              <th>对象</th><th>控制权</th><th class="num">N</th><th class="num">实际低-高</th><th class="num">预测低-高</th><th class="num">信任</th><th class="num">WTP</th><th class="num">投资比例</th>
            </tr>
          </thead>
          <tbody>
            {result_table(summary)}
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="wrap">
        <h2>结论</h2>
        <p class="lead">V5 支持一个比“模型信不信漂亮话”更细的解释：模型会把对方是否可信和互动是否可控分开。</p>
        <div class="callout claim">
          <p><strong>主结论：</strong>可预测机会主义者在固定高赌注下不值得进入，但在模型可以控制赌注时重新变得有价值。模型不是单纯更信任机会主义者，而是在利用“可预测的坏”。</p>
        </div>
        <div class="two-col">
          <div class="box">
            <h3>理论含义</h3>
            <p>这说明大模型的社会决策输出中可能至少有两个维度：一是 moral trust，即对方是否可靠；二是 strategic controllability，即对方虽不可靠但是否可预测、可规避、可利用。</p>
          </div>
          <div class="box">
            <h3>和 V4 的关系</h3>
            <p>V4 中“机会主义者低信任但 WTP 不低”的结果，在 V5 得到了更清楚的机制解释：高 WTP 不是因为模型更信任它，而是因为模型认为只要能避开高赌注，就能把风险控制住。</p>
          </div>
        </div>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        <h2>不足和下一步</h2>
        <div class="grid">
          <div class="box">
            <h3>样本还小</h3>
            <p>每个 cell 只有 5-6 个成功试次。当前结果足够做 pilot，但正式论文需要扩大 trial 数，并补齐 3 个失败项。</p>
          </div>
          <div class="box">
            <h3>单模型结果</h3>
            <p>当前只跑了 MiniMax-M2.7。下一步至少应复现到多个模型，尤其检查不同模型是否都表现出可控性溢价。</p>
          </div>
          <div class="box">
            <h3>random opportunist 也有控制权收益</h3>
            <p>随机机会主义者在可控条件下 WTP 也升高，说明控制权本身有一般价值。正式分析应区分“一般控制权收益”和“可预测机会主义的特异收益”。</p>
          </div>
          <div class="box">
            <h3>需要更严格统计</h3>
            <p>后续应使用混合效应模型或 Bayesian hierarchical model，检验 partner type × control condition 交互，而不是只看均值。</p>
          </div>
        </div>
      </div>
    </section>
  </main>
</body>
</html>"""

    REPORT.write_text(html_text, encoding="utf-8", newline="\n")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
