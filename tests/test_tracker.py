import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from tracker import parse_price, extract_price, should_notify


def test_parse():
    assert parse_price("R$ 1.299,90") == 1299.90
    assert parse_price("1,299.90") == 1299.90
    assert parse_price("1299.9") == 1299.9
    assert parse_price("R$ 2.500") == 2500.0
    assert parse_price("49,90") == 49.90
    assert parse_price("sem preço") is None


def test_jsonld():
    html = '<script type="application/ld+json">{"@type":"Product","offers":{"price":"899.90"}}</script>'
    assert extract_price(html) == 899.90


def test_meta_and_selector():
    assert extract_price('<meta property="og:price:amount" content="10,50">') == 10.5
    assert extract_price('<b class="p">R$ 1.000,00</b>', ".p") == 1000.0


def test_notify_rules():
    assert should_notify(90, 100, None, target=95)
    assert should_notify(90, 100, 90, target=95) is None   # já avisado
    assert should_notify(89, 100, None, drop_pct=10)
    assert should_notify(95, 100, None, drop_pct=10) is None
