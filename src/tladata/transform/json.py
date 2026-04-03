"""TLA+ specification parser and feature extractor.

Parses TLA+ .tla and .cfg files to extract 60+ syntactic features and outputs
fine-grained (60 keys) and coarse-grained (10 keys) JSON representations.
"""

import inspect
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Forward declaration of feature lists
FINE_FEATURES: list[tuple[str, Callable]] = []
COARSE_KEYS: list[str] = []
COARSE_MAP: dict[str, str] = {}


@dataclass
class TlaTransformerConfig:
    """Configuration for TLA+ transformation."""

    specs_data: list[dict[str, Any]]
    """List of spec dictionaries with 'model', 'tla_clean', 'tla_original', 'cfg' keys"""
    output_fine: str | None = None
    """Output path for fine-grained features JSON (None = return dict instead)"""
    output_coarse: str | None = None
    """Output path for coarse-grained features JSON (None = return dict instead)"""


# used to classify which stdlib modules a spec imports
ARITHMETIC_MODS = {"Naturals", "Integers", "Reals", "NaturalsInduction", "WellFoundedInduction"}
DATA_STRUCT_MODS = {
    "Sequences",
    "FiniteSets",
    "Bags",
    "FiniteSetTheorems",
    "SequenceTheorems",
    "Functions",
}
TOOLING_MODS = {"TLC", "TLAPS", "IOUtils", "Json", "CSV", "ShiViz", "RealTime"}

# these are all tla+ reserved words — we skip them when collecting names
_TLA_KEYWORDS = frozenset(
    {
        "ASSUME",
        "ASSUMPTION",
        "AXIOM",
        "THEOREM",
        "LEMMA",
        "COROLLARY",
        "CONSTANT",
        "CONSTANTS",
        "VARIABLE",
        "VARIABLES",
        "INSTANCE",
        "LOCAL",
        "MODULE",
        "EXTENDS",
        "LET",
        "IN",
        "IF",
        "THEN",
        "ELSE",
        "CASE",
        "OTHER",
        "CHOOSE",
        "EXCEPT",
        "WITH",
        "BY",
        "DEF",
        "PROOF",
        "DEFINE",
        "QED",
        "OBVIOUS",
        "OMITTED",
        "SUFFICES",
        "HAVE",
        "TAKE",
        "WITNESS",
        "PICK",
        "USE",
        "HIDE",
        "RECURSIVE",
        "UNCHANGED",
        "ENABLED",
        "SUBSET",
        "UNION",
    }
)

# used to detect where a declaration block ends (next section keyword or separator)
_SECTION_KW = re.compile(
    r"^(?:VARIABLES?|CONSTANTS?|ASSUME|THEOREM|AXIOM|INSTANCE|LOCAL|LET|"
    r"USE|HIDE|TAKE|PICK|SUFFICES|DEFINE|QED|PROOF|BY|OBVIOUS|"
    r"OMITTED|HAVE|WITNESS|RECURSIVE|[-=]{4})",
    re.MULTILINE,
)


# walks data/ recursively and returns the first match — prefers /tla/ or /cfg/ subfolder
def find_file(filename: str, base_paths: list[str] | None = None) -> str | None:
    """Find a file in given base paths or current directory."""
    if not filename:
        return None

    search_paths = base_paths or [os.getcwd()]
    matches = []

    for base_path in search_paths:
        for root, dirs, files in os.walk(base_path):
            if filename in files:
                matches.append(os.path.join(root, filename))

    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    # Prefer /tla/ or /cfg/ subfolder
    for sub in ("/tla/", "/cfg/"):
        hits = [m for m in matches if sub in m]
        if hits:
            return hits[0]
    return matches[0]


# safe file read — returns empty string on any error instead of crashing
def read_text(path: str | None) -> str:
    """Read file as text. Returns empty string on any error."""
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def get_file_content(file_ref: str | None, base_paths: list[str] | None = None) -> str:
    """Get file content from reference. Can be direct path or filename to search for."""
    if not file_ref:
        return ""

    # If it's an absolute or valid relative path, try it directly
    if os.path.isabs(file_ref):
        return read_text(file_ref)

    if os.path.isfile(file_ref):
        return read_text(file_ref)

    # Otherwise search for it
    found = find_file(file_ref, base_paths)
    return read_text(found) if found else ""


