import pytest
from scripts.table_converter import convert

def test_csv_with_numeric():
    inp = "name,age,salary\nAlice,30,50000\nBob,25,60000\nCharlie,35,70000"
    res = convert(inp)
    assert '| name | age | salary |' in res['markdown_table']
    assert '| Alice | 30 | 50000 |' in res['markdown_table']
    assert '| --- | ---: | ---: |' in res['markdown_table']

def test_json():
    inp = '[{"city":"Paris","population":2161000},{"city":"London","population":8982000},{"city":"Berlin","population":3645000}]'
    res = convert(inp)
    assert '| city | population |' in res['markdown_table']
    assert '| Paris | 2161000 |' in res['markdown_table']
    assert '| --- | ---: |' in res['markdown_table']

def test_pipe_delimited():
    inp = "name|age|city\nAlice|30|Paris\nBob|25|London\nCharlie|35|Berlin"
    res = convert(inp)
    assert '| name | age | city |' in res['markdown_table']
    assert '| Bob | 25 | London |' in res['markdown_table']
    assert '<th>name</th><th>age</th><th>city</th>' in res['html_table']

def test_wrong_field_count():
    inp = "a,b,c\n1,2,3\n4,5\n6,7,8,9"
    res = convert(inp)
    assert 'Rows with wrong number of fields:' in res['error_report']
    assert 'Row 2: field count 2 (expected 3)' in res['error_report']
    assert 'Row 3: field count 4 (expected 3)' in res['error_report']
    assert '<th>a</th><th>b</th><th>c</th>' in res['html_table']

def test_single_column_csv():
    inp = "name\nAlice\nBob\nCharlie"
    res = convert(inp)
    assert '| name |' in res['markdown_table']
    assert '| Alice |' in res['markdown_table']
    assert 'error_report' not in res