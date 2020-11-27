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
        self.fwd_cost = 1
        #sub-component params
        self.enqueue_buf = None
        self.queue_stations = [] * int(queue_len)
        self.result_buffer = []
        self.rb_history = []
        self.lsq_history = []
        self.mem_unit = Memory(int(mem_size), word_len=wl, mem_config=config, verbose=verbose)
        self.mem_alu = {"target":-1, "busy":False,"countdown":None}
        #component ref params
        self.reorder_buffer = rob


    def issue(self, instr, sd_rob=None):
        if self.num_stats_free == 0:
            return Warning("Warning! Queue is unable to accept instruction.")

        # create new queue entry with default value
        enqueue = {"op":instr.op, "qrs":instr.rs, "qrt":instr.rt, \
                   "vrs":None, "vrt":None, "imm":int(instr.addr_imm), \
                   "countdown":self.cycles_in_mem, "commit":commit_check(instr), \
                   "eff_addr": None, "pc":instr.pc, "rob_ptr":sd_rob}

        enqueue["vrs"] = self.reorder_buffer.request(enqueue["qrs"])
        enqueue["vrt"] = self.reorder_buffer.request(enqueue["qrt"])

        self.enqueue_buf = enqueue
        self.num_stats_free -= 1  #preemptively reserve the space

    # standard heartbeat operation
    def tick(self, tracker):
        if self.num_stats_free == self.queue_sz:
            # if nothing is queue'd, nothing to do.
            return
        self.__exe_stage__(tracker)  # memory has its own exe stage for eff_addr
        self.__mem_stage__(tracker)



    def __exe_stage__(self, tracker):
        if self.mem_alu["busy"]:
            self.mem_alu["countdown"] -= 1
            if self.mem_alu["countdown"] == 0:
                q_target = self.queue_stations[self.mem_alu["target"]]
                q_target["eff_addr"] = q_target["vrs"] + int(q_target["imm"])
                self.mem_alu["busy"] = False
                self.mem_alu["target"] = -1

        if not self.mem_alu["busy"]:
            for i in range(len(self.queue_stations)):
                # find first entry w/o eff_addr and set up adder to work
                entry = self.queue_stations[i]
                if  entry["vrs"] is not None and entry["eff_addr"] is None:
                    self.mem_alu["target"] = i
                    self.mem_alu["countdown"] = self.cycles_in_exe
                    self.mem_alu["busy"] = True
                    tracker.update("execute", self.queue_stations[i])
                    break

        if self.enqueue_buf is not None:
            self.queue_stations.append(self.enqueue_buf)
            self.enqueue_buf = None


    def __mem_stage__(self, tracker):
        # value-forwarding operations - pass all values and change countdowns
        trgt_addr = 0
        fwd_val = 0
        for i in range(len(self.queue_stations)):
            s_instr = self.queue_stations[i]
            if entry_str_fwd_ready(s_instr): # look for each ready Sd
                trgt_addr = s_instr["eff_addr"]
                fwd_val = s_instr["vrt"]

                for j in range(i, len(self.queue_stations)):  # look for all following Lds
                    l_instr = self.queue_stations[j]
                    if entry_ld_fwd_ready(l_instr, trgt_addr):
                        print("ID fwd candidate {}".format(l_instr))
                        l_instr["vrt"] = fwd_val
                        l_instr["countdown"] = self.fwd_cost

        # memory operations
        data_fwd_idex = self.queue_sz + 1
            # direct operations
        queue_leader = self.queue_stations[0]
        #print("[LSQ] ENTRY of INTEREST: {}".format(queue_leader))
        if not lsq_fwd_ready(queue_leader): #check for fwd'd value
            if lsq_entry_ready(queue_leader):  #check that this instruction is set to go to memory
                if queue_leader["countdown"] == 0:  # queue leader has been fully served by memory

                    if queue_leader["op"] == "Ld":
                        if len(self.result_buffer) < self.CDBe:  # there is space in the results buffer
                            res = self.mem_unit.access("Ld", queue_leader["eff_addr"], None)
                            ld_res = {"op":"Ld", "pc":queue_leader["pc"], \
                                      "dest":queue_leader["qrt"], "value":res}
                            self.result_buffer.append(ld_res)
                            self.queue_stations.pop(0)
                            self.num_stats_free += 1
                            data_fwd_idex = 0
                    else:  # store ops, auto-commit/dequeue when they complete
                        self.mem_unit.access("Sd", queue_leader["eff_addr"], queue_leader["vrt"])
                        self.queue_stations.pop(0)
                        self.num_stats_free += 1
                        self.__reposition_alu_ptr__(0) # its possible to do a store and load-fwd on the same cycle
                        tracker.update("commit", queue_leader) # memory is also commit for Sd

                    # Queue leader was simply served, we must load the next instr. to memory in same cycle
                    if len(self.queue_stations) != 0:  # empty queue check
                        next_leader = self.queue_stations[0]
                        if not lsq_fwd_ready(next_leader) and lsq_entry_ready(next_leader): # we only serve non-fwd'd entries when ready
                            if next_leader["countdown"] == self.cycles_in_mem:
                                tracker.update("memory", next_leader)
                            next_leader["countdown"] -= 1

                else: # if the instr is not fwd'd a val, and is not counted down, then mem is serving it
                    if queue_leader["countdown"] == self.cycles_in_mem:
                        tracker.update("memory", queue_leader)
                    queue_leader["countdown"] -= 1

        # value forwarding operations - if Ld did not go to result buffer, then we can now.
        for entry in self.queue_stations:
            if lsq_fwd_ready(entry):
                if entry["countdown"] == 0:
                    # ready to dequeue, check nothing already buff'd and space available
                    if data_fwd_idex == self.queue_sz + 1 and len(self.result_buffer) < self.CDBe:
                        data_fwd_idex = self.queue_stations.index(entry)
                        ld_res = {"op":"Ld", "pc":entry["pc"], \
                                  "dest":entry["qrt"], "value":entry["vrt"]}
                        self.num_stats_free += 1
                        self.result_buffer.append(ld_res)
                        self.queue_stations.pop(data_fwd_idex)

                else:   # entry got value but must pay transfer penalty
                    if entry["countdown"] == self.fwd_cost:
                        tracker.update("memory", entry)
                    entry["countdown"] -= 1

        self.__reposition_alu_ptr__(data_fwd_idex)


    def deliver(self):
        return self.result_buffer.pop(0)


    def mem_commit(self, rob_loc):
        for stat in self.queue_stations:
            # if committed ROB entry matches q entry ROB ptr, permission given to go to mem on entry
            if rob_loc == stat["rob_ptr"]:
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
        self.mem_alu = {"target":-1, "busy":False, "countdown":None}
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
        out_str+="  Op | q_rs | q_rt | v_rs | v_rt |Address|Str.Commit|Countdown|Imm.\n"
        out_str+="-----------------------------------------------------------------------------\n"

        for stat in self.queue_stations:
            out_str += " " + stat["op"] + "  |  " + stat["qrs"] + "  |  " + \
                       stat["qrt"] + "  |  " + str(stat["vrs"]) + "  |  " +  \
                       str(stat["vrt"]) + "  |   " + str(stat["eff_addr"]) + "  |  " + \
                       str(stat["commit"]) + "   |    " + str(stat["countdown"]) + \
                       "     |   " + str(stat["imm"]) + "\n"

        out_str += "-----------------------------------------------------------------------------\n"
        out_str += "Results Buffer: {}".format(self.result_buffer)
        return out_str