# removes duplicates while preserving order — used before joining into a string
def dedup(lst: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen = []
    for x in lst:
        x = x.strip()
        if x and x not in seen:
            seen.append(x)
    return seen


# joins with comma — most extractors return this format
def fmt(lst: list[str]) -> str:
    """Format list as comma-separated string."""
    return ", ".join(dedup(lst))


# joins with semicolon — used when values themselves may contain commas
def fmt_semi(lst: list[str]) -> str:
    """Format list as semicolon-separated string."""
    return "; ".join(dedup(lst))


# returns true if a line after EXTENDS is just more module names (handles multi-line extends)
def _is_extends_continuation(line):
    stripped = line.strip()
    if not stripped:
        return False
    if not re.match(r"^[\w,\s]*$", stripped):
        return False
    tokens = re.findall(r"\b([A-Za-z_]\w*)\b", stripped)
    return not any(t in _TLA_KEYWORDS for t in tokens)


# collects all module names from every EXTENDS statement including multi-line ones
def _extends(tla):
    mods = []
    for m in re.finditer(r"\bEXTENDS\b[ \t]*", tla):
        pos = m.end()
        for line in tla[pos:].split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if _is_extends_continuation(line):
                for tok in re.split(r"[,\s]+", line):
                    tok = tok.strip()
                    if re.match(r"^[A-Za-z_]\w*$", tok):
                        mods.append(tok)
            else:
                break
    return mods


# pluscal lives in the original .tla — the _clean version strips it so we must load original
def _load_original_tla(entry: dict[str, Any], base_paths: list[str] | None = None) -> str:
    """Load original TLA file content from entry metadata."""
    orig = (entry or {}).get("tla_original", "")
    if orig:
        return get_file_content(orig, base_paths)
    return ""


# extracts the (* --algorithm ... *) block tracking nested comment depth
def _pluscal_block(entry: dict[str, Any], base_paths: list[str] | None = None) -> str:
    """Extract PlusCal algorithm block from entry."""
    text = _load_original_tla(entry, base_paths)
    if not text:
        return ""
    alg_pos = text.find("--algorithm")
    if alg_pos == -1:
        alg_pos = text.find("--fair")
    if alg_pos == -1:
        return ""
    open_pos = text[:alg_pos].rfind("(*")
    if open_pos == -1:
        return text[alg_pos:]
    pos = open_pos + 2
    depth = 1
    while depth > 0 and pos < len(text):
        if text[pos : pos + 2] == "(*":
            depth += 1
            pos += 2
        elif text[pos : pos + 2] == "*)":
            depth -= 1
            pos += 2
        else:
            pos += 1
    return text[open_pos:pos]


def ex_module_name(tla, cfg):
    m = re.search(r"MODULE\s+(\w+)", tla)
    return m.group(1) if m else ""


def ex_extends_modules(tla, cfg):
    return fmt(_extends(tla))


def ex_instance_modules(tla, cfg):
    return fmt([m.group(1) for m in re.finditer(r"\bINSTANCE\s+(\w+)", tla)])


def ex_instance_substitutions(tla, cfg):
    subs = []
    for m in re.finditer(r"\bINSTANCE\s+\w+\s+WITH\b([^\n]+(?:\n[ \t]+[^\n]+)*)", tla):
        for s in re.finditer(r"(\w+)\s*<-\s*(\w+)", m.group(1)):
            subs.append(f"{s.group(1)} <- {s.group(2)}")
    return fmt_semi(subs)


# shared helper for CONSTANTS and VARIABLES — handles multi-line blocks and Op(_) forms
def _collect_decl_block(tla, keyword_pat):
    names = []
    for m in re.finditer(keyword_pat + r"\b[ \t]*", tla):
        pos = m.end()
        eol = tla.find("\n", pos)
        if eol == -1:
            eol = len(tla)
        lines_to_parse = []
        same_line = tla[pos:eol].strip()
        if same_line:
            lines_to_parse.append(same_line)
        for line in tla[eol + 1 :].split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if _SECTION_KW.match(stripped):
                break
            if re.match(r"^[A-Za-z_][\w,\s()_]*$", stripped):
                lines_to_parse.append(stripped)
            else:
                break
        block = re.sub(r"\([_,\s]*\)", "", " ".join(lines_to_parse))
        for tok in re.findall(r"\b([A-Za-z_]\w*)\b", block):
            if tok not in _TLA_KEYWORDS:
                names.append(tok)
    return names


def ex_constant_names(tla, cfg):
    return fmt(_collect_decl_block(tla, r"\bCONSTANTS?"))


def ex_variable_names(tla, cfg):
    return fmt(_collect_decl_block(tla, r"\bVARIABLES?"))


def ex_assumption_names(tla, cfg):
    results = []
    for m in re.finditer(r"\bASSUME\b\s*(\w+\s*==)?", tla):
        named = m.group(1)
        if named:
            results.append("ASSUME " + named.replace("==", "").strip())
        else:
            results.append("ASSUME (anonymous)")
    return fmt_semi(dedup(results))


def ex_theorem_names(tla, cfg):
    results = []
    for m in re.finditer(r"\bTHEOREM\b\s+(\w+)", tla):
        n = m.group(1)
        if n not in _TLA_KEYWORDS:
            results.append(n)
    if not results and re.search(r"\bTHEOREM\b", tla):
        return "THEOREM (anonymous)"
    return fmt(results)


def ex_operator_def_names(tla, cfg):
    names = []
    for m in re.finditer(r"^([A-Za-z_]\w*)\s*(?:\([^)]*\))?\s*==(?!=)", tla, re.MULTILINE):
        n = m.group(1)
        if n not in _TLA_KEYWORDS:
            names.append(n)
    for m in re.finditer(r"^([A-Za-z_]\w*)\s*\[[^\]]+\]\s*==(?!=)", tla, re.MULTILINE):
        n = m.group(1)
        if n not in _TLA_KEYWORDS:
            names.append(n)
    for m in re.finditer(r"^\w+\s+(\\[A-Za-z_]\w*)\s+\w+\s*==(?!=)", tla, re.MULTILINE):
        names.append(m.group(1))
    return fmt(names)


# action defs are operators whose body references primed vars or UNCHANGED or ENABLED
def ex_action_def_names(tla, cfg):
    names = []
    defs = list(
        re.finditer(r"^([A-Za-z_]\w*)\s*(?:\([^)]*\)|\[[^\]]+\])?\s*==(?!=)", tla, re.MULTILINE)
    )
    for i, m in enumerate(defs):
        end = defs[i + 1].start() if i + 1 < len(defs) else len(tla)
        body = tla[m.end() : end]
        if re.search(r"\w+'|\bUNCHANGED\b|\bENABLED\b", body):
            names.append(m.group(1))
    return fmt(names)


def ex_recursive_operator_names(tla, cfg):
    names = []
    for m in re.finditer(r"\bRECURSIVE\b([^\n]+)", tla):
        for tok in re.findall(r"([A-Za-z_]\w*)(?:\s*\([_,\s]*\))?", m.group(1)):
            if tok and tok not in _TLA_KEYWORDS:
                names.append(tok)
    return fmt(names)


def ex_local_operator_names(tla, cfg):
    names = []
    for m in re.finditer(r"\bLOCAL\b\s+([A-Za-z_]\w*)", tla):
        n = m.group(1)
        if n != "INSTANCE" and n not in _TLA_KEYWORDS:
            names.append(n)
    return fmt(names)


def ex_let_in_names(tla, cfg):
    names = []
    for m in re.finditer(r"\bLET\b(.*?)\bIN\b", tla, re.DOTALL):
        block = m.group(1)
        for nm in re.finditer(r"\b([A-Za-z_]\w*)\s*(?:\([^)]*\))?\s*==", block, re.MULTILINE):
            names.append(nm.group(1))
        for nm in re.finditer(r"\b([A-Za-z_]\w*)\s*\[[^\]]+\]\s*==", block, re.MULTILINE):
            names.append(nm.group(1))
    return fmt(names)


def ex_lambda_params(tla, cfg):
    results = [f"LAMBDA {m.group(1).strip()}" for m in re.finditer(r"\bLAMBDA\b([^:]+):", tla)]
    return fmt_semi(dedup(results))


def ex_implication(tla, cfg):
    ops = []
    if re.search(r"=>", tla):
        ops.append("=>")
    if re.search(r"<=>", tla):
        ops.append("<=>")
    return fmt(ops)


def ex_negation(tla, cfg):
    if re.search(r"~(?![>])|\\neg\b|\\lnot\b", tla):
        return "~"
    return ""


def ex_boolean_constants(tla, cfg):
    vals = []
    if re.search(r"\bTRUE\b", tla):
        vals.append("TRUE")
    if re.search(r"\bFALSE\b", tla):
        vals.append("FALSE")
    if re.search(r"\bBOOLEAN\b", tla):
        vals.append("BOOLEAN")
    return fmt(vals)


def ex_quantifiers(tla, cfg):
    ops = []
    if re.search(r"\\A\b", tla):
        ops.append(r"\A")
    if re.search(r"\\E\b", tla):
        ops.append(r"\E")
    if re.search(r"\\AA\b", tla):
        ops.append(r"\AA")
    if re.search(r"\\EE\b", tla):
        ops.append(r"\EE")
    return fmt(ops)


def ex_equality_ops(tla, cfg):
    ops = []
    if re.search(r"(?<![<>!/])=(?!=)", tla):
        ops.append("=")
    if re.search(r"/=|(?<!\w)#(?!\w)", tla):
        ops.append("/=")
    return fmt(ops)


def ex_membership_ops(tla, cfg):
    ops = []
    if re.search(r"\\in\b", tla):
        ops.append(r"\in")
    if re.search(r"\\notin\b", tla):
        ops.append(r"\notin")
    if re.search(r"\\subseteq\b", tla):
        ops.append(r"\subseteq")
    return fmt(ops)


def ex_if_then_else(tla, cfg):
    results = []
    for m in re.finditer(r"\bIF\b(.{1,60}?)\bTHEN\b", tla, re.DOTALL):
        cond = re.sub(r"\s+", " ", m.group(1).strip())[:50]
        results.append(f"IF {cond}")
    summary = fmt_semi(dedup(results))
    if summary and re.search(r"\bELSE\b", tla):
        summary += "; ELSE present"
    return summary


def ex_case_expr(tla, cfg):
    results = []
    if re.search(r"\bCASE\b", tla):
        results.append("CASE")
    if re.search(r"\bOTHER\b", tla):
        results.append("OTHER")
    return fmt(results)


def ex_set_enumeration(tla, cfg):
    forms = []
    if re.search(r"\{[^}]*\\in[^}]*:[^}]*\}", tla):
        forms.append(r"{x \in S : P}")
    if re.search(r"\{[^}]*:[^}]*\\in[^}]*\}", tla):
        forms.append(r"{expr : x \in S}")
    if re.search(r"\{[^}|>:][^}]*\}", tla):
        forms.append("{enum}")
    return fmt(forms)


# skip module body before the first ---- MODULE line to avoid false positives in header
def ex_set_operators(tla, cfg):
    ops = []
    mod_m = re.search(r"-{4,}.*MODULE", tla)
    body = tla[mod_m.start() :] if mod_m else tla
    if re.search(r"\bSUBSET\b", body):
        ops.append("SUBSET")
    if re.search(r"\bUNION\b", body):
        ops.append("UNION")
    if re.search(r"\\cup\b", body):
        ops.append(r"\cup")
    if re.search(r"\\cap\b", body):
        ops.append(r"\cap")
    if re.search(r"\\setminus\b", body):
        ops.append(r"\setminus")
    if re.search(r"(?<![/])\\ ", body):
        ops.append("\\\\")
    if re.search(r"\\subseteq\b", body):
        ops.append(r"\subseteq")
    return fmt(ops)


def ex_finite_set_ops(tla, cfg):
    ops = []
    if re.search(r"\bCardinality\b", tla):
        ops.append("Cardinality")
    if re.search(r"\bIsFiniteSet\b", tla):
        ops.append("IsFiniteSet")
    return fmt(ops)


def ex_function_constructor(tla, cfg):
    forms = []
    if re.search(r"\[[^\]]*\\in[^\]]*\|->", tla):
        forms.append(r"[x \in S |-> expr]")
    if re.search(r"\[[^\]]*->(?!>)[^\]]*\]", tla):
        forms.append("[S -> T]")
    return fmt(forms)


def ex_function_application(tla, cfg):
    forms = []
    if re.search(r"\b\w+\[[^\]]+\]", tla):
        forms.append("f[x]")
    if re.search(r"\bDOMAIN\b", tla):
        forms.append("DOMAIN")
    return fmt(forms)


def ex_function_override(tla, cfg):
    forms = []
    if re.search(r"\bEXCEPT\b", tla):
        forms.append("EXCEPT")
    if re.search(r"\s@\s|\s@\b|\b@\s", tla) or re.search(r"EXCEPT.*@", tla):
        forms.append("@")
    return fmt(forms)


# record detection: look for [field |-> ...] but exclude [x \in S |-> ...] function constructors
def ex_record_constructor(tla, cfg):
    fields = []
    for m in re.finditer(r"[\[,]\s*([A-Za-z_]\w*)\s*\|->", tla):
        field = m.group(1)
        chunk = tla[max(0, m.start() - 100) : m.start() + len(m.group())]
        last_open = chunk.rfind("[")
        if last_open >= 0 and re.search(r"\\in\b", chunk[last_open:]):
            continue
        fields.append(field)
    return fmt(fields)


def ex_record_access(tla, cfg):
    return fmt(re.findall(r"\b\w+\.([A-Za-z_]\w*)\b", tla))


def ex_tuple_constructor(tla, cfg):
    return "<<...>>" if re.search(r"<<", tla) else ""


def ex_sequence_ops(tla, cfg):
    return fmt(
        [
            op
            for op in ["Append", "Head", "Tail", "SubSeq", "Len", "SelectSeq", "Seq"]
            if re.search(r"\b" + op + r"\b", tla)
        ]
    )


# strip ---- MODULE header lines before scanning so '-' in separators doesn't count as minus
def ex_arithmetic_ops(tla, cfg):
    stripped = re.sub(r"^[ \t]*[-=]{4,}.*$", "", tla, flags=re.MULTILINE)
    ops = []
    if re.search(r"\+", stripped):
        ops.append("+")
    if re.search(r"(?<![<\-])-(?![->=])", stripped):
        ops.append("-")
    if re.search(r"\*", stripped):
        ops.append("*")
    if re.search(r"\\div\b|\bdiv\b", stripped):
        ops.append("\\div")
    if re.search(r"\\mod\b|\bMOD\b", stripped):
        ops.append("\\mod")
    if re.search(r"\^", stripped):
        ops.append("^")
    return fmt(ops)


def ex_comparison_ops(tla, cfg):
    ops = []
    if re.search(r"(?<!=)<(?!=|>)", tla):
        ops.append("<")
    if re.search(r"(?<!=)>(?!=)", tla):
        ops.append(">")
    if re.search(r"\\leq\b|<=(?!>)", tla):
        ops.append(r"\leq")
    if re.search(r"\\geq\b|>=", tla):
        ops.append(r"\geq")
    return fmt(ops)


def ex_range_expr(tla, cfg):
    ranges = re.findall(r"(\w+)\s*\.\.\s*(\w+)", tla)
    return fmt([f"{a}..{b}" for a, b in ranges])


def ex_choice_expr(tla, cfg):
    results = []
    for m in re.finditer(r"\bCHOOSE\b\s+(\w+)(?:\s*\\in\s*([^:]+))?\s*:", tla):
        var = m.group(1)
        domain = (m.group(2) or "").strip()[:30]
        results.append(f"CHOOSE {var}" + (f" \\in {domain}" if domain else ""))
    return fmt_semi(dedup(results))


def ex_string_literals(tla, cfg):
    return fmt(re.findall(r'"([^"]*)"', tla))


def ex_arithmetic_modules(tla, cfg):
    return fmt([m for m in _extends(tla) if m in ARITHMETIC_MODS])


def ex_data_structure_modules(tla, cfg):
    return fmt([m for m in _extends(tla) if m in DATA_STRUCT_MODS])


def ex_tooling_modules(tla, cfg):
    return fmt([m for m in _extends(tla) if m in TOOLING_MODS])


def ex_primed_variables(tla, cfg):
    return fmt(re.findall(r"\b([A-Za-z_]\w*)\'", tla))


def ex_unchanged_exprs(tla, cfg):
    results = [
        f"UNCHANGED {m.group(1).strip()}"
        for m in re.finditer(r"\bUNCHANGED\b\s*(<<[^>]*>>|\w+|\([^)]*\))", tla)
    ]
    return fmt_semi(dedup(results))


def ex_enabled_exprs(tla, cfg):
    results = []
    for m in re.finditer(r"\b(ENABLED|DISABLED)\b\s*(\w+)?", tla):
        kw = m.group(1)
        arg = (m.group(2) or "").strip()
        results.append((kw + " " + arg).strip())
    return fmt(dedup(results))


def ex_temporal_subscript(tla, cfg):
    results = []
    for m in re.finditer(r"\[\]\s*\[", tla):
        start = m.end()
        depth, pos = 1, start
        while depth > 0 and pos < len(tla):
            if tla[pos] == "[":
                depth += 1
            elif tla[pos] == "]":
                depth -= 1
            pos += 1
        action = tla[start : pos - 1].strip()
        sub_m = re.match(r"_(<<[^>]*>>|\w+)", tla[pos:])
        if sub_m:
            label = action if re.match(r"^[A-Za-z_]\w*$", action) else "..."
            results.append(f"[][{label}]_{sub_m.group(1)}")
    for m in re.finditer(r"<>\s*<<([^>]+)>>_(<<[^>]*>>|\w+)", tla):
        results.append(f"<><< {m.group(1)} >>_{m.group(2)}")
    for m in re.finditer(r"(?<!\])\[([A-Za-z_]\w*(?:\([^)]*\))?)\]_(<<[^>]*>>|\w+)", tla):
        results.append(f"[{m.group(1)}]_{m.group(2)}")
    return fmt_semi(dedup(results))


def ex_always_op(tla, cfg):
    return "[]" if re.search(r"\[\]", tla) else ""


def ex_eventually_op(tla, cfg):
    return "<>" if re.search(r"<>", tla) else ""


def ex_leads_to_op(tla, cfg):
    return "~>" if re.search(r"~>", tla) else ""


def ex_fairness_conditions(tla, cfg):
    results = []
    for m in re.finditer(r"\b(WF|SF)_(\w+)", tla):
        results.append(m.group(1) + "_" + m.group(2))
    for m in re.finditer(r"\b(WF|SF)_(<<[^>]*>>)", tla):
        results.append(m.group(1) + "_" + m.group(2).strip())
    return fmt(dedup(results))


def ex_proof_hints(tla, cfg):
    return fmt([kw for kw in ["BY", "USE", "HIDE", "DEF"] if re.search(r"\b" + kw + r"\b", tla)])


def ex_proof_commands(tla, cfg):
    return fmt(
        [
            kw
            for kw in ["QED", "OBVIOUS", "SUFFICES", "CASE", "PICK", "WITNESS", "HAVE", "TAKE"]
            if re.search(r"\b" + kw + r"\b", tla)
        ]
    )


def ex_proof_structure_steps(tla, cfg):
    levels = sorted(set(re.findall(r"<(\d+)>", tla)), key=int)
    return ", ".join(f"<{level}>" for level in levels)


def ex_assume_prove_blocks(tla, cfg):
    results = []
    if re.search(r"\bASSUME\b.*\bPROVE\b|\bPROOF\b", tla, re.DOTALL):
        results.append("ASSUME/PROVE")
    if re.search(r"\bPROOF\b", tla):
        results.append("PROOF")
    return fmt(results)


def ex_plus_cal_algorithm(
    tla: str, cfg: str, entry: dict[str, Any] | None = None, base_paths: list[str] | None = None
) -> str:
    """Extract PlusCal algorithm declaration."""
    block = _pluscal_block(entry, base_paths) if entry else ""
    m = re.search(r"--(fair\s+)?algorithm\s+(\w+)", block)
    if m:
        fair = "fair " if m.group(1) else ""
        return f"--{fair}algorithm {m.group(2)}"
    return ""


def ex_plus_cal_processes(
    tla: str, cfg: str, entry: dict[str, Any] | None = None, base_paths: list[str] | None = None
) -> str:
    """Extract PlusCal process definitions."""
    block = _pluscal_block(entry, base_paths) if entry else ""
    procs = []
    for m in re.finditer(r"(?:fair\s+)?process\s+\(?\s*(\w+)\s*(\\in|=)\s*([^\n{)]+)", block):
        name = m.group(1)
        sep = m.group(2)
        val = m.group(3).strip()
        if sep == "=":
            procs.append(f"process {name} = {val}")
        else:
            procs.append(f"process {name} \\in {val}")
    return fmt_semi(dedup(procs))


# model values are constants set equal to themselves in cfg e.g. Node = Node
def ex_model_values(tla, cfg):
    return fmt(
        [m.group(1) for m in re.finditer(r"(\w+)\s*=\s*(\w+)", cfg) if m.group(1) == m.group(2)]
    )


def ex_operator_overrides(tla, cfg):
    return fmt_semi(
        dedup([f"{m.group(1)} <- {m.group(2)}" for m in re.finditer(r"(\w+)\s*<-\s*(\w+)", cfg)])
    )


def ex_symmetry_set(tla, cfg):
    names = []
    for m in re.finditer(r"^SYMMETRY\b\s*\n?([ \t]+\S+)", cfg, re.MULTILINE):
        names.append(m.group(1).strip())
    for m in re.finditer(r"^SYMMETRY\b\s+(\w+)", cfg, re.MULTILINE):
        names.append(m.group(1))
    return fmt(names)


def ex_state_constraint(tla, cfg):
    names = []
    for m in re.finditer(r"^CONSTRAINT\b\s*\n((?:[ \t]+\S+\n?)*)", cfg, re.MULTILINE):
        names += re.findall(r"\S+", m.group(1))
    for m in re.finditer(r"^CONSTRAINT\b\s+(\w+)", cfg, re.MULTILINE):
        names.append(m.group(1))
    return fmt(names)


def ex_action_constraint(tla, cfg):
    names = []
    for m in re.finditer(r"^ACTION_CONSTRAINT\b\s*\n((?:[ \t]+\S+\n?)*)", cfg, re.MULTILINE):
        names += re.findall(r"\S+", m.group(1))
    for m in re.finditer(r"^ACTION_CONSTRAINT\b\s+(\w+)", cfg, re.MULTILINE):
        names.append(m.group(1))
    return fmt(names)


def ex_view_expr(tla, cfg):
    names = []
    for m in re.finditer(r"^VIEW\b\s*\n?([ \t]+\S+)", cfg, re.MULTILINE):
        names.append(m.group(1).strip())
    for m in re.finditer(r"^VIEW\b\s+(\w+)", cfg, re.MULTILINE):
        names.append(m.group(1))
    return fmt(names)


# ordered list of (json key, extractor function) — order here defines key order in output
FINE_FEATURES = [
    ("ModuleName", ex_module_name),
    ("ExtendsModules", ex_extends_modules),
    ("InstanceModules", ex_instance_modules),
    ("InstanceSubstitutions", ex_instance_substitutions),
    ("ConstantNames", ex_constant_names),
    ("VariableNames", ex_variable_names),
    ("AssumptionNames", ex_assumption_names),
    ("TheoremNames", ex_theorem_names),
    ("OperatorDefNames", ex_operator_def_names),
    ("ActionDefNames", ex_action_def_names),
    ("RecursiveOperatorNames", ex_recursive_operator_names),
    ("LocalOperatorNames", ex_local_operator_names),
    ("LetInNames", ex_let_in_names),
    ("LambdaParams", ex_lambda_params),
    ("Implication", ex_implication),
    ("Negation", ex_negation),
    ("BooleanConstants", ex_boolean_constants),
    ("Quantifiers", ex_quantifiers),
    ("EqualityOps", ex_equality_ops),
    ("MembershipOps", ex_membership_ops),
    ("IfThenElse", ex_if_then_else),
    ("CaseExpr", ex_case_expr),
    ("SetEnumeration", ex_set_enumeration),
    ("SetOperators", ex_set_operators),
    ("FiniteSetOps", ex_finite_set_ops),
    ("FunctionConstructor", ex_function_constructor),
    ("FunctionApplication", ex_function_application),
    ("FunctionOverride", ex_function_override),
    ("RecordConstructor", ex_record_constructor),
    ("RecordAccess", ex_record_access),
    ("TupleConstructor", ex_tuple_constructor),
    ("SequenceOps", ex_sequence_ops),
    ("ArithmeticOps", ex_arithmetic_ops),
    ("ComparisonOps", ex_comparison_ops),
    ("RangeExpr", ex_range_expr),
    ("ChoiceExpr", ex_choice_expr),
    ("StringLiterals", ex_string_literals),
    ("ArithmeticModules", ex_arithmetic_modules),
    ("DataStructureModules", ex_data_structure_modules),
    ("ToolingModules", ex_tooling_modules),
    ("PrimedVariables", ex_primed_variables),
    ("UnchangedExprs", ex_unchanged_exprs),
    ("EnabledExprs", ex_enabled_exprs),
    ("TemporalSubscript", ex_temporal_subscript),
    ("AlwaysOp", ex_always_op),
    ("EventuallyOp", ex_eventually_op),
    ("LeadsToOp", ex_leads_to_op),
    ("FairnessConditions", ex_fairness_conditions),
    ("ProofHints", ex_proof_hints),
    ("ProofCommands", ex_proof_commands),
    ("ProofStructureSteps", ex_proof_structure_steps),
    ("AssumeProveBlocks", ex_assume_prove_blocks),
    ("PlusCalAlgorithm", ex_plus_cal_algorithm),
    ("PlusCalProcesses", ex_plus_cal_processes),
    ("ModelValues", ex_model_values),
    ("OperatorOverrides", ex_operator_overrides),
    ("SymmetrySet", ex_symmetry_set),
    ("StateConstraint", ex_state_constraint),
    ("ActionConstraint", ex_action_constraint),
    ("ViewExpr", ex_view_expr),
]

# maps each fine key to one of the 10 coarse buckets
COARSE_MAP = {
    "ModuleName": "ModuleSystem",
    "ExtendsModules": "ModuleSystem",
    "InstanceModules": "ModuleSystem",
    "InstanceSubstitutions": "ModuleSystem",
    "ConstantNames": "Declarations",
    "VariableNames": "Declarations",
    "AssumptionNames": "Declarations",
    "TheoremNames": "Declarations",
    "OperatorDefNames": "Definitions",
    "ActionDefNames": "Definitions",
    "RecursiveOperatorNames": "Definitions",
    "LocalOperatorNames": "Definitions",
    "LetInNames": "Definitions",
    "LambdaParams": "Definitions",
    "Implication": "Expressions",
    "Negation": "Expressions",
    "BooleanConstants": "Expressions",
    "Quantifiers": "Expressions",
    "EqualityOps": "Expressions",
    "MembershipOps": "Expressions",
    "IfThenElse": "Expressions",
    "CaseExpr": "Expressions",
    "SetEnumeration": "Expressions",
    "SetOperators": "Expressions",
    "FiniteSetOps": "Expressions",
    "FunctionConstructor": "Expressions",
    "FunctionApplication": "Expressions",
    "FunctionOverride": "Expressions",
    "RecordConstructor": "Expressions",
    "RecordAccess": "Expressions",
    "TupleConstructor": "Expressions",
    "SequenceOps": "Expressions",
    "ArithmeticOps": "Expressions",
    "ComparisonOps": "Expressions",
    "RangeExpr": "Expressions",
    "ChoiceExpr": "Expressions",
    "StringLiterals": "Expressions",
    "ArithmeticModules": "StandardLibrary",
    "DataStructureModules": "StandardLibrary",
    "ToolingModules": "StandardLibrary",
    "PrimedVariables": "StateAndActions",
    "UnchangedExprs": "StateAndActions",
    "EnabledExprs": "StateAndActions",
    "TemporalSubscript": "StateAndActions",
    "AlwaysOp": "TemporalLogic",
    "EventuallyOp": "TemporalLogic",
    "LeadsToOp": "TemporalLogic",
    "FairnessConditions": "TemporalLogic",
    "ProofHints": "ProofLanguage",
    "ProofCommands": "ProofLanguage",
    "ProofStructureSteps": "ProofLanguage",
    "AssumeProveBlocks": "ProofLanguage",
    "PlusCalAlgorithm": "PlusCal",
    "PlusCalProcesses": "PlusCal",
    "ModelValues": "ToolingModelConfig",
    "OperatorOverrides": "ToolingModelConfig",
    "SymmetrySet": "ToolingModelConfig",
    "StateConstraint": "ToolingModelConfig",
    "ActionConstraint": "ToolingModelConfig",
    "ViewExpr": "ToolingModelConfig",
}

# fixed order for coarse output keys
COARSE_KEYS = [
    "ModuleSystem",
    "Declarations",
    "Definitions",
    "Expressions",
    "StandardLibrary",
    "StateAndActions",
    "TemporalLogic",
    "ProofLanguage",
    "PlusCal",
    "ToolingModelConfig",
]


# ordered list of (json key, extractor function) — order here defines key order in output
FINE_FEATURES = [
    ("ModuleName", ex_module_name),
    ("ExtendsModules", ex_extends_modules),
    ("InstanceModules", ex_instance_modules),
    ("InstanceSubstitutions", ex_instance_substitutions),
    ("ConstantNames", ex_constant_names),
    ("VariableNames", ex_variable_names),
    ("AssumptionNames", ex_assumption_names),
    ("TheoremNames", ex_theorem_names),
    ("OperatorDefNames", ex_operator_def_names),
    ("ActionDefNames", ex_action_def_names),
    ("RecursiveOperatorNames", ex_recursive_operator_names),
    ("LocalOperatorNames", ex_local_operator_names),
    ("LetInNames", ex_let_in_names),
    ("LambdaParams", ex_lambda_params),
    ("Implication", ex_implication),
    ("Negation", ex_negation),
    ("BooleanConstants", ex_boolean_constants),
    ("Quantifiers", ex_quantifiers),
    ("EqualityOps", ex_equality_ops),
    ("MembershipOps", ex_membership_ops),
    ("IfThenElse", ex_if_then_else),
    ("CaseExpr", ex_case_expr),
    ("SetEnumeration", ex_set_enumeration),
    ("SetOperators", ex_set_operators),
    ("FiniteSetOps", ex_finite_set_ops),
    ("FunctionConstructor", ex_function_constructor),
    ("FunctionApplication", ex_function_application),
    ("FunctionOverride", ex_function_override),
    ("RecordConstructor", ex_record_constructor),
    ("RecordAccess", ex_record_access),
    ("TupleConstructor", ex_tuple_constructor),
    ("SequenceOps", ex_sequence_ops),
    ("ArithmeticOps", ex_arithmetic_ops),
    ("ComparisonOps", ex_comparison_ops),
    ("RangeExpr", ex_range_expr),
    ("ChoiceExpr", ex_choice_expr),
    ("StringLiterals", ex_string_literals),
    ("ArithmeticModules", ex_arithmetic_modules),
    ("DataStructureModules", ex_data_structure_modules),
    ("ToolingModules", ex_tooling_modules),
    ("PrimedVariables", ex_primed_variables),
    ("UnchangedExprs", ex_unchanged_exprs),
    ("EnabledExprs", ex_enabled_exprs),
    ("TemporalSubscript", ex_temporal_subscript),
    ("AlwaysOp", ex_always_op),
    ("EventuallyOp", ex_eventually_op),
    ("LeadsToOp", ex_leads_to_op),
    ("FairnessConditions", ex_fairness_conditions),
    ("ProofHints", ex_proof_hints),
    ("ProofCommands", ex_proof_commands),
    ("ProofStructureSteps", ex_proof_structure_steps),
    ("AssumeProveBlocks", ex_assume_prove_blocks),
    ("PlusCalAlgorithm", ex_plus_cal_algorithm),
    ("PlusCalProcesses", ex_plus_cal_processes),
    ("ModelValues", ex_model_values),
    ("OperatorOverrides", ex_operator_overrides),
    ("SymmetrySet", ex_symmetry_set),
    ("StateConstraint", ex_state_constraint),
    ("ActionConstraint", ex_action_constraint),
    ("ViewExpr", ex_view_expr),
]

# maps each fine key to one of the 10 coarse buckets
COARSE_MAP = {
    "ModuleName": "ModuleSystem",
    "ExtendsModules": "ModuleSystem",
    "InstanceModules": "ModuleSystem",
    "InstanceSubstitutions": "ModuleSystem",
    "ConstantNames": "Declarations",
    "VariableNames": "Declarations",
    "AssumptionNames": "Declarations",
    "TheoremNames": "Declarations",
    "OperatorDefNames": "Definitions",
    "ActionDefNames": "Definitions",
    "RecursiveOperatorNames": "Definitions",
    "LocalOperatorNames": "Definitions",
    "LetInNames": "Definitions",
    "LambdaParams": "Definitions",
    "Implication": "Expressions",
    "Negation": "Expressions",
    "BooleanConstants": "Expressions",
    "Quantifiers": "Expressions",
    "EqualityOps": "Expressions",
    "MembershipOps": "Expressions",
    "IfThenElse": "Expressions",
    "CaseExpr": "Expressions",
    "SetEnumeration": "Expressions",
    "SetOperators": "Expressions",
    "FiniteSetOps": "Expressions",
    "FunctionConstructor": "Expressions",
    "FunctionApplication": "Expressions",
    "FunctionOverride": "Expressions",
    "RecordConstructor": "Expressions",
    "RecordAccess": "Expressions",
    "TupleConstructor": "Expressions",
    "SequenceOps": "Expressions",
    "ArithmeticOps": "Expressions",
    "ComparisonOps": "Expressions",
    "RangeExpr": "Expressions",
    "ChoiceExpr": "Expressions",
    "StringLiterals": "Expressions",
    "ArithmeticModules": "StandardLibrary",
    "DataStructureModules": "StandardLibrary",
    "ToolingModules": "StandardLibrary",
    "PrimedVariables": "StateAndActions",
    "UnchangedExprs": "StateAndActions",
    "EnabledExprs": "StateAndActions",
    "TemporalSubscript": "StateAndActions",
    "AlwaysOp": "TemporalLogic",
    "EventuallyOp": "TemporalLogic",
    "LeadsToOp": "TemporalLogic",
    "FairnessConditions": "TemporalLogic",
    "ProofHints": "ProofLanguage",
    "ProofCommands": "ProofLanguage",
    "ProofStructureSteps": "ProofLanguage",
    "AssumeProveBlocks": "ProofLanguage",
    "PlusCalAlgorithm": "PlusCal",
    "PlusCalProcesses": "PlusCal",
    "ModelValues": "ToolingModelConfig",
    "OperatorOverrides": "ToolingModelConfig",
    "SymmetrySet": "ToolingModelConfig",
    "StateConstraint": "ToolingModelConfig",
    "ActionConstraint": "ToolingModelConfig",
    "ViewExpr": "ToolingModelConfig",
}

# fixed order for coarse output keys
COARSE_KEYS = [
    "ModuleSystem",
    "Declarations",
    "Definitions",
    "Expressions",
    "StandardLibrary",
    "StateAndActions",
    "TemporalLogic",
    "ProofLanguage",
    "PlusCal",
    "ToolingModelConfig",
]


class TlaTransformer:
    """High-level TLA+ feature extraction service."""

    def __init__(self, base_paths: list[str] | None = None):
        """Initialize transformer with optional base paths for file search."""
        self.base_paths = base_paths or []

    def transform(
        self,
        specs: list[dict[str, Any]],
        output_fine: str | None = None,
        output_coarse: str | None = None,
        output_individual_dir: str | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Transform specs and optionally write to JSON files.

        Args:
            specs: List of spec dictionaries with 'model', 'tla_clean', 'tla_original', 'cfg'
            output_fine: Optional path to write combined fine-grained JSON
            output_coarse: Optional path to write combined coarse-grained JSON
            output_individual_dir: Optional directory to write individual JSON files per spec
                (each in a subdirectory named after the spec/model)

        Returns:
            Tuple of (fine_records, coarse_records)
        """
        fine_out = []
        coarse_out = []
        errors = []

        for idx, entry in enumerate(specs):
            spec = entry.get("model", f"spec_{idx}")

            # Prefer clean TLA (with pluscal stripped), fall back to original
            tla_text = get_file_content(entry.get("tla_clean", ""), self.base_paths)
            if not tla_text:
                tla_text = get_file_content(entry.get("tla_original", ""), self.base_paths)
            if not tla_text:
                errors.append(f"  [{idx:03d}] TLA not found: {spec}")
                tla_text = ""

            cfg_text = (
                get_file_content(entry.get("cfg", ""), self.base_paths) if entry.get("cfg") else ""
            )

            # Extract all fine-grained features
            fine_record = {"id": idx, "Specification": spec}
            for key, extractor in FINE_FEATURES:
                sig = inspect.signature(extractor)
                try:
                    if "entry" in sig.parameters and "base_paths" in sig.parameters:
                        fine_record[key] = extractor(
                            tla_text, cfg_text, entry=entry, base_paths=self.base_paths
                        )
                    elif "entry" in sig.parameters:
                        fine_record[key] = extractor(tla_text, cfg_text, entry=entry)
                    elif "base_paths" in sig.parameters:
                        fine_record[key] = extractor(tla_text, cfg_text, base_paths=self.base_paths)
                    else:
                        fine_record[key] = extractor(tla_text, cfg_text)
                except Exception as e:
                    errors.append(f"  [{idx:03d}] Error extracting {key} from {spec}: {e}")
                    fine_record[key] = ""

            fine_out.append(fine_record)

            # Group features into coarse buckets
            coarse_record = {"id": idx, "Specification": spec}
            coarse_buckets: dict[str, list[str]] = {k: [] for k in COARSE_KEYS}
            for key, _ in FINE_FEATURES:
                val = fine_record[key]
                cat = COARSE_MAP.get(key)
                if cat and val:
                    coarse_buckets[cat].append(val)

            for cat in COARSE_KEYS:
                coarse_record[cat] = "; ".join(coarse_buckets[cat]) if coarse_buckets[cat] else ""

            coarse_out.append(coarse_record)

        # Write output files if specified
        if output_fine:
            Path(output_fine).parent.mkdir(parents=True, exist_ok=True)
            with open(output_fine, "w", encoding="utf-8") as f:
                json.dump(fine_out, f, indent=2, ensure_ascii=False)

        if output_coarse:
            Path(output_coarse).parent.mkdir(parents=True, exist_ok=True)
            with open(output_coarse, "w", encoding="utf-8") as f:
                json.dump(coarse_out, f, indent=2, ensure_ascii=False)

        # Write individual JSON files if specified
        if output_individual_dir:
            output_dir = Path(output_individual_dir)
            for idx, fine_rec in enumerate(fine_out):
                coarse_rec = coarse_out[idx] if idx < len(coarse_out) else {}
                spec_name = fine_rec.get("Specification", f"spec_{idx:04d}")

                # Create subdirectory for this spec (using model name or ID)
                spec_dir = output_dir / spec_name
                spec_dir.mkdir(parents=True, exist_ok=True)

                # Combine fine and coarse data in a single JSON file
                combined_record = {
                    **fine_rec,
                    **{f"coarse_{k}": v for k, v in coarse_rec.items() if k not in ["id", "Specification"]}
                }

                spec_file = spec_dir / "data.json"
                with open(spec_file, "w", encoding="utf-8") as f:
                    json.dump(combined_record, f, indent=2, ensure_ascii=False)

        if errors:
            print(f"Transformation completed with {len(errors)} warning(s):")
            for err in errors:
                print(err)

        return fine_out, coarse_out


def transform(
    specs: list[dict[str, Any]],
    output_fine: str | None = None,
    output_coarse: str | None = None,
    base_paths: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Standalone function to transform TLA+ specs.

    Args:
        specs: List of spec dictionaries
        output_fine: Optional path to write fine-grained features
        output_coarse: Optional path to write coarse-grained features
        base_paths: Optional list of base paths for file search

    Returns:
        Tuple of (fine_records, coarse_records)
    """
    transformer = TlaTransformer(base_paths)
    return transformer.transform(specs, output_fine, output_coarse)


def main() -> None:
    """Main entry point for backwards compatibility with standalone script."""
    print("Error: This script now requires structured input via the transform() function")
    print("or TlaTransformer class. Use the CLI command 'tladata transform' instead.")
    print("\nExample usage:")
    print("  from tladata.transform.json import transform")
    print("  specs = [{'model': 'Example', 'tla_clean': 'path/to/file.tla', 'cfg': None}]")
    print("  fine, coarse = transform(specs, output_fine='fine.json', output_coarse='coarse.json')")


if __name__ == "__main__":
    main()
