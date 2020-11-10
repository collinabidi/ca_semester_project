import os
import sys
from readingInput import *
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
        rt (string): RT register
        rd (string): RD register
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

        ### uncomment for debugging each argument in buffer
        #print("ARG0: {}".format(args[0]))
        args = args[0] #  the instruction queue
        print("*********************************")
        print(args)
        print("*********************************")
        if args[0] in ["Add.d", "Add", "Sub", "Sub.d", "Mult.d"]:
            ### uncomment when debugging
            # print("R TYPE INSTRUCTION")
            self.type = "r"
            self.op = args[0]
            self.rs = args[2].strip(",")
            self.rt = args[3].strip(",")
            self.rd = args[1].strip(",")
            self.string = ""
            for arg in args:
                self.string += arg + " "

        # I-type instruction
        # args should be formatted as:
        #   [string op, string rs, string rt, string address_immediate]
        elif args[0] in ["Beq", "Bne", "Addi", "Ld", "Sd"]:
            ### uncomment when debugging
            # print("I TYPE INSTRUCTION")
            self.type = "i"
            self.op = args[0]
            self.rs = args[1]
            if args[0] in ["Bne", "Bne", "Addi"]:
                self.rt = args[2].strip(",")
                self.addr_imm = args[3].strip(",")
            elif args[0] in ["Ld","Sd"]:
                self.rd = args[2].split("(")[1].strip(")")
                self.addr_imm = float(args[2].split("(")[0])
            self.string = ""
            for arg in args:
                self.string += arg + " "

        # J-type instruction
        # args should be formatted as:
        #   [string op, string immediate]
        elif args[0] in ["Jump"]:
            self.type = "j"
            self.op = args[0]
            self.target_address = args[1]
            self.string = ""
            for arg in args:
                self.string += arg + " "

        else:
            self.type = "NOOP"
            self.string = ""
            for arg in args:
                self.string += " {}".format(arg)

    def __str__(self):
        return self.string

class InstructionBuffer:
    """ The InstructionBuffer class is a list of the instructions of a program.

    Attributes:
        instruction_list ([] Instruction): a list of Instructions
    """
    def __init__(self, filename):
        # open text_file
        readInput = open(filename, "r")
        f = readInput.readlines()
        # Assume instructions always begin after line 10
        unparsed_instructions = f[11:]
        self.instruction_list = [0]*len(unparsed_instructions)
        for i, inst in enumerate(unparsed_instructions):
            self.instruction_list[i] = Instruction(inst.strip("\n").strip(",").split(" "))
        self.index = 0
        self.PC = 0

    def fetch(self):
        pc = self.PC
        self.PC += 1
        if pc == len(self.instruction_list):
            return Instruction() # return NOP if we get to the end of the buffer.  Is this the behavior we want?
        return self.instruction_list[pc]

    def branch(self, pc_addr):
        self.PC = pc_addr

    def __str__(self):
        output_string = "================================\n"
        output_string += "Index\t|\tInstruction\t\n"
        for i, instruction in enumerate(self.instruction_list):
            output_string += str(str(i) + "\t|\t" + str(self.instruction_list[i]) + "\n")
        output_string += "================================\n"
        return output_string

    def __getitem__(self,i):
        return self.instruction_list[i]

    def __len__(self):
        return len(self.instruction_list)

