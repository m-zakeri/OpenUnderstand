"""Compare this grammar's tree shape with Kotlin's PSI, per element type.

    bash gen_py.sh
    git clone --depth 1 --filter=blob:none --sparse https://github.com/JetBrains/kotlin K
    (cd K && git sparse-checkout set compiler/psi/psi-impl/testData/psi)
    ../../.venv/bin/python compare.py K/compiler/psi/psi-impl/testData/psi

Every .kt whose expected PSI dump has no PsiErrorElement and which the grammar
parses cleanly is compared; the rest are skipped."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psi_spans, antlr_spans

LEAFISH = {"WS", "COMMENT", "SEMICOLON"}
KINDS = set(antlr_spans.SIMPLE.values()) | {
    "BINARY_EXPRESSION", "IS_EXPRESSION", "BINARY_WITH_TYPE", "PREFIX_EXPRESSION", "POSTFIX_EXPRESSION",
    "DOT_QUALIFIED_EXPRESSION", "SAFE_ACCESS_EXPRESSION", "CALL_EXPRESSION", "ARRAY_ACCESS_EXPRESSION",
    "CALLABLE_REFERENCE_EXPRESSION", "CLASS_LITERAL_EXPRESSION", "DESTRUCTURING_DECLARATION",
    "ANNOTATED_EXPRESSION", "LABELED_EXPRESSION", "RETURN", "THROW", "BREAK", "CONTINUE", "OBJECT_LITERAL",
    "USER_TYPE", "NULLABLE_TYPE"}
SKIP_FILES = {"escapedLiterals.kt", "Escapes.kt"}  # their dumps escape text the reader cannot rebuild
PARTIAL = set()


def psi_set(txt, kinds):
    t, ns = psi_spans.parse(txt)
    leaves = [n for n in ns if n["leaf"]]
    out = []
    for n in ns:
        if n["leaf"] or n["type"] not in kinds:
            continue
        inside = [l for l in leaves if l["start"] >= n["start"] and l["end"] <= n["end"]
                  and l["type"] not in LEAFISH and l["end"] > l["start"]]
        if n["type"] == "ENUM_ENTRY":
            inside = [l for l in inside if l["type"] != "COMMA"]
        if inside:
            out.append((n["type"], min(l["start"] for l in inside), max(l["end"] for l in inside)))
    return out


def ours(src):
    a, errs = antlr_spans.spans(src)
    cr = "CALLABLE_REFERENCE_EXPRESSION"   # the grammar can reach one reference two ways
    return errs, collections.Counter(set(x for x in a if x[0] == cr)) + collections.Counter(x for x in a if x[0] != cr)


def main(root, kinds):
    tot = collections.defaultdict(lambda: [0, 0, 0]); ex = collections.defaultdict(list)
    files = identical = 0
    for dp, _, fs in sorted(os.walk(root)):
        for f in sorted(fs):
            if not f.endswith(".kt") or f in SKIP_FILES:
                continue
            kt = os.path.join(dp, f); txt = kt[:-3] + ".txt"
            if not os.path.exists(txt) or "PsiErrorElement" in open(txt, encoding="utf-8").read():
                continue
            src = open(kt, encoding="utf-8").read()
            errs, A = ours(src)
            if errs:
                continue
            A = collections.Counter({k: v for k, v in A.items() if k[0] in kinds})
            P = collections.Counter(psi_set(txt, kinds))
            files += 1; identical += P == A
            for (k, a, b), c in P.items(): tot[k][0] += c
            for (k, a, b), c in A.items(): tot[k][1] += c
            for key in set(A) & set(P): tot[key[0]][2] += min(A[key], P[key])
            for key in P - A: ex[key[0]].append((f, "psi-only", src[key[1]:key[2]]))
            for key in A - P: ex[key[0]].append((f, "ours-only", src[key[1]:key[2]]))
    return files, identical, tot, ex


if __name__ == "__main__":
    kinds = KINDS - PARTIAL
    files, identical, tot, ex = main(sys.argv[1], kinds)
    P = sum(v[0] for v in tot.values()); A = sum(v[1] for v in tot.values()); M = sum(v[2] for v in tot.values())
    print("%-32s %6s %6s %6s" % ("kind", "psi", "ours", "match"))
    for k, (p, a, m) in sorted(tot.items()):
        print("%-32s %6d %6d %6d %s" % (k, p, a, m, "" if p == a == m else "  <-- DIFF"))
    print("files %d, identical %d; recall %.4f precision %.4f" % (files, identical, M / P, M / A))
    if len(sys.argv) > 2:
        for k, v in ex.items():
            for f, side, s in v[:int(sys.argv[2])]: print(k, f, side, repr(s[:90]))
