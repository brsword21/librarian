# Onboarding: Bibliotekarz (Librarian)

Track **Reactive AI: Memory Retrieval Challenge**, START Warsaw x Poland Tech Week Hackathon (team „Ptysie”, slot t08).
Ten plik ma cię wdrożyć w 10 minut. Szczegóły nocy są w `docs/NIGHT_LOG.md`.

## 1. Co budujemy

Asystent AI rozmawia z użytkownikiem miesiącami (200 sesji, ~1,6 mln znaków). Potem pada pytanie, np. „jak ma na imię mój pies?”. Trzeba zrobić trzy rzeczy:
- znaleźć sesje, w których jest odpowiedź;
- dać je **Reactorowi**, czyli modelowi organizatorów (to on musi udzielić odpowiedzi);
- zacytować sesje (session id) albo uczciwie odpowiedzieć „nie wiem” (abstain), gdy odpowiedzi w historii nie ma.

Nasz system to **wyszukiwarka, która zgaduje typ pytania**. Pytanie przechodzi przez taki pipeline:

```
pytanie ──► router (5 typów) ──► soczewka typu ──► paczka dowodów ──► Reactor ──► finalize ──► predictions.jsonl
           core/router.py      lenses/<typ>/    (5–8 fragmentów    (jedyne     (dobór        (format kitu)
           + hand-offy         wyszukiwanie      z datami + notki  źródło      źródeł,
           lenses/pipeline.py  BM25+dense+rerank  kodu: daty, dni)  odpowiedzi) reactorq/finalize.py)
```

Typy pytań i nasze skróty:
- `ssu`: fakt usera;
- `ssa`: co polecił asystent;
- `multi`: liczenie po wielu sesjach;
- `ku`: wartość, która się zmieniła;
- `temporal`: daty i odstępy.

Pitch w jednym zdaniu: **pamięć dla asystentów AI, która wie, czego nie wie**. Reactor czyta ~0,1–0,4% archiwum, a mimo to odpowiada i cytuje źródła.

## 2. Zasady, za które jest dyskwalifikacja (przeczytaj)

- **Finalną odpowiedź daje tylko Reactor.** Nie wolno użyć zewnętrznych modeli (Claude/OpenAI API) w pipeline. Lokalne modele i narzędzia są OK: mamy bge-small, MiniLM cross-encoder i reguły.
- **Nie edytujemy predykcji ręcznie.** Wolno dobierać źródła kodem, ale każde źródło musi popierać odpowiedź Reactora (Kosti na Discordzie).
- **Jedna historia Reactora na jedną historię datasetu, bez resetów** między pytaniami tej samej historii. Ponowienia idą w tej samej historii (`reactorq.queue --reuse-history`).
- **Klucz Reactora (`rxk_…`) nigdy nie trafia do repo, czatu, pliku ani linii poleceń.** Jest w pęku kluczy na Macu Mikołaja.
- **Reactor jest jeden i wolny** (~105 s na pytanie). Pytać może tylko jeden proces naraz. Nie odpalaj niczego, co go woła, bez uzgodnienia z Mikołajem.
- Wyniki symulatora (lokalny LLM, `PROXY.md`) nigdy nie idą do zgłoszenia. `finalize` je odrzuca.

## 3. Stan (31.10, ~07:00)

| Co | Stan |
|---|---|
| Test (146 pytań) na Reactorze | 143 odpowiedzi + 7 ponowień (pytania, których paczka zmieniła się w v3). 3 pytania padły na zerwanym DNS ~06:30 i są ponawiane automatycznie (`runs/final/after_err.sh`). Potem skrypt sam składa `submission/predictions.jsonl` i odświeża `demo/replay.json`. |
| System | v3 (`configs/best.json`, tag `v3`) |
| Offline S, routed, dev / dev200 | kit naive 42,9 → generic hybrid 73,4 → R1 80,4/79,9 → v1 86,0/84,9 → v2 86,9/87,0 → **v3 87,1/87,0** |
| v3 per typ (dev) | ssu 93,4 · ssa 93,6 · multi 87,8 · ku 93,4 · temporal 81,3 |
| Kalibracja Reactora (30 pytań dev) | 20 zgodnych, 6 poprawnych sensem, 4 błędne (2 przez zerwane połączenie). Wszystkie 5 abstencji trafione. Citation F1 0,69 (0,85, gdy odpowiedział). |
| Dobór źródeł | reguły zweryfikowane adwersaryjnie (`runs/citations/verify_report.md`); model uczony odrzucony |
| Frontend | `demo/web`: wersja „library”, port 8800. `demo/web_library`: osobny frontend, port 8804. Warianty z nocnego konkursu: `web_arcane` (zwycięzca sędziego, 52/60), `web_manuscript`, `web_pixel`. |

