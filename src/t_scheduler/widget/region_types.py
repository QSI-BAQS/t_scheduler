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
def region_init(region_type: RegionType, region_label=None):
    if region_label is None:
        # Autodetect from class __name__
        def _cls_init(cls):
            cls_name = cls.__name__
            region_types[region_type][cls_name] = cls
            return cls
        return _cls_init
    else:
        def _factory_init(fn):
            region_types[region_type][region_label] = fn
            return fn
        return _factory_init


