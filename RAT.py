from functional_units import *


class RegisterAliasTable:
    def __init__(self, register_qty=16):
        self.rat_map = {}  # Map of ARF registers to ARF/ROB registers
        self.routing_tbl = {} # Map of instructions to func_units
        self.actv_instruction = None # instruction being worked on or stalled

        self.instr_queue = None      # reference to Instruction Buffer
        self.rob = None              # reference to Reorder Buffer
        self.func_units = {}         # reference to func units
        self.btb = None              # reference to Branch Translation Buffer

        self.__init_registers__(register_qty)

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
    def tick(self):
        hazard_flag = False

        # check for active stall and fetch
        work_instruction = self.actv_instruction
        print("Work Instruction: {}".format(work_instruction))
        if work_instruction is None:
            next_pc = self.func_units["BTB"].fetch_pc()
            print("Received PC = {} from BTB".format(next_pc))
            print("Is PC beyond the end? {}".format(next_pc >= self.instr_queue.total_instructions*4))
            if next_pc is None or next_pc >= self.instr_queue.total_instructions*4:
                hazard_flag = True
                work_instruction = Instruction("NOP")  # Issue Nop
                print("issuing NOP")
            else:
                work_instruction = self.instr_queue.fetch(next_pc)
                print("Fetched instruction from Instruction Queue: {}".format(work_instruction))
                self.actv_instruction = work_instruction

        # translate ISA registers into actual registers (decode)
        transformation = self.__translate__(work_instruction)

        # check for resource dependancy (ROB full)
        if transformation is None:
            hazard_flag = True
            transformation = Instruction("NOP") # ROB structural hazard, issue NOP

        # ID target func_unit and attempt to push instruction
        target_fu = self.routing_tbl[transformation.op]
        push_result = self.func_units[target_fu].issue(transformation)

        # if pushed, clear the held instruction
        if push_result is not type(Warning) and hazard_flag is False:
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
        print("Raw Instruction: {}".format(instr_raw))
        if instr_raw.type not in ["r", "i"]:
            return instr_raw

        # Some instructions store result to rd, others store to rt
        if instr_raw.op in ["Add","Add.d","Sub","Sub.d","Mult.d"]:
            rob_dict = {"op":instr_raw.op, "dest":instr_raw.rd, "type":instr_raw.type}
        elif instr_raw.op == "Addi":
            rob_dict = {"op":instr_raw.op, "dest":instr_raw.rt, "type":instr_raw.type}

        if instr_raw.type == "i":
            if instr_raw.op in ["Bne", "Beq"]:
                # Brendan please check that this is correct
                rs = self.rat_map[instr_raw.rs]
                self.rat_map[instr_raw.rs] = rs
                rt = self.rat_map[instr_raw.rt]
                addr_imm = instr_raw.addr_imm
                return Instruction([instr_raw.op, rs, rt, addr_imm])
            else:
                # Only used for Addi
                # Brendan please check that this is correct
                print(self.rob)
                rt = self.rob.enqueue(rob_dict)
                if rt is None:
                    return None
                self.rat_map[instr_raw.rt] = rt
                rs = self.rat_map[instr_raw.rs]
                addr_imm = instr_raw.addr_imm
                return Instruction([instr_raw.op, rt, rs, addr_imm])


        elif instr_raw.type == "r":
            rd = self.rob.enqueue(rob_dict)
            if rd is None:
                return None
            self.rat_map[instr_raw.rd] = rd

            rt = self.rat_map[instr_raw.rt]
            rs = self.rat_map[instr_raw.rs]
            return Instruction([instr_raw.op, rd, rs, rt])



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
