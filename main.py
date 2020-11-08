import sys
import os
from functional_units import *

def make_instruction(input_list):
    """ Takes an input line split by spaces and returns an Instruction object
    Args:
        input_list (list): a formatted list of strings that contain instruction fields
    """
    return Instruction(input_list)


# This only runs if we call `python3 main.py` from the command line
if __name__ == "__main__":
    print("Testing operation of all classes defined in functional_units.py")

    # Initialize the processor and all functional units
    instruction_buffer = InstructionBuffer(r"C:\Users\HP\github\ca_semester_project\input.txt", "r") # changed: input.txt
    integer_adder = IntegerAdder(3, 5, 1)
    """ TODO
    reorder_buffer = ROB()

    integer_adders = [0]*len(num_integer_adders)
    for i, adder in enumerate(integer_adders):
        integer_adders[i] = IntegerAdder(args)

    fp_adders = [0]*len(num_fp_adders)
    for i, adder in enumerate(fp_adders):
        fp_adders[i] = FPAdder(args)

    fp_mults = [0]*len(num_fp_mults)
    for i, fp_mult in enumerate(fp_mults):
        fp_mults[i] = FPMultiplier(args)

    cdb
    """
    # What's in the instruction buffer?
    print(instruction_buffer)

    # Program counter starts at 0
    program_counter = 0

    # Table to keep track of cycle timing
    timing_table = {}
    for inst in instruction_buffer:
        timing_table[str(inst)] = {"ISSUE":" ","EX":" ","MEM":" ","WB":" ","COMMIT":" "}

    # Begin iterating
    cycle = 0
    while program_counter <= len(instruction_buffer):
        print("\n\nCYCLE: {}".format(cycle))
        print("PC = {}".format(program_counter))


        # ISSUE stage
        print("\tISSUE STAGE")

        # EX stage
        print("\tEX STAGE")

        # MEM stage
        print("\tMEM STAGE")

        # WB stage
        print("\tWB STAGE")

        # COMMIT stage
        print("\tCOMMIT STAGE")

        # Increment cycle counter and program counter
        cycle += 1
        program_counter += 1
