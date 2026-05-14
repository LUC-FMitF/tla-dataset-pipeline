# Prompt Guide 1 — V1 Initial Extraction

You are an expert TLA+ engineer. A TLA+ specification file has been uploaded to this session.

Before extracting anything: read the entire file from top to bottom without skipping anything, including all comments. Understand what algorithm or system the spec models, what every operator does, which operators prime variables, which are purely state-level, and what the temporal properties assert. Only after you have a complete understanding of the file should you begin filling in the JSON below.

---

## Absolute Rules — Never Violate These

**Scope:** Extract only what is syntactically present in this file. Never include constructs inherited from EXTENDS or INSTANCE modules.

**Encoding:** All TLA+ ASCII operators must be stored exactly as they appear in the file. The disjunction is `\/` (stored as `\\/` in JSON strings). The conjunction is `/\` (stored as `/\\`). The box is `[]`. The diamond is `<>`. The leads-to is `~>`. The prime is `'`. The inequality operators are `#` and `/=`. Never drop backslashes. Never replace `\/` with bare `/`.

**Types:** Every field is an array. Use `[]` for empty fields. The only exceptions are `Specification`, `ModuleName`, and `ComplexityTier` which are strings. Never use `""` for array fields. `PlusCalAlgorithm` and `PlusCalProcesses` must be `[]` when no PlusCal content is present.

**UNCHANGED spacing:** Always store `UNCHANGED <<x, y>>` with a space between UNCHANGED and the expression. Never `UNCHANGED<<x, y>>`.

**Implication:** The `Implication` field contains only `=>` and `<=>`. The leads-to operator `~>` belongs only in `LeadsToOp`. Never put `~>` in `Implication`.

**BOOLEAN:** The keyword BOOLEAN (the set {TRUE, FALSE}) must never appear in `BooleanConstants`. `BooleanConstants` contains only the literal values `TRUE` and `FALSE`. BOOLEAN as a set expression belongs in `FunctionConstructor` or `RecordConstructor` context only, as part of those entries.

**LET-bound names:** Names introduced inside LET blocks are never top-level operator definitions. They never appear in `OperatorDefNames`. They go in `LetInNames` or `LocalOperatorNames`.

**ASSUME blocks:** Each ASSUME, ASSUMPTION, or AXIOM block gets its own entry. If the block has a name (e.g., `ASSUME NTF == ...`) record only the name `"NTF"`. If it has no name, record the full expression verbatim. A file may have multiple ASSUME blocks — each one gets its own array entry.

---

## Field Rules

**Specification**
A natural language description of the algorithm or system being specified, what fault model it uses if any, what properties it verifies, and any notable design decisions. Base this on the file comments and content. Minimum 3 sentences. Never leave this empty or set it to the module name.

**ModuleName**
The exact name from the `---- MODULE M ----` line.

**ExtendsModules**
Only modules listed after `EXTENDS` in this file.

**InstanceModules**
Only modules appearing in `INSTANCE M` declarations.

**InstanceSubstitutions**
Only explicit `WITH p <- e` substitutions. `[]` if no WITH clause.

**ConstantNames**
Only names declared after `CONSTANT` or `CONSTANTS`. For operator-valued constants of the form `Ballot(_)` or `IsMajority(_)`, record the name only without the underscore placeholder: `"Ballot"`, not `"Ballot(_)"`.

**VariableNames**
Only names declared after `VARIABLE` or `VARIABLES`.

**AssumptionNames**
One entry per ASSUME / ASSUMPTION / AXIOM block. Named blocks: record the name only. Unnamed blocks: record the full expression verbatim.

**TheoremNames**
One entry per THEOREM / LEMMA / PROPOSITION / COROLLARY. Record the full statement verbatim.

**OperatorDefNames**
Every `Name == expr` definition at the module top level. Includes state predicates, actions, temporal properties, helper functions, and structural definitions. Does not include LET-bound names. Does not include duplicates. Does not include names declared before their definition in a RECURSIVE statement — only the definition `Name == expr` counts.

**ActionDefNames**
Only operators that directly prime at least one state variable in their body, OR operators whose body is a disjunction or conjunction exclusively of other action operators (e.g., `Next == A \/ B \/ C` where A, B, C are themselves actions). Does not include: state predicates, temporal formulas, type invariants, value definitions, LET-bound names, or helper functions that compute values from the current state.

**RecursiveOperatorNames**
Only operators preceded by a `RECURSIVE` declaration in TLA+2 syntax, for example `RECURSIVE fact(_)` followed by `fact(n) == ...`. Does not include recursive function definitions of the form `f[x \in S] == ...` — those are function constructors, not recursive operator definitions.

