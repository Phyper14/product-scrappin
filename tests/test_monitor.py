import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import monitor as m

LD = '<script type="application/ld+json">{"@type":"Product","offers":{"@type":"Offer","price":"3.851,10"}}</script>'


class Parse(unittest.TestCase):
    def test_br_format(self):  # milhar com ponto não pode virar decimal
        self.assertEqual(m.to_float("R$ 4.075,40"), 4075.40)

    def test_jsonld(self):
        self.assertEqual(m.extract_price(LD), 3851.10)

    def test_meta(self):
        self.assertEqual(m.extract_price('<meta property="product:price:amount" content="4184.07">'), 4184.07)

    def test_amazon_markup(self):
        self.assertEqual(m.extract_price('<span class="a-offscreen">R$ 4.289,90</span>'), 4289.90)

    def test_amazon_mobile_prefers_pix(self):  # menor entre preço normal e Pix
        html = ('{"mobile_buybox_group_1":[{"displayPrice":"R$ 4.599,00","priceAmount":4599.00}]} '
                '<span data-a="{priceToPay} com {savings} por cento de desconto" class="aok-offscreen"> R$ 4.369,04 </span>')
        self.assertEqual(m.extract_price(html), 4369.04)

    def test_implausible_price_ignored(self):  # ex.: parcela de R$ 12 não é o preço
        self.assertIsNone(m.extract_price('<meta itemprop="price" content="12.00">'))

    def test_no_price(self):
        self.assertIsNone(m.extract_price("<html>captcha</html>"))


class Decide(unittest.TestCase):
    def test_above_cap_no_alert(self):
        self.assertFalse(m.decide(4000, {}, 3900))

    def test_first_below_cap_alerts(self):
        self.assertTrue(m.decide(3900, {}, 3900))

    def test_same_price_not_repeated(self):
        self.assertFalse(m.decide(3800, {"last_alert_price": 3800}, 3900))

    def test_new_low_alerts_again(self):
        self.assertTrue(m.decide(3700, {"last_alert_price": 3800}, 3900))


class Drop(unittest.TestCase):
    def test_drop_above_cap_alerts(self):  # queda brusca avisa mesmo acima do teto
        self.assertTrue(m.dropped(4500, 4800, 5))

    def test_small_move_ignored(self):
        self.assertFalse(m.dropped(4700, 4800, 5))

    def test_first_reading_has_no_baseline(self):
        self.assertFalse(m.dropped(4000, None, 5))

    def test_disabled_without_percent(self):
        self.assertFalse(m.dropped(1000, 4800, None))

    def test_run_reports_drop_reason(self):
        t = [{"id": "a", "name": "A", "url": "u", "max_price": 1000, "drop_percent": 5}]
        st = {"a": {"history": [], "last_price": 4800.0}}
        m.time.sleep = lambda s: None
        al, _ = m.run(t, st, fetcher=lambda u: '<meta itemprop="price" content="4500">')
        self.assertEqual(al[0][2], "queda de 5%+")


class Run(unittest.TestCase):
    T = [{"id": "a", "name": "A", "url": "u", "max_price": 3900}]

    def setUp(self):
        m.time.sleep = lambda s: None

    def test_alert_then_rearm(self):
        st = {}
        al, ok = m.run(self.T, st, fetcher=lambda u: LD, now="t1")
        self.assertEqual((len(al), ok), (1, 1))
        m.run(self.T, st, fetcher=lambda u: '<meta itemprop="price" content="4500">', now="t2")
        self.assertNotIn("last_alert_price", st["a"])  # voltou acima: rearma
        al, _ = m.run(self.T, st, fetcher=lambda u: LD, now="t3")
        self.assertEqual(len(al), 1)

    def test_fetch_failure_is_not_a_price(self):
        def boom(u): raise OSError("403")
        al, ok = m.run(self.T, {}, fetcher=boom)
        self.assertEqual((al, ok), ([], 0))


if __name__ == "__main__":
    unittest.main()