class FPMultiplier:
    """ The FPMultiplier class encapsulates all functionality of the parameterizable hardware Floating Point Multipler.

    Attributes:
        reservation_stations ({}): dict of stations that can be filled with instructions, cleared, marked busy, etc.
        cycles_in_ex (int): number of cycles that it takes to execute an instruction (one at a time)
        countdown (int): current cycle number that the FPMultiplier is on while executing an instruction
        busy (boolean): denotes the status of the FPMultiplier
        num_filled_stations (int): number of instructions currently occupying the reservation stations
        complete (boolean): flag to indicate that the FPMultiplier is done
        result (int): value that comes out of the operation
    """

    def __init__(self, num_reservations_stations, cycles_in_ex, fu_number):
        """ Initialization function for the FPMultiplier to specify parameters.

        Args:
            num_reservation_stations (int): count of how many reservations stations there will be
            cycles_in_ex (int): count of how many cycles it takes for the FPAdder to execute an instruction
            fu_number (int): index of this functional unit
        """
        self.reservation_stations = {}
        self.fu_number = fu_number
        self.cycles_in_ex = cycles_in_ex
        self.output_waiting = False
        self.num_filled_stations = 0
        for i in range(num_reservations_stations):
            tag = "FPMULT_{}_{}".format(str(fu_number), str(i))
            self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "answer":None, "countdown":self.cycles_in_ex, "dest":None}

        # This buffer keeps a history of results and their associated tags to send to CDB
        self.result_buffer = []

        # This reserves a copy of our reservation station in case we need to backtrack
        self.history = []

    def issue(self, instruction):
        """ Function to insert an instruction into the reservation station

        Args:
            instruction (dict): the instruction to be inserted into an available reservation station ["op", ]
        """
        # Add instruction if there's enough room in the reservation stations
        if self.num_filled_stations < len(self.reservation_stations):
            # Generate tag and fill station
            free_stations = [tag for tag, values in self.reservation_stations.items() if values["busy"] == False]
            if free_stations == []:
                print("No free reservation stations!")
            tag = free_stations[0]
            self.reservation_stations[tag] = {"busy":True, "op":instruction["op"], \
                "vj":instruction["vj"], "vk":instruction["vk"], "qj":instruction["qj"], \
                "qk":instruction["qk"], "answer":None, "countdown":self.cycles_in_ex, "dest":instruction["dest"]}  # TODO Need to set values from the incoming instruction. Pulls values from ARF/RAT/ROB?
            self.num_filled_stations += 1
        else:
            return Warning("Warning! Reservation stations full! Did not insert instruction")

    def deliver(self):
        print("Delivering {} and removing from result buffer".format(self.result_buffer[0]))
        return self.result_buffer.pop(0)

    def tick(self):
        """ Go forward once cycle. If results are buffered on output, raise waiting flag

        Args:
            None
        """
        # Let ready instructions operate
        for tag, instruction in self.reservation_stations.items():
            if instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] != 0:
                instruction["countdown"] -= 1
                # Only start executing one new ready instruction
                if instruction["countdown"] == 4:
                    return
            elif instruction["countdown"] == 0:
                print("{} finished!".format(tag))
                # Calculate answer
                if instruction["op"] == "Mult.d":
                    answer = float(self.reservation_stations[tag]["vj"]) * float(self.reservation_stations[tag]["vk"])
                else:
                    answer = float(self.reservation_stations[tag]["vj"]) / float(self.reservation_stations[tag]["vk"])

                self.reservation_stations[tag]["answer"] = answer
                # Put answer on result_buffer
                self.result_buffer.append({"dest":self.reservation_stations[tag]["dest"],"answer":answer})
                # Free reservation station and reset tags/flags
                self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "answer":None, "countdown":self.cycles_in_ex, "dest":None}
                self.num_filled_stations -= 1
                self.output_waiting = True
            elif instruction["qj"] != None or instruction["qk"] != None:
                print("{} still waiting on {} or {}".format(instruction["qj"], instruction["qk"]))

        if len(self.result_buffer) != 0:
            self.output_waiting = True
        else:
            self.output_waiting = False

        return self.output_waiting

    def save_history(self):
        print("Saved a copy of the reservation station!")
        self.history = self.reservation_stations.copy()

    def reset(self):
        print("Resetting the reservation stations")
        self.reservation_stations = self.history.copy()
        self.num_filled_stations = sum([1 for key,val in self.reservation_stations.items() if val["busy"] == True])
        self.executing = False
        self.current_tag = None

    def __str__(self):
        output_string = "===================================================FP Multiply Unit=================================================================================\n"
        output_string += "Tag\t\t|\tBusy\t|\tOp\t|\tvj\t|\tvk\t|\tqj\t|\tqk       Countdown     Dest\n"
        output_string += "-------------------------------------------------------------------------------------------------------------------------------------------------\n"
        for tag, value in self.reservation_stations.items():
            output_string += str(tag + "\t|\t" + str(value["busy"]) + "\t|\t" + str(value["op"]) + \
                "\t|\t" + str(value["vj"]) + "\t|\t" + str(value["vk"]) + "\t|\t" + str(value["qj"]) + \
                "\t|\t" + str(value["qk"]) + "         " + str(value["countdown"]) + "      " + str(value["dest"]) + "\n")
        output_string += "-------------------------------------------------------------------------------------------------------------------------------------------------\n"
        output_string += "Result Buffer: {}".format(self.result_buffer)
        output_string += "\n=================================================================================================================================================\n"
        return output_string

