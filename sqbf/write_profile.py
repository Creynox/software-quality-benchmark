"""Load only audited write contracts; never an arbitrary scenario module path."""
from importlib import import_module

CONTRACTS = {'LAB-01-SINGLE-PRODUCT-v1': 'projects.ble-elva.tools'}
SUITE_CONTRACTS = {'ENZBERG-NSN014-UX-v1': 'projects.ble-elva.tools.regular_runner'}


def load_suite_profile(contract):
    if contract not in SUITE_CONTRACTS:
        raise ValueError('Unapproved suite adapter contract')
    return import_module(SUITE_CONTRACTS[contract])


def load_write_profile(contract, component):
    if contract not in CONTRACTS or component not in ('lab_guard','lab_runner','working_fixture'):
        raise ValueError('Unapproved write profile')
    return import_module(CONTRACTS[contract]+'.'+component)