**LocalOperatorNames**
Only parametric operator definitions inside a LET block, i.e., definitions of the form `name(args) == expr` inside `LET ... IN`. Simple value bindings like `min == expr` inside LET are not local operators — they go in `LetInNames`.

**LetInNames**
All names bound by `LET name == expr IN` anywhere in the file, whether parametric or not. List each distinct name once regardless of how many LET blocks introduce it.

**LambdaParams**
Parameters of `LAMBDA` expressions only. For example, `LAMBDA a, b : expr` contributes `["a", "b"]`. Not parameters of named operator definitions. Not bound variables in function constructors like `[i \in S |-> ...]`.

**Implication**
`["=>"]` if `=>` appears. `["<=>"]` if `<=>` appears. Both if both appear. Never `~>`.

**Negation**
Only `"~"`, `"\lnot"`, or `"\neg"`. Never `"#"` or `"/="` — those are equality operators.

**BooleanConstants**
Only the literal values `TRUE` and `FALSE` when they appear as values in expressions. Never `BOOLEAN`.

**Quantifiers**
`"\A"` and/or `"\E"` if they appear as quantifiers.

**EqualityOps**
`"="`, `"#"`, and/or `"/="`. These are not negation operators.

**MembershipOps**
`"\in"` and/or `"\notin"`.

**IfThenElse**
One entry per syntactic `IF` occurrence in the file. Write a short description of the condition and which operator it appears in. Example: `"IF pc[i] = V0 THEN nSnt0F' = nSnt0F + 1 ELSE nSnt0F' = nSnt0F (in Faulty)"`. Include IF expressions nested inside LET blocks.

**CaseExpr**
One entry per syntactic `CASE` occurrence. Short description.

**SetEnumeration**
Each distinct `{e1, ..., en}` set literal in the file. Include `{}` for the empty set. Do not include BOOLEAN here. Do not include set comprehension forms like `{x \in S : p}` or `{e : x \in S}` — those are not set enumerations and must not appear in this field.

**SetOperators**
Only those syntactically present: `"SUBSET"`, `"\cup"`, `"\union"`, `"\cap"`, `"\intersect"`, `"\subseteq"`, `"\"` (set difference), `"\X"`, `"\times"`, `"UNION"`, `"DOMAIN"`. Do not include `"\notin"` — that is MembershipOps.

**FiniteSetOps**
`"IsFiniteSet"` and/or `"Cardinality"` only if called in this file. `"Permutations"` belongs to the TLC module, not here. Do not include `"SUBSET"` here.

**FunctionConstructor**
Each distinct form present in the file:
- `[x \in S |-> e]` — function by domain
- `[S -> T]` — set of all functions from S to T

List both the outer and any distinct inner patterns when they are nested. For example `[i \in Proc |-> [j \in Proc |-> Bottom]]` produces two entries: the outer form and the inner form `[j \in Proc |-> Bottom]`.

**FunctionApplication**
Each distinct `f[e]` pattern in the file. Do not list primed forms like `f'[e]` here.

**FunctionOverride**
Each distinct `[f EXCEPT ![e1] = e2]` form. Two forms are distinct if they differ in any way including the assigned value. Include nested EXCEPT using `@`.

**RecordConstructor**
Record value constructors `[field |-> value, ...]` and record type constructors `[field : Set, ...]`. Only those present in this file.

**RecordAccess**
Only explicit `e.field` dot-access expressions that literally appear in the file. Verify each entry exists. Do not infer from constructors.

**TupleConstructor**
Each distinct `<<...>>` expression.

**SequenceOps**
From the Sequences module — only those called in this file: `"Seq"`, `"Append"`, `"SubSeq"`, `"Len"`, `"Head"`, `"Tail"`, `"SelectSeq"`, `"\o"` (concatenation).

**ArithmeticOps**
Only `"+"`, `"-"`, `"*"`, `"\div"`, `"%"`, `"^"`. Note from the standard: only infix `-` is defined in Naturals; prefix `-` requires Integers. Do not include comparison operators here.

**ComparisonOps**
Only `"<"`, `">"`, `"<="`, `">="`. Do not include `"="` or `"#"` here — those are EqualityOps.

**RangeExpr**
Each distinct `a..b` expression. Defined by the Naturals module.

**ChoiceExpr**
Each CHOOSE expression verbatim. This includes both the bounded form `CHOOSE x \in S : p` and the unbounded form `CHOOSE x : p` (without `\in S`). Both forms must be recorded.

**StringLiterals**
Each distinct string literal value without surrounding quotes. `"V0"` in the file becomes `"V0"` in the JSON (the quotes are already there from JSON string syntax).

