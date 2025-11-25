from utils.signature_mapping import (
    collect_event_ids_from_values,
    extract_event_ids_from_text,
    get_event_details,
    get_event_ids_for_signature,
)


def test_get_event_ids_for_signature_exact_match():
    assert get_event_ids_for_signature('43-263047680') == ['4768']


def test_get_event_ids_for_signature_without_prefix():
    assert get_event_ids_for_signature('263047680') == ['4768']


def test_extract_event_ids_from_text_finds_multiple_ids():
    xml_snippet = '<filterData value="43-263047680"/><filterData value="43-263047690"/>'
    event_ids = extract_event_ids_from_text(xml_snippet)
    assert event_ids == ['4768', '4769']


def test_get_event_details_returns_metadata():
    details = get_event_details(['4768'])
    assert details and details[0]['id'] == '4768'
    assert 'description' in details[0]


def test_collect_event_ids_from_values_handles_mixed_formats():
    values = ['43-263047680,43-263047690', ' 4768 ', '47|263047680']
    event_ids = collect_event_ids_from_values(values)
    assert event_ids == {'4768', '4769'}
