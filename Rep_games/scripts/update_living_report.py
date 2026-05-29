from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "reports" / "report_manifest.json"
OUTPUT_PATH = ROOT / "living_report.html"


def load_json(relative_path: str) -> dict:
    path = ROOT / relative_path
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value, digits: int = 3) -> str:
    if value is None:
        return "-"
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def pct(value, digits: int = 1) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.{digits}f}%"


def esc(text) -> str:
    return html.escape(str(text), quote=True)


def rel_link(path: str, label: str) -> str:
    return f'<a href="{esc(path)}">{esc(label)}</a>'


def stat_card(label: str, value: str, note: str = "") -> str:
    return (
        '<div class="stat-card">'
        f'<div class="stat-label">{esc(label)}</div>'
        f'<div class="stat-value">{esc(value)}</div>'
        f'<div class="stat-note">{esc(note)}</div>'
        "</div>"
    )


def bar_row(label: str, value: float, sem: float | None = None, max_value: float = 10.0) -> str:
    width = max(0, min(100, 100 * value / max_value))
    sem_text = f" ± {fmt(sem)} SEM" if sem is not None else ""
    return (
        '<div class="bar-row">'
        f'<div class="bar-label">{esc(label)}</div>'
        '<div class="bar-track">'
        f'<div class="bar-fill" style="width:{width:.1f}%"></div>'
        "</div>"
        f'<div class="bar-value">{fmt(value)}{esc(sem_text)}</div>'
        "</div>"
    )


def table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def get_by_partner_mode(v8: dict, key: str) -> dict:
    return v8.get("by_partner_mode", {}).get(key, {})


def find_condition(v9: dict, **criteria) -> dict:
    for row in v9.get("by_condition", []):
        if all(row.get(k) == v for k, v in criteria.items()):
            return row
    return {}


def find_gap(v9b: dict, instruction_type: str) -> dict:
    for row in v9b.get("high_low_gaps", []):
        if row.get("instruction_type") == instruction_type:
            return row
    return {}


def find_phase(stats: dict, condition: str, honesty: str, phase: str) -> dict:
    for row in stats.get("phase_table", []):
        if row.get("condition") == condition and row.get("honesty") == honesty and row.get("phase") == phase:
            return row
    return {}


