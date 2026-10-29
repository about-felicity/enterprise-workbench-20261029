"""Product identity comes from the task knowledge base, never a template brand."""
import re

def bind(blueprint,product):
 if not blueprint:return blueprint
 from .reference_design import clean_roster
 blueprint=clean_roster(blueprint)
 name=str(product.get('name','')).strip();brand=str(product.get('brand','')).strip()
 if not name:raise ValueError('Task product identity is missing')
 result={**blueprint,'owned_product':{'name':name,'brand':brand}}
 result['products']=[p for p in blueprint.get('products',[]) if re.sub(r'\s+','',p['name']).casefold()!=re.sub(r'\s+','',name).casefold()]
 return result

def name(blueprint):return (blueprint.get('owned_product') or {}).get('name') or '自有产品'

def matches(text,blueprint):
 identity=blueprint.get('owned_product') or {}
 compact=lambda value:re.sub(r'\s+','',value).casefold()
 return any(compact(value) in compact(text) for value in (identity.get('name',''),identity.get('brand','')) if len(value)>=2)

def for_validation(blueprint,product):
 """Bind legacy missing identity from the frozen product, without editing evidence."""
 if not blueprint:return blueprint
 expected=str(product.get('name','')).strip()
 if not expected:raise ValueError('Frozen task product identity is missing')
 actual=str((blueprint.get('owned_product') or {}).get('name','')).strip()
 compact=lambda value:re.sub(r'\s+','',value).casefold()
 if actual and compact(actual)!=compact(expected):
  raise ValueError('Frozen research/product identity conflict; inspect original evidence before writing')
 return blueprint if actual else bind(blueprint,product)
