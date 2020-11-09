# Memory Element classes
# ========================

#Memory inits with the spec'd size, and will fit the value range to it, if provided
#The value 0x0 is reserved as a NULL ref.
#  If called by str, NONE is always returned.
#  If called by ld, the value is dumped.

from functional_units import *

class LoadStoreQueue:
    def __init__(self, mem_size, queue_len, cycles_in_mem, verbose=False, config=None):
        self.verbose = verbose
        self.num_stats_free = queue_len
        self.cycles_in_mem = cycles_in_mem

        self.queue_stations = [] * queue_len
        self.mem_unit = Memory(mem_size, verbose=verbose, mem_config=config)


    def issue(self, instr):
        if self.num_stats_free == 0:
            return Warning("Warning! Queue is unable to accept instruction.")

        #
        enqueue = {"op":instr["op"], "qrs":instr["rs"], "qrt":instr["rt"], \
                   "vrs":None, "vrt":None, "imm":instr["imm"], \
                   "countdown":self.cycles_in_mem+1, "commit":False}

        if enqueue["op"] == "Ld":
            enqueue["commit"] = True
        #request value from register for rt
        #request value from register for rs
        self.num_stats_free -= 1
        self.queue_stations.append(enqueue)


    # standard heartbeat operation
    def tick(self):
        if self.num_stats_free == len(self.queue_stations):
            # if nothing is queue'd, nothing to do.
            return
"""
        WE SHOULDNT NEED TO CHECK FOR VALUES HERE
           ROB is read on "issue" of new instr. to queue
           Arch. Registers are also read on "issue" and no values have to wait.
           CBD will automatically push values to us (and the rob, but we already have them)
          We checked all sources in due time, so no need to repeat.
"""
        queue_leader = self.queue_stations[0]
        if lsq_entry_ready(queue_leader) and self.result_buffer[0] is None:
            # register is ready to go to mem. & not waiting to tender a result
            if(queue_leader["countdown"] -= 1) == 0:
                # calc effective addres
                eff_addr = queue_leader["vrt"] + queue_leader["imm"]
                # act on memory
                res = self.mem_unit.access(queue_leader["op"], eff_addr, queue_leader["vrs"])

                # ready output for system if "Ld"
                if queue_leader["op"] == "Ld":
                    queue_leader["vrs"] = res
                    result = {"dest":queue_leader["qrs"], "value":res}
                    self.result_buffer.append(result)

                # dequeue the operation
                self.num_stats_free += 1
                self.queue_stations.pop(0)


    def deliver(self):
        return self.result_buffer.pop(0)


    # THIS NEEDS TO BE CALLED BY THE ROB WHEN IT COMMITS A VALUE
    #   If the value was tied to a store operation, that operation will dequeue
    def mem_commit(self, rob_loc):
        if self.queue_stations[0]["op"] == "Sd":
            if rob_loc == self.queue_stations[0]["qrs"]:
                self.queue_stations[0]["commit"] = True


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


    # branch prediction rollback
    def rewind(self):
        return

    def __str__(self):
        out_str= "===================Load/Store Queue===================\n")
        out_str+="Op\t|\t|\tq_rs\t|\tq_rt|\tv_rs\t|\tv_rt\t|\tImmidiate\t|\tStr.Commit\t|\tCountdown")
        out_str+="\n-------------------------------------------------------\n")
        for stat in self.queue_stations:
            out_str += stat["op"] + "\t" + stat["qrs"] + "\t" + stat["qrt"] + \
                       "\t" + str(stat["vrs"]) + "\t" + str(stat["vrt"]) + \
                       str(stat["imm"]) + "\t" + str(stat["commit"]) + "\n"
        out_str += "-------------------------------------------------------\n"
        out_str += "Results Buffer: {}".format(self.result_buffer)



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

        if size_bytes % word_len != 0:
            raise SegFaultException("On Initialization: Byte size of mem: " + \
                      str(self.mem_sz) + "is not a mulitple of the word length: " +\
                      str(word_len))

        self.init_mem(mem_config)


    # force initialize values into the memory block
    def init_mem(self, mem_arr):
        if mem_arr is None:
            self.memory = [0x0] * (self.byte_addr % self.word_len)
            if verbose:
                print("[MEMRY]: Init'd clean memory. # Words: " + str(len(self.memory)))

        else:
            if len(mem_arr) != (self.mem_sz * self.word_len):
                self.mem_sz = len(mem_sz) * self.word_len
                if verbose:
                    print("[MEMRY]: Inputted Mem config did not expected size. " +\
                          "Size Param changed.")
            self.memory = mem_arr



    # completely async., completes function as called, at call.
    def access(self, io, byte_addr, value):
        # VALIDITY CHECKS
        if(byte_addr % self.word_len) != 0: # word alignment check
            raise SegFaultException("Misaligned target addr [0x" + hex(byte_addr) + \
                                    "] fails mem. word size: " + str(self.word_len))

        if byte_addr > (self.mem_sz - 1) or byte_addr < 0:  # Bounds check
            raise SegFaultException("Out-of-Bounds Address: "+str(byte_addr)+ \
                                    "  is not [0: " + str(self.mem_sz-1) + "]")

        # ARRAY ACCESSES
        if io == "ld":
            if verbose:
                print("[MEMRY]: Accessed Load at EFF ADDR" + hex(byte_addr))
            return self.memory[byte_addr % self.word_len]

        elif io == "Sd":
            if verbose:
                print("[MEMRY]: Storing value {} at {}", str(value), hex(byte_addr))
            self.memory[byte_addr % self.word_len] = value

        return None


    # clears memory to zeros
    def reset(self):
        self.init_mem(None)


    # prints current contents of memory
    def print_mem(self, width=4):

        mod_blck = self.mem_sz - (self.mem_sz % width)
        remainder = self.mem_sz % width

        print("===Current Memory Configuration===")
        title_line = "\nOffset>"
        for i in range(width):
            title_line += "\t0x" + hex(i*self.word_len)
        print(title_line)

        for i in range(0, mod_blck, width):
            mem_line = "0x" + hex(i*self.word_len)
            for j in range(width):
                mem_line += "\t" + str(self.memory[i+j])
            print(mem_line)

        rem_mem_line = "0x" + hex(mod_blck)
        for i in range(remainder):
            rem_mem_line += "\t" + str(self.memory[mod_blck+i])
        print(rem_mem_line)



class SegFaultException(Exception):
    """ Raised when bad memory ops occur"""
    def __init__(self, message):
        super().__init__("Seg Fault, core dumped:" + message)



if __name__ == "__main__":
    print("Testing memory instructions")
    instr_q = [Instruction("Sd", "ROB1", "ROB2", "0"),
               Instruction("Ld", "ROB3", "ROB2", "0"),
               Instruction("Sd", "ROB4", "ROB2", "3")]
