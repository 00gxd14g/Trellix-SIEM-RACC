import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from utils.signature_mapping import get_event_ids_for_signature, _load_signature_mapping

print("Loading mapping...")
mapping = _load_signature_mapping()
print(f"Mapping size: {len(mapping)}")

test_sigs = ['6000114', '43-6000114', '47|6000114']
for sig in test_sigs:
    ids = get_event_ids_for_signature(sig)
    print(f"Sig '{sig}' -> Event IDs: {ids}")
