"""
# Common Data Bus class: picks an available result and passes it to subscribers

CDB Interface:
|Sources| <--poll res_buf--  |Data Bus| -.read_cdb()--> |Subscribers|
|       |  --.deliver()--->  |        | <--.poll()----  |           |
Sources must implement .deliver() so bus can pull in data to dist.
Subscribers must implement .read_cdb() if they want automatic Delivery
Subscribers call cdb.poll() to get available data on the cycle it's pulled


Bus arbitration
- Bus polls each source each cycle to detect an idle->ready tx.
- If the tx is detected, the source is queued for delivery
- Ties are arbitrated by order of access

Delivery to bus
 - Bus calls source.deliver() to get the data out of the source results_buffer
 - .deliver() should also clear that entry from the output queue.

Pick up from bus
 - The bus hosts  a list of subscribers. Once a value hits the bus, the bus
  will call subscriber.read_cdb(dataType bus_data)
 - Whatever data tuple was read from the bus, cdb will post to the sub
 - Subs can also use cdb.poll() to get the current bus data values
    -- data lives on the line for 1 cycle
"""

# arbitrates the collection actions of the bus.
class Arbiter:
    def __init__(self, cdb_ref):
        self.output_q = []
        self.source_states = None
        self.cdb = cdb_ref

        if cdb_ref is None:
            raise TypeError("Arbiter was not given a reference to parent CBD")

        self.source_states = [0] * len(self.cdb.sources) # init ready state arr


    def reset(self):
        self.source_states = [0] * len(self.cdb.sources)


    def source_poll(self):
        # determines state change of source in result buffer
        for i in range(len(self.source_states)):
            ready_out = self.cdb.sources[i].results_buffer[0]

            if ready_out is not None and self.source_states[i] == 0:
                self.source_states[i] = 1
                self.output_q.append(i)


    def arbitrate(self):
        # returns the next in line for CDB service or None if no data should tx
        next_up = self.output_q[0]

        if next_up is not None:
            self.source_states[next_up] = 0

        self.output_q = self.output_q.pop(0)
        return next_up



# Common Data Bus for transfering results to registers
class CommonDataBus:
    def __init__(self, sources, subscribers):
        self.sources = sources # list of all FUs which feed the bus
        self.subscribers = subscribers # list of units reading the bus.
        self.bus_data = None   # Available data for bus subscribers
        self.arbiter = Arbiter(self)


    # standard heartbeat function
    def tick(self):
        self.arbiter.source_poll()
        target_fu = self.arbiter.arbitrate()

        if target_fu is not None:
            self.bus_data = self.sources[target_fu].deliver()

            for sub in self.subscribers:
                sub.read_cdb(bus_data)

        else:
            self.bus_data = None


    # pickup function for subscriber units to call for data
    #  data lives on line for 1 cycle. If nothing is available, output is none
    def poll(self):
        return self.bus_data


    # clears data on line. Doesn't clear sources by default
    def reset(self, src_kill=False):
        if src_kill:
            self.sources = []
        self.bus_data = None
        self.arbiter.reset()


    # defined as a standard command, but bus does not hold state data
    def rewind(self):
        self.reset()



# Debug class / script
class test_fu:
    def __init__(self, release, output):
        self.countdown = release
        self.reset = release
        self.output = output

    def deliver(self):
        if self.countdown == 0:
            self.countdown = self.reset
            return self.output
        self.countdown -= 1
        return None



if __name__ == "__main__":
    print("Testing data bus...")
    sources = [test_fu(1, ("F1", 15)),
               test_fu(2, ("T2", 23)),
               test_fu(4, ("F3", 38))]


    new_src = test_fu(3, ("T4", 46))

    my_bus = CommonDataBus(sources)
    my_bus.sources.append(new_src)

    cycles = 15
    for cyc in range(cycles):
        my_bus.tick()
        res = my_bus.poll()
        if res is None:
           print("[" + str(cyc) + "] No Data this cycle")
        else:
            res_t, res_v = res
            print("[" + str(cyc) + "] Data Output: Trgt: " + str(res_t) + " Val: "  +str(res_v))


""" very fast but sadly not first-come, first-served so can't use as arbtator
        # traverse loop once, stop at first hit
        for i in range(len(self.sources)):
            src_idx = (self.src_ptr + i) % len(self.sources)
            self.bus_data = self.sources[src_idx].deliver()

            if  self.bus_data is not None:
                self.scr_ptr = src_idx + 1
                return

        self.bus_data = None
"""