**ArithmeticModules**
From EXTENDS only: `"Naturals"`, `"Integers"`, `"Reals"`. User-defined modules and community modules (e.g., `SVG`, `IOUtils`, `Graphs`, `UndirectedGraphs`) go in `ExtendsModules` only and never in any of the three module classification fields.

**DataStructureModules**
From EXTENDS only: `"FiniteSets"`, `"Sequences"`, `"Bags"`. User-defined and community modules go in `ExtendsModules` only.

**ToolingModules**
From EXTENDS only: `"TLC"`, `"TLAPS"`. User-defined and community modules go in `ExtendsModules` only.

**PrimedVariables**
Variable names (without the prime) that appear primed anywhere in the file. This includes priming inside EXCEPT clauses, direct assignment `x' = ...`, and UNCHANGED `x'`. Record the bare variable name without the `'`.

**UnchangedExprs**
Each distinct `UNCHANGED e` expression verbatim. Always include a space: `UNCHANGED <<x, y>>` not `UNCHANGED<<x, y>>`. If the same expression appears in multiple action definitions, list it once only.

**EnabledExprs**
Each `ENABLED A` expression verbatim. Record only the ENABLED expression itself, not the surrounding formula.

**TemporalSubscript**
Each `[][A]_vars`, `<A>_vars`, `WF_vars(A)`, or `SF_vars(A)` expression verbatim. The box subscript `[A]_e` means A or a stuttering step. The angle bracket subscript `<A>_e` means A with a non-stuttering step. Always include the full subscript: `[][Next]_vars` not `[][Next]`.

**AlwaysOp**
Each expression where `[]` is the outermost operator of a complete formula. Always include the full subscript if present.

**EventuallyOp**
Each expression where `<>` is the outermost operator. Full expression with correct encoding.

**ActionComposition**
Each `A \cdot B` action composition expression verbatim. The composition operator `\cdot` is defined in the TLA+ Summary under Action Operators as the sequential composition of two actions. TLC does not implement this operator, so it appears only in specifications intended for manual proof with TLAPS. Record each occurrence with its full left and right operands. This field is empty for the vast majority of specifications in the corpus.

**GuaranteesOp**
Each `-+->` expression verbatim. The guarantees operator `F -+-> G` asserts that whenever F holds, G will eventually hold permanently. It is a temporal operator distinct from leads-to `~>`. Record each occurrence with its full left and right operands.

**LeadsToOp**
Each `~>` expression verbatim.

**FairnessConditions**
WF or SF expressions reachable from the definition of `Spec` or `Spec0`, including through one level of operator expansion. If `Spec` contains a reference to a named `Fairness` operator, and that operator contains WF or SF expressions, those expressions belong here. If fairness is universally quantified inside Spec such as `\A self \in Proc : WF_vars(P(self))`, record the full quantified expression verbatim.

**ProofHints**
Backend solver names used with BY: `"Z3"`, `"Z3T(n)"`, `"SMT"`, `"SMTT(n)"`, `"PTL"`, `"Zenon"`, `"Isabelle"`, `"FS_Subset"`, etc. Only if present.

**ProofCommands**
Proof keywords present in this file: `"BY"`, `"QED"`, `"OBVIOUS"`, `"OMITTED"`, `"USE"`, `"SUFFICES"`, `"ASSUME"`, `"PROVE"`, `"CASE"`, `"DEFS"`, `"DEF"`, `"PICK"`, `"HIDE"`, `"WITNESS"`, `"TAKE"`, `"HAVE"`, `"NEW"`, `"ONLY"`.

**ProofStructureSteps**
Each hierarchical step label such as `"<1>1"`, `"<2>3"`.

**AssumeProveBlocks**
Each `ASSUME ... PROVE ...` or `SUFFICES ASSUME ... PROVE ...` block as a string.

**PlusCalAlgorithm**
`[]` unless a `--algorithm` or `--fair algorithm` block is present.

**PlusCalProcesses**
`[]` unless PlusCal `process` declarations are present.

**ModelValues**, **OperatorOverrides**, **SymmetrySet**, **StateConstraint**, **ActionConstraint**, **ViewExpr**
TLC configuration constructs. `[]` if not present in this file.

**ComplexityTier**
Assign one value: `"basic"` for fewer than 8 operators with no temporal properties beyond a single Spec and no proofs; `"intermediate"` for 8–20 operators with temporal properties and no proofs; `"advanced"` for more than 20 operators, or any TLAPS proofs, or any PlusCal processes.

---

## Output

Return one valid JSON object. No text before or after it.

