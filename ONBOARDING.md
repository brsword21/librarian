# Onboarding: Bibliotekarz (Librarian)

Track **Reactive AI: Memory Retrieval Challenge**, START Warsaw x Poland Tech Week Hackathon (team „Ptysie”, slot t08).
Ten plik ma cię wdrożyć w 10 minut. Pełny kontekst eventu i dziennik nocy są w `docs/NIGHT_LOG.md`.

## 1. Co budujemy

Asystent AI rozmawia z użytkownikiem miesiącami (200 sesji, ~1,6 mln znaków). Potem pada pytanie, np. „jak ma na imię mój pies?”. Trzeba zrobić trzy rzeczy:
1. znaleźć sesje, w których jest odpowiedź;
2. dać je **Reactorowi**, czyli modelowi organizatorów (to on musi udzielić odpowiedzi);
3. zacytować sesje (session id) albo uczciwie odpowiedzieć „nie wiem” (abstain), gdy odpowiedzi w historii nie ma.

Nasz system to **wyszukiwarka, która zgaduje typ pytania**:

```
pytanie ──► router (5 typów) ──► soczewka typu ──► paczka dowodów ──► Reactor ──► finalize ──► predictions.jsonl
           core/router.py      lenses/<typ>/    (średnio ~3 sesje,  (jedyne     (dobór        (format kitu)
           + hand-offy         BM25+dense+rerank 1–9, z datami      źródło      źródeł,
           lenses/pipeline.py                    + notki kodu)      odpowiedzi) reactorq/finalize.py)
```

Notki kodu to np. daty i wyliczona liczba dni.

Typy pytań i ich skróty:
- `ssu`: fakt usera;
- `ssa`: co polecił asystent;
- `multi`: liczenie po wielu sesjach;
- `ku`: wartość, która się zmieniła;
- `temporal`: daty i odstępy.

Pitch w jednym zdaniu: **pamięć dla asystentów AI, która wie, czego nie wie**. Reactor czyta ~0,1–0,4% archiwum, a mimo to odpowiada i cytuje źródła.

## 2. Zasady, za które jest dyskwalifikacja (przeczytaj)

- **Finalną odpowiedź daje tylko Reactor.** Nie wolno użyć zewnętrznych modeli (Claude/OpenAI API) w pipeline. Lokalne modele i narzędzia są OK: mamy bge-small, MiniLM cross-encoder i reguły.
- **Nie edytujemy predykcji ręcznie.** Wolno dobierać źródła kodem, ale każde dodane źródło musi popierać odpowiedź Reactora. Tak napisał organizator na Discordzie.
- **Jedna historia Reactora na jedną historię datasetu, bez resetów** między pytaniami tej samej historii. Ponowienia idą w tej samej historii (`reactorq.queue --reuse-history`). Jeśli serwer jej nie przyjmie (`history_changed`), kolejka otwiera nową.
- **Klucz Reactora (`rxk_…`) nigdy nie trafia do repo, czatu, pliku ani linii poleceń.** Jest w pęku kluczy na Macu Mikołaja.
- **Reactor jest jeden i wolny** (~105 s na pytanie). Pytać może tylko jeden proces naraz. Nie odpalaj niczego, co go woła, bez uzgodnienia z Mikołajem.
- Wyniki symulatora (lokalny LLM, `PROXY.md`) nigdy nie idą do zgłoszenia. `finalize` je odrzuca.

## 3. Stan (31.10, 07:10)

| Co | Stan |
|---|---|
| Test (146 pytań) na Reactorze | **gotowe: 146/146 odpowiedzi Reactora**, 13 abstencji, 0 błędów formatu, 0 odpowiedzi bez źródeł → `submission/predictions.jsonl`. W tym 7 ponowień v3 i 3 ponowienia po zerwanym DNS (~06:30). `demo/replay.json` odświeżony. |
| System | v3 (`configs/best.json`, tag `v3`) |
| Offline S, dev / dev200 | naiwny baseline kitu 42,9 → generic hybrid 73,4 (próbka 80 pytań) → R1 80,4/79,9 → v1 86,0/84,9 → v2 86,9/87,0 → **v3 87,1/87,0** |
| v3 per typ (dev, z routerem) | ssu 87,4 · ssa 93,0 · multi 85,8 · ku 91,5 · temporal 80,3. Sama soczewka na pytaniach swojego typu: 93,4 · 93,6 · 87,8 · 93,4 · 81,3; różnica to błędy routera. |
| Kalibracja Reactora (30 pytań dev, `runs/reactor/e1`+`e1b`) | 20 zgodnych ze scorerem (w tym 5 abstencji), 6 poprawnych sensem, 4 błędne (2 fałszywe abstencje, 2 zerwane połączenia). Citation F1 na e1b (16 pytań z odpowiedzią): 0,69 z samych cytatów Reactora (0,85, gdy odpowiedział), z obecnymi regułami finalize 0,73 (0,90). |
| Dobór źródeł | reguły zweryfikowane adwersaryjnie (`runs/citations/verify_report.md`); model uczony odrzucony |
| Frontend | `demo/web`: wersja „library”, port 8800. `demo/web_library`: osobny frontend, port 8804. Warianty z nocnego konkursu: `web_arcane` (wygrał w ocenie agenta-sędziego), `web_manuscript`, `web_pixel`. Każdy odpalisz: `python3 -m demo.server --web demo/<folder> --port 88xx`. |

