#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Painel Envio de NF e Documentos
# Le a aba PAINEL da planilha "Envio de NF e Documentos" (CSV publicado, URL no
# secret SHEET_CSV_URL) e reescreve ROWS, TODAY, o periodo e a frase do aviso
# dentro do index.html. Uso local: python atualizar_painel.py arquivo.csv
import csv, io, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
BRT = timezone(timedelta(hours=-3))
MESES = "jan fev mar abr mai jun jul ago set out nov dez".split()
COLS = ["data_hora", "solicitante", "numero_totvs", "protocolo", "comprovante",
        "valor", "retorno", "vencimento", "fornecedor"]
DESDE = os.environ.get("DATA_INICIAL", "2026-06-01")


def data_de(txt):
    txt = (txt or "").strip()
    m = re.match(r"^(\d{1,2})\D*de\s+([a-zç]{3})[^,]*,?\s+(\d{4})", txt, re.I)
    if m and m.group(2).lower() in MESES:
        return "%s-%02d-%02d" % (m.group(3), MESES.index(m.group(2).lower()) + 1, int(m.group(1)))
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})", txt)
    if m:
        return "%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1)))
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", txt)
    if m:
        return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
    return None


def valor_de(txt):
    """'R$ 1.256,00' -> 1256.0 · '200.00' -> 200.0 · 'R$ 130' -> 130.0 · 'teste' -> None"""
    s = re.sub(r"[^\d,.\-]", "", txt or "")
    if not re.search(r"\d", s):
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif not re.search(r"\.\d{1,2}$", s):
        s = s.replace(".", "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def retorno_de(txt):
    t = (txt or "").lower()
    if "incorret" in t:
        return "Incorreto"
    if "corret" in t:
        return "Correto"
    return "Sem retorno"


def eh_teste(*campos):
    return any(re.search(r"\btest", (c or ""), re.I) for c in campos)


def js(v):
    return '"%s"' % re.sub(r"\s+", " ", (v or "").strip()).replace("\\", "\\\\").replace('"', '\\"')


def ler(txt):
    linhas = [l for l in csv.reader(io.StringIO(txt)) if any((c or "").strip() for c in l)]
    if not linhas:
        sys.exit("CSV vazio.")
    cab = [(c or "").strip().lower() for c in linhas[0]]
    faltam = [c for c in COLS if c not in cab]
    if faltam:
        sys.exit("Faltam colunas no CSV: %s (recebi %s)" % (faltam, cab))
    idx = {c: cab.index(c) for c in COLS}
    out, testes = [], 0
    for l in linhas[1:]:
        g = lambda c: l[idx[c]].strip() if idx[c] < len(l) else ""
        d = data_de(g("data_hora"))
        if not d or d < DESDE:
            continue
        if eh_teste(g("numero_totvs"), g("valor")):
            testes += 1
            continue
        comp = g("comprovante").lower()
        out.append({
            "d": d,
            "sol": g("solicitante").lstrip("@").strip() or "Não informado",
            "totvs": g("numero_totvs"),
            "forn": g("fornecedor"),
            "prot": re.sub(r"\D", "", g("protocolo")),
            "comp": "Sim" if comp.startswith("s") else ("Não" if comp.startswith("n") else "—"),
            "valor": valor_de(g("valor")),
            "ret": retorno_de(g("retorno")),
            "venc": data_de(g("vencimento")),
        })
    out.sort(key=lambda r: (r["d"], r["prot"]))
    return out, testes


def main():
    if len(sys.argv) > 1:
        txt = open(sys.argv[1], encoding="utf-8-sig").read()
    else:
        url = os.environ.get("SHEET_CSV_URL", "").strip()
        if not url:
            sys.exit("Falta o secret SHEET_CSV_URL.")
        req = urllib.request.Request(url, headers={"User-Agent": "painel-nf"})
        txt = urllib.request.urlopen(req, timeout=60).read().decode("utf-8-sig", "replace")
    regs, testes = ler(txt)
    if not regs:
        sys.exit("Nenhuma linha valida no CSV; nao vou sobrescrever o painel.")

    html = open(INDEX, encoding="utf-8").read()
    antes = html
    agora = datetime.now(BRT)

    def num(v):
        return "null" if v is None else ("%.2f" % v).rstrip("0").rstrip(".")

    corpo = ",\n".join(
        "    { d: %s, sol: %s, totvs: %s, forn: %s, prot: %s, comp: %s, valor: %s, ret: %s, venc: %s }"
        % (js(r["d"]), js(r["sol"]), js(r["totvs"]), js(r["forn"]), js(r["prot"]), js(r["comp"]),
           num(r["valor"]), js(r["ret"]), js(r["venc"]) if r["venc"] else "null") for r in regs)
    html, n = re.subn(r"((?:const|let|var)\s+ROWS\s*=\s*)\[[\s\S]*?\n\s*\];",
                      lambda m: m.group(1) + "[\n" + corpo + "\n  ];", html, count=1)
    if n != 1:
        sys.exit("Nao encontrei ROWS no index.html.")

    html, n = re.subn(r'((?:const|let|var)\s+TODAY\s*=\s*")[^"]*(")',
                      lambda m: m.group(1) + agora.strftime("%Y-%m-%d") + m.group(2), html, count=1)
    if n != 1:
        print("aviso: TODAY nao encontrado.", file=sys.stderr)

    dmin, dmax = regs[0]["d"], regs[-1]["d"]

    def ajusta_input(m):
        tag = m.group(0)
        valor = dmin if 'id="f-from"' in tag else dmax
        tag = re.sub(r'min="[^"]*"', 'min="%s"' % dmin, tag)
        tag = re.sub(r'max="[^"]*"', 'max="%s"' % dmax, tag)
        tag = re.sub(r'value="[^"]*"', 'value="%s"' % valor, tag)
        return tag

    html = re.sub(r'<input[^>]*id="f-(?:from|to)"[^>]*>', ajusta_input, html)
    html = re.sub(r'(DEFAULTS\s*=\s*\{\s*from:\s*")[^"]*(",\s*to:\s*")[^"]*("\s*\})',
                  lambda m: m.group(1) + dmin + m.group(2) + dmax + m.group(3), html, count=1)

    frase = "lidos em %s. São %d envios desde %s (%d linhas de teste ficaram de fora)." % (
        agora.strftime("%d/%m/%Y %Hh%M"), len(regs),
        datetime.strptime(dmin, "%Y-%m-%d").strftime("%d/%m/%Y"), testes)
    html, n = re.subn(r"lidos em .*?ficaram de fora\)\.", lambda m: frase, html, count=1)
    if n != 1:
        print("aviso: frase do aviso nao encontrada.", file=sys.stderr)

    if html == antes:
        print("Sem mudancas: %d envios." % len(regs))
        return
    open(INDEX, "w", encoding="utf-8").write(html)
    print("Painel atualizado: %d envios (%d testes ignorados)." % (len(regs), testes))


main()
