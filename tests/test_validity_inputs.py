"""V2b and V4 async misuse, from the failures of the live run of 2026-11-14 20:51. Real files, real AST; nothing is mocked."""
from backend.qe.validity import inputs

APP = '''
CALCULATORS = {"future_value": fv, "present_value": pv}

def calc(name, params):
    if name not in CALCULATORS:
        return {"error": f"unknown calculator '{name}'"}
    try:
        return CALCULATORS[name](**params)
    except (TypeError, ValueError) as e:
        return {"error": f"invalid inputs: {e}"}
'''


def repo(tmp_path):
    (tmp_path / "src").mkdir(exist_ok=True)
    (tmp_path / "src" / "calc.py").write_text(APP, encoding="utf-8")
    inputs._cache.pop(str(tmp_path), None)
    return tmp_path


POSITIVE = {"type": "Positive", "requirement_id": "REQ-001", "test_data": "rate 5", "expected_result": "returns the value"}
NEGATIVE = {**POSITIVE, "type": "Negative"}


def test_an_invented_calculator_name_in_a_positive_case_is_refused_with_real_names(tmp_path):
    code = "from src.calc import calc\n\ndef test_x():\n    assert calc('interest', {'rate': 5})['value'] == 1\n"
    out = inputs.invented(repo(tmp_path), "t.py", code, POSITIVE, "")
    assert out["status"] == "FAIL" and "'interest'" in out["message"], out


def test_a_real_name_passes_and_a_negative_case_may_use_an_invalid_one(tmp_path):
    root = repo(tmp_path)
    good = "from src.calc import calc\n\ndef test_x():\n    assert calc('future_value', {'rate': 5})['value'] == 1\n"
    assert inputs.invented(root, "t.py", good, POSITIVE, "")["status"] == "PASS"
    bad_on_purpose = "from src.calc import calc\n\ndef test_x():\n    assert calc('interest', {})['error'].startswith('unknown calculator')\n"
    assert inputs.invented(root, "t.py", bad_on_purpose, NEGATIVE, "")["status"] == "PASS"


def test_an_error_text_the_code_never_produces_is_refused(tmp_path):
    code = "from src.calc import calc\n\ndef test_x():\n    assert calc('future_value', {})['error'] == 'invalid parameters'\n"
    out = inputs.invented(repo(tmp_path), "t.py", code, NEGATIVE, "")
    assert out["status"] == "FAIL" and "'invalid parameters'" in out["message"], out
    real = "from src.calc import calc\n\ndef test_x():\n    assert calc('future_value', {})['error'].startswith('invalid inputs:')\n"
    assert inputs.invented(repo(tmp_path), "t.py", real, NEGATIVE, "")["status"] == "PASS"


def test_sync_client_on_async_transport_and_a_missing_await_are_named():
    sync = "import httpx\n\ndef test_x():\n    transport = httpx.ASGITransport(app=app)\n    with httpx.Client(transport=transport) as c:\n        assert c.get('/').status_code == 200\n"
    assert any("sync httpx.Client" in m for m in inputs.async_misuse(sync))
    no_await = "import httpx\n\nasync def test_x():\n    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app)) as c:\n        r = c.get('/')\n        assert r.status_code == 200\n"
    assert any("is not awaited" in m for m in inputs.async_misuse(no_await))
    right = no_await.replace("r = c.get('/')", "r = await c.get('/')")
    assert inputs.async_misuse(right) == []
