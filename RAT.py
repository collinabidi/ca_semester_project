from functional_units import *


class RegisterAliasTable:
    def __init__(self, register_qty=16, verbose=False):
        self.verbose = verbose
        self.rat_map = {}  # Map of ARF registers to ARF/ROB registers
        self.routing_tbl = {} # Map of instructions to func_units
        self.sd_rob_ptr = None # register to hold ROB assignment for Sd instr's
        self.actv_instruction = None # instruction being worked on or stalled
        self.int_adder_counter = 0  # Counter to distribute int_adder instructions equally
        self.fp_adder_counter = 0   # Counter to distribute fp_adder instructions equally
        self.fp_mult_counter = 0    # Counter to distribute fp_mult instructions equally
        self.num_int_adders = 0
        self.num_fp_adders = 0
        self.num_fp_mults = 0

        self.instr_queue = None      # reference to Instruction Buffer
        self.rob = None              # reference to Reorder Buffer
        self.func_units = {}         # reference to func units
        self.btb = None              # reference to Branch Translation Buffer

        self.__init_registers__(register_qty)

        self.rat_map_history = {}


    def __str__(self):
        output_string = "============== RAT =====================\n"
        output_string += "Entry\tValue\t|\tEntry\tValue\n"
        output_string += "----------------------------------------\n"
        i = 1
        for key, value in self.rat_map.items():
            output_string += "{}\t{}".format(key, value)
            if i % 2 == 0:
                output_string += "\n"
            else:
                output_string += "\t|\t"
            i += 1
        output_string += "========================================\n"
        return output_string


    # fix me to handle PC correctly
    def tick(self, tracker):
        hazard_flag = False

        # check for active stall and fetch
        work_instruction = self.actv_instruction
        if work_instruction is None:
            next_pc = self.func_units["BTB"].fetch_pc()
            if next_pc is None or next_pc >= self.instr_queue.total_instructions*4:
                print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>> STALL or END <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
                if next_pc is not None:
                    self.instr_queue.out_of_bounds_hit = True # WE NEVER ACTUALLY VIOLATE THE Prog length. FORCE THE VALUE
                hazard_flag = True
                work_instruction = Instruction("NOP")  # Issue Nop
            else:
                work_instruction = self.instr_queue.fetch(next_pc)
                tracker.update("issue", work_instruction)
                self.actv_instruction = work_instruction
        else:
            self.func_units["BTB"].fetch_pc(f_stall=True)

        # translate ISA registers into actual registers (decode)
        transformation = self.__translate__(work_instruction)

        # check for resource dependancy (ROB full)
        if transformation is None:
            hazard_flag = True
            transformation = Instruction("NOP") # ROB structural hazard, issue NOP
        else:
            # if ROB not full, save transformed instruction (prevents double ROB reservation)
            self.actv_instruction = transformation

        # ID target func_unit and attempt to push instruction
        target_fu = self.routing_tbl[transformation.op]

        # Pick the next (appropriate) non-full functional unit
        print("NUM INT ADDERS: {}".format(self.num_int_adders))
        if target_fu == "INT":
            starting_unit = self.int_adder_counter
            exit_flag = False
            while not exit_flag:
                push_result = self.func_units[target_fu][self.int_adder_counter].issue(transformation)
                if type(push_result) == Warning:
                    self.int_adder_counter = (self.int_adder_counter + 1) % (self.num_int_adders)
                    if self.int_adder_counter == starting_unit:
                        print("ALL FUs ARE FULL!!!")
                        exit_flag = True
                else:
                    self.int_adder_counter = (self.int_adder_counter + 1) % (self.num_int_adders)
                    exit_flag = True
        elif target_fu == "FPA":
            starting_unit = self.fp_adder_counter
            exit_flag = False
            while not exit_flag:
                push_result = self.func_units[target_fu][self.fp_adder_counter].issue(transformation)
                if type(push_result) == Warning:
                    self.fp_adder_counter = (self.fp_adder_counter + 1) % (self.num_fp_adders)
                    if self.fp_adder_counter == starting_unit:
                        print("ALL FP ADDERS ARE FULL!!!")
                        exit_flag = True
                else:
                    self.fp_adder_counter = (self.fp_adder_counter + 1) % (self.num_fp_adders)
                    exit_flag = True
        elif target_fu == "FPM":
            starting_unit = self.fp_mult_counter
            exit_flag = False
            while not exit_flag:
                push_result = self.func_units[target_fu][self.fp_mult_counter].issue(transformation)
                if type(push_result) == Warning:
                    self.fp_mult_counter = (self.fp_mult_counter + 1) % (self.num_fp_mults)
                    if self.fp_mult_counter == starting_unit:
                        print("ALL FP MULTIPLIERS ARE FULL!!!")
                        exit_flag = True
                else:
                    self.fp_mult_counter = (self.fp_mult_counter + 1) % (self.num_fp_mults)
                    exit_flag = True
        else:
            if transformation.op == "Sd":
                push_result = self.func_units[target_fu].issue(transformation, sd_rob=self.sd_rob_ptr)
            else:
                push_result = self.func_units[target_fu].issue(transformation)

        # if pushed, clear the held instruction
        if type(push_result) is not Warning and hazard_flag == False:
            self.actv_instruction = None
            self.sd_rob_ptr = None
            if transformation.op in ["Beq", "Bne"]:
                # if the instruction was a branch, it also needs pushed to btb
                #  route_tbl pushed it to INT for evaluation
                self.func_units["BTB"].issue(transformation, next_pc)

            # Update timing table
            print("!ISSUE: {}".format(transformation))
            #tracker.update("issue", transformation)


    # called by ROB to alert that rob_reg is being commited so can be freed
    def commit_update(self, rob_reg):
        if rob_reg is None:
            return

        for arf_reg, reg_ptr in self.rat_map.items():
            if rob_reg == reg_ptr:
                self.rat_map[arf_reg] = arf_reg

    def save_state(self):
        """ Saves a copy of the RAT. Needs to be called when a branch instruction is issued from
        instruction buffer
        """
        self.rat_map_history = self.rat_map.copy()

    def rewind(self):
        """ Used to reset the RAT back to the instruction before the branch occurred
        """
        self.rat_map = self.rat_map_history.copy()
        #self.actv_instruction = None


    def __translate__(self, instr_raw):
        # Requests a destination register from ROB
        #  then remaps registers from current table
        if instr_raw.type not in ["r", "i"]:
            return instr_raw

        # Some instructions store result to rd, others store to rt
        if instr_raw.op in ["Add","Add.d","Sub","Sub.d","Mult.d"]:
            rob_dict = {"op":instr_raw.op, "dest":instr_raw.rd, "type":instr_raw.type, "instruction":instr_raw, "pc":instr_raw.pc}
        elif instr_raw.op in ["Addi", "Ld"]:
            rob_dict = {"op":instr_raw.op, "dest":instr_raw.rt, "type":instr_raw.type, "instruction":instr_raw, "pc":instr_raw.pc}

        if instr_raw.type == "i":
            # prevents a stalled instruction from re-translation
            if "ROB" in instr_raw.rt or self.sd_rob_ptr is not None:
                return instr_raw

            if instr_raw.op in ["Bne", "Beq"]:
                rs = self.rat_map[instr_raw.rs]
                rt = self.rat_map[instr_raw.rt]
                addr_imm = instr_raw.addr_imm
                return Instruction([instr_raw.op, rs, rt, addr_imm], pc=instr_raw.pc)
            elif instr_raw.op == "Sd":
                self.sd_rob_ptr = self.rob.enqueue(rob_dict)
                if self.sd_rob_ptr is None:
                    return None
                rs = self.rat_map[instr_raw.rs]
                rt = self.rat_map[instr_raw.rt]
                addr_imm = str(instr_raw.addr_imm)+"("+rs+")"
                return Instruction([instr_raw.op, rt, addr_imm], pc=instr_raw.pc)
            elif instr_raw.op == "Addi":
                # Only used for Addi & Ld
                print(self.rob)
                rs = self.rat_map[instr_raw.rs]  #assign source register
                rt = self.rob.enqueue(rob_dict)  #retrieve dest register
                if rt is None:
                    return None
                self.rat_map[instr_raw.rt] = rt # remap source register
                addr_imm = instr_raw.addr_imm
                print("[RAT] Translate >>> Input {} | Output {}".format(instr_raw, Instruction([instr_raw.op, rt, rs, addr_imm], pc=instr_raw.pc)))
                return Instruction([instr_raw.op, rt, rs, addr_imm], pc=instr_raw.pc)
            else:
                # Only used for Ld bc Instruction args are different
                print(self.rob)
                rs = self.rat_map[instr_raw.rs]
                rt = self.rob.enqueue(rob_dict)
                if rt is None:
                    return None
                self.rat_map[instr_raw.rt] = rt
                addr_imm = instr_raw.addr_imm
                imm_rs = str(addr_imm)+"("+rs+")"
                return Instruction([instr_raw.op, rt, imm_rs], pc=instr_raw.pc)

        elif instr_raw.type == "r":
            if "ROB" in instr_raw.rd:
                # prevents a stalled instruction from re-translation
                return instr_raw

            rd = self.rob.enqueue(rob_dict)
            if rd is None:
                return None
            self.rat_map[instr_raw.rd] = rd

            if instr_raw.rd != instr_raw.rt:
                rt = self.rat_map[instr_raw.rt]
            else:
                rt = instr_raw.rt
            if instr_raw.rd != instr_raw.rs:
                rs = self.rat_map[instr_raw.rs]
            else:
                rs = instr_raw.rs
            return Instruction([instr_raw.op, rd, rs, rt], pc=instr_raw.pc)



    def __init_registers__(self, num_arf):
        self.routing_tbl = {"Beq":"INT", "Bne":"INT", "Addi":"INT", \
                            "Ld":"LSQ",  "Sd":"LSQ",  "Add.d":"FPA", \
                            "Add":"INT", "Sub":"INT", "Sub.d":"FPA", \
                            "Mult.d":"FPM", "NOP":"NOP"}

        self.func_units = {"NOP":NoopHandler(),
                           "INT":None,
                           "FPA":None,
                           "FPM":None,
                           "LSQ":None,
                           "BTB":None}

        for i in range(1,num_arf+1):
            self.rat_map["R"+str(i)] = "R"+str(i)
            self.rat_map["F"+str(i)] = "F"+str(i)



# Helper class to RAT. Provides a target for RAT to issue NOOPs
class NoopHandler:
    def __init__(self):
        return

    def issue(self, instruction):
        return None



##### check if not removing twice; instruction unit and RAT removal??? think we are good though
"""
print("First result: {}".format(result))
print(destName)
print(result["answer"])

result = int_adder.deliver() ##### check if not removing twice!!! instruction unit and RAT removal???
print("First result: {}".format(result))
print(destName)
print(result["answer"])
######bug???
#### Collin, how does it know the value of R3 if it was never defined and the result turnout 30?
"""
