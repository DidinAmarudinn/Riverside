from app.agents import guards


def test_claimed_numbers_prices_and_counts():
    reply = "Santan Kara ada kak, stok 8 di rak A1-2, harganya Rp 4.500. Ada juga 3 pcs di cabang lain."
    assert guards.claimed_numbers(reply) == {"8", "4500", "3"}


def test_sizes_in_product_names_are_not_claims():
    assert guards.claimed_numbers("Santan Kara 65 ml dan minyak 2 L tersedia.") == set()


def test_numbers_in_normalises_thousand_separators():
    assert {"4500", "8", "21"} <= guards.numbers_in('{"price_idr": 4500, "units": 8, "distance_km": 21.0}')
    assert "4500" in guards.numbers_in("Rp 4.500")


def test_ungrounded_flags_only_invented_numbers():
    grounded = {"8", "4500"}
    assert guards.ungrounded("stok 8, Rp 4.500", grounded) == set()
    assert guards.ungrounded("stok 12, Rp 4.500", grounded) == {"12"}
    assert guards.ungrounded("Rp 5.000 ya kak", grounded) == {"5000"}


def test_limit_sentences():
    text = "Satu. Dua! Tiga? Empat. Lima."
    assert guards.limit_sentences(text) == "Satu. Dua! Tiga?"
    assert guards.limit_sentences("Cuma dua. Kalimat.") == "Cuma dua. Kalimat."
