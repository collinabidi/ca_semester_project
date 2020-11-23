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
    def __init__(self, mem_size, queue_len, cyc_in_mem, cyc_in_exe, rob, CDBe, verbose=False, config=None, wl=4):
        # hardware params
        self.verbose = verbose
        self.num_stats_free = int(queue_len)
        self.queue_sz = int(queue_len)
        self.cycles_in_mem = int(cyc_in_mem)
        self.cycles_in_exe = int(cyc_in_exe)
        self.CDBe = int(CDBe)
        #sub-component params
        self.queue_stations = [] * int(queue_len)
        self.result_buffer = []
        self.rb_history = []
        self.lsq_history = []
        self.mem_unit = Memory(int(mem_size), word_len=wl, mem_config=config, verbose=verbose)
        self.mem_alu = {"target":None, "busy":False,"countdown":None}
        #component ref params
        self.reorder_buffer = rob


    def issue(self, instr):
        if self.num_stats_free == 0:
            return Warning("Warning! Queue is unable to accept instruction.")

        # create new queue entry with default value
        enqueue = {"op":instr.op, "qrs":instr.rs, "qrt":instr.rt, \
                   "vrs":None, "vrt":None, "imm":int(instr.addr_imm), \
                   "countdown":self.cycles_in_mem, "commit":commit_check(instr), \
                   "eff_addr": None, "pc":instr.pc}

        enqueue["vrs"] = self.reorder_buffer.request(enqueue["qrs"])
        enqueue["vrt"] = self.reorder_buffer.request(enqueue["qrt"])

        self.num_stats_free -= 1
        self.queue_stations.append(enqueue)


    # standard heartbeat operation
    def tick(self, tracker):
        if self.num_stats_free == self.queue_sz:
            # if nothing is queue'd, nothing to do.
            return

        self.__exe_stage__(tracker)  # memory has its own exe stage for eff_addr
        self.__mem_stage__(tracker)


    def __exe_stage__(self, tracker):
        if self.mem_alu["busy"] and (self.mem_alu["countdown"] -= 1) == 0:
            q_target = self.queue_stations[self.mem_alu["target"]]
            q_target["eff_addr"] = q_target["vrt"] + int(q_target["imm"])
            self.mem_alu["busy"] = False
            self.mem_alu["target"] = None

        else:
            for i in range(len(self.queue_stations)):
                # find first entry w/o eff_addr and set up adder to work
                if self.queue_stations["vrt"] is not None:
                    self.mem_alu["target"] = i
                    self.mem_alu["countdown"] = self.cyc_in_exe
                    self.mem_alu["busy"] = True
                    tracker.update("execute", self.queue_stations["target"])
                    return


    def __mem_stage__(self, tracker):
        # value-forwarding operations
        trgt_addr = 0
        fwd_val = 0
             # performs all forwarding and sets countdowns accordingly
        for i in range(len(self.queue_stations)):
            s_instr = self.queue_stations[i]
            if entry_str_fwd_ready(s_instr): # look for each ready Sd
                trgt_addr = s_instr["eff_addr"]
                fwd_val = s_instr["vrt"]

                for j in range(i, len(self.queue_stations)):  # look for following Lds
                    l_instr = self.queue_stations[j]
                    if entry_ld_fwd_ready(l_instr, trgt_addr):
                        l_instr["vrt"] = fwd_val
                        l_instr["countdown"] = 1

        # memory operations
        data_fwd_idex = self.queue_sz + 1
            # direct operations
        queue_leader = self.queue_stations[0]
        if lsq_entry_ready(queue_leader):
            if queue_leader["countdown"] == 0:  # queue leader is ready to access mem

                if queue_leader["op"] == "Ld":
                    if len(self.result_buffer) < self.CDBe:  # there is space in the results buffer
                        res = self.mem_unit.access("Ld", queue_leader["eff_addr"], None)
                        ld_res = {"op":"Ld", "pc":queue_leader["pc"], \
                                  "dest":queue_leader["qrs"], "value":res}
                        self.result_buffer.append(ld_res)
                        self.queue_stations.pop(0)
                        self.num_stats_free += 1
                        data_fwd_idex = 0
                else:
                    self.mem_unit.access("Sd", queue_leader["eff_addr"], queue_leader["vrs"])
                    self.queue_stations.pop(0)
                    self.num_stats_free += 1
                    self.__reposition_alu_ptr__(0) # its possible to do a store and load-fwd on the same cycle
                    tracker.update("commit", queue_leader) # memory is also commit for Sd

            elif queue_leader["countdown"] == self.cycles_in_mem: # queue leader is ready to start mem stage
                tracker.update("memory", queue_leader)
                queue_leader["countdown"] -= 1
            else:                               # queue leader is in memory stage
                queue_leader["countdown"] -= 1

        # load-forwarding operations
        for i in range(len(self.queue_stations)):
            if lsq_fwd_ready(self.queue_stations[i]):
                if self.queue_stations[i]["countdown"] == 0
                    if data_fwd_idex == (self.queue_sz+1) and len(self.result_buffer) < self.CDBe:
                         # we can only forward one value at a time and there must be room in buffer
                        ld_res = {"op":"Ld", "pc":self.queue_stations[i]["pc"],\
                                  "dest":self.queue_stations[i]["qrs"], \
                                  "value":self.queue_stations[i]["vrs"]}
                        self.result_buffer.append(ld_res)
                        self.queue_stations.pop(i)
                        self.num_stats_free += 1
                        data_fwd_idex = i
                else:   # perform the 1 cycle coundown right away but only 1 load can fwd per cycle
                    self.queue_stations[i]["countdown"] -= 1
                    tracker.update("memory", self.queue_stations[i]) # start mem stage

        self.__reposition_alu_ptr__(data_fwd_idex)


    def deliver(self):
        return self.result_buffer.pop(0)


    def mem_commit(self, rob_loc):
        for stat in self.queue_stations:
            if stat["op"] == "Sd":
                if rob_loc == stat["qrs"]:
                    stat["commit"] = True


    def read_cdb(self, bus_data, tracker=None):
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
        self.rb_history = None
        self.lsq_history = None
        self.mem_alu = {"target":None, "busy":False,"countdown":None}
        if mem_reset:
            self.mem_unit.reset()

    # branch prediction state save
    def save_state(self):
        self.rb_history = self.result_buffer.copy()
        self.lsq_histroy = self.queue_stations.copy()

    # branch prediction rollback
    def rewind(self):
        rb_restore = self.rb_history.copy()
        lsq_restore = self.lsq_history.copy()
        self.reset()
        self.queue_stations = lsq_restore
        self.result_buffer = rb_restore

    # keeps alu operating on the right element of the queue
    def __reposition_alu_ptr__(self, popped_idex):
        if popped_idex < self.mem_alu["target"]:
            self.mem_alu["target"] -= 1


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