def build_report() -> str:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    data = {}
    for version in manifest["versions"]:
        if version.get("summary"):
            data[version["id"]] = load_json(version["summary"])
        if version.get("stats"):
            data[f'{version["id"]}_stats'] = load_json(version["stats"])

    v1 = data.get("V1", {})
    v5 = data.get("V5", {})
    v7 = data.get("V7", {})
    v8 = data.get("V8", {})
    v9 = data.get("V9", {})
    v9b = data.get("V9b", {})
    v10 = data.get("V10", {})
    v10_stats = data.get("V10_stats", {})

    v1_r = v1.get("relationships", {}).get("partner_type_mean_trust_vs_average_return", {}).get("r")
    v5_control = v5.get("by_control", {})
    v5_controllable = v5_control.get("controllable_stake", {})
    v5_fixed = v5_control.get("fixed_high_stake", {})
    v7_honest = v7.get("by_partner", {}).get("honest_matched", {})
    v7_dishonest = v7.get("by_partner", {}).get("dishonest_matched", {})
    v8_high = get_by_partner_mode(v8, "high_honesty_matched_return / sequential_trial")
    v8_low = get_by_partner_mode(v8, "low_honesty_matched_return / sequential_trial")
    v9_standard_high = find_condition(
        v9,
        block="main_partner_honesty",
        statement_mode="partner_private_card",
        honesty_level="high",
        return_policy="fair_high",
        orthogonality_instruction="standard",
    )
    v9_standard_low = find_condition(
        v9,
        block="main_partner_honesty",
        statement_mode="partner_private_card",
        honesty_level="low",
        return_policy="fair_high",
        orthogonality_instruction="standard",
    )
    v9_ortho_high = find_condition(
        v9,
        block="main_partner_honesty",
        statement_mode="partner_private_card",
        honesty_level="high",
        return_policy="fair_high",
        orthogonality_instruction="explicit_orthogonality",
    )
    v9_ortho_low = find_condition(
        v9,
        block="main_partner_honesty",
        statement_mode="partner_private_card",
        honesty_level="low",
        return_policy="fair_high",
        orthogonality_instruction="explicit_orthogonality",
    )
    v9b_nat = find_gap(v9b, "natural")
    v9b_ortho = find_gap(v9b, "explicit_orthogonality")
    v9b_attn = find_gap(v9b, "attention_control")
    did = v10_stats.get("did", {})

    phase_rows = []
    for condition in ["Neutral reminder", "Orthogonality disclosure"]:
        for honesty in ["High honesty", "Low honesty"]:
            for phase in ["Pre", "Post"]:
                row = find_phase(v10_stats, condition, honesty, phase)
                if row:
                    phase_rows.append([
                        esc(condition),
                        esc(honesty),
                        esc(phase),
                        esc(row.get("n sessions")),
                        esc(row.get("mean ± SEM", "-").replace("卤", "±")),
                    ])

    version_rows = []
    for version in manifest["versions"]:
        version_rows.append([
            f'<strong>{esc(version["id"])}</strong>',
            esc(version["role"]),
            rel_link(version["report"], "single-version report"),
            rel_link(version["summary"], "summary.json") if version.get("summary") else "-",
        ])

    archive_rows = [
        [f"<code>{esc(path)}</code>", "旧版综合或中间展示稿；建议保留为归档证据，不作为当前入口。"]
        for path in manifest.get("archive_candidates", [])
    ]

    css = """
    :root {
      --ink: #142033;
      --muted: #607086;
      --line: #d9e2ec;
      --bg: #f6f8fb;
      --panel: #ffffff;
      --accent: #235a8c;
      --accent-2: #8b3f5d;
      --soft: #eaf2f8;
      --warn: #fff4df;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", "Microsoft YaHei", Arial, sans-serif;
      background: var(--bg);
      line-height: 1.72;
      font-size: 17px;
    }
    header {
      background: linear-gradient(135deg, #122236 0%, #245f91 100%);
      color: #fff;
      padding: 72px 32px 64px;
    }
    .wrap { max-width: 1120px; margin: 0 auto; }
    .kicker { font-size: 15px; letter-spacing: .06em; text-transform: uppercase; opacity: .86; }
    h1 { margin: 14px 0 18px; font-size: clamp(34px, 5vw, 62px); line-height: 1.08; letter-spacing: 0; }
    .lead { max-width: 980px; font-size: 23px; line-height: 1.62; opacity: .94; }
    main section { padding: 54px 32px; border-bottom: 1px solid var(--line); }
    h2 { font-size: 34px; margin: 0 0 22px; line-height: 1.22; }
    h3 { font-size: 24px; margin: 34px 0 12px; }
    p { margin: 0 0 16px; }
    a { color: var(--accent); text-decoration: none; border-bottom: 1px solid rgba(35, 90, 140, .35); }
    .abstract {
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 28px;
      border-radius: 12px;
      box-shadow: 0 12px 40px rgba(20, 32, 51, .06);
    }
    .stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 24px 0; }
    .stat-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 18px;
      min-height: 126px;
    }
    .stat-label { color: var(--muted); font-size: 14px; }
    .stat-value { font-size: 29px; font-weight: 750; margin: 7px 0; }
    .stat-note { color: var(--muted); font-size: 14px; line-height: 1.45; }
    .arc { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin-top: 24px; }
    .arc-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-top: 5px solid var(--accent);
      border-radius: 12px;
      padding: 20px;
    }
    .arc-card strong { display: block; font-size: 19px; margin-bottom: 8px; }
    .evidence {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 26px;
      margin: 22px 0;
    }
    .evidence h3 { margin-top: 0; }
    .bar-row {
      display: grid;
      grid-template-columns: 240px 1fr 150px;
      gap: 14px;
      align-items: center;
      margin: 12px 0;
      font-size: 15px;
    }
    .bar-track { height: 18px; background: #e7edf4; border-radius: 999px; overflow: hidden; }
    .bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent), #3f8ab8); }
    .bar-value { color: var(--muted); text-align: right; font-variant-numeric: tabular-nums; }
    .callout {
      background: var(--soft);
      border-left: 5px solid var(--accent);
      padding: 18px 20px;
      border-radius: 10px;
      margin: 20px 0;
    }
    .warning {
      background: var(--warn);
      border-left-color: #b57920;
    }
    .table-wrap { overflow-x: auto; margin: 20px 0 6px; }
    table { width: 100%; border-collapse: collapse; background: var(--panel); }
    th, td { border: 1px solid var(--line); padding: 12px 14px; text-align: left; vertical-align: top; }
    th { background: #eef4f9; font-weight: 750; }
    code {
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
      background: #eef2f7;
      padding: 2px 6px;
      border-radius: 5px;
      font-size: .92em;
    }
    .figure-img {
      width: 100%;
      max-width: 980px;
      display: block;
      margin: 18px auto 8px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fff;
    }
    .caption { color: var(--muted); font-size: 15px; text-align: center; }
    .footer-note { color: var(--muted); font-size: 14px; }
    @media (max-width: 900px) {
      .stats-grid, .arc { grid-template-columns: 1fr 1fr; }
      .bar-row { grid-template-columns: 1fr; gap: 6px; }
      .bar-value { text-align: left; }
    }
    @media (max-width: 620px) {
      header, main section { padding-left: 20px; padding-right: 20px; }
      .stats-grid, .arc { grid-template-columns: 1fr; }
      body { font-size: 16px; }
    }
    """

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(manifest["living_report"]["title"])}</title>
  <style>{css}</style>
