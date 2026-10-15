"""Product catalog definition for the synthetic Indonesian grocery store.

Each family expands to several size variants (SKUs). `pop` is a popularity tier
(1 = slow, 5 = fast) used only by the simulator; it is never written to
product_master.csv.

Brand names are illustrative. All data in this project is synthetic.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# (size label, price in IDR, share of family demand)
Size = tuple[str, int, float]


@dataclass(frozen=True)
class Family:
    product: str
    brand: str
    category: str
    subcategory: str
    shelf_life_days: int
    pop: int
    aisle: str
    sizes: tuple[Size, ...]
    aliases: tuple[str, ...] = field(default_factory=tuple)  # informal names shoppers use


def F(product, brand, category, subcategory, shelf, pop, aisle, sizes, aliases=()):
    return Family(product, brand, category, subcategory, shelf, pop, aisle, tuple(sizes), tuple(aliases))


CE, DA, IF, BV, SN, FP, MS, BK, HH, PC, BB, FZ = (
    "Cooking Essentials", "Dairy & Eggs", "Instant Food", "Beverages", "Snacks",
    "Fresh Produce", "Meat & Seafood", "Bakery", "Household", "Personal Care",
    "Baby", "Frozen",
)

FAMILIES: tuple[Family, ...] = (
    # --- Cooking essentials -------------------------------------------------
    F("Santan Kotak", "Kara", CE, "Coconut Milk", 270, 4, "A1",
      [("65 ml", 4500, .5), ("200 ml", 11500, .35), ("1 L", 42000, .15)],
      ["santan", "santan kara", "santan kotak"]),
    F("Santan Kotak", "Sasa", CE, "Coconut Milk", 270, 3, "A1",
      [("65 ml", 4200, .55), ("200 ml", 10500, .45)], ["santan sasa"]),
    F("Minyak Goreng", "Bimoli", CE, "Cooking Oil", 540, 5, "A2",
      [("1 L", 19000, .35), ("2 L", 37000, .5), ("5 L", 90000, .15)], ["minyak", "migor", "minyak goreng"]),
    F("Minyak Goreng", "Filma", CE, "Cooking Oil", 540, 4, "A2",
      [("1 L", 18500, .4), ("2 L", 36000, .6)], ["migor filma"]),
    F("Minyak Goreng", "Sania", CE, "Cooking Oil", 540, 4, "A2",
      [("1 L", 19500, .4), ("2 L", 38000, .6)], ["migor sania"]),
    F("Gula Pasir", "Gulaku", CE, "Sugar", 720, 5, "A3",
      [("500 g", 8500, .4), ("1 kg", 16500, .6)], ["gula", "gula pasir"]),
    F("Tepung Terigu", "Segitiga Biru", CE, "Flour", 365, 3, "A3",
      [("500 g", 8000, .45), ("1 kg", 14500, .55)], ["tepung", "terigu", "tepung segitiga"]),
    F("Tepung Terigu", "Cakra Kembar", CE, "Flour", 365, 2, "A3",
      [("1 kg", 15000, 1.0)], ["tepung cakra"]),
    F("Garam Dapur", "Refina", CE, "Salt", 1000, 2, "A3",
      [("250 g", 4000, .6), ("500 g", 6500, .4)], ["garam"]),
    F("Kecap Manis", "Bango", CE, "Soy Sauce", 540, 4, "A4",
      [("135 ml", 8500, .35), ("275 ml", 15500, .4), ("600 ml", 30000, .25)], ["kecap", "kecap bango"]),
    F("Kecap Manis", "ABC", CE, "Soy Sauce", 540, 3, "A4",
      [("135 ml", 7500, .4), ("275 ml", 14000, .6)], ["kecap abc"]),
    F("Saus Sambal", "ABC", CE, "Chili Sauce", 540, 4, "A4",
      [("135 ml", 8000, .4), ("275 ml", 14500, .6)], ["saus sambal", "sambal botol", "saos sambal"]),
    F("Saus Sambal", "Indofood", CE, "Chili Sauce", 540, 3, "A4",
      [("140 ml", 7500, .45), ("340 ml", 15000, .55)], ["sambal indofood"]),
    F("Saus Tomat", "Del Monte", CE, "Tomato Sauce", 540, 3, "A4",
      [("340 g", 14000, .6), ("1 kg", 33000, .4)], ["saus tomat", "saos tomat"]),
    F("Bumbu Nasi Goreng", "Indofood", CE, "Seasoning", 365, 3, "A5",
      [("20 g", 2500, .65), ("50 g", 5500, .35)], ["bumbu nasi goreng", "bumbu racik"]),
    F("Bumbu Ayam Goreng", "Sajiku", CE, "Seasoning", 365, 3, "A5",
      [("20 g", 2800, .6), ("50 g", 6000, .4)], ["bumbu ayam goreng", "sajiku"]),
    F("Kaldu Bubuk Ayam", "Royco", CE, "Seasoning", 365, 4, "A5",
      [("100 g", 6500, .55), ("230 g", 13500, .45)], ["royco", "kaldu ayam"]),
    F("Penyedap Rasa", "Masako", CE, "Seasoning", 365, 4, "A5",
      [("100 g", 4500, .55), ("250 g", 10000, .45)], ["masako", "penyedap"]),
    F("Beras Premium", "Rojolele", CE, "Rice", 180, 5, "A6",
      [("5 kg", 72000, .65), ("10 kg", 140000, .35)], ["beras", "beras rojolele"]),
    F("Beras Pandan Wangi", "Cianjur", CE, "Rice", 180, 4, "A6",
      [("5 kg", 78000, 1.0)], ["beras pandan wangi", "pandan wangi"]),
    # --- Dairy & eggs ---------------------------------------------------------
    F("Susu UHT Full Cream", "Ultra Milk", DA, "UHT Milk", 270, 4, "B1",
      [("200 ml", 5500, .55), ("1 L", 19500, .45)], ["susu uht", "susu ultra", "susu full cream"]),
    F("Susu UHT Coklat", "Indomilk", DA, "UHT Milk", 270, 3, "B1",
      [("190 ml", 5000, .6), ("1 L", 18500, .4)], ["susu coklat", "susu indomilk"]),
    F("Susu Kental Manis", "Frisian Flag", DA, "Condensed Milk", 365, 3, "B2",
      [("370 g", 13000, 1.0)], ["skm", "susu kental manis", "kental manis"]),
    F("Telur Ayam", "Peternak Lokal", DA, "Eggs", 21, 5, "B3",
      [("10 pcs", 24000, .6), ("30 pcs", 68000, .4)], ["telur", "telor", "telur ayam"]),
    F("Yogurt Plain", "Cimory", DA, "Yogurt", 21, 2, "B4",
      [("120 ml", 9000, .55), ("250 ml", 15000, .45)], ["yogurt", "yoghurt"]),
    F("Keju Slice Cheddar", "Kraft", DA, "Cheese", 180, 2, "B4",
      [("12 slices", 28000, 1.0)], ["keju", "keju slice"]),
    F("Mentega", "Blue Band", DA, "Butter & Margarine", 270, 3, "B5",
      [("200 g", 14000, .6), ("500 g", 31000, .4)], ["mentega", "margarin", "blue band"]),
    # --- Instant food ---------------------------------------------------------
    F("Mi Goreng", "Indomie", IF, "Instant Noodles", 270, 5, "C1",
      [("85 g", 3500, .6), ("5 pcs", 17000, .4)], ["indomie", "indomie goreng", "mie goreng", "mi instan"]),
    F("Mi Soto", "Indomie", IF, "Instant Noodles", 270, 4, "C1",
      [("70 g", 3300, .65), ("5 pcs", 16000, .35)], ["indomie soto", "mie soto"]),
    F("Mi Kuah Ayam Bawang", "Mie Sedaap", IF, "Instant Noodles", 270, 4, "C1",
      [("75 g", 3200, .65), ("5 pcs", 15500, .35)], ["mie sedaap", "mie kuah"]),
    F("Mi Goreng", "Mie Sedaap", IF, "Instant Noodles", 270, 4, "C1",
      [("90 g", 3400, .6), ("5 pcs", 16500, .4)], ["sedaap goreng"]),
    F("Bubur Instan Ayam", "Sun", IF, "Porridge", 365, 2, "C2",
      [("45 g", 5500, 1.0)], ["bubur instan", "bubur sun"]),
    F("Sarden Saus Tomat", "ABC", IF, "Canned Fish", 720, 3, "C2",
      [("155 g", 12500, .6), ("425 g", 27000, .4)], ["sarden", "sarden abc"]),
    # --- Beverages ------------------------------------------------------------
    F("Air Mineral", "Aqua", BV, "Water", 540, 5, "D1",
      [("600 ml", 3500, .45), ("1.5 L", 6500, .35), ("19 L Galon", 22000, .2)], ["aqua", "air mineral", "air putih", "galon"]),
    F("Air Mineral", "Le Minerale", BV, "Water", 540, 4, "D1",
      [("600 ml", 3300, .5), ("1.5 L", 6000, .5)], ["le minerale", "leminerale"]),
    F("Teh Celup", "Sariwangi", BV, "Tea", 540, 3, "D2",
      [("25 bags", 7500, 1.0)], ["teh celup", "sariwangi", "teh"]),
    F("Teh Botol", "Sosro", BV, "Ready-to-drink Tea", 360, 4, "D3",
      [("350 ml", 5500, 1.0)], ["teh botol", "teh sosro"]),
    F("Teh Kotak Jasmine", "Teh Pucuk", BV, "Ready-to-drink Tea", 360, 4, "D3",
      [("350 ml", 4500, .6), ("1.5 L", 9500, .4)], ["teh pucuk"]),
    F("Kopi Sachet", "Kapal Api", BV, "Coffee", 540, 4, "D2",
      [("10 sachets", 14000, 1.0)], ["kopi", "kopi kapal api", "kapal api"]),
    F("Kopi 3in1", "Indocafe", BV, "Coffee", 540, 3, "D2",
      [("10 sachets", 16500, 1.0)], ["kopi 3in1", "kopi sachet", "indocafe"]),
    F("Minuman Isotonik", "Pocari Sweat", BV, "Sports Drink", 540, 3, "D3",
      [("500 ml", 8500, 1.0)], ["pocari", "pocari sweat"]),
    F("Sirup Cocopandan", "Marjan", BV, "Syrup", 540, 2, "D4",
      [("460 ml", 22000, 1.0)], ["sirup", "sirup marjan", "marjan"]),
    F("Minuman Soda", "Coca-Cola", BV, "Soft Drink", 360, 3, "D3",
      [("390 ml", 6000, .55), ("1.5 L", 15000, .45)], ["coca cola", "cola", "coke"]),
    F("Susu Kedelai", "V-Soy", BV, "Plant Milk", 270, 1, "D5",
      [("200 ml", 6500, 1.0)], ["susu kedelai", "soy milk"]),
    # --- Snacks ---------------------------------------------------------------
    F("Keripik Kentang", "Chitato", SN, "Chips", 180, 4, "E1",
      [("68 g", 11000, .6), ("140 g", 21000, .4)], ["chitato", "keripik kentang", "chiki"]),
    F("Biskuit Kelapa", "Roma", SN, "Biscuits", 270, 3, "E2",
      [("300 g", 12500, 1.0)], ["biskuit roma", "roma kelapa"]),
    F("Biskuit Marie", "Regal", SN, "Biscuits", 270, 3, "E2",
      [("250 g", 11000, 1.0)], ["biskuit regal", "marie regal"]),
    F("Wafer Coklat", "Tango", SN, "Wafer", 270, 3, "E2",
      [("130 g", 9500, 1.0)], ["wafer tango", "tango"]),
    F("Kerupuk Udang", "Finna", SN, "Crackers", 180, 2, "E3",
      [("200 g", 15000, 1.0)], ["kerupuk", "kerupuk udang", "krupuk"]),
    F("Coklat Batang", "SilverQueen", SN, "Chocolate", 360, 2, "E4",
      [("58 g", 14000, .6), ("100 g", 23000, .4)], ["silverqueen", "coklat"]),
    F("Kacang Garing", "Dua Kelinci", SN, "Nuts", 270, 2, "E3",
      [("200 g", 13500, 1.0)], ["kacang", "kacang garing"]),
    # --- Fresh produce --------------------------------------------------------
    F("Bawang Merah", "", FP, "Vegetables", 14, 4, "F1",
      [("250 g", 12000, .55), ("500 g", 23000, .45)], ["bawang merah", "bawmer"]),
    F("Bawang Putih", "", FP, "Vegetables", 21, 4, "F1",
      [("250 g", 10000, .55), ("500 g", 19000, .45)], ["bawang putih", "bawput"]),
    F("Cabai Merah Keriting", "", FP, "Vegetables", 5, 4, "F1",
      [("100 g", 8000, .6), ("250 g", 19000, .4)], ["cabai", "cabe", "cabe merah", "cabai merah"]),
    F("Cabai Rawit", "", FP, "Vegetables", 5, 3, "F1",
      [("100 g", 9000, .6), ("250 g", 21000, .4)], ["cabe rawit", "cabai rawit", "rawit"]),
    F("Tomat", "", FP, "Vegetables", 6, 3, "F2",
      [("500 g", 9000, 1.0)], ["tomat"]),
    F("Kentang", "", FP, "Vegetables", 21, 3, "F2",
      [("500 g", 10000, .6), ("1 kg", 19000, .4)], ["kentang"]),
    F("Wortel", "", FP, "Vegetables", 10, 3, "F2",
      [("500 g", 8500, 1.0)], ["wortel"]),
    F("Bayam", "", FP, "Vegetables", 3, 3, "F3",
      [("1 ikat", 4000, 1.0)], ["bayam"]),
    F("Kangkung", "", FP, "Vegetables", 3, 3, "F3",
      [("1 ikat", 3500, 1.0)], ["kangkung"]),
    F("Pisang Cavendish", "", FP, "Fruit", 5, 3, "F4",
      [("1 sisir", 22000, 1.0)], ["pisang"]),
    F("Jeruk Mandarin", "", FP, "Fruit", 10, 2, "F4",
      [("1 kg", 32000, 1.0)], ["jeruk", "jeruk mandarin"]),
    F("Tempe Segar", "Pak Haji", FP, "Tofu & Tempeh", 3, 4, "F5",
      [("1 papan", 6000, 1.0)], ["tempe", "tempe segar"]),
    F("Tahu Putih", "Pak Haji", FP, "Tofu & Tempeh", 3, 3, "F5",
      [("10 pcs", 8000, 1.0)], ["tahu", "tahu putih"]),
    # --- Meat & seafood -------------------------------------------------------
    F("Ayam Potong Segar", "Fresh Farm", MS, "Chicken", 3, 4, "G1",
      [("500 g", 24000, .55), ("1 kg", 46000, .45)], ["ayam", "ayam potong", "ayam segar"]),
    F("Daging Sapi Giling", "Fresh Farm", MS, "Beef", 3, 2, "G2",
      [("250 g", 38000, 1.0)], ["daging giling", "daging sapi", "sapi giling"]),
    F("Ikan Bandeng Presto", "Fresh Farm", MS, "Fish", 3, 2, "G3",
      [("1 ekor", 28000, 1.0)], ["bandeng", "ikan bandeng"]),
    F("Sosis Ayam", "Champ", FZ, "Frozen Meat", 180, 3, "H1",
      [("375 g", 32000, 1.0)], ["sosis", "sosis champ"]),
    F("Nugget Ayam", "Fiesta", FZ, "Frozen Meat", 180, 3, "H1",
      [("500 g", 45000, 1.0)], ["nugget", "naget"]),
    F("Bakso Sapi", "Pronas", FZ, "Frozen Meat", 180, 2, "H1",
      [("500 g", 38000, 1.0)], ["bakso", "bakso sapi"]),
    # --- Bakery ---------------------------------------------------------------
    F("Roti Tawar Jumbo", "Sari Roti", BK, "Bread", 5, 4, "I1",
      [("1 pack", 17000, 1.0)], ["roti tawar", "sari roti", "roti"]),
    F("Roti Tawar Kupas", "Sari Roti", BK, "Bread", 5, 3, "I1",
      [("1 pack", 19500, 1.0)], ["roti tawar kupas"]),
    # --- Household ------------------------------------------------------------
    F("Deterjen Bubuk", "Rinso", HH, "Laundry", 720, 3, "J1",
      [("800 g", 22000, .6), ("1.8 kg", 45000, .4)], ["deterjen", "rinso", "sabun cuci"]),
    F("Sabun Cuci Piring", "Sunlight", HH, "Dishwashing", 720, 3, "J1",
      [("400 ml", 11000, .6), ("800 ml", 20000, .4)], ["sunlight", "sabun cuci piring"]),
    F("Pembersih Lantai", "Wipol", HH, "Cleaning", 720, 2, "J2",
      [("780 ml", 18500, 1.0)], ["wipol", "pembersih lantai"]),
    F("Tisu Wajah", "Paseo", HH, "Tissue", 720, 3, "J3",
      [("250 sheets", 14000, .6), ("2x250 sheets", 26000, .4)], ["tisu", "tissue", "paseo"]),
    F("Kantong Sampah", "Hippo", HH, "Cleaning", 1000, 1, "J2",
      [("20 pcs", 12000, 1.0)], ["kantong sampah", "plastik sampah"]),
    # --- Personal care --------------------------------------------------------
    F("Sabun Mandi Batang", "Lifebuoy", PC, "Soap", 720, 3, "K1",
      [("3x80 g", 11000, 1.0)], ["sabun mandi", "lifebuoy"]),
    F("Sampo Anti Ketombe", "Clear", PC, "Hair Care", 720, 2, "K2",
      [("160 ml", 22000, .6), ("340 ml", 39000, .4)], ["sampo", "shampoo", "sampo clear"]),
    F("Pasta Gigi", "Pepsodent", PC, "Oral Care", 720, 4, "K3",
      [("75 g", 9500, .55), ("190 g", 19000, .45)], ["pasta gigi", "odol", "pepsodent"]),
    # --- Baby -----------------------------------------------------------------
    F("Popok Bayi Celana", "MamyPoko", BB, "Diapers", 1000, 2, "L1",
      [("M 24 pcs", 68000, .5), ("L 22 pcs", 68000, .5)], ["popok", "pampers", "diapers", "mamypoko"]),
    F("Susu Formula Tahap 3", "SGM", BB, "Formula", 540, 2, "L2",
      [("400 g", 62000, .6), ("900 g", 125000, .4)], ["susu formula", "susu bayi", "sgm"]),
)


FAMILIES = FAMILIES + (
    # --- Second wave: more brands / sizes so substitutes exist for most items ---
    F("Minyak Goreng", "Tropical", CE, "Cooking Oil", 540, 3, "A2",
      [("1 L", 18800, .3), ("2 L", 36500, .45), ("5 L", 89000, .25)], ["migor tropical"]),
    F("Gula Pasir", "Rose Brand", CE, "Sugar", 720, 3, "A3",
      [("500 g", 8700, .4), ("1 kg", 16800, .45), ("2 kg", 32500, .15)], ["gula rose brand"]),
    F("Gula Merah", "Aren Asli", CE, "Sugar", 360, 2, "A3",
      [("250 g", 9000, .6), ("500 g", 17000, .4)], ["gula merah", "gula aren", "gula jawa"]),
    F("Tepung Beras", "Rose Brand", CE, "Flour", 365, 2, "A3",
      [("500 g", 7500, 1.0)], ["tepung beras"]),
    F("Tepung Bumbu Serbaguna", "Sajiku", CE, "Flour", 365, 3, "A5",
      [("75 g", 4800, .5), ("200 g", 11000, .5)], ["tepung bumbu", "tepung crispy", "tepung sajiku"]),
    F("Kecap Asin", "Sari Murni", CE, "Soy Sauce", 540, 2, "A4",
      [("150 ml", 7000, .6), ("620 ml", 20000, .4)], ["kecap asin"]),
    F("Saus Tiram", "Lee Kum Kee", CE, "Sauces", 540, 2, "A4",
      [("118 ml", 12500, .6), ("510 g", 31000, .4)], ["saus tiram", "saos tiram"]),
    F("Terasi Udang", "Jawara", CE, "Seasoning", 365, 2, "A5",
      [("50 g", 6500, 1.0)], ["terasi", "trasi"]),
    F("Merica Bubuk", "Ladaku", CE, "Seasoning", 540, 2, "A5",
      [("15 g", 4500, .6), ("50 g", 11500, .4)], ["merica", "lada bubuk", "lada"]),
    F("Beras Medium", "Bulog", CE, "Rice", 180, 4, "A6",
      [("5 kg", 62000, .7), ("10 kg", 118000, .3)], ["beras medium", "beras biasa", "beras murah"]),
    F("Susu UHT Low Fat", "Greenfields", DA, "UHT Milk", 270, 2, "B1",
      [("250 ml", 7500, .5), ("1 L", 22000, .5)], ["susu greenfields", "susu low fat"]),
    F("Susu UHT Stroberi", "Frisian Flag", DA, "UHT Milk", 270, 3, "B1",
      [("225 ml", 6000, .6), ("1 L", 19000, .4)], ["susu stroberi", "susu rasa stroberi"]),
    F("Telur Bebek Asin", "Brebes", DA, "Eggs", 30, 2, "B3",
      [("4 pcs", 18000, 1.0)], ["telur asin", "telor asin"]),
    F("Krimer Kental Manis", "Indomilk", DA, "Condensed Milk", 365, 3, "B2",
      [("370 g", 12500, 1.0)], ["kental manis indomilk", "krimer"]),
    F("Mi Instan Kari Ayam", "Indomie", IF, "Instant Noodles", 270, 3, "C1",
      [("72 g", 3300, .65), ("5 pcs", 16000, .35)], ["indomie kari", "mie kari ayam"]),
    F("Mi Instan Ayam Spesial", "Indomie", IF, "Instant Noodles", 270, 3, "C1",
      [("69 g", 3200, .65), ("5 pcs", 15500, .35)], ["indomie ayam spesial", "indomie kuah"]),
    F("Pop Mie Rasa Ayam", "Pop Mie", IF, "Instant Noodles", 270, 3, "C1",
      [("75 g", 6500, 1.0)], ["pop mie", "popmie"]),
    F("Sarden Cabe", "Botan", IF, "Canned Fish", 720, 2, "C2",
      [("155 g", 11500, 1.0)], ["sarden botan", "sarden cabe"]),
    F("Kornet Sapi", "Pronas", IF, "Canned Meat", 720, 2, "C2",
      [("198 g", 29000, 1.0)], ["kornet", "kornet pronas"]),
    F("Teh Celup", "Tong Tji", BV, "Tea", 540, 2, "D2",
      [("25 bags", 8500, 1.0)], ["teh tong tji", "teh tongji"]),
    F("Kopi Bubuk", "Kapal Api", BV, "Coffee", 540, 3, "D2",
      [("165 g", 17000, .5), ("380 g", 36000, .5)], ["kopi bubuk", "kopi hitam"]),
    F("Susu Coklat Bubuk", "Milo", BV, "Malt Drink", 540, 3, "D2",
      [("300 g", 32000, .5), ("1 kg", 82000, .5)], ["milo", "susu milo"]),
    F("Minuman Isotonik", "Mizone", BV, "Sports Drink", 540, 2, "D3",
      [("500 ml", 5500, 1.0)], ["mizone"]),
    F("Jus Buah Jambu", "Buavita", BV, "Juice", 270, 2, "D3",
      [("250 ml", 7500, .55), ("1 L", 22000, .45)], ["jus jambu", "buavita", "jus buah"]),
    F("Soda Lemon", "Sprite", BV, "Soft Drink", 360, 3, "D3",
      [("390 ml", 6000, .55), ("1.5 L", 15000, .45)], ["sprite", "soda lemon"]),
    F("Keripik Singkong", "Maicih", SN, "Chips", 180, 2, "E1",
      [("100 g", 15000, 1.0)], ["keripik singkong", "kripik singkong", "maicih"]),
    F("Keripik Kentang", "Lay's", SN, "Chips", 180, 3, "E1",
      [("68 g", 11500, .6), ("140 g", 22000, .4)], ["lays", "lay's", "keripik lays"]),
    F("Coklat Wafer", "Beng-Beng", SN, "Wafer", 270, 4, "E2",
      [("1 pc 20 g", 2500, .45), ("10 pcs", 22000, .55)], ["beng beng", "bengbeng"]),
    F("Biskuit Sandwich Coklat", "Oreo", SN, "Biscuits", 270, 3, "E2",
      [("137 g", 9500, .6), ("259 g", 15500, .4)], ["oreo", "biskuit oreo"]),
    F("Biskuit Gandum", "Good Time", SN, "Biscuits", 270, 2, "E2",
      [("80 g", 8500, 1.0)], ["good time", "goodtime", "biskuit coklat chip"]),
    F("Permen Mint", "Kopiko", SN, "Candy", 360, 3, "E4",
      [("27 g", 2500, .5), ("120 g", 9000, .5)], ["kopiko", "permen kopi", "permen"]),
    F("Pisang Sale", "Gunung Sari", SN, "Dried Fruit", 180, 1, "E3",
      [("200 g", 18000, 1.0)], ["pisang sale"]),
    F("Apel Fuji", "", FP, "Fruit", 14, 2, "F4",
      [("500 g", 24000, 1.0)], ["apel", "apel fuji"]),
    F("Jeruk Nipis", "", FP, "Fruit", 10, 3, "F4",
      [("250 g", 7000, 1.0)], ["jeruk nipis", "limau"]),
    F("Bawang Bombay", "", FP, "Vegetables", 21, 3, "F1",
      [("500 g", 14000, 1.0)], ["bawang bombay", "bombay"]),
    F("Sawi Hijau", "", FP, "Vegetables", 3, 3, "F3",
      [("1 ikat", 4500, 1.0)], ["sawi", "sawi hijau", "caisim"]),
    F("Timun", "", FP, "Vegetables", 7, 3, "F2",
      [("500 g", 7000, 1.0)], ["timun", "mentimun"]),
    F("Jagung Manis", "", FP, "Vegetables", 4, 2, "F2",
      [("2 pcs", 9000, 1.0)], ["jagung", "jagung manis"]),
    F("Ayam Fillet Dada", "Fresh Farm", MS, "Chicken", 3, 3, "G1",
      [("500 g", 35000, 1.0)], ["dada ayam", "fillet ayam", "ayam fillet"]),
    F("Udang Segar", "Fresh Farm", MS, "Seafood", 2, 2, "G3",
      [("250 g", 36000, 1.0)], ["udang", "udang segar"]),
    F("Ikan Lele Segar", "Fresh Farm", MS, "Fish", 2, 2, "G3",
      [("500 g", 22000, 1.0)], ["lele", "ikan lele"]),
    F("French Fries", "McCain", FZ, "Frozen Snacks", 270, 2, "H2",
      [("450 g", 38000, 1.0)], ["kentang goreng", "french fries", "kentang beku"]),
    F("Dimsum Ayam", "Belfoods", FZ, "Frozen Snacks", 180, 2, "H2",
      [("400 g", 42000, 1.0)], ["dimsum", "dimsum ayam", "dimsum beku"]),
    F("Roti Sobek Coklat", "Sari Roti", BK, "Bread", 5, 3, "I1",
      [("1 pack", 14500, 1.0)], ["roti sobek", "roti coklat"]),
    F("Roti Gandum", "Sari Roti", BK, "Bread", 5, 2, "I1",
      [("1 pack", 23000, 1.0)], ["roti gandum", "roti whole wheat"]),
    F("Pelembut Pakaian", "Molto", HH, "Laundry", 720, 3, "J1",
      [("800 ml", 17500, .5), ("1.6 L", 31000, .5)], ["pelembut", "molto", "pewangi pakaian"]),
    F("Deterjen Cair", "Attack", HH, "Laundry", 720, 2, "J1",
      [("800 ml", 28000, 1.0)], ["deterjen cair", "attack"]),
    F("Sabun Cuci Tangan", "Lifebuoy", HH, "Cleaning", 720, 3, "J2",
      [("200 ml", 14500, .5), ("400 ml refill", 22000, .5)], ["sabun cuci tangan", "handsoap", "hand soap"]),
    F("Obat Nyamuk Bakar", "Baygon", HH, "Insecticide", 1000, 2, "J2",
      [("12 coils", 9500, 1.0)], ["obat nyamuk", "baygon"]),
    F("Sikat Gigi", "Formula", PC, "Oral Care", 1000, 3, "K3",
      [("1 pc", 8000, 1.0)], ["sikat gigi"]),
    F("Sabun Mandi Cair", "Dettol", PC, "Soap", 720, 2, "K1",
      [("250 ml", 26000, .5), ("450 ml refill", 38000, .5)], ["sabun cair", "sabun mandi cair", "dettol"]),
    F("Deodoran Roll On", "Rexona", PC, "Deodorant", 720, 2, "K2",
      [("45 ml", 17500, 1.0)], ["deodoran", "rexona", "roll on"]),
    F("Pembalut Wanita", "Laurier", PC, "Feminine Care", 1000, 3, "K4",
      [("20 pads", 15500, .55), ("30 pads", 21000, .45)], ["pembalut", "laurier"]),
    F("Bubur Bayi Instan", "Milna", BB, "Baby Food", 365, 2, "L2",
      [("120 g", 27000, 1.0)], ["bubur bayi", "bubur milna", "mpasi"]),
    F("Tisu Basah Bayi", "Nuvo", BB, "Baby Care", 720, 2, "L1",
      [("50 sheets", 14000, 1.0)], ["tisu basah", "wet wipes"]),
)


@dataclass(frozen=True)
class NotStocked:
    """Items shoppers ask for that the store does not carry (assortment gaps).

    These land in product_master.csv as `is_carried = false` rows (SKU `NC-001`..), so the
    assortment-gap views and the extractor catalog treat them exactly like real products.
    `pack_size`/`price` are nominal reference values (never sold, never simulated).
    """
    name: str
    category: str
    weight: float
    aliases: tuple[str, ...]
    pack_size: str = ""
    price: int = 0


NOT_STOCKED: tuple[NotStocked, ...] = (
    NotStocked("Oat Milk", "Beverages", 5.0, ("oat milk", "susu oat", "oatmilk", "oat mulk"), "1 L", 32000),
    NotStocked("Almond Milk", "Beverages", 2.2, ("almond milk", "susu almond", "susu kacang almond"), "1 L", 35000),
    NotStocked("Sambal Ijo Instan", "Cooking Essentials", 3.6, ("sambal ijo", "saus ijo", "sambal hijau", "saos ijo"), "275 ml", 16000),
    NotStocked("Sambal Matah Botolan", "Cooking Essentials", 2.4, ("sambal matah", "matah botolan", "sambel matah"), "200 ml", 24000),
    NotStocked("Greek Yogurt", "Dairy & Eggs", 2.8, ("greek yogurt", "yogurt yunani", "greek yoghurt"), "500 g", 45000),
    NotStocked("Granola", "Snacks", 1.8, ("granola", "granola bar", "granola cereal"), "250 g", 38000),
    NotStocked("Kimchi", "Fresh Produce", 1.6, ("kimchi", "kimci", "sawi kimchi"), "250 g", 28000),
    NotStocked("Brown Rice", "Cooking Essentials", 2.5, ("beras merah", "beras merah organik", "brown rice"), "2 kg", 42000),
    NotStocked("Natural Peanut Butter", "Cooking Essentials", 1.7, ("selai kacang natural", "peanut butter", "selai kacang tanpa gula"), "340 g", 48000),
    NotStocked("Shirataki Noodles", "Instant Food", 1.2, ("mie shirataki", "shirataki", "mi shirataki"), "200 g", 22000),
    NotStocked("Microwave Rice", "Instant Food", 1.5, ("nasi instan microwave", "nasi instan", "nasi siap makan"), "250 g", 18000),
    NotStocked("Extra Virgin Olive Oil", "Cooking Essentials", 1.4, ("minyak zaitun", "olive oil", "minyak zaitun extra virgin"), "250 ml", 65000),
    NotStocked("Frozen Tempe Mendoan", "Frozen", 1.9, ("mendoan beku", "tempe mendoan", "mendoan frozen"), "400 g", 26000),
    NotStocked("Salmon Fillet", "Meat & Seafood", 1.5, ("salmon", "fillet salmon", "ikan salmon"), "250 g", 75000),
    NotStocked("Gluten-Free Pasta", "Instant Food", 0.8, ("pasta bebas gluten", "gluten free pasta", "pasta gluten free"), "400 g", 42000),
)


def nc_sku(idx: int) -> str:
    """SKU for the idx-th not-stocked item, matching the NC-xxx rows in product_master."""
    return f"NC-{idx + 1:03d}"
