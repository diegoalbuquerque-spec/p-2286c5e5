# Painel Envio de NF e Documentos — como publicar

Mesmo modelo do painel TOTVS: planilha → aba PAINEL → CSV publicado → GitHub Actions 3x/dia → GitHub Pages.

## 1. Planilha "Envio de NF e Documentos"

1. Crie uma aba nova chamada **PAINEL**.
2. Em **A1:I1** escreva os cabeçalhos (exatamente assim):
   `data_hora | solicitante | numero_totvs | protocolo | comprovante | valor | retorno | vencimento | fornecedor`
3. Em **A2** cole (planilha em pt-BR):

```
=SEERRO(FILTER({'Página1'!A2:A1000\'Página1'!B2:B1000\'Página1'!C2:C1000\'Página1'!D2:D1000\'Página1'!E2:E1000\'Página1'!F2:F1000\'Página1'!G2:G1000\'Página1'!I2:I1000\'Página1'!J2:J1000};'Página1'!A2:A1000<>"");"")
```

   A coluna **H (Link Documento Slack) fica de fora de propósito** — é o único dado que abriria o documento.
   Hoje a Página1 tem ~1.200 linhas: troque `1000` por `5000` para ter folga.
4. Arquivo → Compartilhar → **Publicar na Web** → escolha só a aba **PAINEL** → formato **CSV** → Publicar. Copie a URL.

## 2. GitHub

1. Crie um repositório novo com nome neutro, sem "NF" nem "Shippify" — sugestão: `p-2286c5e5`.
2. **Add file → Upload files** e arraste o conteúdo desta pasta (inclusive a pasta `.github`).
   Se o navegador não mostrar a pasta `.github` (arquivo oculto), crie o arquivo à mão em
   `.github/workflows/atualizar-painel.yml` e cole o conteúdo.
3. Settings → Secrets and variables → Actions → **New repository secret**: `SHEET_CSV_URL` = URL do passo 1.4.
4. Settings → Pages → Source: **Deploy from a branch** → `main` / `(root)`.
5. Actions → Atualizar painel → **Run workflow** para a primeira carga.

Endereço final: `https://diegoalbuquerque-spec.github.io/p-2286c5e5/`

## O que deixa ele escondido (e o que não deixa)

- `noindex, nofollow, noarchive` na página: Google e afins não indexam.
- `referrer: no-referrer`: quem clicar num link saindo do painel não revela o endereço.
- Nome de repositório neutro e nenhum link a partir do painel TOTVS.
- **Limite honesto:** o repositório é público. Quem abrir o seu perfil no GitHub vê o repositório e consegue ler os valores no código. Para fechar de verdade, a saída é senha nos dados (posso fazer depois sem mudar o visual).

## Regras de dados do script

- Data em português ("1º de jul., 2026 15h26") ou dd/mm/aaaa vira data.
- Valor aceita "R$ 1.256,00", "R$1.205,00", "200.00", "R$ 130"; texto sem número vira vazio.
- Retorno: contém "incorreto" → Incorreto; "correto" → Correto; vazio → Sem retorno.
- Linhas com "test" no Nº TOTVS ou no Valor são ignoradas.
- `DATA_INICIAL` (padrão 2026-06-01) corta registros antigos.
- CSV vazio ou sem as colunas → o workflow falha **sem** sobrescrever o painel.
