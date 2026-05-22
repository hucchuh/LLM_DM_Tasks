from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "v1_v4_integrated_experiment_report.html"


MAIN = r"""  <main>
    <section>
      <div class="wrap">
        <h2>研究问题和任务</h2>
        <p class="lead">这份报告只回答一个具体问题：在重复信任博弈中，当同一个对象“说得好听”和“实际返还记录”不完全一致时，大语言模型后续更相信哪一类信息？</p>

        <div class="grid">
          <div class="box">
            <h3>任务怎么做</h3>
            <p>模型看到一个对象过去几轮的互动记录。每一轮都有两类信息：对象说了什么，以及它实际返还了多少。随后模型要判断是否继续合作、愿意付多少入场费、下一轮投多少，以及给出信任评分。</p>
          </div>
          <div class="box">
            <h3>核心比较</h3>
            <p>我们把语言线索和行为记录尽量拆开：语言包括中性表达、温暖表达、承诺、道歉；行为包括稳定返还、机会主义、高赌注背叛、逐步修复和逐步恶化。</p>
          </div>
          <div class="box">
            <h3>报告读法</h3>
            <p>下面不再单独讲抽象背景，而是按实验版本展开。每一版先说明怎么操纵变量，再说明结果和不足，最后交代下一版具体修正了什么。</p>
          </div>
        </div>
      </div>
    </section>

    <section class="version band">
      <div class="wrap">
        <h2>V1：开放式 pilot，先看任务里有没有信号</h2>
        <div class="version-layout">
          <div>
            <h3>操作的实验变量</h3>
            <p>V1 同时改变对象的语言风格和返还行为，形成六类对象：稳定合作者、谨慎但可靠者、真实修复者、机会主义者、会说话但少返还者、只道歉不修复者。</p>
            <table>
              <thead>
                <tr>
                  <th>对象类型</th>
                  <th>语言线索</th>
                  <th>行为记录</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>稳定合作者</td><td>友好、承诺长期合作</td><td>稳定公平返还</td></tr>
                <tr><td>谨慎但可靠者</td><td>不夸张承诺，表达谨慎</td><td>稳定公平返还</td></tr>
                <tr><td>真实修复者</td><td>低返还后道歉，并在后续补偿</td><td>有波动，但会修复</td></tr>
                <tr><td>机会主义者</td><td>表面合作，尤其高赌注前更友好</td><td>低赌注较公平，高赌注少返还</td></tr>
                <tr><td>会说话但少返还者</td><td>温暖、解释充分</td><td>持续偏低返还</td></tr>
                <tr><td>只道歉不修复者</td><td>反复道歉和解释</td><td>持续低返还，没有补偿</td></tr>
              </tbody>
            </table>

            <h3>实验流程</h3>
            <p>每个试次给模型一段完整历史：每轮赌注大小、对方说的话、投资额、对方收到多少、返还多少。模型随后输出下一轮投资、预期返还比例、信任评分和信心。V1 共 24 个试次，成功解析 23 个。</p>

            <h3>主要结论</h3>
            <div class="callout claim">
              <p>模型明显会看实际返还。稳定公平返还和真实修复得到高信任；会说话但少返还、只道歉不修复得到低信任和低投资。这说明任务本身可以产生“语言 vs 行为”的分离信号。</p>
            </div>
          </div>

          <div>
            <div class="box">
              <h3>关键结果</h3>
              <table>
                <thead>
                  <tr>
                    <th>对象类型</th>
                    <th class="num">平均返还</th>
                    <th class="num">信任评分</th>
                    <th class="num">下一轮投资</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td>稳定合作者</td><td class="num">0.503</td><td class="num">78.25</td><td class="num">10.00</td></tr>
                  <tr><td>谨慎但可靠者</td><td class="num">0.502</td><td class="num">70.25</td><td class="num">10.00</td></tr>
                  <tr><td>真实修复者</td><td class="num">0.481</td><td class="num">68.75</td><td class="num">10.00</td></tr>
                  <tr><td>机会主义者</td><td class="num">0.400</td><td class="num">51.00</td><td class="num">8.50</td></tr>
                  <tr><td>会说话但少返还者</td><td class="num">0.331</td><td class="num">38.25</td><td class="num">4.50</td></tr>
                  <tr><td>只道歉不修复者</td><td class="num">0.283</td><td class="num">27.67</td><td class="num">1.67</td></tr>
                </tbody>
              </table>
              <p>对象层面的信任评分和平均返还几乎同步变化，相关约为 0.992。</p>
            </div>

            <div class="callout warning">
              <p><strong>主要不足：</strong>V1 里不同对象的平均返还本来就不同。因此，结果可能只是说明模型会看平均返还，而不能说明模型理解了“对方在不同情境下怎么行动”。</p>
            </div>
            <div class="callout">
              <p><strong>下一版怎么改：</strong>V2 把所有条件的平均返还控制成相同，只改变返还出现的位置和模式，专门检验模型是否只看平均值。</p>
            </div>
          </div>
        </div>

        <h3>V1 图表</h3>
        <div class="figure-grid">
          <figure class="figure">
            <img src="figures_cn/v1_trust_by_partner_cn.png" alt="V1 不同对象的信任评分">
            <figcaption class="caption">V1 信任评分：返还稳定、公平的对象得分最高；会说好话但持续少返还、只道歉不修复的对象明显更低。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v1_investment_by_partner_cn.png" alt="V1 不同对象的下一轮投资">
            <figcaption class="caption">V1 下一轮投资：模型愿意继续把钱投给可靠对象和真实修复者，而不是只看对方话说得是否好听。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v1_trust_vs_return_cn.png" alt="V1 对象层面信任与平均返还">
            <figcaption class="caption">V1 对象层面关系：不同对象的平均返还越高，模型给出的信任评分越高。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v1_trial_return_trust_cn.png" alt="V1 逐试次信任与平均返还">
            <figcaption class="caption">V1 逐试次关系：即使不按对象类型汇总，单次历史中的平均返还也和信任评分同步变化。</figcaption>
          </figure>
        </div>
      </div>
    </section>

    <section class="version">
      <div class="wrap">
        <h2>V2：控制平均返还，测试模型是否理解行为模式</h2>
        <div class="version-layout">
          <div>
            <h3>操作的实验变量</h3>
            <p>V2 的核心操作是：所有条件的平均返还都等于 0.40，只改变返还的分布方式。例如，一个对象在低赌注时返还高、高赌注时返还低；另一个对象正好相反。</p>
            <table>
              <thead>
                <tr>
                  <th>条件</th>
                  <th>行为安排</th>
                  <th class="num">平均返还</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>稳定中性</td><td>每轮都返还 0.40，语言中性</td><td class="num">0.40</td></tr>
                <tr><td>稳定温暖</td><td>每轮都返还 0.40，语言温暖</td><td class="num">0.40</td></tr>
                <tr><td>高赌注背叛</td><td>低赌注返还高，高赌注返还低</td><td class="num">0.40</td></tr>
                <tr><td>高赌注慷慨</td><td>低赌注返还低，高赌注返还高</td><td class="num">0.40</td></tr>
                <tr><td>逐步修复</td><td>早期低返还，后期逐渐提高</td><td class="num">0.40</td></tr>
                <tr><td>逐步恶化</td><td>早期高返还，后期逐渐下降</td><td class="num">0.40</td></tr>
              </tbody>
            </table>

            <h3>实验流程</h3>
            <p>模型看到过去几轮完整记录后，需要分别判断低、中、高赌注下对方会返还多少，并给出相应投资和总体信任评分。V2 共 36 个成功试次，每个条件 6 个试次。</p>

            <h3>主要结论</h3>
            <div class="callout claim">
              <p>模型不是只看平均返还。即使平均返还完全相同，它仍然能区分“高赌注更危险”和“高赌注更值得信任”的对象，并据此改变高赌注投资。</p>
            </div>
          </div>

          <div>
            <div class="box">
              <h3>关键结果</h3>
              <table>
                <thead>
                  <tr>
                    <th>条件</th>
                    <th class="num">信任</th>
                    <th class="num">高低赌注预测差</th>
                    <th class="num">高赌注投资</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td>稳定中性</td><td class="num">73.33</td><td class="num">0.00</td><td class="num">10</td></tr>
                  <tr><td>稳定温暖</td><td class="num">57.17</td><td class="num">0.00</td><td class="num">10</td></tr>
                  <tr><td>高赌注背叛</td><td class="num">49.17</td><td class="num">-0.30</td><td class="num">0</td></tr>
                  <tr><td>高赌注慷慨</td><td class="num">77.50</td><td class="num">+0.30</td><td class="num">10</td></tr>
                  <tr><td>逐步修复</td><td class="num">59.50</td><td class="num">+0.075</td><td class="num">10</td></tr>
                  <tr><td>逐步恶化</td><td class="num">35.00</td><td class="num">-0.028</td><td class="num">0</td></tr>
                </tbody>
              </table>
              <p>最清楚的分离来自高赌注条件：高赌注背叛时，模型把高赌注预测降低 0.30；高赌注慷慨时，则提高 0.30。</p>
            </div>

            <div class="callout warning">
              <p><strong>主要不足：</strong>V2 太整齐，容易被模型当成找规律题。它还显式要求模型分别预测低、中、高赌注下的返还，这可能提示模型去寻找赌注差异。</p>
            </div>
            <div class="callout">
              <p><strong>下一版怎么改：</strong>V3 加入噪声，让返还记录不再整齐；同时系统加入语言条件，检验温暖承诺和道歉解释是否能改变判断。</p>
            </div>
          </div>
        </div>

        <h3>V2 图表</h3>
        <div class="figure-grid">
          <figure class="figure">
            <img src="figures_cn/v2_trust_by_condition_cn.png" alt="V2 平均返还相同条件下的信任评分">
            <figcaption class="caption">V2 总体信任：所有条件平均返还都控制为 0.40，但模型仍区分稳定、修复、恶化和高赌注背叛。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v2_conditional_predictions_cn.png" alt="V2 不同赌注下的预期返还">
            <figcaption class="caption">V2 条件化预测：模型不只记一个平均值，而是能说出低、中、高赌注下对方可能返还多少。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v2_high_low_gap_cn.png" alt="V2 高低赌注预测差">
            <figcaption class="caption">V2 高低赌注差：高赌注背叛条件为负，高赌注慷慨条件为正，说明模型在追踪“什么时候更危险”。</figcaption>
          </figure>
        </div>
      </div>
    </section>

    <section class="version band">
      <div class="wrap">
        <h2>V3：加入噪声和语言条件，检验结果是否仍然成立</h2>
        <div class="version-layout">
          <div>
            <h3>操作的实验变量</h3>
            <p>V3 同时操纵两类变量：行为记录和语言说法。行为记录包括稳定中等返还、机会主义、逐步修复、只道歉不修复；语言说法包括中性、温暖承诺、道歉解释。</p>
            <table>
              <thead>
                <tr>
                  <th>变量</th>
                  <th>水平</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>行为记录</td><td>稳定中等、机会主义、逐步修复、只道歉不修复</td></tr>
                <tr><td>语言说法</td><td>中性、温暖承诺、道歉解释</td></tr>
                <tr><td>记录形式</td><td>每段历史 6 轮；返还率带有噪声，不再呈现整齐数列</td></tr>
              </tbody>
            </table>

            <h3>实验流程</h3>
            <p>V3 共 72 个成功试次。模型看到 6 轮历史后，回答总体信任、不同赌注下的预期返还和投资。另有一个探索性问题询问模型自报更依赖行为还是说法。</p>

            <h3>主要结论</h3>
            <div class="callout claim">
              <p>加入噪声和语言条件后，行为记录仍然是主要来源。机会主义和只道歉不修复显著降低高赌注预期；逐步修复则提高高赌注预期。语言说法有小幅影响，但解释力远低于行为记录。</p>
            </div>
          </div>

          <div>
            <div class="box">
              <h3>关键结果</h3>
              <table>
                <thead>
                  <tr>
                    <th>行为记录</th>
                    <th class="num">高低赌注预测差</th>
                    <th class="num">高赌注投资</th>
                    <th class="num">信任</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td>稳定中等</td><td class="num">-0.005</td><td class="num">9.444</td><td class="num">64.500</td></tr>
                  <tr><td>机会主义</td><td class="num">-0.299</td><td class="num">3.333</td><td class="num">44.722</td></tr>
                  <tr><td>逐步修复</td><td class="num">+0.222</td><td class="num">9.722</td><td class="num">65.944</td></tr>
                  <tr><td>只道歉不修复</td><td class="num">-0.160</td><td class="num">1.444</td><td class="num">36.389</td></tr>
                </tbody>
              </table>
              <p>按简单解释力估算，信任评分主要由行为记录解释；语言说法只能解释很小一部分变化。高低赌注预测差几乎完全由行为记录决定。</p>
            </div>

            <div class="callout warning">
              <p><strong>主要不足：</strong>V3 仍然太像解释题。它要求模型估计不同赌注下的返还，还问了自报权重，这会暴露研究目的。自报“我更看重行为”不能作为机制证据。</p>
            </div>
            <div class="callout">
              <p><strong>下一版怎么改：</strong>V4 不再问模型估计平均返还，也不问它依赖什么信息；只问愿意付多少继续互动、下一轮投多少。并且把同一段数字行为记录复制成不同语言版本，干净分离语言本身的影响。</p>
            </div>
          </div>
        </div>

        <h3>V3 图表</h3>
        <div class="figure-grid">
          <figure class="figure">
            <img src="figures_cn/v3_trust_by_behavior_language_cn.png" alt="V3 行为记录与说法对信任评分的影响">
            <figcaption class="caption">V3 信任评分：加入噪声以后，行为记录仍然拉开主要差异；说法只带来小幅波动。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v3_high_low_gap_cn.png" alt="V3 高低赌注预测差">
            <figcaption class="caption">V3 高低赌注差：机会主义和只道歉不修复让模型预期高赌注更糟，逐步修复则让高赌注预期更好。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v3_language_trust_cn.png" alt="V3 说法对信任评分的平均影响">
            <figcaption class="caption">V3 说法平均影响：温暖承诺和道歉解释会轻微改变信任，但幅度远小于行为记录。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v3_self_report_weight_cn.png" alt="V3 自报权重">
            <figcaption class="caption">V3 自报权重：模型自己也说更依赖行为记录；不过这个题会暴露研究目的，所以只作为探索性结果。</figcaption>
          </figure>
        </div>
      </div>
    </section>

    <section class="version">
      <div class="wrap">
        <h2>V4：只换说法，不换行为，直接问有成本的选择</h2>
        <div class="version-layout">
          <div>
            <h3>操作的实验变量</h3>
            <p>V4 是目前最干净的一版。同一段数字行为记录会被复制成四个语言版本，数字完全一样，只替换对方说的话：中性、温暖、承诺、道歉。行为记录、语言说法和下一轮赌注大小形成交叉设计。</p>
            <table>
              <thead>
                <tr>
                  <th>变量</th>
                  <th>水平</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>行为记录</td><td>稳定中等、机会主义、逐步修复、逐步恶化</td></tr>
                <tr><td>语言说法</td><td>中性、温暖、承诺、道歉</td></tr>
                <tr><td>下一轮赌注</td><td>低赌注、中赌注、高赌注</td></tr>
                <tr><td>因变量</td><td>是否继续、愿意支付的入场费、下一轮投资、信任评分</td></tr>
              </tbody>
            </table>

            <h3>实验流程</h3>
            <p>模型看到一段历史记录后，不再被要求估计平均返还，也不需要解释自己依赖什么信息。它只需要做选择：是否继续和这个对象互动、最多愿意付多少入场费、下一轮愿意投多少、信任评分是多少。V4 共 96 个成功试次。</p>

            <h3>主要结论</h3>
            <div class="callout claim">
              <p>在最干净的设计里，行为记录仍然主导结果。逐步恶化几乎不值得继续；逐步修复获得最高入场费和最高投资。语言说法本身有局部影响，例如道歉会略微提高入场费，但不足以解释主要选择变化。</p>
            </div>
          </div>

          <div>
            <div class="box">
              <h3>关键结果</h3>
              <table>
                <thead>
                  <tr>
                    <th>行为记录</th>
                    <th class="num">入场费</th>
                    <th class="num">投资比例</th>
                    <th class="num">信任</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td>逐步恶化</td><td class="num">0.042</td><td class="num">0.167</td><td class="num">28.917</td></tr>
                  <tr><td>逐步修复</td><td class="num">3.375</td><td class="num">1.000</td><td class="num">65.208</td></tr>
                  <tr><td>稳定中等</td><td class="num">1.333</td><td class="num">0.964</td><td class="num">62.792</td></tr>
                  <tr><td>机会主义</td><td class="num">2.000</td><td class="num">0.710</td><td class="num">48.875</td></tr>
                </tbody>
              </table>
              <p>简单解释力估算显示，行为记录对入场费、投资比例、信任评分的解释力都明显高于语言说法。</p>
            </div>

            <div class="callout warning">
              <p><strong>主要不足：</strong>V4 仍然只是单一模型的 API 层面结果，不是真实人类被试实验；它也还是一次性给完整历史，而不是逐轮动态更新。因此它能证明任务中的稳定输出模式，但还不能证明模型拥有类似人类的信任更新机制。</p>
            </div>
            <div class="callout">
              <p><strong>下一步怎么改：</strong>用 V4 作为主实验原型，先做多模型重复，再做逐轮动态版本，最后加入真实人类被试。这样可以区分：这是某个模型的提示词行为，还是更一般的模型决策规律。</p>
            </div>
          </div>
        </div>

        <h3>V4 图表</h3>
        <div class="figure-grid">
          <figure class="figure">
            <img src="figures_cn/v4_wtp_by_behavior_language_cn.png" alt="V4 行为记录与说法对入场费的影响">
            <figcaption class="caption">V4 入场费：同一段行为记录只换说法时，模型愿意付出的成本主要仍随行为记录变化。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v4_investment_by_behavior_stake_cn.png" alt="V4 行为记录与赌注对投资比例的影响">
            <figcaption class="caption">V4 下一轮投资比例：模型对逐步恶化者几乎不再投资，对机会主义对象在高赌注时明显收缩。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v4_trust_by_behavior_language_cn.png" alt="V4 行为记录与说法对信任评分的影响">
            <figcaption class="caption">V4 信任评分：说法有局部波动，但稳定修复和逐步恶化之间的差异主要来自实际返还历史。</figcaption>
          </figure>
          <figure class="figure">
            <img src="figures_cn/v4_language_wtp_cn.png" alt="V4 说法对入场费的平均影响">
            <figcaption class="caption">V4 说法平均影响：道歉条件下入场费略高，但整体语言差异很小，不能解释主要选择变化。</figcaption>
          </figure>
        </div>
      </div>
    </section>

    <section class="band">
      <div class="wrap">
        <h2>跨版本总结</h2>
        <p class="lead">四版实验的递进可以压缩成一句话：V1 发现模型会看行为，V2 排除“只看平均值”，V3 检查噪声和语言条件，V4 用更干净的有成本选择确认主结果。</p>
        <div class="finding-grid">
          <div class="finding">
            <span class="finding-number">01</span>
            <h3>最稳定的结果</h3>
            <p>模型的信任评分、愿意付出的入场费和下一轮投资，主要随实际返还记录变化，而不是随漂亮话、承诺或道歉稳定变化。</p>
          </div>
          <div class="finding">
            <span class="finding-number">02</span>
            <h3>不是简单平均</h3>
            <p>平均返还相同的时候，模型仍然会区分返还发生在低赌注还是高赌注、趋势是在修复还是恶化。</p>
          </div>
          <div class="finding">
            <span class="finding-number">03</span>
            <h3>语言不是完全没用</h3>
            <p>语言会产生局部影响，尤其可能影响“要不要再给一次机会”或愿意付的小额成本。但它目前不是主要驱动力。</p>
          </div>
          <div class="finding">
            <span class="finding-number">04</span>
            <h3>下一步最关键</h3>
            <p>正式研究应以 V4 为主模板，扩大到多模型、逐轮动态更新和人类被试对照。这样才能把“API 输出规律”推进到更强的机制解释。</p>
          </div>
        </div>

        <div class="two-col">
          <div class="box">
            <h3>现在可以怎样讲这个 story</h3>
            <p>在重复信任博弈中，大语言模型并不会稳定地被友好语言或道歉牵着走。它更像是在追踪对方过去是否兑现合作，尤其会注意高赌注下是否背叛、后续是否修复。</p>
          </div>
          <div class="box">
            <h3>现在还不能怎样讲</h3>
            <p>不能说模型真的像人一样形成了信任，也不能说所有模型都如此。当前结论更准确地说是：在这个范式中，模型输出表现出对行为记录的强依赖。</p>
          </div>
        </div>
      </div>
    </section>

    <section>
      <div class="wrap">
        <h2>附录：示例提示词</h2>
        <p class="lead">下面不是完整逐字复现所有试次，而是整理后的提示词骨架，方便理解模型到底看到什么、回答什么。</p>

        <div class="prompt-box">
          <h3>早期版本：看历史后决定下一轮投资</h3>
          <p>这一版主要用于观察模型是否会根据过去返还调整信任和投资。</p>
          <pre>你正在和同一个对象进行多轮投资游戏。
每轮你有 10 个代币，可以投入 0 到 10 个。
你的投入会变成三倍交给对方，对方再决定返还多少。

下面是你和这个对象过去几轮的记录：
第 1 轮（低赌注）：对方说：“我重视长期合作。”你投入 4 个，对方收到 12 个，返还 6.1 个。
第 2 轮（中赌注）：……

现在你要决定下一轮还投多少。
请只用 JSON 回答：
{
  "investment_next": 0,
  "predicted_return_fraction_next": 0.0,
  "trust_rating": 0,
  "confidence": 0.0
}</pre>
        </div>

        <div class="prompt-box">
          <h3>V2/V3：询问不同赌注下的判断</h3>
          <p>这一类问题帮助我们看模型是否区分低赌注和高赌注，但也更容易让任务像找规律。</p>
          <pre>你看到同一个对象过去几轮的互动记录。
请判断：
- 如果下一轮是低赌注，你预计对方会返还多少比例？
- 如果下一轮是中赌注，你预计对方会返还多少比例？
- 如果下一轮是高赌注，你预计对方会返还多少比例？
- 每种情况下你愿意投入多少？
- 你对这个对象的信任评分是多少？

请只用 JSON 回答。</pre>
        </div>

        <div class="prompt-box">
          <h3>V4：同一行为记录只换说法，问有成本的选择</h3>
          <p>这是目前最关键的版本。模型不再被要求估计平均值，而是做一个继续互动的选择。</p>
          <pre>你正在决定是否继续和一个对象互动。
规则：
- 低赌注最多投入 4 个代币；
- 中赌注最多投入 7 个代币；
- 高赌注最多投入 10 个代币；
- 投入会变成三倍交给对方，对方再返还一部分。

你观察到这个对象过去几轮的记录：
第 1 轮（低赌注）：对方说：“我已经记录了这一轮。”上一位参与者投入 4 个，对方收到 12 个，返还 5.0 个。
第 2 轮（高赌注）：……

现在即将开始一个新的高赌注回合。
如果继续，请说明你最多愿意从额外 10 个代币中支付多少入场费。
然后说明你下一轮愿意投入多少。

请只用 JSON 回答：
{
  "continue_interaction": true,
  "willingness_to_pay": 0,
  "investment_next": 0,
  "trust_rating": 0
}</pre>
        </div>
      </div>
    </section>
  </main>"""


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    start_idx = text.index(start)
    end_idx = text.index(end, start_idx) + len(end)
    return text[:start_idx] + replacement + text[end_idx:]


def main() -> None:
    html = HTML.read_text(encoding="utf-8")
    html = replace_between(html, "  <main>", "  </main>", MAIN)
    html = html.replace(
        "这份报告把 V1 到 V4 的实验递进讲清楚：我们怎样一步步排除替代解释，为什么最后更相信“行为记录主导选择”这个结论。",
        "这份报告按实验版本呈现：每一版都写清变量、流程、结果、主要结论、主要不足，以及下一版如何修正前一版的问题。",
    )
    HTML.write_text(html, encoding="utf-8", newline="\n")
    from update_home_and_actual_prompts import update_html as apply_home_and_prompt_updates

    apply_home_and_prompt_updates()
    print(f"updated {HTML}")


if __name__ == "__main__":
    main()
