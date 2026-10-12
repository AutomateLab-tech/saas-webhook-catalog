from catalog import extractor


def test_examples_are_excluded_by_contract_not_name(monkeypatch):
    class DemoA:
        is_example = True
    class DemoB:
        is_example = True
    class Production:
        is_example = False
    monkeypatch.setattr(extractor, "_REGISTRY", {"not-named-example": DemoA, "another-demo": DemoB, "real-vendor": Production})
    assert extractor.list_slugs() == ["real-vendor"]
    assert extractor.list_slugs(include_examples=True) == ["another-demo", "not-named-example", "real-vendor"]
