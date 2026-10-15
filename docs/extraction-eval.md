# Extraction accuracy — extractor-v1-20261015

All data is synthetic; accuracy is measured against the simulator's hidden ground truth.

- Conversations evaluated : **3110**  (not extracted: 0)
- Outcome accuracy        : **99.00%**  `████████████████████████████`
- SKU exact               : **80.65%**  `███████████████████████·····`  (of 2186 SKU requests)
- Item + size             : **83.26%**  `███████████████████████·····`  (brand-insensitive)
- not_carried recall      : **100.00%**  precision 100.00%  (of 924)
- substituted recall      : **100.00%**  (of 41)
- confidence < 0.7        : 31  (1.0% of evaluated) — excluded from forecast B

## Outcome confusion matrix (row = ground truth, col = prediction)

| gt \ pred | out_of_stock | substituted | purchased | not_carried | total |
|---|---|---|---|---|---|
| **out_of_stock** | 141 | 0 | 0 | 0 | 141 |
| **substituted** | 0 | 41 | 0 | 0 | 41 |
| **purchased** | 0 | 0 | 1973 | 0 | 1973 |
| **not_carried** | 0 | 0 | 0 | 924 | 924 |

## Outcome failures (sample)

- `C000131` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "min ada roit? dong"}, {"role": "agent", "text": "Ada kak. Roti Tawar Jumbo Sari Roti 1 pack ada di rak I1-4. Harganya Rp17.000."},
- `C000287` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "sore, bimoli migor ada gak? cepet ya"}, {"role": "agent", "text": "Ada kak. Minyak Goreng Bimoli 2 L ada di rak A2-4. Harganya Rp3
- `C000599` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "mba odl kosong ya? yaa"}, {"role": "agent", "text": "Ada kak. Pasta Gigi Pepsodent 190 g ada di rak K3-2. Harganya Rp19.000."}, {"
- `C000686` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "Lagi nyari bawput, ada?"}, {"role": "agent", "text": "Ada kak. bawput ada di rak F1-1. Harganya Rp10.000."}, {"role": "shopper", "
- `C000825` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "mba nyari minuman isotonik 500lm nih"}, {"role": "agent", "text": "Ada kak. Minuman Isotonik Mizone 500 ml ada di rak D3-1. Hargan
- `C001071` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "Ada bawmer ga ya? plis"}, {"role": "agent", "text": "Ada kak. Bawang Merah 500 g ada di rak F1-4. Harganya Rp23.000."}, {"role": "
- `C001101` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "pagi kak, permisi minuman isotonik 500ml ada? ya"}, {"role": "agent", "text": "Ada kak. Minuman Isotonik Mizone 500 ml ada di rak 
- `C001168` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "pagi kak, ada jual sewi? cepet ya"}, {"role": "agent", "text": "Ada kak. sewi ada di rak F3-4. Harganya Rp4.500."}]
- `C001184` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "nyari bawput 500gr nih kak"}, {"role": "agent", "text": "Ada kak. Bawang Putih 500 g ada di rak F1-2. Harganya Rp19.000."}, {"role
- `C001291` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "Min migor 5 L masih ada? deh"}, {"role": "agent", "text": "Ada kak. migor 5 L ada di rak A2-1. Harganya Rp90.000."}]
- `C001310` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "mas bawput di rak mana? plis"}, {"role": "agent", "text": "Ada kak. Bawang Putih 250 g ada di rak F1-1. Harganya Rp10.000."}]
- `C001316` gt=**purchased** pred=**low_confidence** — [{"role": "shopper", "text": "Kak swai di rak mana? deh"}, {"role": "agent", "text": "Ada kak. Sawi Hijau 1 ikat ada di rak F3-4. Harganya Rp4.500."}]

## SKU failures (item+size mismatch, sample)

- `C000014` gt=`SKU-0010` (minyak goreng 2 l) pred=`SKU-0009` (minyak goreng 1 l)
- `C000017` gt=`SKU-0181` (coklat wafer 10 pcs) pred=`SKU-0180` (coklat wafer 1 pc 20 g)
- `C000024` gt=`SKU-0168` (kopi bubuk 165 g) pred=`SKU-0074` (kopi sachet 10 sachets)
- `C000029` gt=`SKU-0072` (teh kotak jasmine 350 ml) pred=`SKU-0071` (teh botol 350 ml)
- `C000051` gt=`SKU-0054` (mi goreng 85 g) pred=`SKU-0055` (mi goreng 5 pcs)
- `C000052` gt=`SKU-0180` (coklat wafer 1 pc 20 g) pred=`SKU-0087` (coklat batang 58 g)
- `C000062` gt=`SKU-0064` (sarden saus tomat 425 g) pred=`SKU-0063` (sarden saus tomat 155 g)
- `C000065` gt=`SKU-0079` (minuman soda 1.5 l) pred=`SKU-0078` (minuman soda 390 ml)
- `C000079` gt=`SKU-0139` (gula pasir 2 kg) pred=`SKU-0137` (gula pasir 500 g)
- `C000082` gt=`SKU-0034` (bumbu ayam goreng 50 g) pred=`SKU-0033` (bumbu ayam goreng 20 g)
- `C000092` gt=`SKU-0010` (minyak goreng 2 l) pred=`SKU-0009` (minyak goreng 1 l)
- `C000097` gt=`SKU-0048` (telur ayam 30 pcs) pred=`SKU-0047` (telur ayam 10 pcs)
