import os
import sys
from collections.abc import Sequence

# . If the instruction is
# type r (Read) it will have parameters op, rs, rt, rd, shamt, funct.
# If instruction is type i (Immediate) then it will have parameters 
# op, rs, rt, address/immediate. If the instruction is type j (Jump)
# then it will have parameters op, target_address
class Instruction():
    """ Basic class for the Instruction objects
    Attributes:
        type (string): r, i, j, or no-op depending on instruction type
        op (string): type of operation (Add, Add.d, Sub, Sub.d, Ld, Sd, Beq, etc.)
        rs (string): RS register
        rs_value (int): value at the RS register (needs to be fetched from RAT/CDB?)
        rt (string): RT register
        rt_value: (int) value at the RT register (needs to be fetched from RAT/CDB?)
        rd (string): RD register
        rd_value (int): value at the RD register (needs to be fetched from RAT/CDB?)
        shamt (int): shift amount
        funct (string): sub-operation value. Probably won't be used
        addr_imm (int): immediate address value (needs to potentially fetched from RAT/CDB?)
        target_address (int): target address value (needs to potentially be fetched from RAT/CDB?)
    """
    def __init__(self, *args):

        """ Initialization function for the Instruction object.

        Args:
            Depends upon whether R-type, I-type, J-type, or no-op
        """
        
        # R-type instruction
        # args should be formatted as: 
        #   [string op, string rs, string rt,, string rd, string shamt, string funct]
        if args[0] in ["Add.d", "Add", "Sub", "Sub.d", "Mult.d"]:
            self.type = "r"
            self.op = args[0]
            self.rs = args[1]
            self.rt = args[2]
            self.rd = args[3]
            self.shamt = args[4]
            self.funct = args[5]
            self.string = ""
            for arg in args:
                self.string += arg

        # I-type instruction
        # args should be formatted as: 
        #   [string op, string rs, string rt, string address_immediate]
        elif args[0] in ["Beq", "Bne", "Addi", "Ld", "Sd"]:
            self.type = "i"
            self.op = args.op
            self.rs = args[1]
            self.rt = args[2]
            self.addr_imm = args[3]
            self.string = ""
            for arg in args:
                self.string += arg
        
        # J-type instruction
        # args should be formatted as: 
        #   [string op, string immediate]
        elif args[0] in ["Jump"]:
            self.type = "j"
            self.op = args[0]
            self.target_address = args[1]
            self.string = ""
            for arg in args:
                self.string += arg
        
        else: 
            self.type = "NOOP"
            self.string = ""
            for arg in args:
                self.string += arg

    def __str__(self):
        return self.string

class InstructionBuffer: 
    """ The InstructionBuffer class is an iterable list of the instructions of a program.

    Attributes:
        instruction_list ([] Instruction): a list of Instructions        
    """
    def __init__(self, filename):
        # open text_file
        readInput = open(filename, "r")
        f = readInput.readlines()
        # Assume instructions always begin after line 
        unparsed_instructions = f[10:]
        self.instruction_list = [0]*len(unparsed_instructions)
        for i, inst in enumerate(unparsed_instructions):
            self.instruction_list[i] = Instruction(inst.strip("\n"))
        self.index = 0

    def __str__(self):
        output_string = "================================\n"
        output_string += "Index\t|\tInstruction\t\n"
        for i, instruction in enumerate(self.instruction_list):
            output_string += str(str(i) + "\t|\t" + str(self.instruction_list[i]) + "\n")
        output_string += "================================\n"
        return output_string

    def __next__(self):
        """ Returns next value from InstructionBuffer object's lists
        """
        if self.index < len(self.instruction_list):
            result = self.instruction_list[index]
            self.index += 1
            return result
        raise StopIteration

    def __getitem__(self,i):
        return self.instruction_list[i]
    
    def __len__(self):
        return len(self.instruction_list)


class IntegerAdder:
    """ The IntegerAdder class encapsulates all functionality of the parameterizable hardware Integer Adder.

    Attributes:
        reservation_stations ([] ReservationStation): array of ReservationStations that can be filled with
            instructions, cleared, marked busy, etc.
        cycles_in_ex (int): number of cycles that it takes to execute an instruction (one at a time)
        countdown (int): current cycle number that the IntegerAdder is on while executing an instruction
        busy (boolean): denotes the status of the IntegerAdder
        num_filled_stations (int): number of instructions currently occupying the reservation stations
        complete (boolean): flag to indicate that the IntegerAdder is done
        result (int): value that comes out of the operation
        verbose (boolean): if True, print out verbose statements.
    """

    def __init__(self, num_reservations_stations, cycles_in_ex, verbose=False):
        """ Initialization function for the IntegerAdder to specify parameters.

        Args:
            num_reservation_stations (int): count of how many reservations stations there will be
            cycles_in_ex (int): count of how many cycles it takes for the IntegerAdder to execute an instruction
        """
        self.reservation_stations = RESERVATION_STATION_CLASS(num_reservations_stations)
        self.cycles_in_ex = cycles_in_ex
        self.countdown = cycles_in_ex
        self.busy = False
        self.num_filled_stations = 0
        self.complete = False
        self.result = 0
        self.verbose = verbose
        
    def insert_instruction(self, instruction):
        """ Function to insert an instruction into the reservation station

        Args:
            instruction (Instruction): the actual instruction object to be inserted
        """
        # Add instruction if there's enough room in the reservation stations
        if num_filled_stations < len(self.reservation_stations):
            self.reservation_stations[num_filled_stations] = instruction
            self.num_filled_stations += 1
            if self.verbose:
                print("Inserted another instruction into the reservation station. " \
                "There are now {} instructions in the reservation stations".format(self.num_filled_stations))
        else:
            return Warning("Warning! Reservation stations full! Did not insert instruction")

    def tick(self):
        """ Go forward once cycle

        Args: 
            None
        """
        #do_stuff

    def deliver(self):
        """ Deliver instruction value

        Args:
            None
        """
        if self.complete:
            return result
        else:
            if self.verbose:
                print("Integer Adder has {} more cycles.".format(self.countdown))
            return None

    def rewind(self):
        """ Go back and restore the past state. Called when branch prediction is incorrect.

        Args:
            None
        """
        # Rewind the reservation stations to the last checkpoint

        # Mark the IntegerAdder not busy

        # Fill reservation stations with correct values

        # Check that flags are properly reset
        

# This only runs if we call `python3 functional_units.py` from the command line       
if __name__ == "__main__":
    print("Testing operation of all classes defined in functional_units.py")
    
    # Initialize the processor and all functional units
    instruction_buffer = InstructionBuffer("input.txt")
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
    # Two ways to print out instructions: iterate through the buffer...
    for i, instruction in enumerate(instruction_buffer):
        print("Instruction {}: {}".format(i, instruction))

    # ...or you can just print as a string!
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
