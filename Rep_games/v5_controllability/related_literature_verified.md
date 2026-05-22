# Verified Related Literature

本清单服务于 V1-V5 的研究主线：

> 当 partner 说的话和做的事不一致时，LLM 能不能区分 verbal cue 和 behavioral evidence；并且 social trust 与 willingness to pay 是否是可分离的机制。

检索和核查原则：

- 优先列顶刊和顶会：Nature / Science / Nature Human Behaviour / Nature Neuroscience / Nature Communications / PNAS / PNAS Nexus / Neuron / Econometrica / AER / NeurIPS / ICLR。
- 每条只放已经核到题名、作者、venue、年份和 DOI 或官方页面的文献。
- “LLM 重复信任游戏”这一精确交叉点，目前未发现已经发表在顶刊或顶会的专门文章；最相关的是一篇 arXiv preprint，因此单独标注。

## A. LLM、agent 与互动博弈

### 1. Akata et al. (2025) — Playing repeated games with large language models

- Venue: Nature Human Behaviour
- DOI: https://doi.org/10.1038/s41562-025-02172-y
- 核查来源: https://www.nature.com/articles/s41562-025-02172-y
- 任务: LLM-vs-LLM、LLM-vs-hand-coded strategy、human-vs-LLM 的 finitely repeated 2 x 2 games。
- 主要游戏: Prisoner’s Dilemma family, Battle of the Sexes, 144 个 2 x 2 games。
- 相关性: 这是目前最重要的顶刊锚点。它说明可以用行为博弈论系统研究 LLM 的 repeated social interaction。对我们来说，它提供方法论合法性，但没有专门做 trust game，也没有把 verbal cue 与 behavioral evidence 的冲突作为主线。

### 2. Duan et al. (2024) — GTBench: Uncovering the Strategic Reasoning Limitations of LLMs via Game-Theoretic Evaluations

- Venue: NeurIPS 2024
- Paper: https://proceedings.neurips.cc/paper_files/paper/2024/file/3191170938b6102e5c203b036b7c16dd-Paper-Conference.pdf
- Code: https://github.com/jinhaoduan/GTBench
- 任务: 10 个 game-theoretic tasks，包含 complete/incomplete information、dynamic/static、probabilistic/deterministic settings，并有 LLM-vs-LLM 评估。
- 相关性: 顶会锚点。它支持“用 game-theoretic evaluations 测 LLM strategic reasoning limitations”。但它更偏逻辑和战略推理，不是社会信任、语言承诺和行为证据冲突。

### 3. Xu et al. (2025) — Large Language Models Often Say One Thing and Do Another

- Venue: ICLR 2025
- DBLP: https://dblp.org/rec/conf/iclr/XuLHZZ0S25
- arXiv: https://arxiv.org/abs/2503.07003
- 任务: Words and Deeds Consistency Test, WDCT。
- 相关性: 这是我们“说一套、做一套”主线最直接的顶会锚点。它关注 LLM 自己的 words-deeds inconsistency；我们的实验可以区别为：不是测试模型自己的原则是否一致，而是测试模型能否识别 partner 的 words-deeds inconsistency，并把该识别转化为 social trust 与 WTP 的不同输出。

### 4. Meta FAIR Diplomacy Team / Bakhtin et al. (2022) — Human-level play in the game of Diplomacy by combining language models with strategic reasoning

- Venue: Science
- DOI: https://doi.org/10.1126/science.ade9097
- 核查来源: https://www.eurekalert.org/news-releases/971930
- 任务: Diplomacy，多人自然语言谈判、合作和竞争。
- 相关性: 顶刊锚点。它证明语言模型可以被嵌入到策略互动中，并需要推断他人信念和意图。但它是工程系统，包含 planning + RL + dialogue model，不是 API-level behavioral experiment。

### 5. Dvorak et al. (2025) — Adverse reactions to the use of large language models in social interactions

- Venue: PNAS Nexus
- DOI: https://doi.org/10.1093/pnasnexus/pgaf112
- 核查来源: https://academic.oup.com/pnasnexus/article-abstract/doi/10.1093/pnasnexus/pgaf112/8107485
- 任务: 人类参与者在 Ultimatum Game、Binary Trust Game、Prisoner’s Dilemma、Stag Hunt、Coordination Game 中与 ChatGPT-mediated partner 互动。
- 相关性: 很适合作为 human-AI trust 背景。它不是让 LLM 自己做 repeated trust decision，而是看人知道 AI 介入后如何降低信任与合作。

### 6. Xie, Mei, Yuan & Jackson (2025) — Using large language models to categorize strategic situations and decipher motivations behind human behaviors