Metryka offline, którą optymalizujemy:

`S = 100 · mean(0,65·PA + 0,30·CF1 − 0,05·chars/16000)`

- **PA:** paczka pozwala odpowiedzieć.
- **CF1:** F1 cytowań.
- **chars:** długość paczki.

Wszystkie przebiegi są w `runs/leaderboard.csv`. Nowy wariant przyjmujemy przy ≥ +2 pkt na dev i bez straty na dev200.

## 4. Harmonogram do końca

| Kiedy | Co |
|---|---|
| teraz – 09:00 | pitch (3 min + 2 min Q&A), demo, ewentualne poprawki systemu |
| ~07:15 | Reactor wolny: można sprawdzić pytanie na żywo w demie (`/api/ask`) |
| 09:00 – 10:15 | publiczne repo do zgłoszenia (README/SOLUTION.md), walidacja 146 predykcji, formularz |
| **11:00** | **code freeze + deadline zgłoszenia** |
| 11:30 | pitch w tracku; 13:30 finał (top 3) |

Otwarte zadania (wpisz się):
- [ ] **Pitch:** historia w 3 min, use case biznesowy, liczby z tabeli wyżej, demo na 5 przystankach. Właściciel: …
- [ ] **Q&A:** dlaczego bez zewnętrznych LLM, jak dobieramy źródła, gdzie system przegrywa (temporal 81, odmowy Reactora). Właściciel: …
- [ ] **SOLUTION.md / README dla jury:** harness + benchmark to 4 z 12 pkt oceny. Właściciel: …
- [ ] **Demo:** test `/api/ask` na żywo po zwolnieniu Reactora, próba generalna na projektorze. Właściciel: …
- [ ] **Walidacja zgłoszenia:** 146 linii, `score.validate` bez błędów, 0 odpowiedzi bez źródeł. Właściciel: Mikołaj
- [ ] (opcjonalnie) **poprawki systemu.** Każda zmiana paczek wymaga ponownego pytania Reactora (~105 s na pytanie), więc najpierw offline S na dev i dev200, potem tylko pytania, których paczka się zmieniła.

## 5. Setup: trzy poziomy

### Poziom 0: samo demo (2 min, bez danych)
```sh
git clone https://github.com/brsword21/librarian.git && cd librarian
python3 -m demo.server --web demo/web --port 8800      # → http://127.0.0.1:8800
```
Odtwarza nagrane odpowiedzi z `demo/replay.json`. Live (`/api/pack`, `/api/ask`) wymaga poziomu 1–2.
Sterowanie: Spacja (trasa), ←/→, F (pełny ekran), Q (pytania), H (jak to działa).

