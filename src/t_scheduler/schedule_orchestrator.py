from collections import deque

from .strategy import BaseStrategy
from .widget import Widget
from .tracker import *
from .base import *
from .base.gate import RotateGate

class ScheduleOrchestrator:
    def __init__(
        self,
        gate_dag_roots,
        widget,
        strategy,
        debug: bool = False,
        tikz_output: bool = False,
        json: bool=False
    ):
        self.widget: Widget = widget
        self.strategy: BaseStrategy = strategy

        self.processed = set()

        self.waiting = deque(gate_dag_roots)
        self.queued = []

        self.active = deque()
        self.next_active = []

        self.output_layers = []

        self.curr_layer = []

        self.debug = debug

        self.ROTATION_DURATION = 3
        self.time = 0

        self.tikz_output = tikz_output
        self.json_output = json

        if self.tikz_output or self.json_output:
            self.output_objs = []
            self.widget.make_coordinate_adapter()
        
        if self.json_output:
            self.json = {'regions': self.widget.save_json_regions(), 
                         'layers': [], 
                         'width': self.widget.width, 
                         'height': self.widget.height,
                         'base_layer': self.widget.save_json_patches_state()}

        self.vol_tracker = SpaceTimeVolumeTracker(self)
        self.strategy.register_vol_tracker(self.vol_tracker) # type: ignore

    def save_tikz_frame(self):
        from lattice_surgery_draw.primitives.composers import TexFile
        with open(f"out/{self.time}.tex", "w") as f:
            output = TexFile(
                self.widget.save_tikz_frame(
                    self.widget.make_tikz_routes(self.output_layers[-1])
                )
            )
            print(output, file=f)

    def save_json(self):
        import json
        with open(f"out/json.out", 'w') as f:
            json.dump(self.json, f)

    def prewarm(self, num_cycles):
        print("prewarm", num_cycles)
        for _ in range(num_cycles):
            self.schedule_pass(prewarm=True)

    def schedule(self):
        print("schedule")
        self.queued.extend(self.waiting)

        while self.queued or self.active:
            self.schedule_pass()

        for row in self.strategy.register_router.region.sc_patches:
            for cell in row:
                cell: Patch
                if cell.patch_type == PatchType.REG and cell.reg_vol_tag is not None:
                    if cell.reg_vol_tag.duration is None:
                        cell.reg_vol_tag.end()
                    cell.reg_vol_tag.apply()

    def prepare_gs(self, gs_dag_roots, all_gs_gates=tuple(), time_limit=float('inf')):
        # Process our gate queue

        queue_backup = self.queued

        self.queued = gs_dag_roots

        while (self.queued or self.active) and self.time < time_limit:
            self.schedule_pass()
        
        if set(all_gs_gates).difference(self.processed):
            raise Exception(f"Graph state prep didn't finish in the time limit ({time_limit})")

        self.queued = queue_backup
        
        print("prepare done", self.time)

    def run_bell(self, bell_gates, time_limit=float('inf')):
        # Process our gate queue
        queue_backup = self.queued

        self.queued = bell_gates

        while (self.queued or self.active) and self.time < time_limit:
            self.schedule_pass()
        
        if set(bell_gates).difference(self.processed):
            raise Exception(f"Bell IO didn't finish in the time limit ({time_limit})")

        self.queued = queue_backup
        
        print("bell done", self.time)

    def schedule_pass(self, prewarm=False):
        if not prewarm:
            # Process our gate queue

            # self.queued.sort(key=lambda gate: gate.schedule_weight)

            next_queued = []
            for gate in self.queued:
                if gate in self.processed:
                    continue
                elif gate.available() and (active_gate := self.strategy.alloc_gate(gate)):
                    if not isinstance(active_gate, RotateGate):
                        # TODO don't check like this: ugly
                        active_gate.vol_tag = self.vol_tracker.make_tag(SpaceTimeVolumeType.ROUTING_VOLUME)
                        active_gate.vol_tag.start()

                    self.active.append(active_gate)
                    self.processed.add(active_gate)
                else:
                    next_queued.append(gate)

            self.queued = next_queued

        if self.strategy.needs_upkeep:
            self.active.extend(self.strategy.upkeep())

        # Print widget board state
        if self.debug:
            print(self.widget.to_str_output_dedup(), end="")

        self.output_layers.append([])
        for gate in self.active:
            self.output_layers[-1].append(gate.transaction.active_cells)

        if self.tikz_output:
            from lattice_surgery_draw.primitives.composers import TexFile

            with open(f"out/{self.time}.tex", "w") as f:
                output = TexFile(
                    self.widget.save_tikz_frame(
                        self.widget.make_tikz_routes(self.output_layers[-1])
                    )
                )
                print(output, file=f)

            # from lattice_surgery_draw.tikz_layer import TikzLayers
            # print('\\begin{tikzpicture}[scale=0.5]', file=file)
            # print(''.join(map(str,
            #                   self.widget.save_tikz_region_layer() + self.widget.save_tikz_patches_layer())), file=file)
            # print('\\end{tikzpicture}\n\\newpage', file=file)
            # file.close()

        if self.json_output:
            self.json['layers'].append(self.widget.save_json_patches_state())

        for gate in self.active:
            gate.tick()

        self.widget.update()

        for gate in self.active:
            gate.cleanup(self)

        for gate in self.active:
            gate.next(self)
            if not gate.completed():
                self.next_active.append(gate)
            else:
                for child in gate.post:
                    if all(g.completed() for g in child.pre):
                        if self.debug:
                            print("queuing", child)
                        self.queued.append(child)
                if gate.vol_tag:
                    gate.vol_tag.apply(space = gate.transaction.route_count())

        # print(self.time, self.active)

        self.active = self.next_active
        self.next_active = deque()
        self.time += 1

    def get_space_time_volume(self):
        # volume = 0
        # for layer in self.output_layers:
        #     for gate_cells in layer:
        #         volume += len(gate_cells)
        # return volume
        return {
            tag_type.name: value
            for tag_type, value in 
            self.vol_tracker.duration.items()
        }

    def get_T_stats(self):
        return self.vol_tracker.t_usage

    def get_total_cycles(self) -> int:
        return self.time

    def json_debug(self):
        import json
        with open(f"../t_sched_vis/debug.json", 'w') as f:
            json.dump(self.json, f)
        from t_scheduler.debug import main
        main()
