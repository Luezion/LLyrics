"""Usado pelo GitHub Actions: valida um estilo enviado por issue e, se aprovado, coloca na galeria.

python community/publish.py check   -> imprime um resumo (ou erro) para comentar na issue
python community/publish.py publish -> adiciona em community/looks.json
Lê o texto da issue de ISSUE_BODY e o número de ISSUE_NUMBER.
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import lookcode  # noqa: E402

GALLERY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "looks.json")


def fields(body):
    """Lê os campos de um formulário de issue do GitHub (### Título + valor)."""
    out, cur = {}, None
    for line in (body or "").replace("\r", "").split("\n"):
        if line.startswith("### "):
            cur = line[4:].strip().lower()
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    clean = {}
    for k, v in out.items():
        text = "\n".join(v).strip().strip("`").replace("text\n", "", 1).strip()
        if text == "_No response_":
            text = ""
        clean[k] = text
    pick = lambda prefix: next((v for k, v in clean.items() if k.startswith(prefix)), "")  # noqa: E731
    return {
        "name": pick("style name")[:60],
        "author": pick("your name")[:40],
        "description": pick("short description")[:160],
        "code": lookcode.find_code(pick("style code") or body or "") or "",
    }


def main():
    mode = sys.argv[1]
    f = fields(os.environ.get("ISSUE_BODY", ""))
    try:
        style = lookcode.decode(f["code"])
    except ValueError as e:
        print(f"❌ The style code is not valid ({e}). / El código no es válido. / O código não é válido.")
        sys.exit(1 if mode == "publish" else 0)
    if not f["name"]:
        print("❌ Missing style name. / Falta el nombre. / Falta o nome.")
        sys.exit(1 if mode == "publish" else 0)
    if mode == "check":
        print(f"✅ Valid style: **{f['name']}**" + (f" by {f['author']}" if f["author"] else "")
              + f" ({len(style)} options). Waiting for approval. / Esperando aprobación. / Aguardando aprovação.")
        return
    with open(GALLERY, encoding="utf-8") as fh:
        data = json.load(fh)
    num = os.environ.get("ISSUE_NUMBER", "0")
    look_id = f"issue-{num}"
    data["looks"] = [x for x in data["looks"] if x.get("id") != look_id]
    data["looks"].append({
        "id": look_id,
        "name": f["name"],
        "author": f["author"],
        "description": f["description"],
        "code": lookcode.encode(style),
        "added": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    with open(GALLERY, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"🎉 **{f['name']}** is now in the LLyrics community gallery! / ¡Ya está en la galería! / Já está na galeria!")


if __name__ == "__main__":
    main()
