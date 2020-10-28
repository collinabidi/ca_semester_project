import os
import sys

# . If the instruction is
# type r (Read) it will have parameters op, rs, rt, rd, shamt, funct.
# If instruction is type i (Immediate) then it will have parameters 
# op, rs, rt, address/immediate. If the instruction is type j (Jump)
# then it will have parameters op, target_address
class Instruction:
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
    def __init__(self, args):

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

        # I-type instruction
        # args should be formatted as: 
        #   [string op, string rs, string rt, string address_immediate]
        elif args[0] in ["Beq", "Bne", "Addi", "Ld", "Sd"]:
            self.type = "i"
            self.op = args.op
            self.rs = args[1]
            self.rt = args[2]
            self.addr_imm = args[3]
        
        # J-type instruction
        # args should be formatted as: 
        #   [string op, string immediate]
        elif args[0] in ["Jump"]:
            self.type = "j"
            self.op = args[0]
            self.target_address = args[1]
        
        else: 
            self.type = "NOOP"


# make_instruction takes an input line split by spaces and returns an Instruction
# object with the appropriate parameters as defined by Instruction class
def make_instruction(input_list):
    return Instruction(input_list)

# Example of how to use make_instruction() function

# Let's make a pretend instruction in a list. We actually don't really care about shamt or funct
# in our implementation because we don't have any instructions that use either parameter.
# I just included them for the sake of completeness
instruction_example = ["Add.d", "R1", "R2", "R3", "x", "x"]
print("instruction_example is just a list: {}".format(instruction_example))

# We can call the make_instruction function to create an Instruction object
# that uses the information from the instruction_example variable
my_instruction_object = make_instruction(instruction_example)

# We can now access the public variables of the instruction object by calling it with a "." operator
print("**************************")
print("instruction OP value: {}".format(my_instruction_object.op))
print("instruction RS value: {}".format(my_instruction_object.rs))
print("instruction RT value: {}".format(my_instruction_object.rt))
print("instruction RD value: {}".format(my_instruction_object.rd))
print("**************************")

# If we have an instruction queue, then we can now append to it
instruction_queue = []
instruction_queue.append(my_instruction_object)
print("Instruction Queue with ONE Instruction object: {}".format(instruction_queue))
print("**************************")

# Let's make another instruction and append it to queue
another_instruction_object = make_instruction(["Sub", "R1", "R3", "R4", "zssfsdfddoens'treallymatter", "mehhhhhhhh"])
instruction_queue.append(another_instruction_object)
print("Instruction Queue with TWO Instruction objects: {}".format(instruction_queue))
print("**************************")


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
        do_stuff

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
        

                
                

