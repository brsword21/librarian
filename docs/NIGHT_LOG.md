# START Warsaw x Poland Tech Week Hackathon — kontekst

Stan na: 2026-10-30, ~22:15. **Wybrany track: Reactive AI — Memory Retrieval Challenge.**

## Logistyka
- Miejsce: Kolektyw3, Warszawa. Teamy 3–4 os.
- Hacking: pt 30.10 20:00 → sob 31.10 **11:00 (code freeze + deadline submisji)**
- 11:30–13:00 pitche w trackach: **3 min pitch + 2 min Q&A**, ~13–15 teamów na track
- 13:30 Grand Finale: top 3 z każdego tracku, 3 min pitch + 3 min Q&A; 14:45 nagrody; wyjście z venue do 17:00
- Linki: Luma https://luma.com/n3yb17kl · HackLeague https://app.hackleague.org/events/start-warsaw-x-poland-tech-week-hackathon?chapter=warsaw
- Partnerzy narzędziowi: OpenAI (nagroda TBC), ElevenLabs, Prelint ($250 kredytów/team). **Uwaga: w tym tracku nie wolno użyć API OpenAI/Claude w pipeline (patrz Zasady).**

## Mapa folderu
| Ścieżka | Co to |
|---|---|
| `memory-challenge/` | klon https://github.com/RxAI-dev/memory-challenge (commit `f0a317d`, nietknięty) |
| `memory-challenge/reactor/` | kit: `client.py`, `predictions.py`, `examples/run_benchmark.py`, `PARTICIPANTS.md`, `QUICKSTART.md` |
| `memory-challenge/score.py` | lokalny scorer (tylko stdlib) |
| `.venv/` | Python 3.12 + `websockets` 17.4. **Systemowy `python3` to 3.9 i nie działa z kitem: zawsze `.venv/bin/python`** |
| `data/dev`, `data/dev-large`, `data/test` | dane z release `data-v1` (archiwa w `data-download/`) |
| `reactor.sh` + `reactor.env` | wrapper na `client.py`: URL i agent id z `reactor.env`, klucz z pęku kluczy macOS |
| `materialy/` | decki partnerów (PDF + zrzuty) |

## Setup: stan
- [x] repo sklonowane, venv, `client.py --help` i przykład `predictions.py` przechodzą offline
- [x] dane pobrane i rozpakowane (dev, dev-large, test)
- [x] `score.py` działa (baseline „wszystko abstain” na dev = 5,7% correct)
- [x] hosty API odpowiadają (`*.api.reactor-hackathon.rxai.dev`)
- [ ] **dane dostępowe z platformy eventu**: base URL `https://tNN.api.reactor-hackathon.rxai.dev`, agent id `agt_...`, klucz `rxk_...`
  1. URL i agent id wpisać do `reactor.env` (nie są tajne)
  2. klucz: we własnym Terminalu `security add-generic-password -a "$USER" -s reactor-hackathon-key -w` (pyta i nie pokazuje). Nigdy do pliku, czatu ani w argumencie komendy.
  3. test: `./reactor.sh --new-history` → `{"status": "history", "history_id": ...}`

Komendy:
```sh
./reactor.sh --new-history
./reactor.sh --history <reactor_history_id> --question "..." --question-date "2023/05/30 (Tue) 08:08" \
    --evidence ev.json --question-id q_... >> results.jsonl
# baseline z kitu (naiwny keyword retrieval); pojedyncze cudzysłowy, żeby zmienne rozwinął wewnętrzny sh:
./reactor.sh --run sh -c '.venv/bin/python memory-challenge/reactor/examples/run_benchmark.py \
    --questions Q.jsonl --histories data/dev/histories.jsonl \
    --base-url "$REACTOR_BASE_URL" --agent-id "$REACTOR_AGENT_ID" --out results.jsonl'
.venv/bin/python memory-challenge/reactor/predictions.py results.jsonl --histories data/test/histories.jsonl \
    --out predictions.jsonl --abstain-on agent,no-answer
.venv/bin/python memory-challenge/score.py data/dev/gold.jsonl predictions.jsonl --details details.jsonl
```

---

## Zadanie
Rozmowy user–asystent z tygodni lub miesięcy. Na każde pytanie użytkownika trzeba: znaleźć właściwe sesje w zaszumionej historii, uzyskać odpowiedź **od Reactora**, zacytować sesje (session id) i **wstrzymać się (abstain)**, gdy historia nie zawiera odpowiedzi.

