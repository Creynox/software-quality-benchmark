"""Load only audited write contracts; never an arbitrary scenario module path."""
from importlib import import_module

CONTRACTS = {'LAB-01-SINGLE-PRODUCT-v1': 'projects.ble-elva.tools'}


def load_write_profile(contract, component):
    if contract not in CONTRACTS or component not in ('lab_guard','lab_runner','working_fixture'):
        raise ValueError('Unapproved write profile')
    return import_module(CONTRACTS[contract]+'.'+component)
