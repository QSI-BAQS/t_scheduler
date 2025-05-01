from enum import Enum
from typing import Dict

class TSourceTrackingTag:
    '''
        Tags and tracks the source of a T state
        Used to check if a factory contributes to the spac-time volume
        : tracker : Resource state tracker 
        : source : source object
    '''
    def __init__(self, tracker, source: str):
        self.source = source
        self.tracker = tracker
    
    def apply(self):
        '''
            Applies the T state to the computation
            Wipes the source and triggers an update on the tracker to increase the t usage for this source     
        '''
        self.tracker.t_usage[self.source] = self.tracker.t_usage.get(self.source, 0) + 1
        self.source = None

    def copy(self):
        '''
            Copy constructor
        '''
        return TSourceTrackingTag(self.tracker, self.source)

class SpaceTimeVolumeTrackingContext(list):
    '''
        Context tracker for space-time volume
        Tracks sources, factories and   
    '''
    def __init__(self, tracker):
        self.tracker = tracker
        self.factory_tag: TFactorySpaceTimeVolumeTrackingTag | None = None
        self.source_tag: TSourceTrackingTag | None = None
        self.curr_active = None
        self.applied = False

    def transition(self, new_tag):
        if self.curr_active is not None:
            self.curr_active.end(offset=1)
            self.append(self.curr_active)
        self.curr_active = new_tag

    def apply(self):
        assert not self.applied
        self.applied = True
        if self.factory_tag is not None:
            self.factory_tag.apply()
        self.factory_tag = None
        # print("apply", id(self))
        # print("source", self.source_tag.source)
        self.source_tag.apply()
        while self:
            tag = self.pop()
            tag.apply()

    def shallow_copy(self):
        ctx = SpaceTimeVolumeTrackingContext(self.tracker)
        # print("create in shallow_copy:", id(self), '->', id(ctx))
        ctx.factory_tag = self.factory_tag
        ctx.source_tag = self.source_tag.copy()
        return ctx

class SpaceTimeVolumeType(Enum):
    REGISTER_VOLUME = 0
    FACTORY_VOLUME = 1
    ROUTING_VOLUME = 2
    T_IDLE_VOLUME = 3
    BELL_IDLE_VOLUME = 4
    BELL_ROUTING_VOLUME = 5

class SpaceTimeVolumeTrackingTag:
    def __init__(self, timer_source, tracker, tag_type, mult=1):
        self.timer_source = timer_source
        self.start_time = None
        self.tracker = tracker
        self.tag_type = tag_type
        self.duration = None
        self.mult = mult

    def start(self, debug=None, offset=0):
        assert self.start_time is None
        self.start_time = self.timer_source.time + offset
        self.debug = debug

    def end(self, offset = 0):
        assert self.start_time is not None
        self.duration = (self.timer_source.time - self.start_time + offset) * self.mult
        if self.debug:
            print("ended with", self.duration)
    
    def apply(self, space = 1):
        assert self.duration is not None
        self.tracker.track(self.tag_type, self.duration * space)
        if self.debug:
            print("adding:", self.tag_type, self.duration, "start", self.start_time)


    def copy(self):
        tag = SpaceTimeVolumeTrackingTag(self.timer_source, self.tracker, self.tag_type, mult=self.mult)
        tag.start_time = self.start_time
        tag.debug = self.debug
        return tag

class TFactorySpaceTimeVolumeTrackingTag:
    def __init__(self, tracker, factory = None):
        if factory is not None:
            self.duration = factory.n_cycles * factory.height * factory.width
        else:
            self.duration = 0
        self.tracker = tracker

    def apply(self):
        self.tracker.track(SpaceTimeVolumeType.FACTORY_VOLUME, self.duration)
        self.duration = 0

class SpaceTimeVolumeTracker:
    def __init__(self, timer_source):
        self.timer_source = timer_source
        self.total_volume = 0
        self.duration = {
            tag_type: 0 for tag_type in SpaceTimeVolumeType
        }

        self.t_usage: Dict[str, int] = {}

    def make_tag(self, tag_type: SpaceTimeVolumeType, mult=1):
        return SpaceTimeVolumeTrackingTag(self.timer_source, self, tag_type, mult=mult)

    def track(self, tag_type, duration):
        self.duration[tag_type] += duration
    
    def dump_duration_state(self):
        return self.duration.copy()
