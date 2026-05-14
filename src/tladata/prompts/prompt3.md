# Prompt Guide 3 — V3 Fine-Grained Division

You are an expert TLA+ engineer. Two files are uploaded: the original TLA+ specification file and the verified V2 JSON. Read the entire TLA+ file from top to bottom before doing anything. Understand the role of every operator: what it computes, whether it transitions state, whether it defines a temporal property, and whether it is a helper or structural definition. Only then produce the V3 JSON.

Keep every existing field from V2 exactly as it is, including the renamed field `NamesInLet`. Add only the new fields below, placed after all existing fields.

---

## New Fields

**OperatorDefNames_StatePredicate**

Operators from `OperatorDefNames` that are Boolean-valued, contain no primed variables in their body, and contain no temporal operators `[]`, `<>`, or `~>` in their body. These are typically type correctness predicates, invariants, and condition checks on the current state.

If an operator contains `ENABLED` but no temporal operators and no primed variables, it may be placed here. Add a note in `DivisionNotes` flagging the ENABLED usage.

**OperatorDefNames_TemporalProperty**

Operators from `OperatorDefNames` whose body contains `[]`, `<>`, or `~>` at or near the outermost level. `Spec` and `Spec0` always go here. Named safety and liveness properties go here.

Note on implication: if an operator is defined as `P => []Q` or `P => <>Q`, the outermost operator is `=>` not `[]` or `<>`. Such an operator is still a temporal property because its meaning is temporal. Place it in `OperatorDefNames_TemporalProperty` and add a note in `DivisionNotes` explaining the implication wrapper.

**OperatorDefNames_Init**

Operators from `OperatorDefNames` whose name is exactly `"Init"` or begins with `"Init"`.

**OperatorDefNames_ValueDef**

Operators from `OperatorDefNames` that define a non-Boolean, non-action, non-temporal value: sets, tuples, constants, message constructors, helper functions, auxiliary computed values. Module-level helper functions that take parameters and return computed values (e.g., `Phs1Msg(v, i)`, `MAX(arr)`, `rcvd0(self)`) belong here.

**Partition rule — mandatory before returning:**
Action operators in `ActionDefNames` must NOT appear in any of the four sub-fields. Every other operator in `OperatorDefNames` must appear in exactly one sub-field. Verify:

`|StatePredicate| + |TemporalProperty| + |Init| + |ValueDef| + |ActionDefNames| = |OperatorDefNames|`

If the counts do not match, fix the discrepancy before returning. After verifying, add a count confirmation to `DivisionNotes`:
`"Partition count: StatePredicate(X) + TemporalProperty(Y) + Init(Z) + ValueDef(W) + ActionDefNames(V) = OperatorDefNames(T). Verified."`

**FunctionConstructor_ByDomain**

Only `[x \in S |-> e]` forms from `FunctionConstructor`.

**FunctionConstructor_SetType**

Only `[S -> T]` forms from `FunctionConstructor`. Note: S may be a variable expression, e.g., `[valsRcvd -> incoming[n]]` is still a `[S -> T]` form.

These two sub-fields together must exactly equal `FunctionConstructor`. If `FunctionConstructor_ByDomain` is empty, add a note to `DivisionNotes` confirming all FunctionConstructor entries are `[S -> T]` forms.

**UnchangedExprs_Explicit**

Only `UNCHANGED <<...>>` forms from `UnchangedExprs` where variables are listed explicitly.

**UnchangedExprs_VarRef**

Only `UNCHANGED varname` forms from `UnchangedExprs` where varname references a previously defined tuple variable such as `vars`.

These two sub-fields together must exactly equal `UnchangedExprs`.

**TemporalNesting**

Boolean. Set to `true` only when a temporal operator (`[]`, `<>`, `~>`) appears explicitly nested inside another temporal operator in the source file text — meaning you can point to a specific line where this occurs.

Using `~>` as a shorthand does NOT count as explicit nesting. `F ~> G` is syntactic sugar for `[](F => <>G)`, but if the file writes only `F ~> G`, `TemporalNesting` is `false` for that usage.

If an operator is defined as `P => []Q`, the `[]` is nested inside `=>` which is not itself a temporal operator. This counts as `false` for TemporalNesting unless `[]Q` or `<>R` also appears inside another `[]`, `<>`, or `~>` elsewhere.

If `true`, quote the exact line from the file in `DivisionNotes`.

**CorpusSource**

Relative path in the TLA+ Examples repository: `specifications/[folder]/[filename].tla`. Use the module name as the folder name if the folder cannot be determined from file content. If uncertain, add a note in `DivisionNotes`.

**VerificationTools**

