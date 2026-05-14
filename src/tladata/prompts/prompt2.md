# Prompt Guide 2 — V2 Verification

You are an expert TLA+ engineer. Two files are uploaded: the original TLA+ specification file and the V1 JSON extraction. Read the entire TLA+ file completely before doing anything else. Build a full understanding of every operator, variable, action, and temporal property. Then verify the V1 JSON against what you found.

This JSON will be used to fine-tune a language model. Every uncorrected error will be learned as correct behavior.

---

## Phase 1 — Encoding Scan

Before any field checks, scan the entire JSON for these encoding errors. Flag every occurrence found.

Disjunction `\/` must be stored as `\\/` in JSON strings. Bare `/` used as disjunction is always wrong. Check: `EventuallyOp`, `LeadsToOp`, `AlwaysOp`, `FairnessConditions`, `TemporalSubscript`, `IfThenElse`, `FunctionOverride`, `SetEnumeration`.

Conjunction `/\` must be stored as `/\\` in JSON strings.

`Implication` must contain only `=>` and `<=>`. If `~>` is present it must be moved to `LeadsToOp`.

`UNCHANGED` expressions must have a space: `UNCHANGED <<x, y>>` not `UNCHANGED<<x, y>>`.

`PlusCalAlgorithm` and `PlusCalProcesses` must be `[]` when empty, never `""`.

`BooleanConstants` must contain only `TRUE` and `FALSE`. Remove `BOOLEAN` if present.

`FiniteSetOps` must not contain `SUBSET`. Move `SUBSET` to `SetOperators`.

`SetOperators` must not contain `\notin`. Move `\notin` to `MembershipOps`.

`AlwaysOp` entries must include the full subscript: `[][Next]_vars` not `[][Next]`.

`EnabledExprs` must contain only the ENABLED expression itself, not surrounding context.

---

## Phase 2 — Completeness

Count every `==` definition at the module top level in the TLA+ file. State: file count = X, JSON OperatorDefNames count = Y. They must match. If they differ, identify the missing or extra entries before continuing.

Find every variable that appears with a prime `'` anywhere in the file, including inside EXCEPT clauses. Every such variable name must appear in `PrimedVariables`.

Find every `UNCHANGED` expression. Each distinct one must appear in `UnchangedExprs`. Two expressions are distinct if they differ in any way including variable order or spacing.

Find every `[f EXCEPT ![e] = v]` form. Each distinct one must appear in `FunctionOverride`. This field is very commonly empty when it should not be.

Find every string literal in double quotes. Each value without surrounding quotes must appear in `StringLiterals`.

Find every temporal formula where `[]`, `<>`, `~>`, or `-+->` is the outermost operator. Each must appear in `AlwaysOp`, `EventuallyOp`, `LeadsToOp`, or `GuaranteesOp` respectively, with full subscripts. Also find every `A \cdot B` action composition expression and confirm it appears in `ActionComposition`.

Find every `ASSUME`, `ASSUMPTION`, and `AXIOM` block. Each must have an entry in `AssumptionNames`. Named blocks: name only. Unnamed blocks: full expression verbatim. Each block gets its own array entry.

---

## Phase 3 — Correctness

Go through every value in the JSON and confirm it appears in the TLA+ file. Flag any value that does not exist in the file. High-risk fields: `OperatorDefNames`, `ActionDefNames`, `FunctionOverride`, `RecordAccess`, `AssumptionNames`, `LetInNames`.

Specifically check:

`OperatorDefNames` must contain no LET-bound names and no duplicates. LET-bound names go in `LetInNames` or `LocalOperatorNames`.

`ActionDefNames` must contain only operators that prime at least one variable in their body directly, or operators defined as compositions of other actions. State predicates, temporal properties, type invariants, value definitions, and LET-bound names must not appear here.

`LocalOperatorNames` must contain only parametric definitions inside LET blocks (i.e., `name(args) == expr` form). Simple bindings like `min == expr` belong in `LetInNames` only.

`RecordAccess` must contain only `e.field` expressions that literally appear in the file. Remove any entry that cannot be found verbatim in the file.

`FairnessConditions` must contain only WF or SF expressions from inside `Spec` or `Spec0`. Not from any other operator.

---

## Phase 4 — Deduplication

`UnchangedExprs`: each distinct expression once only.
`FunctionConstructor`: each distinct pattern once only.
`RangeExpr`: each distinct range once only.
`OperatorDefNames`: no duplicates.
`ActionDefNames`: no duplicates.

---

## Phase 5 — Empty Field Confirmation

For every field that is `[]`, confirm the TLA+ file genuinely has no content for it. The following fields are most commonly wrong when empty: `FunctionOverride`, `AssumptionNames`, `IfThenElse`, `RecordAccess`, `LocalOperatorNames`.

---

## Output

Return the corrected JSON first with no text before it. Then write:

```
CHANGE LOG
Field: [name] | Change: [what changed] | Reason: [why]
```

One line per change. Omit fields that required no changes. If no changes were needed write "No changes required" and state the operator count from Phase 2 to confirm completeness was verified.

---

## Illustrative Examples

Do not copy these. They show the correct format and behavior for common problem cases.

**Unnamed ASSUME blocks — each gets its own entry**
A spec with `ASSUME 2 * T < N /\ 0 <= F` and a separate `ASSUME \A v \in Values: v # Bottom` produces:
```json
"AssumptionNames": [
  "2 * T < N /\\ 0 <= F",
  "\\A v \\in Values: v # Bottom"
]
```

**FunctionOverride — commonly missed**
`[pc EXCEPT ![i] = "D0"]` and `[pc EXCEPT ![i] = "D1"]` are two distinct entries because the assigned value differs.

**TemporalSubscript vs AlwaysOp**
`[][Next]_vars` appears in both `TemporalSubscript` and `AlwaysOp` because `[]` is the outermost operator and the full subscript must be present in both.

**LeadsToOp — never in Implication**
`participant[j].vote = yes ~> participant[i].decision = commit` goes in `LeadsToOp` only. `Implication` gets only `=>` and `<=>`.