Typy pytań:
| Typ | Co testuje | Przykład |
|---|---|---|
| single-session-user | fakt podany raz przez usera | What degree did I graduate with? |
| single-session-assistant | co powiedział/polecił asystent | What ratio of tea tree oil to carrier oil should I use? |
| multi-session | łączenie faktów z kilku sesji (liczenie, sumy) | Total distance of hikes on two consecutive weekends? |
| knowledge-update | najnowsza wartość czegoś, co się zmieniło | My personal best in the charity 5K? |
| temporal-reasoning | daty, odstępy, kolejność | Days between MoMA visit and the exhibition? |

Pytania bez odpowiedzi: ~6% w dev, ~8% w test. Pytanie nie zawsze mówi, której rozmowy dotyczy. Typ pytania jest podany tylko w gold dla dev.

## Zasady (README + Discord)
- **Finalna odpowiedź musi pochodzić z Reactora**, wyprodukowana przez zgłoszony kod. Zero ręcznej edycji predykcji.
- **Lokalne modele i narzędzia są dozwolone**: embeddingi, rerankery, BM25, mały klasyfikator, filtry. Cała reszta wokół Reactora to nasz kod.
- **Zewnętrzne modele są zakazane** (Veronika N, Discord 21:51): np. przepuszczenie danych przez Claude/OpenAI API = dyskwalifikacja. Czyli generowanie słów kluczowych/odpowiedzi przez zewnętrzny LLM odpada; wolno lokalny model albo sam Reactor.
- Wolno rozmawiać z Reactorem w kilku turach (back-and-forth) przed finalną odpowiedzią.
- Wolno wgrać całą historię do pamięci Reactora i potem pytać: to jest „baseline to beat”.
- Reactor umie przeglądać publiczne strony: można wystawić własną wyszukiwarkę pod publicznym URL (bez klucza i niczego wrażliwego w URL).
- Submisja: (1) `predictions.jsonl` na wszystkie 146 pytań testowych, (2) kod: publiczne repo lub archiwum + krótki README jak uruchomić (organizatorzy mogą odpalić ponownie na kilku pytaniach), (3) prezentacja. Sposób zgłoszenia ma być ogłoszony; code freeze 11:00.

## Dane (release `data-v1`)
| Split | Pytania | Historie | Sesji/historię | Znaków/historię | Gold |
|---|---|---|---|---|---|
| `dev` | 526 (470 + 56 przeformułowań pytań SSA bez wskazówki „our previous chat”) | 470, zwykle 1 pytanie/historię | ~48 (38–62) | ~490 tys. | tak |
| `dev-large` | te same 526 | te same, ~500 sesji | ~500 | ~5 mln (plik 2,45 GB: czytać strumieniowo, linia po linii) | tak |
| `test` | **146** | **15**, po 9–10 pytań | **200** | **~1,65 mln** (~400 tys. tokenów) | nie |

- Sesja: średnio ~10 tys. znaków (dev) / ~8 tys. (test), max 78 tys.; zwykle ~12 tur.
- Format: `histories.jsonl` → `{history_id, sessions:[{session_id, date "2023/05/20 (Sat) 02:21", turns:[{turn_id, role, content}]}]}`; `questions.jsonl` → `{question_id, history_id, question, question_date}`; `gold.jsonl` → `{question_id, question_type, abstain, answer, aliases, evidence:[session_id]}`.
- Sesje są chronologicznie, żadna nie jest późniejsza niż pytanie. Ta sama sesja może mieć różne daty w różnych historiach: brać datę z bieżącej historii.
- Dev pochodzi z publicznego LongMemEval (MIT); test to nowe dane w tym samym formacie, **z celowymi near-missami**.

Dev: rozkład typów i liczba sesji-dowodów w gold
| Typ | n | abstain | sesji w evidence |
|---|---|---|---|
| multi-session | 133 | 12 | 2–5 (mediana 2, średnio 3) |
| temporal-reasoning | 133 | 6 | 1–6 (mediana 2) |
| single-session-assistant | 112 | 0 | 1 |
| knowledge-update | 78 | 6 | **zawsze 2** (stara + nowa wartość: cytować obie) |
| single-session-user | 70 | 6 | 1 |

Sesje-dowody są rozłożone po całej historii (nie skupiają się na końcu). Złote odpowiedzi są krótkie: mediana 10 znaków.