Metryka offline, którą optymalizujemy:

`S = 100 · mean(0,65·PA + 0,30·CF1 − 0,05·chars/16000)`

- **PA:** paczka pozwala odpowiedzieć.
- **CF1:** F1 cytowań.
- **chars:** długość paczki.

Wszystkie przebiegi są w `runs/leaderboard.csv`. Wariant przyjmujemy przy ≥ +2 pkt na dev i bez straty na dev200.

## 4. Harmonogram do końca

| Kiedy | Co |
|---|---|
| teraz – 09:00 | pitch (3 min + 2 min Q&A), demo, ewentualne poprawki systemu |
| już | Reactor wolny: pytanie na żywo w demie (`/api/ask`), jedna osoba naraz |
| 09:00 – 10:30 | publiczny snapshot repo do zgłoszenia (niżej), walidacja 146 predykcji, formularz |
| **11:00** | **code freeze + deadline zgłoszenia** |
| 11:30 | pitch w tracku; 13:30 finał (top 3) |

Ocena jury tracku: 12 pkt, po 4 za ideę, harness i aplikację, liczone tylko „z użyciem Reactora”. Do tego osobno punkty z benchmarku.

Otwarte zadania (wpisz się):
- [ ] **Pitch:** historia na 3 min, use case biznesowy, liczby z tabeli wyżej, demo na 5 przystankach. Właściciel: …
- [ ] **Q&A:** dlaczego bez zewnętrznych LLM, jak dobieramy źródła, gdzie system przegrywa (temporal 80, multi 86, router, odmowy Reactora). Właściciel: …
- [ ] **SOLUTION.md / README dla jury:** harness, benchmark, decyzje. Właściciel: …
- [ ] **Demo:** test `/api/ask` na żywo, próba generalna na projektorze. Właściciel: …
- [ ] **Zgłoszenie:** walidacja, potem publiczny snapshot. Właściciel: Mikołaj
  - Tego repo **nie upubliczniamy**: historia ma prywatne notatki i maile.
  - Przy zgłoszeniu (~10:45) z HEAD powstaje czyste repo `brsword21/librarian-submission`: jeden commit, bez `docs/NIGHT_LOG.md` i bez scratchy.
  - Wcześniej nie, bo inne teamy zobaczyłyby nasze odpowiedzi.
- [ ] (opcjonalnie) **poprawki systemu:** każda zmiana paczek wymaga ponownego pytania Reactora (~105 s na pytanie). Najpierw offline S na dev i dev200, potem pytamy tylko o pytania, których paczka się zmieniła (`harness.audit --diff OLD NEW`).

## 5. Setup: trzy poziomy

Repo jest prywatne. Mikołaj zaprasza cię jako collaboratora: podaj login GitHub. Zaakceptuj zaproszenie (mail albo github.com/notifications), a potem klonuj przez `gh repo clone brsword21/librarian` albo `git clone` po `gh auth login`. Jeśli zamierzasz dojść do poziomu 1, od razu klonuj do osobnego folderu `hackathon/`.

### Poziom 0: samo demo (2 min, bez danych i bibliotek)
```sh
mkdir hackathon && cd hackathon && gh repo clone brsword21/librarian && cd librarian
python3 -m demo.server --web demo/web --port 8800      # → http://127.0.0.1:8800
```
Odtwarza nagrane odpowiedzi z `demo/replay.json`. Live (`/api/pack`, `/api/ask`) wymaga poziomu 1–2.

Sterowanie: Spacja (trasa), ←/→, F (pełny ekran), Q (pytania), H (jak to działa).