- Venue: PNAS
- DOI: https://doi.org/10.1073/pnas.2512075122
- 核查来源: https://ideas.repec.org/a/nas/journl/v122y2025pe2512075122.html
- 任务: Dictator Game、Ultimatum Game、Investment Game、Public Goods Game、Bomb Risk Game 等经典经济游戏。
- 相关性: 顶刊锚点。它把 LLM 用作 strategic situation / motivation 的分类工具。对我们有用的是：可以把 LLM 输出看成对情境动机和策略结构的可操作读数，而不是只看文本质量。

### 7. Ou et al. (2025) — Social preferences with unstable interactive reasoning: Large language models in economic trust games

- Status: arXiv preprint, not verified as top-journal/top-conference publication
- arXiv: https://arxiv.org/abs/2505.17053
- 任务: ChatGPT-4、Claude、Bard 在 economic trust games 中作为玩家，包含 one-shot 和 multi-round scenarios，以及 persona prompting。
- 相关性: 这是“LLM + economic trust games”最直接相关的一篇，但目前不是顶刊/顶会。它的结论里有一点很适合对照：LLMs 有 trust/reciprocity 倾向，但 multi-round interactive reasoning 不稳定，persona prompt 影响很大。

## B. 人类 repeated trust game / cheap talk / promise

### 8. Berg, Dickhaut & McCabe (1995) — Trust, Reciprocity, and Social History

- Venue: Games and Economic Behavior
- DOI: https://doi.org/10.1006/game.1995.1027
- 核查来源: https://cir.nii.ac.jp/crid/1362544418972953984
- 任务: 经典 trust game / investment game。
- 相关性: trust game 的基础范式。我们的 `willingness_to_pay`、投资、返还比例都可以锚定在这一传统上。

### 9. Axelrod & Hamilton (1981) — The Evolution of Cooperation

- Venue: Science
- DOI: https://doi.org/10.1126/science.7466396
- 核查来源: https://cir.nii.ac.jp/crid/1362544421299593344
- 任务: Iterated Prisoner’s Dilemma, tit-for-tat, repeated interaction。
- 相关性: 重复互动中合作、背叛、宽恕、声誉形成的经典理论锚点。

### 10. Dal Bo (2005) — Cooperation under the Shadow of the Future: Experimental Evidence from Infinitely Repeated Games

- Venue: American Economic Review
- 核查来源: https://econpapers.repec.org/RePEc:aea:aecrev:v:95:y:2005:i:5:p:1591-1604
- 任务: infinitely repeated games, shadow of the future。
- 相关性: 人类在重复博弈中如何因为未来互动而改变合作行为。对我们有用的是“模型是否真的在追踪未来互动结构”，而不是只做单轮启发式判断。

### 11. Charness & Dufwenberg (2006) — Promises and Partnership

- Venue: Econometrica
- DOI: https://doi.org/10.1111/j.1468-0262.2006.00719.x
- 核查来源: https://experts.arizona.edu/en/publications/promises-and-partnership
- 任务: communication, promises, lies, beliefs, trust/cooperation。
- 相关性: 这是 verbal cue 如何影响 trust/cooperation 的顶级经济学锚点。我们的实验可以接它的问题，但转向 LLM 是否能识别 promise 与 actual behavior 的分离。

### 12. Vanberg (2008) — Why Do People Keep Their Promises? An Experimental Test of Two Explanations

- Venue: Econometrica
- DOI: https://doi.org/10.3982/ECTA7673
- 核查来源: https://www.econometricsociety.org/publications/econometrica/2008/11/01/why-do-people-keep-their-promises-experimental-test-two
- 任务: promise keeping, expectation vs preference for keeping one’s word。
- 相关性: 支持“语言承诺不只是信息，也可能是一种社会规范和自我约束”。我们的 LLM 实验可以问：模型是否把 partner 的承诺当作规范信号，还是在行为冲突后折价。

### 13. Crawford & Sobel (1982) — Strategic Information Transmission

- Venue: Econometrica
- DOI: https://doi.org/10.2307/1913390
- 核查来源: https://www.haverford.edu/sites/default/files/CrawfordSobel1982.pdf
- 任务: cheap talk / sender-receiver strategic communication。
- 相关性: cheap talk 理论基础。我们的 verbal cue 可被定义为 cheap talk，因为它不直接改变 payoff，但可能改变 receiver belief。

### 14. Farrell & Rabin (1996) — Cheap Talk

- Venue: Journal of Economic Perspectives
- DOI: https://doi.org/10.1257/jep.10.3.103
- 核查来源: https://www.aeaweb.org/articles?id=10.1257/jep.10.3.103
- 任务: cheap talk 综述。
- 相关性: 适合写 introduction，说明“cheap talk 并非总是无效，也并非总是可信；关键取决于利益一致性、可验证性和互动结构”。

## C. fMRI / neuroeconomics of trust

### 15. McCabe et al. (2001) — A functional imaging study of cooperation in two-person reciprocal exchange

