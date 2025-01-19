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

# Class decorator for injecting into the region 
# type table
def export_region(region_type: RegionType, region_label=None):
    if region_label is None:
        # Autodetect from obj __qualname__
        def _init(obj):
            name = obj.__qualname__
            region_types[region_type][name] = obj
            return obj
        return _init
    else:
        def _init(obj):
            region_types[region_type][region_label] = obj
            return obj
        return _init


