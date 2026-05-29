# V9b: Instruction-Control Test

Detailed report: [`output/report.html`](output/report.html).

V9b tests whether V9's `explicit_orthogonality` instruction is a neutral rule clarification or an active causal/rule cue.

The minimal design is:

```text
2 honesty levels x 1 fair/high return policy x 3 instruction types x 6 seeds x 18 trials
```

Instruction types:

- `natural`: inherited from V9 standard prompt.
- `explicit_orthogonality`: inherited from V9 explicit prompt.
- `attention_control`: newly run. It adds a similarly formal note, but does not state that truth and return are causally unrelated.

The main outcome is the high-low honesty gap in investment under each instruction type.