- Venue: PNAS
- DOI: https://doi.org/10.1073/pnas.211415698
- 核查来源: https://cir.nii.ac.jp/crid/1361137043600205184
- 任务: reciprocal exchange / trust-like game with fMRI。
- 相关性: 早期把 reciprocal exchange 与脑成像结合的顶刊研究。

### 16. King-Casas et al. (2005) — Getting to Know You: Reputation and Trust in a Two-Person Economic Exchange

- Venue: Science
- DOI: https://doi.org/10.1126/science.1108062
- 核查来源: https://cir.nii.ac.jp/crid/1362544420891911552
- 任务: multiround trust game + fMRI。
- 相关性: 对 V5 特别重要。它表明人类会在多轮 exchange 中形成 reputation，并且 dorsal striatum 的反应与下一轮 trust intention 和声誉形成有关。

### 17. Delgado, Frank & Phelps (2005) — Perceptions of moral character modulate the neural systems of reward during the trust game

- Venue: Nature Neuroscience
- 核查来源: https://www.nature.com/articles/nn1575
- 任务: prior moral character information + trust game。
- 相关性: 说明 prior social/moral information 可以调制 reward learning。对我们的 verbal cue / social trust 很有启发：语言或评价信息可能改变对相同行为证据的解释。

### 18. Kosfeld et al. (2005) — Oxytocin increases trust in humans

- Venue: Nature
- DOI: https://doi.org/10.1038/nature03701
- 核查来源: https://pubmed.ncbi.nlm.nih.gov/15931222/
- 任务: oxytocin manipulation + trust game。
- 相关性: 证明 trust 可以被生物状态操纵。不是我们当前主线的直接方法，但适合说明 trust 不是纯 payoff calculation。

### 19. Baumgartner et al. (2008) — Oxytocin shapes the neural circuitry of trust and trust adaptation in humans

- Venue: Neuron
- DOI: https://doi.org/10.1016/j.neuron.2008.04.009
- 核查来源: https://pubmed.ncbi.nlm.nih.gov/18498743/
- 任务: oxytocin + fMRI + breach of trust / trust adaptation。
- 相关性: 与我们最相关的是“breach 后是否更新 trust”。它显示人类的 trust adaptation 会被 oxytocin 改变，并涉及 amygdala、midbrain、dorsal striatum。

### 20. Krueger et al. (2007) — Neural correlates of trust

- Venue: PNAS
- DOI: https://doi.org/10.1073/pnas.0710103104
- 核查来源: https://pmc.ncbi.nlm.nih.gov/articles/PMC2148426/
- 任务: sequential reciprocal trust game + hyperscanning fMRI。
- 相关性: 对“conditional vs unconditional trust”很重要，可作为 social trust 不是单一变量的神经证据。

### 21. Phan et al. (2010) — Reputation for reciprocity engages the brain reward center

- Venue: PNAS
- DOI: https://doi.org/10.1073/pnas.1008137107
- 核查来源: https://pubmed.ncbi.nlm.nih.gov/20615982/
- 任务: iterative trust game with fictive partners acquiring different reputations。
- 相关性: 与 V5 的 partner policy / reputation tracking 非常贴近。重点是 reciprocal reputation 调制 ventral striatum 和 orbitofrontal cortex。

### 22. Bellucci, Molter & Park (2019) — Neural representations of honesty predict future trust behavior

- Venue: Nature Communications
- DOI: https://doi.org/10.1038/s41467-019-13261-8
- 核查来源: https://www.nature.com/articles/s41467-019-13261-8
- 任务: take advice game + one-shot trust game + fMRI/MVPA。
- 相关性: 这篇和我们的“说/做分离”主线很近。它把 honest/dishonest behavior 和 subsequent trust behavior 分开，并试图解码 neural representation of trustworthiness。

## D. 当前研究的定位

从上述文献看，我们的 V1-V5 可以这样定位：

1. 不是简单复现 LLM repeated games。Akata et al. 已经在 NHB 做了大规模 repeated 2 x 2 games。
2. 不是泛泛研究 LLM strategic reasoning。GTBench 已经在 NeurIPS 做了 game-theoretic evaluation。
3. 我们的更具体切口是：在 repeated trust-like interaction 中，LLM 是否能把 partner 的 verbal cue 与 behavioral evidence 分开。
4. 进一步的问题是：即使模型根据行为降低 social trust，它是否仍会因为可控、可预测、可获利而保持 WTP。
5. 这个切口连接三条顶级文献线：
   - LLM repeated game / strategic reasoning
   - human cheap talk / promise / trust game
   - neural and behavioral evidence for reputation learning and trust adaptation

一句话定位：

> Prior work asks whether LLMs can play repeated games or whether humans trust AI. Our question is whether LLMs can separate what a partner says from what the partner does, and whether this separation produces dissociable social-trust and costly-choice signals.
