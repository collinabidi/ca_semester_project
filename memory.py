# Memory Element classes
# ========================

"""
    Load Store Queue
     - mem_size: number of bytes in memory (cooperates with arg wl=4 [word_len])
     - queue_len: number of stations available in memory load/store queue
     - cyc_in_mem: how long it takes to get a response from memory
        -- implemented as "countdown" on the visualization
    - rob: reference to the reorder buffer objects
    - config=None: Memory Initialization configuration

    The LSQ expects:
    - The ROB to have .request(register) so that it can poll for avialable data
    - The ROB to call lsq.mem_comitt(register) so that it can detect a commit
        relevant to a store operation

    The LSQ implements:
    - .deliver()/result_buffer[] so it may be a source

    Core Memory Block
    - Block is parameterizable in the following ways:
    - size_bytes: Size of the member available in bytes, total bytes avialable to store
    - word_len=4: Length of the word. Though the actual array doesn't care, the class
        forces effective addresses to align to a word length

    - Number of elements available is size_bytes / word_len
    - Class cannot init if size_bytes % word_len != 0
    - To think in terms of elements, not bytes, set word_len = 1.
"""
from functional_units import *


class LoadStoreQueue:
    def __init__(self, mem_size, queue_len, cycles_in_mem, rob, CDBe, verbose=False, config=None, wl=4):
        # hardware params
        self.verbose = verbose
        self.num_stats_free = int(queue_len)
        self.queue_sz = int(queue_len)
        self.cycles_in_mem = int(cycles_in_mem)
        #sub-component params
        self.queue_stations = [] * int(queue_len)
        self.result_buffer = []
        self.rb_history = []
        self.lsq_history = []
        self.CDBe = int(CDBe)
        self.mem_unit = Memory(int(mem_size), word_len=wl, mem_config=config, verbose=verbose)
        #component ref params
        self.reorder_buffer = rob


    def issue(self, instr):
        if self.num_stats_free == 0:
            return Warning("Warning! Queue is unable to accept instruction.")

        # create new queue entry with default value
        enqueue = {"op":instr.op, "qrs":instr.rs, "qrt":instr.rt, \
                   "vrs":None, "vrt":None, "imm":instr.addr_imm, \
                   "countdown":self.cycles_in_mem, "commit":commit_check(instr)}

        enqueue["vrs"] = self.reorder_buffer.request(enqueue["qrs"])
        enqueue["vrt"] = self.reorder_buffer.request(enqueue["qrt"])

        self.num_stats_free -= 1
        self.queue_stations.append(enqueue)


    # standard heartbeat operation
    def tick(self):
        if self.num_stats_free == self.queue_sz:
            # if nothing is queue'd, nothing to do.
            return

        queue_leader = self.queue_stations[0]
        if lsq_entry_ready(queue_leader) and(len(self.result_buffer) < self.CDBe):
            # register is ready to go to mem. & not waiting to tender a result
            queue_leader["countdown"] -= 1
            if (queue_leader["countdown"]) == 0:
                # calc effective addres
                eff_addr = queue_leader["vrt"] + int(queue_leader["imm"])
                # act on memory
                res = self.mem_unit.access(queue_leader["op"], eff_addr, queue_leader["vrs"])

                # ready output for system if "Ld"
                if queue_leader["op"] == "Ld":
                    queue_leader["vrs"] = res
                    result = {"op":"Ld", "pc":None,
                              "dest":queue_leader["qrs"], "value":res}
                    self.result_buffer.append(result)

                # dequeue the operation
                self.num_stats_free += 1
                self.queue_stations.pop(0)


    def deliver(self):
        return self.result_buffer.pop(0)


    # THIS NEEDS TO BE CALLED BY THE ROB WHEN IT COMMITS A VALUE
    #   If the value was tied to a store operation, that operation will dequeue
    def mem_commit(self, rob_loc):
        for stat in self.queue_stations:
            if stat["op"] == "Sd":
                if rob_loc == stat["qrs"]:
                    stat["commit"] = True


    def read_cdb(self, bus_data):
        if bus_data is None:
            return

        for lsq_entry in self.queue_stations:
            if lsq_entry["qrs"] == bus_data["dest"]:
                lsq_entry["vrs"] = bus_data["value"]

            if lsq_entry["qrt"] == bus_data["dest"]:
                lsq_entry["vrt"] = bus_data["value"]


    # clear held values
    def reset(self, mem_reset=False):
        self.queue_stations = []
        self.result_buffer = []
        if mem_reset:
            self.mem_unit.reset()

    def save_state(self):
        self.rb_history = self.result_buffer.copy()
        self.lsq_histroy = self.queue_stations.copy()

    # branch prediction rollback
    def rewind(self):
        return


    def __str__(self):
        out_str= "======================== Load/Store Queue [Size: "+str(self.queue_sz)+"] =========================\n"
        out_str+="  Op |  q_rs  |  q_rt  |  v_rs  |  v_rt  | Str.Commit | Countdown | Immediate\n"
        out_str+="-----------------------------------------------------------------------------\n"

        for stat in self.queue_stations:
            out_str += " " + stat["op"] + "  |  " + stat["qrs"] + "  |  " + \
                       stat["qrt"] + "  |  " + str(stat["vrs"]) + "  |  " +  \
                       str(stat["vrt"]) + "  |   " + str(stat["commit"]) +  \
                       "    |     " + str(stat["countdown"]) + "     |   " + \
                       str(stat["imm"]) + "\n"

        out_str += "-----------------------------------------------------------------------------\n"
        out_str += "Results Buffer: {}".format(self.result_buffer)
        return out_str