# =====================RULES FOR CHECKING QUEUE ENTRY STATUS====================
# stand alone rule about commit readiness
def commit_check(register):
    # we only avoid default commit if we are waiting on the action from the ROB
    return not (register.op == "Sd")


# stand alone rule about LSQ entry readiness for head of queue
def lsq_entry_ready(entry):
    if entry["op"] == "Ld":
        # if load made it front of queue, it's going to go to mem.
        return entry["eff_addr"] is not None and entry["commit"] is True

    elif entry["op"] == "Sd":
        # we can go to mem once we have a value, an address, and permission to commit
        return entry["vrt"] is not None and entry["eff_addr"] is not None and entry["commit"] is True

    return False


# tests if an entry is ready to pre-preemptively exit the queue
def lsq_fwd_ready(entry):
    if entry["op"] == "Sd":
        # never forward a store instruction out of queue
        return False
    # if address and value are in entry, action was forwarded, Ld can leave queue
    return entry["eff_addr"] is not None and entry["vrt"] is not None


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
        output = "\n\n===Current Memory Configuration===\n"
        for idex in range(len(self.memory)):
            if self.memory[idex] != 0:
                addr = idex * self.word_len
                output += "MEM[" + str(addr) + "]="+str(self.memory[idex])+"\t"
        output += "\n=================================\n"
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
