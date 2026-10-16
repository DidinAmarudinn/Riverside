# Extraction accuracy: Gemini vs. the offline matcher

All data is synthetic; accuracy is measured against the simulator's hidden ground truth (`gt_sku`, `gt_outcome`).
Run on 2026-10-16 over the same random sample of **800 conversations** (seed 20261016, drawn from the 3,234 in
BigQuery) with `app.extract.batch` (`--llm gemini`, gemini-2.5-flash on Vertex AI, model default thinking) and with
the offline matcher (`--llm template`), each scored by `app.extract.eval`. In both runs the outcome comes from
the same rules (§6.3); Gemini picks the product, quantity and confidence.

| Metric | Offline matcher | Gemini 2.5 Flash |
|---|---:|---:|
| Outcome accuracy | 98.88% | 99.25% |
| SKU exact (of 561 SKU requests) | 80.39% | **94.65%** |
| Item + size, brand-insensitive | 83.42% | **95.37%** |
| not_carried recall | 100.00% | 100.00% |
| substituted recall (of 12) | 100.00% | 83.33% |
| Confidence < 0.7 (left out of forecast B) | 9 | 4 |

The chats are generated from templates with slang, abbreviations and typos, so the offline matcher already does
well on outcomes; the gap is in naming the right product and size from informal text.
The full-dataset numbers in [extraction-eval.md](extraction-eval.md) are the offline matcher's.

## Gemini run, full report


All data is synthetic; accuracy is measured against the simulator's hidden ground truth.

- Conversations evaluated : **800**  (not extracted: 0)
- Outcome accuracy        : **99.25%**  `████████████████████████████`
- SKU exact               : **94.65%**  `███████████████████████████·`  (of 561 SKU requests)
- Item + size             : **95.37%**  `███████████████████████████·`  (brand-insensitive)
- not_carried recall      : **100.00%**  precision 100.00%  (of 239)
- substituted recall      : **83.33%**  (of 12)
- confidence < 0.7        : 4  (0.5% of evaluated) — excluded from forecast B

## Outcome confusion matrix (row = ground truth, col = prediction)

| gt \ pred | out_of_stock | substituted | purchased | not_carried | total |
|---|---|---|---|---|---|
| **out_of_stock** | 23 | 3 | 0 | 0 | 26 |
| **substituted** | 2 | 10 | 0 | 0 | 12 |
| **purchased** | 0 | 0 | 522 | 0 | 522 |
| **not_carried** | 0 | 0 | 0 | 239 | 239 |

## Outcome failures (sample)

- `C002086` gt=**substituted** pred=**out_of_stock** — [{"role": "shopper", "text": "Sabun mandi cair dttol 250 ml masih ada? cepet ya"}, {"role": "agent", "text": "Maaf kak, Sabun Mandi Cair Dettol 250 ml lagi koso
- `C002621` gt=**substituted** pred=**out_of_stock** — [{"role": "shopper", "text": "permisi kak, cabe merah 100gr kosong ya? ya"}, {"role": "agent", "text": "Maaf kak, Cabai Merah Keriting 100 g lagi kosong nih. Ma
- `C000626` gt=**out_of_stock** pred=**substituted** — [{"role": "shopper", "text": "Garam dapur 250 gram di rak mana? nih"}, {"role": "agent", "text": "Maaf kak, Garam Dapur Refina 250 g lagi kosong nih. Mau coba G
- `C001974` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "Permisi cabai ada?"}, {"role": "agent", "text": "Ada kak. cabai ada di rak F1-4. Harganya Rp19.000."}]
- `C001670` gt=**out_of_stock** pred=**substituted** — [{"role": "shopper", "text": "sore, mi goreng indomie 5 pcs ada gak? kak"}, {"role": "agent", "text": "Maaf kak, Mi Goreng Indomie 5 pcs lagi kosong nih. Mau co
- `C000276` gt=**out_of_stock** pred=**substituted** — [{"role": "shopper", "text": "susu uht full crream ultra milk 200 ml kosong ya? deh"}, {"role": "agent", "text": "Maaf kak, Susu UHT Full Cream Ultra Milk 200 m

## SKU failures (item+size mismatch, sample)

- `C001647` gt=`SKU-0014` (gula pasir 1 kg) pred=`` (gula pasir gulaku 1 kg)
- `C002280` gt=`SKU-0094` (cabai merah keriting 100 g) pred=`SKU-0096` (cabai rawit 100 g)
- `C002760` gt=`SKU-0094` (cabai merah keriting 100 g) pred=`` (cabai merah keriting)
- `C001358` gt=`SKU-0002` (santan kotak 200 ml) pred=`SKU-0001` (santan kotak 65 ml)
- `C001565` gt=`SKU-0075` (kopi 3in1 10 sachets) pred=`SKU-0074` (kopi sachet 10 sachets)
- `C001396` gt=`SKU-0208` (sabun mandi cair 250 ml) pred=`` (sabun mandi cair)
- `C002970` gt=`SKU-0207` (sikat gigi 1 pc) pred=`` (pasta gigi)
- `C001581` gt=`SKU-0057` (mi soto 5 pcs) pred=`SKU-0056` (mi soto 70 g)
- `C001779` gt=`SKU-0006` (minyak goreng 1 l) pred=`` (minyak goreng)
- `C000930` gt=`SKU-0048` (telur ayam 30 pcs) pred=`SKU-0047` (telur ayam 10 pcs)
- `C001606` gt=`SKU-0073` (teh kotak jasmine 1.5 l) pred=`SKU-0072` (teh kotak jasmine 350 ml)
- `C000322` gt=`SKU-0209` (sabun mandi cair 450 ml refill) pred=`` (sabun mandi cair)