```json
{
  "id": null,
  "Specification": "",
  "ModuleName": "",
  "ExtendsModules": [],
  "InstanceModules": [],
  "InstanceSubstitutions": [],
  "ConstantNames": [],
  "VariableNames": [],
  "AssumptionNames": [],
  "TheoremNames": [],
  "OperatorDefNames": [],
  "ActionDefNames": [],
  "RecursiveOperatorNames": [],
  "LocalOperatorNames": [],
  "NamesInLet": [],
  "LambdaParams": [],
  "Implication": [],
  "Negation": [],
  "BooleanConstants": [],
  "Quantifiers": [],
  "EqualityOps": [],
  "MembershipOps": [],
  "IfThenElse": [],
  "CaseExpr": [],
  "SetEnumeration": [],
  "SetOperators": [],
  "FiniteSetOps": [],
  "FunctionConstructor": [],
  "FunctionApplication": [],
  "FunctionOverride": [],
  "RecordConstructor": [],
  "RecordAccess": [],
  "TupleConstructor": [],
  "SequenceOps": [],
  "ArithmeticOps": [],
  "ComparisonOps": [],
  "RangeExpr": [],
  "ChoiceExpr": [],
  "StringLiterals": [],
  "ArithmeticModules": [],
  "DataStructureModules": [],
  "ToolingModules": [],
  "PrimedVariables": [],
  "UnchangedExprs": [],
  "EnabledExprs": [],
  "TemporalSubscript": [],
  "AlwaysOp": [],
  "EventuallyOp": [],
  "LeadsToOp": [],
  "GuaranteesOp": [],
  "ActionComposition": [],
  "FairnessConditions": [],
  "ProofHints": [],
  "ProofCommands": [],
  "ProofStructureSteps": [],
  "AssumeProveBlocks": [],
  "PlusCalAlgorithm": [],
  "PlusCalProcesses": [],
  "ModelValues": [],
  "OperatorOverrides": [],
  "SymmetrySet": [],
  "StateConstraint": [],
  "ActionConstraint": [],
  "ViewExpr": [],
  "ComplexityTier": ""
}
```

---

## Illustrative Examples

These are drawn from real specs to show correct format. Derive your own values from the uploaded file — do not copy these.

**Multiple unnamed ASSUME blocks (bosco-style spec)**
A file with five unnamed ASSUME blocks produces five separate entries:
```json
"AssumptionNames": [
  "N \\in Nat /\\ T \\in Nat /\\ F \\in Nat",
  "moreNplus3Tdiv2 \\in Nat /\\ moreNminusTdiv2 \\in Nat",
  "(N > 3 * T) /\\ (T >= F) /\\ (F >= 0)",
  "2 * moreNplus3Tdiv2 = N + 3 * T + 1 \\/ 2 * moreNplus3Tdiv2 = N + 3 * T + 2",
  "2 * moreNminusTdiv2 = N - T + 1 \\/ 2 * moreNminusTdiv2 = N - T + 2"
]
```

**Named ASSUME block**
`ASSUME NTF == N \in Nat /\ T \in Nat` produces `"AssumptionNames": ["NTF"]`.

**Nested FunctionConstructor**
`[i \in Proc |-> [j \in Proc |-> Bottom]]` produces two entries:
```json
"FunctionConstructor": [
  "[i \\in Proc |-> [j \\in Proc |-> Bottom]]",
  "[j \\in Proc |-> Bottom]"
]
```

**UNCHANGED with correct spacing and encoding**
```json
"UnchangedExprs": [
  "UNCHANGED << nSnt0, nSnt1, nRcvd0, nRcvd1 >>",
  "UNCHANGED << nSnt1, nSnt0F, nSnt1F, nFaulty, nRcvd0, nRcvd1 >>",
  "UNCHANGED vars"
]
```

**EventuallyOp with correct \/ encoding**
`<>(\A i \in Proc: pc[i] = "CRASH" \/ pc[i] = "DONE")` produces:
```json
"EventuallyOp": ["<>(\\A i \\in Proc: pc[i] = \"CRASH\" \\/ pc[i] = \"DONE\")"]
```

**FairnessConditions vs TemporalSubscript**
`Spec == Init /\ [][Next]_vars /\ WF_vars(\E i \in Proc: Receive(i) \/ Decide(i))`
```json
"TemporalSubscript": [
  "[][Next]_vars",
  "WF_vars(\\E i \\in Proc: Receive(i) \\/ Decide(i))"
],
"FairnessConditions": [
  "WF_vars(\\E i \\in Proc: Receive(i) \\/ Decide(i))"
]
```

Both fields contain the WF expression. TemporalSubscript also contains the box formula.
