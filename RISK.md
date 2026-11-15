# Supplied-candidate token edit risk

This native-only addition separates two decisions about the same supplied CTC
law. Maximum posterior transcript minimizes sentence-level zero-one loss.
Minimum expected edit count can prefer a different transcript. Neither is a
measured recognition result without a real reference and a justified model.

## Input and finite decision set

`ctclab.risk.audit_risk` accepts exactly `symbols`, `blank`, `frames` and
`candidates`. Symbols, blank index and independent rational frame laws use the
same validator as the prefix mode: 2..4 symbols, 0..6 frames, canonical bounded
rational strings, each row summing exactly to one. The internal reuse sets a
placeholder width of one only for validation; no beam search is run.

Candidates are 1..32 distinct lists of nonblank integer token indices, each of
length 0..6. Empty candidates and candidates with zero law probability are
allowed. They are possible decisions, not a truncated approximation to the
random reference distribution. The entire positive-probability transcript law
is retained even when a reference transcript is absent from the candidate list.

The command is:

```sh
python -m ctclab.risk_cli --input request.json --output report.json
```

Omit `--output` for stdout; `--input -` reads stdin. The 64KiB parser rejects
duplicate keys, JSON floating/exponent tokens and nonfinite constants. A malformed
request exits 2 without replacing an existing output. File output uses a temporary
file in the destination directory followed by atomic replacement. Input and
output cannot be the same resolved path. This is a generator, not a report
verification command; generated reports should not be treated as authenticated.

## Complete law and risk witnesses

For every frame path p, multiply its exact rational emission probabilities and
apply CTC collapse: merge adjacent equal tokens, then remove blanks. Sum positive
path masses by transcript y to obtain P(y). No path sampling, pruning,
renormalization, language model or floating conversion is used.

Unit token edit distance d(h,y) is the minimum number of single-token insertions,
deletions and substitutions. Equal tokens cost zero; all three edits cost one.
A rolling-row dynamic program computes the distance. For each supplied candidate h:

```
edit_risk(h) = sum_y P(y) * d(h,y)
sentence_error_risk(h) = 1 - P(h)
edit_loss_mass(h,k) = sum_{y: d(h,y)=k} P(y)
```

Every candidate record includes its distances in the report's lexicographically
ordered support, posterior mass, both risks and the seven-bin loss histogram.
Both candidate and reference strings have length at most six, so distance is at
most six. The report retains every tied minimum candidate index, in input order,
and every tied full-law MAP transcript. No arbitrary single tie winner is chosen.
The copied request does not alias the caller's lists.

At most 4^6=4096 frame paths are enumerated. With S positive transcripts, H
candidates and maximum string length L, distance work is O(H*S*L^2), plus path
construction. Report size includes H*S distances. These small limits are part of
the contract, not a claim of scalable minimum-risk decoding.

## Selected disagreement

The README's three-frame blank,A,B law was selected in an original seeded search:
seed 719, zero-based trial 7 of positive integer frame weights 1..9, normalized
exactly. The search compared all binary nonblank strings up to length three;
the published example supplies only B and A,B so its decision domain is explicit.

A,B is the unique full-law MAP transcript, with mass 729/2240. B has mass
171/560. Among the supplied candidates, B minimizes expected token edit count:
127/160 instead of 449/560, a difference of 9/1120. Sentence-error risks go in
the opposite direction: B has 389/560 and A,B has 1511/2240. This development
control illustrates the loss-function distinction. It is not held-out accuracy,
a typical-frequency claim, or evidence that edit-risk decisions always beat MAP.

## Checks and boundaries

Five new tests retain all earlier tests. They compare 961 binary string pairs
against complete monotone edit-alignment enumeration; compare 80 seeded supplied
laws against the separate prefix recurrence and candidate risks against the
alignment reference; pin the selected disagreement; cover zero frames, zero-mass
candidates, ties, nonzero blank indices, malformed candidates and the maximum
four-symbol/six-frame/32-candidate boundary; and check CLI output, strict refusal,
input preservation and atomic failure behavior. Both old report regenerations
and both existing installed-package workflows remain required. The original
wheel workflow additionally runs all five new tests outside the checkout and
checks the two new module origins.

The target atlas's floating arithmetic and the prefix mode's search semantics
stay unchanged. This risk mode supplies no browser interface, acoustic model,
learned probability calibration or unrestricted action-space optimum. Unit token
edit count is not reference-length-normalized WER. Supplied model-expected loss
is not the user's actual error probability or expected real-world error.

Source: Xu, Povey, Mangu and Zhu, [Minimum Bayes Risk Decoding and System
Combination Based on a Recursion for Edit Distance](https://danielpovey.com/files/csl11_consensus.pdf),
section 2, equations 3 and 4, for the standard expected-Levenshtein-risk objective
and finite decision domains. This small implementation enumerates a bounded
supplied CTC law and candidate set. It does not implement the paper's lattice
recursion, optimization method or system combination. No paper code or data are
copied, and no new decoding method is claimed.
