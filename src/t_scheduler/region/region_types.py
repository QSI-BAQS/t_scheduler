from typing import Literal


RegionType = str

BUS_REGION = 'Bus'
REGISTER_REGION = 'Register'
FACTORY_REGION = 'Factory' 
BUFFER_REGION = 'Buffer'
BELL_REGION = 'Bell'

region_types = {
    BUS_REGION: {},
    REGISTER_REGION: {},
    FACTORY_REGION: {},
    BUFFER_REGION: {},
    BELL_REGION: {}
}

region_args = {}


def export_option(cls):
    obj = {}
    obj['default'] = cls.get_default()
    obj['option_type'] = 'option'
    obj['options'] = list(set(cls)) # type: ignore
    obj['name'] = cls.get_name()

# Class decorator for injecting into the region 
# type table
def export_region(region_type: RegionType, region_label=None, args=tuple()):
    if region_label is None:
        # Autodetect from obj __qualname__
        def _init(obj):
            name = obj.__qualname__
            region_types[region_type][name] = obj
            return obj
    else:
        def _init(obj):
            region_types[region_type][region_label] = obj
            return obj

    region_args[region_label] = [export_option(a) for a in args]

    return _init

