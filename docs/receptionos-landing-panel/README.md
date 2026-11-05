# receptionOS: test nowego landingu na symulowanym panelu klientów

Test z 5 listopada 2026 r. Sprawdzaliśmy, jak nowy landing
(<https://receptionos-new-landing.mikolajstawicki22.workers.dev/k6/>) odbiorą właściciele i menedżerowie
klinik stomatologicznych.

Narzędzie: skill `founder-consumer` z [Jakeschincariol/founder-skill](https://github.com/Jakeschincariol/founder-skill).
Panel liczył 20 kupujących. Każdy był osobnym subagentem Claude z własną kartą: segment, dochód, sposób kupowania,
codzienny nawyk i główna obiekcja. Wszyscy zobaczyli ten sam skrót landingu ([pitch.md](pitch.md)) i zdecydowali,
czy umówiliby bezpłatny audyt, bo właśnie o to prosi strona. Karty rozdał deterministyczny skrypt (seed 7),
a wyniki policzył skrypt `panel.py`. Nikt nie odpowiadał za kupujących.

> To są symulowani kupujący, nie klienci. Dobrze wyłapują obiekcje, segmenty i sformułowania, ale nie przewidują
> konwersji. Modele językowe są skłonne się zgadzać, więc 30% traktuj jako górną granicę. Grupy są małe
> (2–7 osób), więc procenty w podziałach to tylko kierunek. Profil klienta ([customer.json](customer.json)) to
> założenia, nie dane z rozmów z klientami. Cytaty to materiał badawczy, nie opinie klientów.

## Wynik

**6 umawia audyt · 14 nie (30%)**

### Kto umawia audyt, a kto nie

- **Decydują postawy, nie wielkość kliniki.** Grupy „nastawiony na wzrost” (4 z 4) i „wczesny użytkownik” (2 z 2)
  umawiają wszyscy. W pozostałych pięciu grupach (sceptyk technologii, liczy każdą złotówkę, gasi pożary, lojalny
  wobec obecnych dostawców, pyta kolegów po fachu) nikt.
- **Kupujący mają jeden wspólny powód:** płacą za reklamy implantów i ortodoncji i chcą wiedzieć, ile leadów ginie
  przy telefonie. Ten argument działa, ale landing mówi o nim tylko pośrednio.
- **Średnie kliniki (3–6 foteli): umawia 1 osoba z 7.** To najsłabszy wynik, a właśnie te kliniki mają recepcjonistki
  i ten problem.

### Dlaczego odpadają

1. **Zaufanie (6 osób).** Nie znają nikogo, kto tego używa, a audyt oznacza obcych udających pacjentów, którzy
   oceniają ich zespół. Bezpłatny audyt, czyli główne wezwanie do działania, dla wielu jest barierą, nie zachętą.
2. **Brak ceny (3 osoby jako główny powód, wspomina prawie każdy).** Darmowy audyt odbierają jako wstęp do rozmowy
   z handlowcem.
3. **Przyzwyczajenie i system gabinetowy (3 + 1).** Mają już centralę albo firmę od telefonów, a przy Estomedzie
   AI tylko zostawia notatki. Z pięciu osób na Estomedzie odmówiły cztery. Piąta (P002) umawia audyt, ale sama mówi,
   że brak zapisu wizyt w Estomedzie pewnie powstrzyma ją przed zakupem abonamentu.

Inne wątki, które wracają:

- **„top 1% klinik”** odstrasza małe gabinety („to dla dużych sieci, nie dla mnie”).
- **RODO:** główna obiekcja trzech osób (P011, P017, P018), a P013 umówi audyt tylko wtedy, gdy zobaczy umowę
  powierzenia. Chodzi o nagrywane rozmowy z danymi o zdrowiu: gdzie są przechowywane i kto podpisuje umowę powierzenia
  danych.
- **Obawa, że recepcjonistka poczuje się kontrolowana i odejdzie.** Pojawia się nawet u tych, którzy audyt umawiają.

### Co zamieniłoby „nie” na „tak” (najczęściej)

- Rekomendacja od kogoś z podobnej kliniki (grupa na Facebooku, znajomy właściciel).
- Widełki ceny na stronie, np. „od X zł za stanowisko”, albo prosty pakiet tylko na telefony po godzinach.
- Umowa powierzenia danych i informacja, gdzie są nagrania, pokazane od razu.
- Zapis wizyt bezpośrednio w Estomedzie.

### Ceny (zł netto miesięcznie za całą klinikę, mediany z 20 odpowiedzi)

| zbyt tanio | okazja | robi się drogo | za drogo |
|---:|---:|---:|---:|
| 300 | 750 | 1 800 | 3 150 |

Rozrzut jest duży: „okazja” od 249 do 3 000 zł. Mały gabinet i sieć to praktycznie dwa różne rynki cenowe.

## Co bym zmienił na landingu przed wydaniem pieniędzy na ruch

1. Widełki ceny albo cena „od”, choćby dla najprostszego pakietu.
2. Sekcja o RODO: umowa powierzenia, gdzie są dane, kto jest administratorem.
3. Opinie konkretnych klinik w różnych rozmiarach, nie tylko partnerów.
4. Audyt pokazany jako pomoc dla recepcji, nie kontrola: kto widzi raport, czy można wyłączyć oceny osób.
5. Sprawdzić, czy hasło „top 1%” nie odcina małych i średnich gabinetów.
6. Jasno napisać, co dostaje klinika na Estomedzie, skoro AI nie zapisuje tam wizyt.

## Pliki

- [customer.json](customer.json): profil klienta (segmenty, zachowania, obiekcje, nawyki)
- [pitch.md](pitch.md): to, co zobaczył każdy kupujący (skrót landingu)
- [panel/results.md](panel/results.md): pełne wyniki z cytatami, [panel/results.json](panel/results.json): to samo
  w JSON
- [panel/personas.json](panel/personas.json): 20 kart kupujących, [panel/panel.json](panel/panel.json): seed i wejścia
- [panel/answers/](panel/answers/): surowe odpowiedzi wszystkich 20 kupujących

Imiona kupujących są angielskie, bo tak działa skrypt. Nie mają znaczenia dla wyniku.