### Poziom 1: kod, harness, sweepy (~15 min + AirDrop)
Potrzebne: macOS/Linux, [`uv`](https://docs.astral.sh/uv/), `gh` (zalogowany).
```sh
mkdir hackathon && cd hackathon
git clone https://github.com/brsword21/librarian.git
sh librarian/tools/setup.sh          # kit organizatorów obok repo (przypięty commit), dane data-v1, venv
```
Z Maca Mikołaja weź **team cache** (~1,6 GB przez AirDrop; tworzy go `sh librarian/tools/pack_team_cache.sh`). Rozpakuj w `hackathon/`: `tar -xf librarian_team_cache.tar`. Bez cache każdy sweep liczy embeddingi od zera, czyli godziny.

```sh
cd librarian
.venv/bin/python -m core.model_server &                 # embeddingi + reranker na :8765 (jedyny proces z torchem)
.venv/bin/python -m harness.sweep --lens lenses/pipeline.py --split dev --tag moj_test   # cały system, S per typ
.venv/bin/python -m harness.sweep --lens lenses/temporal/a_r3_gap.py --variants span_own --split dev200 --type temporal
.venv/bin/python -m harness.failures runs/moj_test/<typ>/<lens>/<wariant>/dev --n 20   # 20 najgorszych pytań: czego zabrakło
```
Bez team cache:
- `python -m core.data shard dev test`;
- `WITH_DEV_LARGE=1 sh tools/setup.sh` + `python -m core.data dev200` (dev-large to 2,3 GB);
- `python -m core.gold_turns` (wymaga `data/lme/longmemeval_oracle.json` z HF `xiaowu0162/longmemeval-cleaned`);
- `python -m core.precompute dev dev200 test` (długo).

### Poziom 2: Reactor (tylko jedna osoba, uzgodnij)
1. `tools/reactor.env.example` skopiuj do katalogu nad repo jako `reactor.env`, a `tools/reactor.sh` jako `reactor.sh`.
2. Obok utwórz `.venv` z `websockets` (`uv venv .venv && uv pip install --python .venv/bin/python "websockets>=14"`).
3. Klucz wpisz we własnym Terminalu: `security add-generic-password -a "$USER" -s reactor-hackathon-key -w`.

Potem:
```sh
.venv/bin/python -m reactorq.build_packs --config configs/best.json --split test --out runs/final/x_packs.jsonl --qids q1,q2
.venv/bin/python -m reactorq.queue --packs runs/final/x_packs.jsonl --out runs/final/x_results.jsonl --timeout 600 \
    --reuse-history runs/final/v1_results.jsonl
.venv/bin/python -m reactorq.finalize --results runs/final/v1_results.jsonl runs/final/v3_reask_results.jsonl \
    runs/final/v3_err_reask_results.jsonl runs/final/x_results.jsonl \
    --packs runs/final/v3_test_packs.jsonl runs/final/v2_test_packs.jsonl runs/final/v1_test_packs.jsonl \
    --split test --out submission/predictions.jsonl
```

## 6. Mapa repo

| Ścieżka | Co |
|---|---|
| `core/` | dane, jednostki tekstu, indeks (BM25 + dense + RRF + rerank), daty, router, pakowanie, model_server, cache |
| `lenses/` | soczewki: `generic.py` (bazowa), `pipeline.py` (cały system), `<typ>/a_*` (struktura) i `b_*` (semantyka), `merged_r*` (scalone). `scratch_*`: robocze pliki agentów. |
| `harness/` | `sweep` (leaderboard), `metrics` (S, PA, CF1), `failures`, `audit` (test bez gold), `make_samples` |
| `reactorq/` | `build_packs`, `queue` (wznawialna, cache po hashu paczki), `finalize` (format kitu + dobór źródeł), `calibrate`, `proxy_*` (symulator) |
| `configs/` | `best.json` (= v3), `best_v1/v2/r1.json`, `exp/` |
| `demo/` | `server.py` (:8800; `/replay.json`, `/api/status`, `/api/pack`, `/api/ask`), `export_replay.py`, frontendy |
| `runs/` | `leaderboard.csv`, `SYNTHESIS_r1..r4.md` (raporty scalacza z rund agentów), `final/` (paczki i odpowiedzi testu), `reactor/` (kalibracja E1/E1b), `citations/` (raporty doboru źródeł), `proxy/` (symulator) |
| `CONTRACT.md` | kontrakt soczewki: `Lens.build(q, history_index, params) -> EvidencePack` |
| `RESEARCH.md` | research z rundy 0 (co działa na LongMemEval) |
| `docs/NIGHT_LOG.md` | pełny kontekst eventu, zasady, dane, dziennik nocy |

Tagi: `v1`, `v2`, `v3` to wersje, na których szły przebiegi testu.

## 7. Jak pracować z Claude Code w tym repo
`CLAUDE.md` ma zasady dla agentów: zakaz Reactora i zewnętrznych API, edycja tylko własnych plików, liczenie przez harness. Odpal `claude` w `librarian/`, a sam je wczyta.