Tools applicable to this spec based on file content. `"TLC"` if TLC operators appear or a `.cfg` model is likely. `"TLAPS"` if `EXTENDS TLAPS` or proof steps are present. `"Apalache"` if Apalache annotations appear. Leave `[]` if genuinely uncertain.

**DivisionNotes**

Array of strings recording: ambiguous operator classifications, the mandatory partition count confirmation, evidence for `TemporalNesting` if `true`, confirmation that `FunctionConstructor_ByDomain` is empty if it is, any ENABLED-containing operators placed in StatePredicate, and any operators placed in ValueDef by elimination. Leave `[]` only if nothing needs recording after the count check passes cleanly.

---

## Output

Return the complete JSON with all V2 fields preserved and new fields added at the end. No text before or after the JSON.

---

## Reference Sample

This is a complete V3 JSON for the `cf1s_folklore` spec (one of the specs in this corpus). It shows correct format and level of detail. Derive all your own values from the uploaded file — do not copy these.

```json
{
  "id": null,
  "Specification": "An encoding of the one-step Byzantine consensus algorithm from Dobre and Suri (2006). N processes with up to F Byzantine faults communicate in a single round, each sending ECHO0 or ECHO1. Processes decide based on message count thresholds. Verifies OneStep0_Ltl and OneStep1_Ltl safety properties under weak fairness on Receive, Propose, and Decide actions.",
  "ModuleName": "cf1s_folklore",
  "ExtendsModules": ["Naturals", "FiniteSets"],
  "InstanceModules": [],
  "InstanceSubstitutions": [],
  "ConstantNames": ["N", "T", "F"],
  "VariableNames": ["nSnt0", "nSnt1", "nSnt0F", "nSnt1F", "nFaulty", "pc", "nRcvd0", "nRcvd1"],
  "AssumptionNames": ["NTF"],
  "TheoremNames": [],
  "OperatorDefNames": [
    "Proc", "Status", "vars",
    "Init", "Init0", "Init1",
    "Faulty", "Propose", "Receive", "Decide", "Next",
    "Spec",
    "TypeOK", "OneStep0_Ltl", "OneStep1_Ltl"
  ],
  "ActionDefNames": ["Faulty", "Propose", "Receive", "Decide", "Next"],
  "RecursiveOperatorNames": [],
  "LocalOperatorNames": [],
  "LetInNames": [],
  "LambdaParams": [],
  "Implication": ["=>"],
  "Negation": [],
  "BooleanConstants": [],
  "Quantifiers": ["\\A", "\\E"],
  "EqualityOps": ["=", "#"],
  "MembershipOps": ["\\in"],
  "IfThenElse": [
    "IF pc[i] = V0 THEN nSnt0F' = nSnt0F + 1 ELSE nSnt0F' = nSnt0F (in Faulty)",
    "IF pc[i] = V1 THEN nSnt1F' = nSnt1F + 1 ELSE nSnt1F' = nSnt1F (in Faulty)"
  ],
  "CaseExpr": [],
  "SetEnumeration": [
    "{\"V0\", \"V1\"}",
    "{\"V0\", \"V1\", \"S0\", \"S1\", \"D0\", \"D1\", \"U0\", \"U1\", \"BYZ\"}"
  ],
  "SetOperators": [],
  "FiniteSetOps": [],
  "FunctionConstructor": [
    "[Proc -> {\"V0\", \"V1\"}]",
    "[Proc -> Status]",
    "[Proc -> 0..N]",
    "[i \\in Proc |-> 0]",
    "[i \\in Proc |-> \"V0\"]",
    "[i \\in Proc |-> \"V1\"]"
  ],
  "FunctionApplication": ["pc[i]", "nRcvd0[i]", "nRcvd1[i]"],
  "FunctionOverride": [
    "[pc EXCEPT ![i] = \"BYZ\"]",
    "[pc EXCEPT ![i] = \"S0\"]",
    "[pc EXCEPT ![i] = \"S1\"]",
    "[pc EXCEPT ![i] = \"D0\"]",
    "[pc EXCEPT ![i] = \"D1\"]",
    "[pc EXCEPT ![i] = \"U0\"]",
    "[pc EXCEPT ![i] = \"U1\"]",
    "[nRcvd0 EXCEPT ![i] = nRcvd0[i] + 1]",
    "[nRcvd1 EXCEPT ![i] = nRcvd1[i] + 1]"
  ],
  "RecordConstructor": [],
  "RecordAccess": [],
  "TupleConstructor": ["<< nSnt0, nSnt1, nSnt0F, nSnt1F, nFaulty, pc, nRcvd0, nRcvd1 >>"],
  "SequenceOps": [],
  "ArithmeticOps": ["+"],
  "ComparisonOps": [">=", "<"],
  "RangeExpr": ["0..N", "0..F", "1..N"],
  "ChoiceExpr": [],
  "StringLiterals": ["V0", "V1", "S0", "S1", "D0", "D1", "U0", "U1", "BYZ"],
  "ArithmeticModules": ["Naturals"],
  "DataStructureModules": ["FiniteSets"],
  "ToolingModules": [],
  "PrimedVariables": ["pc", "nFaulty", "nSnt0F", "nSnt1F", "nSnt0", "nSnt1", "nRcvd0", "nRcvd1"],
  "UnchangedExprs": [
    "UNCHANGED << nSnt0, nSnt1, nRcvd0, nRcvd1 >>",
    "UNCHANGED << nSnt1, nSnt0F, nSnt1F, nFaulty, nRcvd0, nRcvd1 >>",
    "UNCHANGED << nSnt0, nSnt0F, nSnt1F, nFaulty, nRcvd0, nRcvd1 >>",
    "UNCHANGED << nSnt0, nSnt1, nSnt0F, nFaulty, pc, nSnt1F, nRcvd1 >>",
    "UNCHANGED << nSnt0, nSnt1, nSnt0F, nFaulty, pc, nSnt1F, nRcvd0 >>",
    "UNCHANGED vars",
    "UNCHANGED << nSnt0, nSnt1, nSnt0F, nSnt1F, nFaulty, nRcvd0, nRcvd1 >>"
  ],
  "EnabledExprs": [],
  "TemporalSubscript": [
    "[][Next]_vars",
    "WF_vars(\\E self \\in Proc : \\/ Receive(self) \\/ Propose(self) \\/ Decide(self))"
  ],
  "AlwaysOp": ["[][Next]_vars"],
  "EventuallyOp": [],
  "LeadsToOp": [],
  "FairnessConditions": [
    "WF_vars(\\E self \\in Proc : \\/ Receive(self) \\/ Propose(self) \\/ Decide(self))"
  ],
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
  "ComplexityTier": "intermediate",
  "OperatorDefNames_StatePredicate": ["TypeOK"],
  "OperatorDefNames_TemporalProperty": ["Spec", "OneStep0_Ltl", "OneStep1_Ltl"],
  "OperatorDefNames_Init": ["Init", "Init0", "Init1"],
  "OperatorDefNames_ValueDef": ["Proc", "Status", "vars"],
  "FunctionConstructor_ByDomain": [
    "[i \\in Proc |-> 0]",
    "[i \\in Proc |-> \"V0\"]",
    "[i \\in Proc |-> \"V1\"]"
  ],
  "FunctionConstructor_SetType": [
    "[Proc -> {\"V0\", \"V1\"}]",
    "[Proc -> Status]",
    "[Proc -> 0..N]"
  ],
  "UnchangedExprs_Explicit": [
    "UNCHANGED << nSnt0, nSnt1, nRcvd0, nRcvd1 >>",
    "UNCHANGED << nSnt1, nSnt0F, nSnt1F, nFaulty, nRcvd0, nRcvd1 >>",
    "UNCHANGED << nSnt0, nSnt0F, nSnt1F, nFaulty, nRcvd0, nRcvd1 >>",
    "UNCHANGED << nSnt0, nSnt1, nSnt0F, nFaulty, pc, nSnt1F, nRcvd1 >>",
    "UNCHANGED << nSnt0, nSnt1, nSnt0F, nFaulty, pc, nSnt1F, nRcvd0 >>",
    "UNCHANGED << nSnt0, nSnt1, nSnt0F, nSnt1F, nFaulty, nRcvd0, nRcvd1 >>"
  ],
  "UnchangedExprs_VarRef": ["UNCHANGED vars"],
  "TemporalNesting": false,
  "CorpusSource": "specifications/cf1s/cf1s_folklore.tla",
  "VerificationTools": ["TLC"],
  "DivisionNotes": [
    "Partition count: StatePredicate(1) + TemporalProperty(3) + Init(3) + ValueDef(3) + ActionDefNames(5) = 15 = OperatorDefNames total. Verified.",
    "OneStep0_Ltl and OneStep1_Ltl are placed in TemporalProperty because their bodies are of the form P => []Q and P => <>Q respectively. The outermost operator is => but the meaning is temporal. TemporalNesting is false because [] and <> do not appear nested inside each other — they appear inside an implication.",
    "TemporalNesting is false. No temporal operator appears explicitly nested inside another temporal operator in this file."
  ]
}
```
