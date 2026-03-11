import pathlib, re, tokenize, io

def strip_comments_and_docstrings(source: str) -> str:
    output_tokens = []
    prev_toktype = tokenize.INDENT
    tokgen = tokenize.generate_tokens(io.StringIO(source).readline)
    for tok in tokgen:
        toktype = tok.type
        ttext = tok.string
        if toktype == tokenize.COMMENT:
            continue
        if toktype == tokenize.STRING and prev_toktype == tokenize.INDENT:
            # skip docstring
            continue
        output_tokens.append(tok)
        prev_toktype = toktype
    return tokenize.untokenize(output_tokens)


for path in pathlib.Path("backend").rglob("*.py"):
    if path.name.startswith("test_"):
        path.unlink()
        print("deleted", path)
        continue
    text = path.read_text(encoding="utf-8")
    new = strip_comments_and_docstrings(text)
    if new != text:
        path.write_text(new, encoding="utf-8")
        print("cleaned", path)
