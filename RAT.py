from functional_units import *
from readingInput import input_parser


class RegisterAliasTable:
    def __init__(self, register_qty=32):
        self.rat_map = {}  # Map of ARF registers to ARF/ROB registers
        self.routing_tbl = {} # Map of instructions to func_units
        self.actv_instruction = None # instruction being worked on or stalled

        self.instr_queue = None      # reference to Instruction Buffer
        self.rob = None              # reference to Reorder Buffer
        self.func_units = {}         # reference to func units

        self.__init_registers__(register_qty)


    def tick(self):
        # check for active stall and fetch
        if self.actv_instruction is None:
            self.actv_instruction = self.instr_queue.fetch()

        # translate ISA registers into actual registers (decode)
        transformation = self.__translate__(self.actv_instruction)

        # check for resource dependancy (ROB full)
        if transformation is not None:
            #ID target func_unit and attempt to push instruction
            target_fu = self.routing_tbl[transformation.op]
            push_result = self.func_units[target_fu].issue(transformation)

            # if pushed, clear the held instruction
            if push_result is not type(Warning):
                self.actv_instruction = None
                if transformation.op in ["Beq", "Bne"]:
                    # if the instruction was a branch, it also needs pushed to btb
                    #  route_tbl pushes it to INT for evaluation
                    self.func_units["BTB"].issue(transformation)
        # if could not push or transform, we still hold this actv instruction, effectively stalling one cycle


    # called by ROB to alert that rob_reg is being commited so can be freed
    def commit_update(self, rob_reg):
        if rob_reg is None:
            return

        for arf_reg, reg_ptr in self.rat_map.items():
            if rob_reg == reg_ptr:
                self.rat_map[arf_reg] = arf_reg


    def __translate__(self, instr_raw):
        # Requests a destination register from ROB
        #  then remaps registers from current table
        if instr_raw.type not in ["r", "i"]:
            return instr_raw

        rob_dict = {"type":instr_raw.op, "dest":instr_raw.rs}
        if instr_raw.type == "i":

            if instr_raw.op in ["Bne", "Beq"]:
                rs = self.rat_map[instr_raw.rs]
            else:
                rs = self.rob.enqueue(rob_dict)
                if rs is None:
                    return None

            self.rat_map[instr_raw.rs] = rs
            rt = self.rat_map[instr_raw.rt]
            addr_imm = instr_raw.addr_imm

            return Instruction(instr_raw.op, rs, rt, addr_imm)

        elif instr_raw.type == "r":
            rs = self.rob.enqueue(rob_dict)
            if rs is None:
                return None
            self.rat_map[instr_raw.rs] = rs

            rt = self.rat_map[instr_raw.rt]
            rd = self.rat_map[instr_raw.rd]
            return Instruction(instr_raw.op, rd, rs, rt)



    def __init_registers__(self, num_arf):
        self.routing_tbl = {"Beq":"INT", "Bne":"INT", "Addi":"FPA", \
                            "Ld":"LSQ",  "Sd":"LSQ",  "Add.d":"FPA", \
                            "Add":"INT", "Sub":"INT", "Sub.d":"FPA", \
                            "Mult.d":"FPM", "NOOP":"NOP"}

        self.func_units = {"NOP":NoopHandler(),
                           "INT":None,
                           "FPA":None,
                           "FPM":None,
                           "LSQ":None,
                           "BTB":None}

        for i in range(num_arf):
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
