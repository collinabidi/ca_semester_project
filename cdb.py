"""
# Common Data Bus class: picks an available result and passes it to subscribers

CDB Interface:
|Sources| <--poll req--  |Data Bus| ---data---> |Subscribers|
|       |  ----data----> |        |             |           |
Sources must implement .arbitrate() so bus can ask how many cycles data has waited
Sources must implement .deliver() so bus can pull in data to dist.
Subscribers must call cdb.poll() to get available data on the cycle it's pulled


Bus arbitration
- Bus polls each source for how long it's been ready (.arbitrate())
  -- return 0 indicates nothing is Ready
  -- return 1+ indicates num cycles waiting (so increment each cycle)

- Once polled, bus claims highest weight available data (.deliver())
  -- return None is called at wrong time
  -- return data for bus as tuple (or other agreed on obj)
  -- calling this func should zero out .arbitrate() counter for the source
"""

class CommonDataBus:
    def __init__(self, sources):
        self.sources = sources # list of all FUs which feed the bus
        self.bus_data = None   # Available data for bus subscribers


    # standard heartbeat function
    def tick(self):
        first_come = 0
        longest_time = 0

        for i in range(0, len(self.sources)):
            wait_time = self.source[i].arbitrate()
            if wait_time > longest_time:
                first_come = i
                longest_time = wait_time

        if longest_time != 0:
            self.bus_data = self.sources[first_come].deliver()
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
