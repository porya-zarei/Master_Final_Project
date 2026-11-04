# Seminar I — Presentation Decks

**Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning**
Pouria Zarei · Supervisor: Prof. Mohammad Javad Yazdanpanah · University of Tehran

## Files

| File | What it is |
|---|---|
| `Seminar_I_Pouria_Zarei.pptx` | English deck (15 slides, 16:9, animations + speaker notes) |
| `Seminar_I_Pouria_Zarei.pdf` | English deck, PDF backup |
| `Seminar_I_Pouria_Zarei_FA.pptx` | Persian deck, RTL (16 slides, animations + Persian notes) |
| `Seminar_I_Pouria_Zarei_FA.pdf` | Persian deck, PDF backup |
| `build_deck.py` / `build_deck_fa.py` | Rebuild each deck (`python build_deck*.py`) |
| `assets_prep.py` | Regenerates the image crops in `assets/` |
| `render*.ps1` | Export every slide to PNG via PowerPoint (QA / previews) |
| `export_pdf.ps1` | Export a deck to PDF via PowerPoint |
| `render/`, `render_fa/` | Full-resolution slide previews |

## English deck (10 min)

Title · Roadmap · ADCS loop · Why faults are hard · Research question ·
Proposal architecture · Validation plan · Three papers · Paper 1–3 ·
Gaps → ideas · Conclusion · Thank you · References.

## Persian deck (۱۰ دقیقه) — follows `Seminar_I_Content_Plan_Persian_Natural.md`

| # | اسلاید | # | اسلاید |
|---|---|---|---|
| ۱ | عنوان | ۹ | سه مقاله منتخب |
| ۲ | مسیر ارائه | ۱۰ | مقاله اول |
| ۳ | ماهواره و ADCS | ۱۱ | مقاله دوم |
| ۴ | یک نسخه برای همه وجود ندارد | ۱۲ | مقاله سوم |
| ۵ | از کنترل ساده تا یادگیری‌محور | ۱۳ | شکاف‌ها و ایده‌ها |
| ۶ | حسگرهای ADCS | ۱۴ | جمع‌بندی |
| ۷ | موضوع پژوهش | ۱۵ | سپاسگزاری |
| ۸ | معماری پیشنهادی | ۱۶ | منابع |

Slides 4, 5, 6 are background; if the talk runs long, slide 5 is the one to cut.
Speaker notes carry Persian timing markers (۰:۰۰ → ۱۰:۰۰).

## Design system (both decks)

- Light ground, University-of-Tehran blue `#16639E`, navy `#0E3355`.
- Faults = red, constraints = amber, RL = purple, healthy = green.
- Latin deck: Segoe UI. Persian deck: Dubai (RTL paragraphs, Persian digits, mirrored diagrams).
- Fade-in only, one step per idea; slide transitions: fade.
- Every slide with an image or a borrowed claim carries a footnote.

## Notes on the Persian deck

- Layout is fully mirrored: content starts on the right, the ADCS loop flows
  right→left, table columns run right→left, cards are ordered right→left.
- Numbers in text and page numbers use Persian digits; technical tokens
  (ADCS, RL, LQR, MPC, CubeSat, …) stay in Latin.
- Avoid starting a Persian sentence with a Latin token — PowerPoint reorders it.
  If you edit, keep Persian first (`سامانه ADCS` not `ADCS سامانه`).