# stand alone rule about store commit rules
def commit_check(register):
    # we only avoid default commit if we are waiting on the action from the ROB
    if register.op == "Ld":
        return True
    if "ROB" in register.rs:
        return False
    return True


# stand alone rule about LSQ entry readiness
def lsq_entry_ready(entry):
    if entry["op"] == "Ld":
        if entry["vrt"] is not None and entry["commit"] is True:
            return True
        return False

    elif entry["op"] == "Sd":
        if entry["vrs"] is not None and entry["vrt"] is not None and entry["commit"] is True:
            return True
        return False

    return False



# Memory management class
class Memory:
    def __init__(self, size_bytes, word_len=4, mem_config=None, verbose=False):
        self.mem_sz = size_bytes
        self.word_len = word_len
        self.memory = []
        self.verbose = verbose

        if size_bytes % word_len != 0:
            raise SegFaultException(" On Initialization: Byte size of mem: " + \
                      str(self.mem_sz) + " is not a mulitple of the word length: " +\
                      str(word_len))

        self.init_mem(mem_config)


    # force initialize values into the memory block
    def init_mem(self, mem_arr):
        if mem_arr is None:
            self.memory = [0x0] * int(self.mem_sz / self.word_len)
            if self.verbose:
                print("[MEMRY]: Init'd clean memory. # Words: " + str(len(self.memory)))

        else:
            #print("with config")
            if len(mem_arr) != (self.mem_sz * self.word_len):
                self.mem_sz = len(mem_arr) * self.word_len
                if self.verbose:
                    print("[MEMRY]: Inputted Mem config did not expected size. " +\
                          "Size Param changed.")
            self.memory = mem_arr



    # completely async., completes function as called, at call.
    def access(self, io, byte_addr, value):
        # VALIDITY CHECKS
        if(byte_addr % self.word_len) != 0: # word alignment check
            raise SegFaultException(" Misaligned target addr [" + hex(byte_addr) + \
                                    "] fails mem. word size: " + str(self.word_len))

        if byte_addr > (self.mem_sz - 1) or byte_addr < 0:  # Bounds check
            raise SegFaultException(" Out-of-Bounds Address: "+str(byte_addr)+ \
                                    "  is not [0: " + str(self.mem_sz-1) + "]")

        # ARRAY ACCESSES
        if io == "Ld":
            if self.verbose:
                print("[MEMRY]: Accessed Load at EFF ADDR" + hex(byte_addr))
            return self.memory[int(byte_addr / self.word_len)]

        elif io == "Sd":
            if self.verbose:
                print("[MEMRY]: Storing value {} at {}", str(value), hex(byte_addr))
            self.memory[int(byte_addr / self.word_len)] = value

        return None


    # clears memory to zeros
    def reset(self):
        self.init_mem(None)


    # prints current contents of memory
    def __str__(self):
        output = "===Current Memory Configuration===\n"
        for idex in range(len(self.memory)):
            if self.memory[idex] != 0:
                addr = idex * self.word_len
                output += "MEM[" + str(addr) + "]="+str(self.memory[idex])+"\t"
        output += "================================="
        return output

