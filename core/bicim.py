"""Tutar biçimlendirme: binlik ayraç NOKTA (1000 -> 1.000, 85647 -> 85.647)."""


def tl(deger) -> str:
    """Tutarı tam sayı olarak, binlik ayraçlı yazar. Küsurat gösterilmez (eski '.0f' davranışı
    korunur). Negatifler '-1.250' biçiminde gelir."""
    try:
        n = int(round(float(deger)))
    except (TypeError, ValueError):
        return str(deger)
    return f"{n:,}".replace(",", ".")
