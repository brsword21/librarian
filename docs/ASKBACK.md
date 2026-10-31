# Ask-back: Reactor przeszukuje pamięć usera sam

**Idea (do pitchu):** dziś Reactor dostaje jedną paczkę i albo odpowiada, albo mówi „nie wiem”. W ask-back dostaje
też prywatny link do archiwum tego jednego usera (nasz indeks: BM25 + bge + cross-encoder) i **zanim powie „nie wiem”,
sam dopytuje pamięć** 1–3 zapytaniami. Potem, w tej samej historii Reactora (pamięta rundę 1), dostaje paczkę +
wszystko, co sam znalazł, jako `[E#]`, więc cytuje prawdziwe sesje. Reactor przestaje być czytnikiem na końcu
pipeline'u, a zaczyna współpracować z naszą wyszukiwarką („Reactor as a collaborative tool”, case brief).

To nie jest szukanie w internecie: „przeglądarka” Reactora to jedyny sposób, żeby wywołał nasze narzędzie. Link
działa tylko dla jednej historii (losowy token per pytanie), a każde zapytanie jest logowane.

**Liczby (offline, dev, bez Reactora):** v3 gubi złotą sesję w 16 z 496 pytań z odpowiedzią. Dwa proste zapytania
słów kluczowych (zastępstwo zapytań Reactora) odzyskują brakujący dowód w **11 z 16** (13 z 21 sesji):
multi 5/6, temporal 5/9, ku 1/1. Przykład: „What new kitchen gadget did I invest in before getting the Air Fryer?” →
sesja z Instant Pot (nasz otwarty problem „kategoria → konkret”). Na 13 abstencjach testu wyszukiwarka zwykle
pokazuje celowe wabiki (running group: „Stumptown Joggers” — user nie dołączył; „Forest Park Flyers” — grupa
sąsiada), czyli te abstencje są najpewniej trafne: ask-back to też **weryfikacja „nie wiem”**.

## Uruchomienie (Mac z kluczem Reactora)

```sh
cd librarian
.venv/bin/python -m core.model_server &                                  # jeśli nie działa
.venv/bin/python -m demo.server --web demo/web_min --port 8800 &          # demo + /m/<token>/search
sh tools/tunnel.sh 8800                                                  # wypisze https://xxxx.trycloudflare.com
```
Sprawdź w przeglądarce `https://xxxx.trycloudflare.com/` (pierwsze sekundy DNS może nie działać lokalnie).

1. **Smoke test (1 pytanie, ~1–2 min):** czy Reactor w ogóle otwiera link?
   ```sh
   .venv/bin/python -m reactorq.askback --smoke --public-url https://xxxx.trycloudflare.com
   ```
   `OK: Reactor reads our memory links.` → idziemy dalej. `NO REQUEST` → Reactor nie przegląda; zostaje demo w
   trybie „dry run” + liczby offline powyżej.
2. **Dev (prawdziwa liczba z Reactorem, ~2 pytania Reactora na qid):** pytania, gdzie dowód odzyskano offline:
   ```sh
   .venv/bin/python -m reactorq.askback --public-url https://xxxx.trycloudflare.com \
     --qids q_3dc608395f82,q_b7049267f6d0,q_1525ff1b6137,q_2aadd3ab0197,q_558b8a20cdc1
   ```
   Porównaj odpowiedzi z gold (`data/dev/gold.jsonl`).
3. **13 abstencji testu (demo + decyzja):** `--qids` pominięte = abstencje z `submission/predictions.jsonl`.
   ```sh
   .venv/bin/python -m reactorq.askback --public-url https://xxxx.trycloudflare.com
   ```
   ~13 × 2 × ~100 s ≈ 40 min. Wyniki: `demo/askback.json` (demo pokazuje „live Reactor”) i
   `runs/askback/results.jsonl` (format zgodny z `reactorq.finalize`).

`--dry-run` robi to samo bez Reactora (symulowane zapytania przez prawdziwy link i serwer) — tak powstało obecne
`demo/askback.json` (oznaczone w demie jako „dry run, no Reactor”).

## Zgłoszenie: domyślnie BEZ zmian

W teście ~8% pytań nie ma odpowiedzi (~12 z 146), a mamy 13 abstencji: większość jest pewnie trafna. Zamiana trafnej
abstencji na odpowiedź kosztuje tyle samo, ile zysk z naprawy. Podmieniaj predykcję tylko gdy: Reactor w rundzie 2
odpowiedział, zacytował sesję, a ta sesja zawiera odpowiedź (reguła containment z `finalize`). Nigdy ręcznie.

## Pliki
- `reactorq/memory.py` — wyszukiwanie w jednej historii, tokeny, log zapytań (`runs/askback/`, poza gitem)
- `demo/server.py` — `GET /m/<token>/search?q=` (tekst), `GET /askback.json`
- `reactorq/askback.py` — runda 1 / runda 2, `--smoke`, `--dry-run`
- `tools/tunnel.sh` — Cloudflare quick tunnel (bez konta)
- `demo/web_min/` — nowe, minimalne demo (halftone): sekcja „Reactor asked back”