# =====================RULES FOR CHECKING QUEUE ENTRY STATUS====================
# stand alone rule about commit readiness
def commit_check(register):
    # we only avoid default commit if we are waiting on the action from the ROB
    # return not (register.op == "Sd" and ("ROB" in register.rs))
    if register.op == "Ld":
        return True
    if "ROB" in register.rs:
        return False
    return True


# stand alone rule about LSQ entry readiness for head of queue
def lsq_entry_ready(entry):
    if entry["op"] == "Ld":
        # if load made it front of queue, it's going to go to mem.
        return entry["eff_addr"] is not None and entry["commit"] is True

    elif entry["op"] == "Sd":
        # we can go to mem once we have a value, an address, and permission to commit
        return entry["vrs"] is not None and entry["eff_addr"] is not None and entry["commit"] is True

    return False


# stand alone rule about LSQ entry forward-readiness
def lsq_fwd_ready(entry):
    if entry["op"] == "Sd":
        # never forward a store instruction out of queue
        return False
    # if the address and the value are in the station, action was forwarded, instr can leave queue
    return entry["eff_addr"] is not None and entry["vrs"] is not None


def entry_str_fwd_ready(entry):
    return entry["op"] == "Sd" and entry["vrt"] is not None and entry["eff_addr"] is not None


def entry_ld_fwd_ready(entry, ref_addr):
    return entry["op"] == "Ld" and entry["eff_addr"] == ref_addr and entry["vrt"] is None
# =============================================================================



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
            if len(mem_arr) != (self.mem_sz / self.word_len):
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
                print("[MEMRY]: Accessed Load at EFF ADDR: " + hex(byte_addr))
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
        self.sub.read_cdb(cdb_data[self.cycles % 3], tracker=None)


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