""" Prints out the full memory unit contents
    def __str__(self, width=4):
        item_sz = int(self.mem_sz / self.word_len)
        mod_blck = item_sz - (item_sz % width)
        remainder = item_sz % width

        output = "===Current Memory Configuration==="
        title_line = "\nOffset>"
        for i in range(width):
            title_line += "\t" + hex(i*self.word_len)
        output += title_line + "\n"

        for i in range(0, mod_blck, width):
            mem_line = hex(i*self.word_len)
            for j in range(width):
                mem_line += "\t" + str(self.memory[i+j])
            output += mem_line + "\n"

        rem_mem_line = hex(mod_blck*self.word_len)
        for i in range(remainder):
            rem_mem_line += "\t" + str(self.memory[mod_blck+i])
        if remainder != 0:
            output += rem_mem_line + "\n"
        return output
"""



class SegFaultException(Exception):
    """ Raised when bad memory ops occur"""
    def __init__(self, message):
        super().__init__("Seg fault, core dumped:" + message)

# =============================================================================
#  Dummy units to test functionalities
class test_rob:
    def __init__(self, mem_ref):
        self.cycle = -1
        self.lsq = mem_ref


    def request(self, register):
        rob_reg = {"ROB1": None, "ROB2":4, "ROB3":None, "ROB4":None}
        return rob_reg[register]

    def tick(self):
        self.cycle += 1
        if self.cycle % 4 == 0:
            self.lsq.mem_commit("ROB1")
        else:
            self.lsq.mem_commit(None)


class test_cdb:
    def __init__(self, sub):
        self.sub = sub
        self.cycles = 0

    def tick(self):
        self.cycles += 1
        cdb_data = [None, {"dest":"ROB1", "value":13}, {"dest":"ROB3", "value":59}]
        self.sub.read_cdb(cdb_data[self.cycles % 3])


if __name__ == "__main__":
    print("Testing memory instructions")

    inst = [{"op":"Sd", "rs":"ROB1", "rt":"ROB2", "imm":"0"},
    {"op":"Ld", "rs":"ROB3", "rt":"ROB2", "imm":"0"},
    {"op":"Sd", "rs":"ROB4", "rt":"ROB2", "imm":"0"}]

    ld_str_q = LoadStoreQueue(26, 3, 4, None, wl=2) #bytes, queue, cyles
    cdb = test_cdb(ld_str_q)
    rob = test_rob(ld_str_q)
    ld_str_q.reorder_buffer = rob
    #print(ld_str_q)
    #print(ld_str_q.mem_unit)

    print("************************************")

    ld_str_q.issue(inst[0])
    ld_str_q.issue(inst[1])
    ld_str_q.issue(inst[2])
    print(ld_str_q)


    ld_str_q.tick()
    cdb.tick()
    rob.tick()

    ld_str_q.tick()
    ld_str_q.tick()
    ld_str_q.tick()
    print(ld_str_q)

    cdb.tick()
    cdb.tick()
    print(ld_str_q)

    ld_str_q.tick()
    print(ld_str_q)
    print(ld_str_q.mem_unit)

    ld_str_q.tick()
    ld_str_q.tick()
    ld_str_q.tick()
    ld_str_q.tick()
    print(ld_str_q)
    ld_str_q.deliver()
    print(ld_str_q)