### Obserwacje z testu (ręczny przegląd 146 pytań)
- Szablony, z grubsza: fakty usera ~47 („What is my cat's name?”, „What did I end up naming…”, „What was the last X I mentioned…”), **różnice dni ~35** („How many days apart were X and Y?”, „How many days after X did I Y?”), polecenia asystenta ~25 („What was the name of that X you recommended…”), liczenie/sumy ~24 („How many books have I read since March?”, „How much in total…”), aktualizacje ~15 („…now?”, „current…”, „right now?”).
- Pytania temporalne: **daty zdarzeń są w treści jako ISO** („My son's school play is on 2023-06-10”), obok podstawionych near-missów: „My son's school concert is on 2023-06-09, but that is separate from the play”, „Your daughter's regular dentist checkup is on 2023-07-01, not the orthodontist appointment”. Odpowiedź to różnica dat, którą lepiej policzyć we własnym kodzie.
- Godzina pytania w teście to zawsze 00:00; sesje nie powtarzają się między historiami.
- Niektóre historie mają serię prawie identycznych pytań, np. 8 o wartościach elementów w „National R-77” („What X did I end up using”). Wiele sesji o tym samym urządzeniu działa jak near-miss, więc liczy się słowo „end up”, czyli ostatnia decyzja.

## Ocena
- **Answer accuracy**: sędzia LLM porównuje z gold i aliasami. **Kilka kandydatów, asekuracja lub negacja = źle.** Odpowiedź na pytanie bez odpowiedzi = źle; abstain na pytanie z odpowiedzią = źle. Lokalnie `score.py` dopasowuje znormalizowany gold/alias jako całą frazę, a resztę oznacza jako „unjudged”.
- **Evidence F1**: cytowane vs złote session id na **każdym pytaniu z odpowiedzią, także tam, gdzie się wstrzymaliśmy** (wtedy F1 = 0). Zbędne cytaty obniżają precision.
- **Abstention**: recall na pytaniach bez odpowiedzi i odsetek fałszywych abstain.
- Brak predykcji dla pytania = źle. **`predictions.py` domyślnie POMIJA** abstain agenta i pytania bez odpowiedzi (timeout itp.), więc zawsze `--abstain-on agent,no-answer` albo ponów zapytanie.
- Jury tracku: max 12 pkt (idea / harness / aplikacja, po 4 tylko „z użyciem Reactora”) + punkty z benchmarku. Jak to się sumuje, ma być ogłoszone.

## Reactor: jak działa API
- WebSocket chat per agent. **Jedna historia Reactora na historię datasetu**: `--new-history`, potem wszystkie pytania tej historii jedno po drugim. Reset tylko między historiami datasetu, bo czyści pamięć, chat i zaległe odpowiedzi.
- **Jedno pytanie naraz na agenta** (`busy` / `previous_pending` klient ponawia sam). Równoległość tylko przy wielu agentach; uruchomionych jest 11 instancji na 11 teamów, czyli najpewniej mamy 1.
- Wiadomość: pytanie + data pytania + pasaże `[E1]..[En]` (każdy z `id` = session_id i `date` = data sesji) + instrukcja cytowania. **Limit: 16 000 znaków w kliencie** (`--max-chars`), **32 000 na serwerze**. Średnia sesja ma ~10 tys. znaków, więc wysyłać fragmenty, nie całe sesje. Zostawiać tury asystenta i oznaczać `user:` / `assistant:`.
- Odpowiedź: linia `# FINAL ANSWER [ref:xxxxxxxx]: ...`; `INSUFFICIENT_EVIDENCE` → `abstained: true`. Cytaty działają tylko przez etykiety `[E#]` z `--evidence`.
- Latencja „dziesiątki sekund”, domyślny timeout 300 s (support poda zalecany). Exit codes: 0 answered/history, 2 error, 3 timeout, 4 refused, 5 closed.
- Reactor to „szybki model instrukcyjny”: arytmetykę dat i liczenie lepiej robić we własnym kodzie i podawać jako hint.
- Wgranie całej historii przez `--text` w częściach: każda część to pełna tura agenta. Historia testowa (1,65 mln znaków) to ~52 części po 32 tys., czyli przy ~20–40 s na część **~20–35 min na historię i 5–9 h na cały test**. Jako główna strategia to się nie mieści w czasie.

## Wnioski do planowania
- **Przepustowość Reactora to twarde ograniczenie.** 146 pytań × ~30–60 s ≈ 1,2–2,5 h na jeden przebieg testu na jednym agencie. Finalny przebieg trzeba zacząć najpóźniej ~07:00–07:30.
- **Retrieval stroić offline na dev**, bez Reactora: recall@k sesji względem gold `evidence` kosztuje zero czasu agenta. Reactora sprawdzać tylko na małej próbce dev.
- Test (200 sesji) jest ~4× większy od dev (48 sesji); dev-large (500 sesji) to stress test retrievalu.
- Budżet ~16 tys. znaków na pytanie to ok. 1–2% historii testowej, więc precyzja retrievalu jest tak samo ważna jak recall.
- Sprzęt: Apple M2, 16 GB RAM. Lokalne embeddingi (np. bge-small/e5-small) są OK; lokalny LLM możliwy, ale wolny (ollama niezainstalowana).

## Otwarte pytania
- [ ] Dane dostępowe (URL `tNN`, agent id, klucz): z platformy eventu
- [ ] Sposób zgłoszenia i format prezentacji (README: „announced at kickoff”)
- [ ] Jak wynik benchmarku łączy się z oceną jury
- [ ] Zalecany `--timeout` od supportu
- [ ] Skład teamu, repo na kod (publiczne do zgłoszenia)

## Reactive AI: firma (z decku, `materialy/ReactiveAI_deck.pdf`)
„The shortest path to singularity”. Budują Large Awareness Model: foundation model z pamięcią w rdzeniu (RxT → Reactor AGI → LAM), zamiast czytania całej rozmowy od nowa przy każdej wiadomości. Chwalą się prowadzeniem w benchmarku BEAM 10M i 2 miesiącami ciągłej pracy (60 000 cykli). Founderzy: Wiktor Stanisławek (CEO), Adam Filipek (CTO), Weronika Bagniewska (CSO). Nagroda tracku: fast-track rekrutacyjny do Reactive AI dla całego teamu + gift cardy. Discord: https://discord.gg/wBwC5WBhv

---

## Track 2: Bending Spoons (niewybrany)
Deck: `materialy/BendingSpoons_deck.pdf`. Bez konkretnego problem statementu w decku; kryterium „The Occam Award — Relentless simplification”: produkt, którego nie trzeba się uczyć, jedna perfekcyjna funkcja zamiast dziesięciu przeciętnych.

---

## Stan nocy (aktualizacja 02:20)
- Kod: `librarian/` (git, tagi `v1`, wkrótce `v2`). Kontrakt dla agentów: `librarian/CONTRACT.md`, research: `librarian/RESEARCH.md`, syntezy rund: `librarian/runs/SYNTHESIS_r*.md`.
- Serwer modeli: `.venv/bin/python -m core.model_server` (port 8765, jedyny proces z torchem); cache embeddingów w `librarian/cache/`.
- Reactor: slot t08, `reactor.env` uzupełniony, klucz w pęku kluczy (`reactor-hackathon-key`). Kolejka: `python -m reactorq.queue --packs ... --out ...` (wznawialna, cache odpowiedzi po hashu paczki, ponowienia).
- Zgłoszenie: `python -m reactorq.finalize --results <results.jsonl...> --split test --out submission/predictions.jsonl`.
- Pułapka kitu: `predictions.py --histories` wywraca się na `histories.jsonl` (U+2028 w tekście); używamy `cache/session_ids_<split>.jsonl`.
- Pomiary offline (S, dev / dev200): r1 80.4/79.9 → v1 86.0/84.9. Kalibracja na Reactorze (30 dev): ~62% dopasowanych + ~22% poprawnych semantycznie; F1 cytatów ~0.7; abstencje 5/5.
- Czas Reactora na teście: ~105 s/pytanie (45–110 s + ~25 s oczekiwania „busy”). Przebieg v1 wystartował 01:47.

## 04:25 atrybucja źródeł (workflow citations)
- reactorq/finalize.py = reguły zweryfikowane adwersaryjnie (runs/citations/verify_report.md): fuzzy fill-missing, ku-chain tylko gdy Reactor cytuje 1 sesję, computed-chain, containment (≥2 słowa treści) na ssu/ssa/ku/temporal; reply-rows tylko opt-in (--reply-rows), model uczony (reactorq/attribution.py) NIE podpięty (+0 na realnych odp., 1 wabik „Masa”).
- Dry run na 99 odp. testu: odpowiedzi bez zmian, usunięte 2 niepopierające sesje z ku-chain, 0 błędów formatu. Stara wersja: scratchpad/finalize_before_rules.py.
