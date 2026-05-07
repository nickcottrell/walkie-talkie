# Walkie-Talkie Round-Trip Benchmark

The load-bearing artifact for this repo. Without a measurable round-trip
score, walkie-talkie is just code in a folder.

## What it measures

Round-trip semantic preservation across paraphrase pairs. The encoder is
asked to produce a geometric record from each surface form of the same
underlying content, and the benchmark scores how well those records
agree.

Five metrics:

1. **Topic agreement rate** — fraction of clusters where every paraphrase
   resolves to the same `topic_band`, and that label matches the expected one.
2. **Polarity-sign agreement rate** — fraction of clusters where the polarity
   sign (positive / negative / neutral) is uniform and matches expectation.
3. **Regime agreement rate** — fraction of clusters where every paraphrase
   resolves to the same regime label (and matches expectation if one is set).
4. **Mean basin dispersion** — average max-pairwise shortest-arc hue distance
   between basin centroids within a cluster, in degrees. Lower is more stable.
   The basin-stability score reported in the composite is `1 - dispersion/180°`.
5. **Refusal uniformity** — fraction of refusal-case inputs (PEM private key
   blocks etc.) that the encoder correctly refuses.

The **composite score** is the mean of all five.

## Corpus

`corpus.py` defines paraphrase clusters by hand. Each cluster carries a
label, expected topic, expected polarity, expected regime, and 2–4 surface
paraphrases. The corpus is small and curated — this is a smoke benchmark,
not a published evaluation.

## Running

```
python3 benchmark/run.py
```

Writes:
- `benchmark/output/score.json` — machine-readable metrics + per-cluster detail
- `benchmark/output/report.md` — human-readable summary

Exit code = number of clusters where any metric (topic/polarity/regime) failed.
Useful for CI gating.

## Interpreting the score

- **0.85+** — encoder is producing stable structural geometry across paraphrase
- **0.70–0.85** — usable; some clusters drift, worth investigating
- **<0.70** — encoder is not doing its job; primitives are too sensitive to surface form

The benchmark is deliberately strict (it requires *exact* topic/polarity/regime
match per cluster). A drop here is a real signal that the encoder needs work.

## Adding to the corpus

Edit `corpus.py`. New clusters go in `CORPUS`; new refusal cases go in
`REFUSAL_CASES`. Re-run `benchmark/run.py` to re-score.

## Limitations of v0

- Corpus is small (8 clusters, 3 refusal cases). No coverage of multilingual,
  dialectal, or noisy text.
- Polarity dictionary is a small word list; weak sentiment doesn't move it.
- Topic-band detection is keyword-based, not semantic. Paraphrases that don't
  share topic keywords will fail topic-agreement even if humans would agree.
- No contrastive metric yet (between-cluster *separation*). v0.2.
