# Library style for the existing presentation demo

Use the existing frontend served on port 8800, preserving its complete recorded replay, timeline, evidence, code notes, candidate checks and Reactor answer. User prefers this information-rich demonstration to the separate quiet frontend.

- Improve actual reading sizes and contrast at 1440×900 and 1920×1080. Reading material uses upright Alegreya instead of tiny type and dense cursive.
- Apply the existing illustrated monastery/retro-electronics style. Use local WebP books, librarian, Reactor, lens icons and local fonts. Ambient effects limited to indicator lights; replay movement remains meaningful.
- Add a scrollable explanation after the demo: the noisy-history problem, illustrated five-stage walkthrough, the five lenses and a return to the demo.
- Keep backend calls, predictions, evidence content, answer strings and citation logic intact. Do not call Reactor while testing. Keep the separate port-8804 variant available.
- Validate representative answer types, abstention, evidence opening, question chooser, tour controls, scrolling, keyboard and reduced motion. Retain before/after screenshots. Original files backed up under `demo/web_before_library_style/`.