### Poziom 1: kod, harness, sweepy (~2 min + pobranie ~100 MB)
Potrzebne: macOS/Linux, [`uv`](https://docs.astral.sh/uv/), git, curl.
```sh
cd hackathon && sh librarian/tools/setup.sh
```
Skrypt robi wszystko naraz:
- kit organizatorów obok repo (przypięty commit);
- dane dev i test;
- plik oracle LongMemEval;
- venv;
- pocięte historie;
- tury z odpowiedziami.

Potem z `librarian/`:
```sh
.venv/bin/python -m core.model_server          # w OSOBNEJ karcie terminala; 1. start pobiera 2 modele z HF (~150 MB)
.venv/bin/python -m harness.sweep --lens lenses/pipeline.py --variants routed --split dev --type temporal --tag moj_test
.venv/bin/python -m harness.failures runs/moj_test/temporal/pipeline/routed/dev --n 20   # najgorsze pytania: czego zabrakło
```
- `--variants routed` to cały system v3. Bez `--variants` sweep puszcza wszystkie 10 wariantów pipeline'u.
- `--type X` ogranicza sweep do jednego typu. `--limit N` bierze pierwsze N pytań z pliku.

**Team cache, czyli pełna prędkość i dev200.** Na Macu Mikołaja leży `librarian_team_cache.tar` (1,6 GB). Zawiera embeddingi, dev200 i pocięte historie, a dostajesz go AirDropem. Rozpakuj w `hackathon/` (folder repo musi się nazywać `librarian`):
```sh
cd hackathon && tar -xf ~/Downloads/librarian_team_cache.tar
```
Bez cache:
- małe sweepy (`--type`, `--limit 20`) działają od razu, ~5 s na historię przy pierwszym liczeniu embeddingów;
- cały dev to ~35–40 min;
- dev200 wymaga `WITH_DEV_LARGE=1 sh tools/setup.sh`, a potem `.venv/bin/python -m core.data dev200` (dev-large to 0,74 GB do pobrania, 2,3 GB po rozpakowaniu).

**Git:**
- Każdy sweep dopisuje wiersz do śledzonego `runs/leaderboard.csv`. Przed `git pull` commituj swoje wiersze; jeśli to tylko próby, zrób `git checkout runs/leaderboard.csv`. Przy konflikcie zostaw wiersze obu stron.
- Pracuj na gałęzi `imie/temat` i rób PR do `main`.
- Wyniki per pytanie (`runs/<tag>/…`) są w .gitignore.

### Poziom 2: Reactor (tylko jedna osoba, uzgodnij z Mikołajem)
```sh
cd hackathon     # katalog NAD repo
cp librarian/tools/reactor.env.example reactor.env && cp librarian/tools/reactor.sh reactor.sh
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python "websockets>=14"   # venv klienta Reactora
security add-generic-password -a "$USER" -s reactor-hackathon-key -w     # wkleja się klucz, nie widać go
cd librarian
SUFFIX="Write the final answer line as: only the answer itself (a name, number, date or short phrase), followed by the [E#] label(s) of the passage(s) that state it. No explanation, no alternatives."
.venv/bin/python -m reactorq.build_packs --config configs/best.json --split test --suffix "$SUFFIX" \
    --out runs/final/x_packs.jsonl --qids q1,q2
.venv/bin/python -m reactorq.queue --packs runs/final/x_packs.jsonl --out runs/final/x_results.jsonl --timeout 600 \
    --reuse-history runs/final/v1_results.jsonl
.venv/bin/python -m reactorq.finalize --results runs/final/v1_results.jsonl runs/final/v3_reask_results.jsonl \
    runs/final/v3_err_reask_results.jsonl runs/final/x_results.jsonl \
    --packs runs/final/x_packs.jsonl runs/final/v3_test_packs.jsonl runs/final/v2_test_packs.jsonl runs/final/v1_test_packs.jsonl \
    --split test --out submission/predictions.jsonl
```
Uwagi:
- Sufiks musi być dokładnie ten sam: wszystkie zgłoszone paczki go mają.
- Bez plików `x_*` ostatnia komenda odtwarza zgłoszenie bajt w bajt.

## 6. Mapa repo

| Ścieżka | Co |
|---|---|
| `core/` | dane, jednostki tekstu, indeks (BM25 + dense + RRF + rerank), daty, router, pakowanie, model_server, cache |
| `lenses/` | soczewki: `generic.py` (bazowa), `pipeline.py` (cały system), `<typ>/a_*` (struktura) i `b_*` (semantyka), `merged_r*` (scalone). `scratch_*`: robocze pliki agentów. |
| `harness/` | `sweep` (leaderboard), `metrics` (S, PA, CF1), `failures`, `audit` (test bez gold; `--diff OLD NEW` porównuje paczki), `make_samples` |
| `reactorq/` | `build_packs`, `queue` (wznawialna, cache po hashu paczki), `finalize` (format kitu + dobór źródeł), `calibrate`, `proxy_*` (symulator) |
| `configs/` | `best.json` (= v3), `best_v1/v2/r1.json`, `exp/` |
| `demo/` | `server.py` (`/replay.json`, `/api/status`, `/api/pack`, `/api/ask`), `export_replay.py`, frontendy |
| `runs/` | `leaderboard.csv`, `SYNTHESIS_r1..r4.md` (raporty scalacza z rund agentów), `final/` (paczki i odpowiedzi testu), `reactor/` (kalibracja E1/E1b), `citations/` (raporty doboru źródeł), `proxy/` (symulator) |
| `tools/` | `setup.sh`, `pack_team_cache.sh`, `reactor.sh` + `reactor.env.example` |
| `CONTRACT.md` | kontrakt soczewki: plik .py z `VARIANTS = {nazwa: kwargs}` i `build(q, hx, **params) -> EvidencePack` |
| `RESEARCH.md` | research z rundy 0 (co działa na LongMemEval) |
| `docs/NIGHT_LOG.md` | kontekst eventu, zasady, dane, dziennik nocy (prywatne, nie idzie do zgłoszenia) |

Tagi: `v1`, `v2`, `v3` to wersje, na których szły przebiegi testu.

## 7. Claude Code w tym repo
`CLAUDE.md` ma zasady dla agentów: zakaz Reactora i zewnętrznych API, edycja tylko własnych plików, liczenie przez harness. Odpal `claude` w `librarian/`, a sam je wczyta.
