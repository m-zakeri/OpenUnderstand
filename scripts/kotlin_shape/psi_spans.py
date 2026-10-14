"""Read a Kotlin compiler PSI dump (.txt) into typed source spans.

Leaves carry their text, so concatenating them rebuilds the source; a node's
span is the offsets of its first and last leaf. Whitespace/comment leaves are
kept so offsets line up, but spans are trimmed of them."""
import re, sys

LEAF = re.compile(r"^(\s*)(PsiWhiteSpace|PsiComment\((\w+)\)|PsiElement\((\w+)\)|PsiErrorElement)(.*)$")

def unescape(s):
    return (s.replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
             .replace("\\'", "'").replace("\\\\", "\\"))

def parse(path):
    """-> (text, nodes) ; node = dict(type, start, end, depth, leaf)"""
    lines = open(path, encoding="utf-8").read().split("\n")
    text, nodes, stack = [], [], []   # stack of open node indices by depth
    pos = 0
    for ln in lines[1:]:
        if not ln.strip() or ln.strip() == "<empty list>":
            continue
        depth = (len(ln) - len(ln.lstrip(" "))) // 2
        body = ln.strip()
        m = re.match(r"^(PsiWhiteSpace|PsiComment\((\w+)\)|PsiElement\(([\w.]+)\)|PsiErrorElement:.*)", body)
        if body.startswith("PsiErrorElement"):
            nodes.append(dict(type="ERROR", start=pos, end=pos, depth=depth, leaf=False))
            del stack[depth - 1:]; stack.append(len(nodes) - 1)
            continue
        if m and (body.startswith("PsiWhiteSpace") or body.startswith("PsiComment") or body.startswith("PsiElement(")):
            t = re.search(r"\('(.*)'\)$", body, re.S)
            s = unescape(t.group(1)) if t else ""
            kind = "WS" if body.startswith("PsiWhiteSpace") else ("COMMENT" if body.startswith("PsiComment") else m.group(3))
            if any(nodes[i]["type"] in ("KDoc", "ERROR") and nodes[i]["type"] == "KDoc" for i in stack[:depth - 1]):
                kind = "COMMENT"
            nodes.append(dict(type=kind, start=pos, end=pos + len(s), depth=depth, leaf=True))
            text.append(s); pos += len(s)
            for i in stack[:depth - 1]:
                nodes[i]["end"] = pos
            continue
        nodes.append(dict(type=body.split(":")[0].split("(")[0], start=pos, end=pos, depth=depth, leaf=False))
        del stack[depth - 1:]; stack.append(len(nodes) - 1)
    return "".join(text), nodes

if __name__ == "__main__":
    import collections
    c = collections.Counter(); bad = 0
    for p in sys.argv[1:]:
        t, ns = parse(p)
        src = open(p[:-4] + ".kt", encoding="utf-8").read() if not p.endswith(".kts") else ""
        if t != src: bad += 1
        c.update(n["type"] for n in ns if not n["leaf"])
    print("text mismatch:", bad, "of", len(sys.argv) - 1)
    for k, v in c.most_common(70): print(v, k)