class FPAdder:
    """ The FPAdder class encapsulates all functionality of the parameterizable hardware Floating Point Adder.

    Attributes:
        reservation_stations ({}): dict of stations that can be filled with instructions, cleared, marked busy, etc.
        cycles_in_ex (int): number of cycles that it takes to execute an instruction (one at a time)
        countdown (int): current cycle number that the FPAdder is on while executing an instruction
        busy (boolean): denotes the status of the FPAdder
        num_filled_stations (int): number of instructions currently occupying the reservation stations
        complete (boolean): flag to indicate that the FPAdder is done
        result (int): value that comes out of the operation
    """

    def __init__(self, num_reservations_stations, cycles_in_ex, fu_number):
        """ Initialization function for the FPAdder to specify parameters.

        Args:
            num_reservation_stations (int): count of how many reservations stations there will be
            cycles_in_ex (int): count of how many cycles it takes for the FPAdder to execute an instruction
            fu_number (int): index of this functional unit
        """
        self.reservation_stations = {}
        self.fu_number = fu_number
        self.cycles_in_ex = cycles_in_ex
        self.output_waiting = False
        self.num_filled_stations = 0
        for i in range(num_reservations_stations):
            tag = "FPADD_{}_{}".format(str(fu_number), str(i))
            self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "answer":None, "countdown":self.cycles_in_ex, "dest":None}

        # This buffer keeps a history of results and their associated tags to send to CDB
        self.result_buffer = []

        # This reserves a copy of our reservation station in case we need to backtrack
        self.history = []

    def issue(self, instruction):
        """ Function to insert an instruction into the reservation station

        Args:
            instruction (dict): the instruction to be inserted into an available reservation station ["op", ]
        """
        # Add instruction if there's enough room in the reservation stations
        if self.num_filled_stations < len(self.reservation_stations):
            # Generate tag and fill station
            free_stations = [tag for tag, values in self.reservation_stations.items() if values["busy"] == False]
            if free_stations == []:
                print("No free reservation stations!")
            tag = free_stations[0]
            self.reservation_stations[tag] = {"busy":True, "op":instruction["op"], \
                "vj":instruction["vj"], "vk":instruction["vk"], "qj":instruction["qj"], \
                "qk":instruction["qk"], "answer":None, "countdown":self.cycles_in_ex, "dest":instruction["dest"]}  # TODO Need to set values from the incoming instruction. Pulls values from ARF/RAT/ROB?
            self.num_filled_stations += 1
        else:
            return Warning("Warning! Reservation stations full! Did not insert instruction")

    def deliver(self):
        print("Delivering {} and removing from result buffer".format(self.result_buffer[0]))
        return self.result_buffer.pop(0)

    def tick(self):
        """ Go forward once cycle. If results are buffered on output, raise waiting flag

        Args:
            None
        """
        # Let ready instructions operate
        for tag, instruction in self.reservation_stations.items():
            if instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] != 0:
                instruction["countdown"] -= 1
                # Only start executing one new ready instruction
                if instruction["countdown"] == 4:
                    return
            elif instruction["countdown"] == 0:
                print("{} finished!".format(tag))
                # Calculate answer
                if instruction["op"] == "Add.d":
                    answer = float(self.reservation_stations[tag]["vj"]) + float(self.reservation_stations[tag]["vk"])
                else:
                    answer = float(self.reservation_stations[tag]["vj"]) - float(self.reservation_stations[tag]["vk"])

                self.reservation_stations[tag]["answer"] = answer
                # Put answer on result_buffer
                self.result_buffer.append({"dest":self.reservation_stations[tag]["dest"],"answer":answer})
                # Free reservation station and reset tags/flags
                self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "answer":None, "countdown":self.cycles_in_ex, "dest":None}
                self.num_filled_stations -= 1
                self.output_waiting = True
            elif instruction["qj"] != None or instruction["qk"] != None:
                print("{} still waiting on {} or {}".format(instruction["qj"], instruction["qk"]))

        if len(self.result_buffer) != 0:
            self.output_waiting = True
        else:
            self.output_waiting = False

        return self.output_waiting

    def save_history(self):
        print("Saved a copy of the reservation station!")
        self.history = self.reservation_stations.copy()

    def reset(self):
        print("Resetting the reservation stations")
        self.reservation_stations = self.history.copy()
        self.num_filled_stations = sum([1 for key,val in self.reservation_stations.items() if val["busy"] == True])
        self.executing = False
        self.current_tag = None

    def __str__(self):
        output_string = "===================================================FP Adder Unit=================================================================================\n"
        output_string += "Tag\t\t|\tBusy\t|\tOp\t|\tvj\t|\tvk\t|\tqj\t|\tqk\t|\tAnswer\t|\tCountdown\n"
        output_string += "-------------------------------------------------------------------------------------------------------------------------------------------------\n"
        for tag, value in self.reservation_stations.items():
            output_string += str(tag + "\t|\t" + str(value["busy"]) + "\t|\t" + str(value["op"]) + \
                "\t|\t" + str(value["vj"]) + "\t|\t" + str(value["vk"]) + "\t|\t" + str(value["qj"]) + \
                "\t|\t" + str(value["qk"]) + "\t|\t" + str(value["answer"]) + "\t|\t" + str(value["countdown"]) + "\n")
        output_string += "-------------------------------------------------------------------------------------------------------------------------------------------------\n"
        output_string += "Result Buffer: {}".format(self.result_buffer)
        output_string += "\n=================================================================================================================================================\n"
        return output_string

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

    def __init__(self, num_reservations_stations, cycles_in_ex, fu_number):
        """ Initialization function for the IntegerAdder to specify parameters.

        Args:
            num_reservation_stations (int): count of how many reservations stations there will be
            cycles_in_ex (int): count of how many cycles it takes for the IntegerAdder to execute an instruction
            fu_number (int): index of this functional unit
        """
        self.reservation_stations = {}
        self.fu_number = fu_number
        self.cycles_in_ex = cycles_in_ex
        self.countdown = cycles_in_ex
        self.executing = False
        self.output_waiting = False
        self.current_tag = None
        self.num_filled_stations = 0
        for i in range(num_reservations_stations):
            tag = "INTADD_{}_{}".format(str(fu_number), str(i))
            self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "answer":None, "dest":None}

        # This buffer keeps a history of results and their associated tags to send to CDB
        self.result_buffer = []

        # This keeps track of stations that are ready to go
        self.ready_queue = []

        # This reserves a copy of our reservation station in case we need to backtrack
        self.history = []

    def issue(self, instruction):
        """ Function to insert an instruction into the reservation station

        Args:
            instruction (dict): the instruction to be inserted into an available reservation station ["op", ]
        """
        # Add instruction if there's enough room in the reservation stations
        if self.num_filled_stations < len(self.reservation_stations):
            # Generate tag and fill station
            free_stations = [tag for tag, values in self.reservation_stations.items() if values["busy"] == False]
            if free_stations == []:
                print("No free reservation stations!")
            tag = free_stations[0]
            self.reservation_stations[tag] = {"busy":True, "op":instruction["op"],"vj":instruction["vj"], "vk":instruction["vk"], \
                "qj":instruction["qj"], "qk":instruction["qk"], "answer":None, "dest":instruction["dest"]} # TODO Need to set values from the incoming instruction. Pulls values from ARF/RAT/ROB?
            self.num_filled_stations += 1
        else:
            return Warning("Warning! Reservation stations full! Did not insert instruction")

    def save_history(self):
        print("Saved a copy of the reservation station!")
        self.history = self.reservation_stations.copy()

    def reset(self):
        print("Resetting the reservation stations")
        self.reservation_stations = self.history.copy()
        self.num_filled_stations = sum([1 for key,val in self.reservation_stations.items() if val["busy"] == True])
        self.executing = False
        self.current_tag = None

    def tick(self):
        """ Go forward once cycle. If results are buffered on output, raise waiting flag

        Args:
            None
        """
        # Check for ready instructions and add to queue
        for tag, instruction in self.reservation_stations.items():
            if instruction["vj"] != None and instruction["vk"] != None and tag not in self.ready_queue:
                self.ready_queue.append(tag)

        if self.countdown != 0 and self.executing == True:
            self.countdown -= 1
        elif self.countdown == 0 and self.executing == True:
            # Calculate answer
            if self.reservation_stations[self.current_tag]["op"] == "Add":
                answer = int(self.reservation_stations[self.current_tag]["vj"]) + int(self.reservation_stations[self.current_tag]["vk"])
            else:
                answer = int(self.reservation_stations[self.current_tag]["vj"]) - int(self.reservation_stations[self.current_tag]["vk"])

            self.reservation_stations[self.current_tag]["answer"] = answer
            # Put answer on result_buffer
            self.result_buffer.append({"dest":self.reservation_stations[self.current_tag]["dest"],"answer":answer})
            # Free reservation station and reset tags/flags
            self.reservation_stations[self.current_tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "answer":None, "dest":None}
            self.ready_queue.remove(self.current_tag)
            self.current_tag = None
            self.num_filled_stations -= 1
            self.executing = False
            self.output_waiting = True
            self.countdown = self.cycles_in_ex

        # Begin executing next instruction if idle
        if self.executing == False and len(self.ready_queue) != 0:
            self.current_tag = self.ready_queue[0]
            self.executing = True
            self.countdown = self.cycles_in_ex
            #self.ready_queue.remove(self.current_tag)

        if len(self.result_buffer) != 0:
            self.output_waiting = True
        else:
            self.output_waiting = False

        return self.output_waiting

    def deliver(self):
        print("Delivering {} and removing from result buffer".format(self.result_buffer[0])) #changed 0 to 1 because instruction queue starts with 1?
        return self.result_buffer.pop(0)


    def __str__(self):
        if self.executing:
            output_string = "===================================================Integer Adder: Executing=================================================\n"
        else:
            output_string = "===================================================Integer Adder: Idle======================================================\n"

        output_string += "Tag\t\t|\tBusy\t|\tOp\t|\tvj\t|\tvk\t|\tqj\t|\tqk\t|\tAnswer\n"
        output_string += "----------------------------------------------------------------------------------------------------------------------------------\n"
        for tag, value in self.reservation_stations.items():
            output_string += str(tag + "\t|\t" + str(value["busy"]) + "\t|\t" + str(value["op"]) + \
                "\t|\t" + str(value["vj"]) + "\t|\t" + str(value["vk"]) + "\t|\t" + str(value["qj"]) + \
                "\t|\t" + str(value["qk"]) + "\t|\t" + str(value["answer"]) + "\n")
        output_string += "----------------------------------------------------------------------------------------------------------------------------------\n"
        output_string += "Result Buffer: {}\nReady Instruction Queue: {}".format(self.result_buffer, self.ready_queue)
        output_string += "\n==================================================================================================================================\n"
        return output_string