</head>
<body>
<header>
  <div class="wrap">
    <div class="kicker">Rep Games living report · MiniMax API pilot series · generated from version summaries</div>
    <h1>{esc(manifest["living_report"]["title"])}</h1>
    <p class="lead">这份报告不是各版本实验的流水账，而是把 V1-V10 串成一个正在成形的研究故事：大语言模型在重复社会互动中并不只是被好听的话影响；它们非常擅长追踪实际收益，但在面对可核验的诚实性信号时，又会把 honesty 当成合作价值的代理线索。这种代理线索什么时候影响 costly choice，什么时候会被规则说明纠偏，是当前最值得继续深挖的问题。</p>
  </div>
</header>

<main>
  <section>
    <div class="wrap">
      <div class="abstract">
        <h2>摘要</h2>
        <p>本项目研究一个很具体的问题：当一个互动对象的语言、诚实性和真实返还收益可以被拆开时，大语言模型的投资决策到底由什么驱动？早期结果显示，模型对 repeated trust game 中的平均返还和条件性背叛极为敏感，普通的道歉、承诺和温暖表达很难改变它的判断。随后，实验把“说真话”改造成可核验的社会信号，并把 honesty 与 payoff 匹配或正交化。结果显示，即使实际收益相同，模型仍会因为对方更诚实而提高信任、WTP 或投资；但当明确告知 truth 与 return policy 无因果关系时，这种效应会改变，甚至在低诚实条件下出现更高的探索性投资。</p>
        <p>当前最合理的结论不是“LLM 信不信人”，而是：模型会同时进行 payoff tracking 和 social-signal generalization。前者让模型看起来很理性，后者让模型在 honesty 与 payoff 被人为拆开时出现可测的偏置与机会成本。</p>
      </div>

      <div class="stats-grid">
        {stat_card("V1 payoff tracking", f"r = {fmt(v1_r)}", "partner-level trust 与平均返还几乎重合")}
        {stat_card("V8 honesty cost", f"{fmt(v8_high.get('mean_run_trial_payoff'))} vs {fmt(v8_low.get('mean_run_trial_payoff'))}", "高诚实 vs 低诚实，每轮 payoff；返还率被匹配")}
        {stat_card("V10 sessions", f"{v10.get('successful_runs', '-')}/{v10.get('total_runs', '-')}", "expanded session 全部成功")}
        {stat_card("V10 disclosure effect", f"DID = {fmt(did.get('mean'))}", f"t({did.get('df', '-')}) = {fmt(did.get('t'))}, p = {fmt(did.get('p'))}")}
      </div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <h2>研究问题与递进逻辑</h2>
      <p>这个项目最初的问题是 cheap talk：如果一个对象说得很友好、会道歉、会承诺，但实际返还很差，模型会被语言牵着走吗？第一组实验给出的答案相当清楚：多数时候不会。模型更像是在提取对方的返还结构。</p>
      <p>但这个结论还不够有意思，因为它容易变成“模型会做表格题”。真正的推进来自第二个问题：如果语言不是空泛的 warmth，而是可被反馈验证的 factual honesty，模型会不会把“这个人说真话”泛化成“这个人值得合作”？于是 V7-V10 把 honesty 与 payoff 拆开：有的对象说真话更多，但不一定让模型赚更多；有的对象说假话更多，但返还政策同样公平。</p>
      <p>因此整条证据链不是版本堆叠，而是四个递进问题：</p>
      <div class="arc">
        <div class="arc-card"><strong>1. 行为证据是否主导？</strong>V1-V4 检查模型是否更依赖实际返还，而非温暖语言、承诺和道歉。</div>
        <div class="arc-card"><strong>2. 信任和付费能否分离？</strong>V5-V6 检查 moral trust、WTP 和实际投资是否属于同一个心理量。</div>
        <div class="arc-card"><strong>3. 诚实是否迁移到投资？</strong>V7-V8 在 payoff matched 条件下检查 factual honesty 是否改变 costly choice。</div>
        <div class="arc-card"><strong>4. 这种迁移有没有边界？</strong>V9-V10 加入 orthogonality instruction 和中途 disclosure，检查模型能否被规则说明纠偏。</div>
      </div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <h2>方法概览</h2>
      <p>所有实验都是 API-level pilot。模型作为投资者，在每轮获得 10 个 token，可选择投资 0-10 个 token。投资会被 tripled 后交给 partner，partner 再按预先设定的 policy 返还一部分。每轮收益为：</p>
      <div class="callout"><code>payoff_t = 10 - investment_t + returned_tokens_t</code></div>
      <p>不同版本操纵的不是同一个变量。早期版本主要改变语言风格和返还历史；中期版本控制平均返还、引入条件性背叛和可控赌注；后期版本把 partner 的 factual honesty 设计成可核验信号，并通过 matched return、irrelevant truth、no statement、cheap talk only、explicit orthogonality 等对照排除替代解释。</p>
      <p>报告中的 error bar 和统计口径以后统一采用认知心理学常用表达：以 LLM session 为独立单位，图中误差条报告 SEM；主要比较报告均值、SEM、t 检验或配对/差异中的差异检验，并清楚说明 choice round、LLM session 与 matched scenario id 的区别。</p>
    </div>
  </section>

  <section>
    <div class="wrap">
      <h2>结果一：普通漂亮话很难覆盖实际返还</h2>
      <div class="evidence">
        <h3>从 cheap talk 到 payoff tracking</h3>
        <p>V1 的 partner-level 结果中，trust rating 与平均返还高度相关，<strong>r = {fmt(v1_r)}</strong>。这意味着模型并不是简单地根据 apology、warmth 或 promise 做社会评价，而是很快把注意力放在对方实际返还了多少。</p>
        {table(["证据", "结果", "解释"], [
            ["V1", f"trust 与 average return 的 partner-level 相关为 <strong>{fmt(v1_r)}</strong>", "语言风格不是主要驱动，实际返还更强。"],
            ["V2-V4", "控制平均返还、加入噪声、yoked history 后，语言线索仍然很弱。", "模型更像是在估计 policy 和 expected value。"],
            ["V5", f"controllable stake WTP = <strong>{fmt(v5_controllable.get('willingness_to_pay'))}</strong>，fixed high stake WTP = <strong>{fmt(v5_fixed.get('willingness_to_pay'))}</strong>", "即使 moral trust 不高，可控性也会产生进入价值。"],
        ])}
        <div class="callout">这一阶段的关键教训是：如果只操纵漂亮话，故事会很薄。模型会把它当作弱 cue，并优先使用 revealed behavior。</div>
      </div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <h2>结果二：trust、WTP 与 investment 不是同一个变量</h2>
      <div class="evidence">
        <h3>模型可以不信任一个对象，但仍然愿意为机会付费</h3>
        <p>V5 说明，WTP 不能被简单解释成 social trust。一个对象可能被判断为不够可信，但如果它的风险可预测、可控制，模型仍可能愿意支付入场成本。这一点改变了后续实验的设计：我们不再把“信任”当成单一因变量，而是分别测 moral trust、WTP 和实际投资。</p>
        {bar_row("controllable stake WTP", v5_controllable.get("willingness_to_pay", 0), max_value=3)}
        {bar_row("fixed high stake WTP", v5_fixed.get("willingness_to_pay", 0), max_value=3)}
        <p class="caption">V5 中 WTP 更接近 option value，而不是单纯的道德信任评分。</p>
      </div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <h2>结果三：当 honesty 可核验时，它会迁移到 costly choice</h2>
      <div class="evidence">
        <h3>V7：一次性决策中的 payoff-matched honesty effect</h3>
        <p>V7 先让模型观察 advice task。诚实组和不诚实组的 recommendation win rate 都被匹配为 0.5，因此“更诚实”并不带来更高 advice payoff。即便如此，模型仍对诚实对象给出更高 WTP、investment 和 moral trust。</p>
        {bar_row("honest matched WTP", v7_honest.get("willingness_to_pay", 0), max_value=4)}
        {bar_row("dishonest matched WTP", v7_dishonest.get("willingness_to_pay", 0), max_value=4)}
        {bar_row("honest matched investment", v7_honest.get("investment", 0), max_value=5)}
        {bar_row("dishonest matched investment", v7_dishonest.get("investment", 0), max_value=5)}

        <h3>V8：逐轮投资中的 honesty bias 与收益代价</h3>
        <p>V8 把一次性 history prompt 改成 sequential trial-by-trial：每轮先给一个可核验陈述，再让模型投资，随后反馈真实值和返还。高诚实与低诚实 partner 的 return-rate sequence 被 yoked，因此返还政策本身相同。</p>
        {table(["条件", "truth rate", "return rate", "mean investment", "mean payoff"], [
            ["High honesty matched return", pct(v8_high.get("truth_rate")), pct(v8_high.get("mean_return_rate")), f"<strong>{fmt(v8_high.get('mean_investment'))}</strong>", f"<strong>{fmt(v8_high.get('mean_run_trial_payoff'))}</strong>"],
            ["Low honesty matched return", pct(v8_low.get("truth_rate")), pct(v8_low.get("mean_return_rate")), f"<strong>{fmt(v8_low.get('mean_investment'))}</strong>", f"<strong>{fmt(v8_low.get('mean_run_trial_payoff'))}</strong>"],
        ])}
        <div class="callout">V8 的关键 implication 是：低诚实对象并没有更差的返还政策，但模型因为较低 factual honesty 而投资更少，最终少拿到一部分 payoff。这可以被理解为 honesty proxy 带来的机会成本。</div>
      </div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <h2>结果四：honesty effect 有边界，且规则说明会改变策略</h2>
      <div class="evidence">
        <h3>V9：把 honesty 的来源拆开</h3>
        <p>V9 把 V8 扩成更系统的控制设计：partner 私有卡陈述、无陈述、无关事实真假、cheap talk only，以及 explicit orthogonality instruction。这个版本的价值在于排除一个简单解释：模型是不是只要看到“真/假反馈”就会机械迁移？结果并不支持这么简单的说法。模型仍强烈追踪 return policy，同时 honesty 的影响取决于陈述是否被理解成来自 partner 的社会合作信号。</p>
        {table(["V9 fair/high return 条件", "high honesty investment", "low honesty investment", "解释"], [
            ["standard instruction", f"{fmt(v9_standard_high.get('mean_investment'))}", f"{fmt(v9_standard_low.get('mean_investment'))}", "自然语境中，高诚实仍有优势。"],
            ["explicit orthogonality", f"{fmt(v9_ortho_high.get('mean_investment'))}", f"{fmt(v9_ortho_low.get('mean_investment'))}", "明确说明 truth 与 return 无因果关系后，低诚实条件反而更高，提示模型策略被重设。"],
        ])}

        <h3>V9b：反转不是普通注意力提示造成的</h3>
        <p>V9b 专门比较 natural、attention-control 与 explicit orthogonality。attention-control 仍保留高诚实优势，而 explicit orthogonality 出现明显反转，说明关键不是“多了一段说明”，而是这段说明的因果内容改变了模型如何解释低诚实对象。</p>
        {table(["instruction", "high investment", "low investment", "high-low gap"], [
            ["natural", fmt(v9b_nat.get("high_investment")), fmt(v9b_nat.get("low_investment")), fmt(v9b_nat.get("high_minus_low"))],
            ["attention control", fmt(v9b_attn.get("high_investment")), fmt(v9b_attn.get("low_investment")), fmt(v9b_attn.get("high_minus_low"))],
            ["explicit orthogonality", fmt(v9b_ortho.get("high_investment")), fmt(v9b_ortho.get("low_investment")), fmt(v9b_ortho.get("high_minus_low"))],
        ])}

        <h3>V10：中途 disclosure 的 within-session 检验</h3>
        <p>V10 把 orthogonality instruction 放到同一个 session 的中点。前 6 个 choice rounds 不说明 truth-return 无关；第 6 轮后，neutral 组只收到普通提醒，orthogonality 组收到“truth 与 return policy 无因果关系”的说明。这样可以看 disclosure 是否改变后半程投资，而不是比较完全不同 prompt 下的两个实验。</p>
        {table(["condition", "honesty", "phase", "n sessions", "mean investment ± SEM"], phase_rows)}
        <img class="figure-img" src="v10_audit_disclosure_switch/sessions/expanded_30seeds/figures/academic_phase_means.png" alt="V10 phase means">
        <p class="caption">V10 expanded session：误差条为 SEM，独立单位为 matched LLM session。</p>
        <div class="callout">V10 的差异中的差异为 <strong>DID = {fmt(did.get("mean"))}</strong>, SEM = {fmt(did.get("se"))}, t({did.get("df", "-")}) = {fmt(did.get("t"))}, p = {fmt(did.get("p"))}。这说明 disclosure 改变了 high-low honesty gap 的变化趋势：neutral 条件下 low honesty 的投资进一步下降，而 orthogonality disclosure 后 low honesty 的投资没有继续下降，反而有所恢复。</div>
      </div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <h2>当前解释</h2>
      <p>现在最有生命力的 story 是双机制：一方面，模型会做非常强的 payoff tracking；另一方面，模型也会把可核验 honesty 当作合作价值的代理变量。普通 cheap talk 太弱，通常抵不过行为证据；但 factual honesty 比 tone 更强，因为它带有事实反馈，容易被模型解释成稳定特质或合作倾向。</p>
      <p>V9-V10 让这个故事更细：honesty effect 不是无条件的。当我们明确告诉模型 truth 与 return policy 无关，它可以重新组织策略。最有趣的是，这种说明不只是让模型“少相信 honesty”，而可能增加对低诚实对象的探索性投资。一个可能解释是：低诚实原本被当作负面社会信号；规则说明解除这个负面先验后，模型转向根据近期 payoff 重新学习，因而在低诚实条件下增加 exploration。</p>
      <div class="callout warning">这个解释还不是最终结论。现在最需要的新实验不是再加很多变量，而是围绕“orthogonality disclosure 是否释放低诚实对象下的探索性投资”做一个更干净、更高样本、更可拟合参数的设计。</div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <h2>建议下一步</h2>
      <p>下一阶段不建议继续平行扩很多 V11/V12，而是把 V10 的关键现象做成主实验：保留 high vs low honesty 和 neutral vs orthogonality disclosure，固定 return policy，增加 LLM sessions，并把前几轮探索、后几轮利用、previous payoff sensitivity、truth-rate sensitivity 分开建模。</p>
      {table(["目标", "建议做法", "为什么"], [
          ["确认现象", "把 V10 expanded session 增加到预先确定的 LLM session 数，并保持 SEM 与 session-level 统计。", "判断 low-honesty exploration 是否稳定，而不是少数 session 的偶然波动。"],
          ["拟合机制", "用 trial-level computational model 估计 payoff learning rate、honesty prior weight、orthogonality discount、exploration temperature。", "把“看收益”和“看诚实”拆成可比较参数。"],
          ["排除提示效应", "保留 attention-control，与 explicit orthogonality 区分。", "确认不是额外说明或更长 prompt 本身造成策略变化。"],
          ["跨模型复现", "在 MiniMax 稳定后再跑 Qwen、DeepSeek、GPT/Claude 等。", "判断这是单模型特性还是更一般的 LLM 决策模式。"],
      ])}
    </div>
  </section>

  <section>
    <div class="wrap">
      <h2>版本证据索引</h2>
      <p>下面保留版本索引，方便回查单版本报告。总报告的正文只吸收每版对主线有贡献的证据，不把旧报告内容机械复制进来。</p>
      {table(["version", "role in argument", "HTML report", "data summary"], version_rows)}
      <h3>建议归档但暂不删除的旧报告</h3>
      {table(["file", "status"], archive_rows)}
      <p class="footer-note">Generated by <code>Rep_games/scripts/update_living_report.py</code>. Update workflow: finish a version-level report and summary.json, update <code>reports/report_manifest.json</code> if the version changes the main story, then rerun the script.</p>
    </div>
  </section>
</main>
</body>
</html>
"""
    return html_doc


def main() -> None:
    report = build_report()
    OUTPUT_PATH.write_text(report, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
