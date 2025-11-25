import json
import os
import re
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Sequence, Set

_MAPPING_FILENAME = 'esm_signature_id.json'


def _mapping_path() -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    return os.path.join(base_dir, _MAPPING_FILENAME)


def _normalize_signature(signature: str) -> Set[str]:
    variants = set()
    sig = signature.strip()
    if not sig:
        return variants
    variants.add(sig)

    if '-' in sig:
        suffix = sig.split('-', 1)[1]
        if suffix:
            variants.add(suffix)

    if sig.startswith('43-'):
        variants.add(sig[3:])

    if not sig.startswith('43-'):
        variants.add(f'43-{sig}')

    return {variant.strip() for variant in variants if variant.strip()}


def _load_signature_mapping() -> Dict[str, Set[str]]:
    mapping_path = _mapping_path()
    if not os.path.exists(mapping_path):
        return {}

    with open(mapping_path, 'r', encoding='utf-8') as handle:
        data = json.load(handle)

    signature_to_events: Dict[str, Set[str]] = {}

    for entry in data:
        event_id = entry.get('Event ID')
        signature_value = entry.get('Signature ID')

        if not signature_value or event_id in (None, ''):
            continue

        event_id_str = str(event_id).strip()
        if not event_id_str:
            continue

        raw_signatures = [part.strip() for part in str(signature_value).split(',') if part.strip()]

        for raw_signature in raw_signatures:
            for variant in _normalize_signature(raw_signature):
                signature_to_events.setdefault(variant, set()).add(event_id_str)

    return signature_to_events


def _load_event_metadata() -> Dict[str, Dict[str, Optional[str]]]:
    mapping_path = _mapping_path()
    if not os.path.exists(mapping_path):
        return {}

    with open(mapping_path, 'r', encoding='utf-8') as handle:
        data = json.load(handle)

    metadata: Dict[str, Dict[str, Optional[str]]] = {}

    for entry in data:
        event_id = entry.get('Event ID')
        if event_id in (None, ''):
            continue
        event_id_str = str(event_id).strip()
        metadata[event_id_str] = {
            'description': entry.get('Description'),
            'audit_policy': entry.get('Audit Policy')
        }

    return metadata


@lru_cache(maxsize=1)
def _cached_signature_mapping() -> Dict[str, Set[str]]:
    return _load_signature_mapping()


@lru_cache(maxsize=1)
def _cached_event_metadata() -> Dict[str, Dict[str, Optional[str]]]:
    return _load_event_metadata()


def get_event_ids_for_signature(signature_id: Optional[str]) -> List[str]:
    if signature_id is None:
        return []

    signature = str(signature_id).strip()
    if not signature:
        return []

    signature_map = _cached_signature_mapping()
    event_ids = signature_map.get(signature)

    if not event_ids and '|' in signature:
        signature = signature.split('|', 1)[1]
        event_ids = signature_map.get(signature)

    if not event_ids and '-' in signature:
        signature = signature.split('-', 1)[1]
        event_ids = signature_map.get(signature)

    if not event_ids:
        event_ids = signature_map.get(f'43-{signature}')

    if not event_ids:
        return []

    return sorted(event_ids)


def extract_event_ids_from_text(xml_text: Optional[str]) -> List[str]:
    if not xml_text:
        return []

    matches = set(re.findall(r'43-\d+', xml_text))
    event_ids: Set[str] = set()

    for signature in matches:
        event_ids.update(get_event_ids_for_signature(signature))

    return sorted(event_ids)


def merge_event_ids(parts: Iterable[Iterable[str]]) -> List[str]:
    combined: Set[str] = set()
    for part in parts:
        combined.update(part)
    return sorted(combined)


def collect_event_ids_from_values(values: Sequence[Optional[str]]) -> Set[str]:
    event_ids: Set[str] = set()

    for value in values:
        if value is None:
            continue

        text = str(value).strip()
        if not text:
            continue

        event_ids.update(extract_event_ids_from_text(text))

        for token in re.split(r'[|,\s]+', text):
            token = token.strip()
            if not token:
                continue
            event_ids.update(get_event_ids_for_signature(token))

    return event_ids


def get_rule_event_ids(rule) -> List[str]:
    if rule is None:
        return []

    event_ids = collect_event_ids_from_values([
        getattr(rule, 'sig_id', None),
        getattr(rule, 'rule_id', None),
        getattr(rule, 'description', None),
    ])

    event_ids.update(extract_event_ids_from_text(getattr(rule, 'xml_content', None)))

    return sorted(event_ids)


def get_alarm_event_ids(alarm, include_related_rules: bool = False) -> List[str]:
    if alarm is None:
        return []

    event_ids = collect_event_ids_from_values([
        getattr(alarm, 'match_value', None),
        getattr(alarm, 'match_field', None),
        getattr(alarm, 'note', None),
    ])

    event_ids.update(extract_event_ids_from_text(getattr(alarm, 'xml_content', None)))

    if include_related_rules:
        for rule in getattr(alarm, 'rules', []) or []:
            event_ids.update(get_rule_event_ids(rule))

    return sorted(event_ids)


def get_event_details(event_ids: Iterable[str]) -> List[Dict[str, Optional[str]]]:
    metadata = _cached_event_metadata()
    details = []

    for event_id in sorted({str(event_id).strip() for event_id in event_ids if str(event_id).strip()}):
        info = metadata.get(event_id, {})
        details.append({
            'id': event_id,
            'description': info.get('description'),
            'audit_policy': info.get('audit_policy')
        })

    return details