# This only runs if we call `python3 functional_units.py` from the command line
if __name__ == "__main__":
    print("Testing operation of all classes defined in functional_units.py")

    # Initialize the processor and all functional units
    instruction_buffer = InstructionBuffer(r"C:\Users\HP\github\ca_semester_project\input.txt")
    #instruction_buffer = InstructionBuffer("input.txt")

    """
    input_params = input_parser("input.txt")
    integer_adders = []
    for i in range(input_params.intA["nfu"]):
        integer_adders[i] = IntegerAdder(input_params.intA["nrg"], input_parser.intA["cie"], i)
    fp_adders = []
    for i in range(input_params.FPA["nfu"]):
        fp_adders[i] = FPAdder(input_params.FPA["nrg"], input_parser.FPA["cie"], i)
    fp_multipliers = []
    for i in range(input_params.FPM["nfu"]):
        fp_multipliers[i] = FPMultiplier(input_params.FPM["nrg"], input_parser.FPM["cie"], i)
    """

    # What's in the instruction buffer?
    print(instruction_buffer)

    # This prints out the instruction buffer objects one by one
    # i = 0
    # for value in instruction_buffer:
    #     print("i = {}: value = {}".format(i, value))
    #     i = i + 1

    print("INSTRUCTION QUEUE")
    for i, instruction in enumerate(instruction_buffer):
        print("i = {}: value = {}".format(i, instruction))
        print(instruction.__dict__)


    """
    # Program counter starts at 0
    program_counter = 0

    # Table to keep track of cycle timing
    timing_table = {}
    for inst in instruction_buffer:
        timing_table[str(inst)] = {"ISSUE":" ","EX":" ","MEM":" ","WB":" ","COMMIT":" "}

    # Begin iterating
    cycle = 0
    """
    # create object called inputs to access regNames and regInitials
    inputs = input_parser(r"C:\Users\HP\github\ca_semester_project\input.txt")
    #inputparsed = input_parser("input.txt")
    int_adder = int_adder = IntegerAdder(int(inputs.intA['nrg']), int(inputs.intA['cie']), int(inputs.intA['nfu']))


    # Issue instruction to fp_adder functional unit
    for instruction in instruction_buffer:
        # If there's room in the IntAdder and instruction is Add or Sub, issue it!
        if instruction.op == "Sub" or instruction.op == "Add" and int_adder.num_filled_stations < len(int_adder.reservation_stations):
            int_adder.issue({"op":instruction.op,"vj":10, "vk":20, "qj":instruction.rs, "qk":instruction.rt, "dest":instruction.rd})
        int_adder.tick()
        print(int_adder)

    for i in range(0, 10):
        int_adder.tick()
        print(int_adder)

    # This will give you a dictionary: for example, {"dest","ROB1":"answer":10.3} would be the output for an operation with
    # destination ROB1 and value 10.3

    #print(self.result_buffer)
    result = int_adder.deliver()
    print("First result: {}".format(result))
