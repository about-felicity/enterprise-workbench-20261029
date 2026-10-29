import hashlib
import json
import re
from pathlib import Path

from ..runtime import atomic_json
from ..staged_editorial import read
from . import VERSION


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def text_hash(text):
    return hashlib.sha256(text.encode("utf8")).hexdigest()


def prompt_material(material):
    """Factor repeated import metadata; preserve every fact and original field."""
    product = dict(material['raw_product'])
    facts = product.get('facts')
    if (isinstance(facts, list) and len(facts) > 1 and all(isinstance(f, dict) for f in facts)
            and 'fact_defaults' not in product):
        shared = {k: v for k, v in facts[0].items() if k != 'text'
                  and all(k in f and f[k] == v for f in facts[1:])}
        if shared:
            product['fact_defaults'] = shared
            product['facts'] = [{k: v for k, v in f.items() if k not in shared} for f in facts]
    return {'raw_product': product, 'layers': material['layers'], 'usage_rules': material['usage_rules']}


def evidence_product(material):
    """Send full original text once; keep any facts not literally present there."""
    product = prompt_material(material)['raw_product']
    source = product.get('raw_source_text')
    if not isinstance(source, str) or not source.strip(): return product
    norm = lambda s: re.sub(r'\s+', '', s)
    original = norm(source)
    if isinstance(product.get('facts'), list):
        product = dict(product)
        product['facts'] = [f for f in product['facts']
            if not isinstance(f, dict) or not isinstance(f.get('text'), str) or not norm(f['text']) or norm(f['text']) not in original]
        if not product['facts']: product.pop('fact_defaults', None)
    return product


def bounded_output(client, prompt, directory, meta, *, stage, system_prompt, preferred, minimum):
    directory = Path(directory)
    if (directory / 'api_state.json').exists(): return read(directory / 'request.json')['max_tokens']
    remaining = getattr(getattr(client, 'budget', None), 'remaining', None)
    available = remaining(meta, stage) if callable(remaining) else None
    if not isinstance(available, (float, int)): return preferred
    from ..deepseek_api import request_payload
    from ..api_budget import INPUT_MISS, OUTPUT
    size = len(json.dumps(request_payload(prompt, 0, system_prompt)['messages'], ensure_ascii=False).encode('utf8')) + 256
    affordable = int((available-size*INPUT_MISS/1000000-.000001)*1000000/OUTPUT)
    maximum = max(minimum, min(preferred, affordable))
    atomic_json(directory/'output_budget_plan.json', {'remaining_cny':available,'input_byte_bound':size,
        'max_tokens':maximum,'minimum_complete_output_tokens':minimum,'ledger_reservation_still_required':True})
    return maximum


def strings(value, name, *, required=False):
    if not isinstance(value, list) or any(not isinstance(s, str) or not s.strip() for s in value):
        raise ValueError("Invalid " + name)
    if required and not value:
        raise ValueError("Missing " + name)
    return value


def enabled(job):
    return job.get("meta", {}).get("workflow") == VERSION


def cache_root(root):
    root = Path(root)
    config = read(root / "rewrite_policy.json") if (root / "rewrite_policy.json").exists() else {}
    return Path(config.get("cache_dir") or root / "rewrite_cache")


def request(client, prompt, directory, *, stage, meta, temperature, maximum, system_prompt=None):
    # DeepSeekClient owns the durable send intent, budget reservation and response.
    # No transport retry or alternate request identity is introduced here.
    result = client.complete(prompt, directory, stage=stage,
                             meta={**meta, "cost_scope": "article"},
                             temperature=temperature, max_tokens=maximum,
                             **({'system_prompt': system_prompt} if system_prompt is not None else {}))
    # The provider sometimes echoes response_format as a top-level metadata
    # field. Preserve the paid raw response; remove only this exact marker,
    # then let the stage's strict schema validate every remaining field.
    if isinstance(result, dict) and result.get("type") == "json_object":
        atomic_json(Path(directory) / "format_projection.json", {
            "reason": "redundant_response_format_marker", "raw_response_sha256": digest(result),
            "removed": {"type": "json_object"}, "new_paid_requests": 0})
        return {k: v for k, v in result.items() if k != "type"}
    return result


def seal(value):
    result = {k: v for k, v in value.items() if k != "sha256"}
    return {**result, "sha256": digest(result)}


def verify(value):
    if not isinstance(value, dict) or value.get("sha256") != digest({k: v for k, v in value.items() if k != "sha256"}):
        raise ValueError("Rewrite artifact changed or incomplete")
    return value
