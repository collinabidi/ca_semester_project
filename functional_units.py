import os
import sys
from reading_input import *

class Instruction():
    """ Basic class for the Instruction objects
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
            self.type = "NOP"
            self.string = ""
            for arg in args:
                self.string += " {}".format(arg)

    def __str__(self):
        return self.string

class InstructionBuffer:
    """ The InstructionBuffer class is a list of the instructions of a program.
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

    def fetch(self, pc):
        """ Get the next instruction from the buffer
        """
        pc = self.PC
        self.PC += 1
        # If we reach the end of the instructions, return a NOP
        if pc == len(self.instruction_list):
            return Instruction()
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
    """

    def __init__(self, num_reservations_stations, cycles_in_ex, fu_number):
        """ Initialization function for the FPMultiplier to specify parameters.
        """
        self.reservation_stations = {}
        self.fu_number = fu_number
        self.cycles_in_ex = cycles_in_ex
        self.num_filled_stations = 0
        for i in range(num_reservations_stations):
            tag = "FPMULT_{}_{}".format(str(fu_number), str(i))
            self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "value":None, "countdown":self.cycles_in_ex, "dest":None}

        # This buffer keeps a history of results and their associated tags to send to CDB
        self.result_buffer = []

        # This reserves a copy of our reservation station in case we need to backtrack
        self.history = []

    def issue(self, instruction):
        """ Function to insert an instruction into the reservation station
        """
        # Check if there's enough room in the reservation stations
        if self.num_filled_stations >= len(self.reservation_stations):
            return Warning("Reservation Station of FPMultiplier {} is full".format(self.fu_number))
        else:
            # Generate tag and fill station
            free_stations = [tag for tag, values in self.reservation_stations.items() if values["busy"] == False]
            if free_stations == []:
                print("No free reservation stations!")
            tag = free_stations[0]
            # Add Rd, Rs, Rt
            if instruction.op == "Mult.d":
                self.reservation_stations[tag] = {"busy":True, op:instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                print("Checking ROB for {}".format(instruction.rs))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                print("Checking ROB for {}".format(instruction.rt))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
            elif instruction.op == "Div.d":
                self.reservation_stations[tag] = {"busy":True, op:instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                print("Checking ROB for {}".format(instruction.rs))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)

            self.num_filled_stations += 1

    def deliver(self):
        """ Deliver the result to the CDB and remove it from the buffer
        """
        return self.result_buffer.pop(0)

    def tick(self):
        """ Go forward once cycle and perform calculations. Add a waiting instruction to be executed. If a station is done, put result on output buffer
        """
        new_instruction_began = False
        for tag, instruction in self.reservation_stations.items():
            if instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] != 0 and new_instruction_began != True:
                instruction["countdown"] -= 1
                new_instruction_began = True
            elif instruction["countdown"] == 0:
                print("{} finished!".format(tag))
                if instruction["op"] == "Mult.d":
                    answer = float(self.reservation_stations[tag]["vj"]) * float(self.reservation_stations[tag]["vk"])
                else:
                    answer = float(self.reservation_stations[tag]["vj"]) / float(self.reservation_stations[tag]["vk"])

                self.reservation_stations[tag]["value"] = answer
                self.result_buffer.append({"dest":self.reservation_stations[tag]["dest"],"value":answer})
                self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "value":None, "countdown":self.cycles_in_ex, "dest":None}
                self.num_filled_stations -= 1

    def save_state(self):
        """ Saves a copy of the reservation stations. Needs to be called when a branch instruction is issued from
        instruction buffer
        """
        self.history = self.reservation_stations.copy()

    def rewind(self):
        """ Used to reset the reservation stations back to the instruction before the branch occurred
        """
        self.reservation_stations = self.history.copy()
        self.num_filled_stations = sum([1 for key,val in self.reservation_stations.items() if val["busy"] == True])
        self.executing = False
        self.current_tag = None
    
    def read_cdb(self, bus_data):
        """ Read data on CDB and check if unit is looking for that value. Data bus formatted as {"dest":Destination, "value":Value}
        """
        for tag, station in self.reservation_stations.items():
            if station["qj"] == bus_data["dest"]:
                station["vj"] = bus_data["value"]
            if station["qk"] == bus_data["dest"]:
                station["vk"] = bus_data["value"]

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
        self.num_filled_stations = 0
        for i in range(num_reservations_stations):
            tag = "FPADD_{}_{}".format(str(fu_number), str(i))
            self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "value":None, "countdown":self.cycles_in_ex, "dest":None}

        # This buffer keeps a history of results and their associated tags to send to CDB
        self.result_buffer = []

        # This reserves a copy of our reservation station in case we need to backtrack
        self.history = []

    def issue(self, instruction):
        """ Function to insert an instruction into the reservation station
        """
        # Check if there's enough room in the reservation stations
        if self.num_filled_stations >= len(self.reservation_stations):
            return Warning("Reservation Station of FPAdder {} is full".format(self.fu_number))
        else:
            tag = [tag for tag, values in self.reservation_stations.items() if values["busy"] == False][0]
            if instruction.op == "Add.d":
                # Add: Rd = Rs + Rt
                self.reservation_stations[tag] = {"busy":True, op:instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                print("Checking ROB for {}".format(instruction.rs))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                print("Checking ROB for {}".format(instruction.rt))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)

            elif instruction.op == "Sub.d":
                # Sub: Rd = Rs - Rt
                self.reservation_stations[tag] = {"busy":True, op:instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                print("Checking ROB for {}".format(instruction.rs))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                print("Checking ROB for {}".format(instruction.rt))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
            self.num_filled_stations += 1

        if self.num_filled_stations == self.size:
            print("FP Adder {} is now full!".format(self.fu_number))
        return self.num_filled_stations == self.size

    def deliver(self):
        return self.result_buffer.pop(0)

    def tick(self):
        """ Go forward once cycle and perform calculations. Add a waiting instruction to be executed. If a station is done, put result on output buffer
        """
        # Let ready instructions operate
        for tag, instruction in self.reservation_stations.items():
            if instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] != 0 and new_instruction_began != True:
                instruction["countdown"] -= 1
                new_instruction_began = True
            elif instruction["countdown"] == 0:
                print("{} finished!".format(tag))
                # Calculate value
                if instruction["op"] == "Add.d":
                    answer = float(self.reservation_stations[tag]["vj"]) + float(self.reservation_stations[tag]["vk"])
                else:
                    answer = float(self.reservation_stations[tag]["vj"]) - float(self.reservation_stations[tag]["vk"])

                self.reservation_stations[tag]["value"] = answer
                self.result_buffer.append({"dest":self.reservation_stations[tag]["dest"],"value":answer})
                self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "value":None, "countdown":self.cycles_in_ex, "dest":None}
                self.num_filled_stations -= 1
            elif instruction["qj"] != None or instruction["qk"] != None:
                print("{} still waiting on {} or {}".format(instruction["qj"], instruction["qk"]))

    def save_state(self):
        """ Saves a copy of the reservation stations. Needs to be called when a branch instruction is issued from
        instruction buffer
        """
        self.history = self.reservation_stations.copy()

    def rewind(self):
        """ Used to reset the reservation stations back to the instruction before the branch occurred
        """
        self.reservation_stations = self.history.copy()
        self.num_filled_stations = sum([1 for key,val in self.reservation_stations.items() if val["busy"] == True])
        self.executing = False
        self.current_tag = None

    def read_cdb(self, bus_data):
        """ Read data on CDB and check if unit is looking for that value. Data bus formatted as {"dest":Destination, "value":Value}
        """
        for tag, station in self.reservation_stations.items():
            if station["qj"] == bus_data["dest"]:
                station["vj"] = bus_data["value"]
            if station["qk"] == bus_data["dest"]:
                station["vk"] = bus_data["value"]

    def __str__(self):
        output_string = "===================================================FP Adder Unit=================================================================================\n"
        output_string += "Tag\t\t|\tBusy\t|\tOp\t|\tvj\t|\tvk\t|\tqj\t|\tqk\t|\tvalue\t|\tCountdown\n"
        output_string += "-------------------------------------------------------------------------------------------------------------------------------------------------\n"
        for tag, value in self.reservation_stations.items():
            output_string += str(tag + "\t|\t" + str(value["busy"]) + "\t|\t" + str(value["op"]) + \
                "\t|\t" + str(value["vj"]) + "\t|\t" + str(value["vk"]) + "\t|\t" + str(value["qj"]) + \
                "\t|\t" + str(value["qk"]) + "\t|\t" + str(value["value"]) + "\t|\t" + str(value["countdown"]) + "\n")
        output_string += "-------------------------------------------------------------------------------------------------------------------------------------------------\n"
        output_string += "Result Buffer: {}".format(self.result_buffer)
        output_string += "\n=================================================================================================================================================\n"
        return output_string

class IntegerAdder:
    """ The IntegerAdder class encapsulates all functionality of the parameterizable hardware Integer Adder.
    """

    def __init__(self, num_reservations_stations, cycles_in_ex, fu_number, rob):
        """ Initialization function for the IntegerAdder to specify parameters.
        """
        self.reservation_stations = {}
        self.fu_number = fu_number
        self.cycles_in_ex = cycles_in_ex
        self.countdown = cycles_in_ex
        self.executing = False
        self.current_tag = None
        self.num_filled_stations = 0
        self.size = num_reservations_stations
        for i in range(num_reservations_stations):
            tag = "INTADD_{}_{}".format(str(fu_number), str(i))
            self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "value":None, "dest":None}

        # This buffer keeps a history of results and their associated tags to send to CDB
        self.result_buffer = []

        # This keeps track of stations that are ready to go
        self.ready_queue = []

        # This reserves a copy of our reservation station in case we need to backtrack
        self.history = []

        # Register the rob to make requests
        self.rob = rob

    def issue(self, instruction):
        """ Function to insert an instruction into the reservation station. Returns whether full or not
        """
        # Check if there's enough room in the reservation stations
        if self.num_filled_stations >= self.size:
            return Warning("Reservation Station of IntegerAdder {} is full".format(self.fu_number))
        else:
            tag = [tag for tag, values in self.reservation_stations.items() if values["busy"] == False][0]
            if instruction.op == "Add":
                # Add: Rd = Rs + Rt
                self.reservation_stations[tag] = {"busy":True, op:instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                print("Checking ROB for {}".format(instruction.rs))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                print("Checking ROB for {}".format(instruction.rt))
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)
            elif instruction.op == "Sub":
                # Sub: Rd = Rs - Rt
                self.reservation_stations[tag] = {"busy":True, op:instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                print("Checking ROB for {}".format(instruction.rs))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                print("Checking ROB for {}".format(instruction.rt))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
            elif instruction.op == "Addi":
                # Addi: Rd = Rs + imm
                self.reservation_stations[tag] = {"busy":True, op:instruction.op, "qk":instruction.rs, "vk":instruction["imm"], "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                print("Checking ROB for {}".format(instruction.rs))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
            self.num_filled_stations += 1

        if self.num_filled_stations == self.size:
            print("Integer Adder {} is full!".format(self.fu_number))
        return self.num_filled_stations == self.size

    def tick(self):
        """ Go forward once cycle and perform calculations. Add a waiting instruction to be executed. If a station is done, put result on output buffer
        """
        # Check for ready instructions and add to queue
        for tag, instruction in self.reservation_stations.items():
            if instruction["vj"] != None and instruction["vk"] != None and tag not in self.ready_queue:
                self.ready_queue.append(tag)

        if self.countdown != 0 and self.executing == True:
            self.countdown -= 1
        elif self.countdown == 0 and self.executing == True:
            # Calculate answer
            if self.reservation_stations[self.current_tag]["op"] == "Add" or self.reservation_stations[self.current_tag]["op"] == "Addi":
                answer = int(self.reservation_stations[self.current_tag]["vj"]) + int(self.reservation_stations[self.current_tag]["vk"])
            else:
                answer = int(self.reservation_stations[self.current_tag]["vj"]) - int(self.reservation_stations[self.current_tag]["vk"])

            self.reservation_stations[self.current_tag]["value"] = answer
            # Put answer on result_buffer
            self.result_buffer.append({"dest":self.reservation_stations[self.current_tag]["dest"],"value":answer})
            # Free reservation station and reset tags/flags
            self.reservation_stations[self.current_tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "value":None, "dest":None}
            self.ready_queue.remove(self.current_tag)
            self.current_tag = None
            self.num_filled_stations -= 1
            self.executing = False
            self.countdown = self.cycles_in_ex

        # Begin executing next instruction if idle
        if self.executing == False and len(self.ready_queue) != 0:
            self.current_tag = self.ready_queue[0]
            self.executing = True
            self.countdown = self.cycles_in_ex


    def deliver(self):
        print("Delivering {} and removing from result buffer".format(self.result_buffer[0]))
        return self.result_buffer.pop(0)

    def save_state(self):
        """ Saves a copy of the reservation stations. Needs to be called when a branch instruction is issued from
        instruction buffer
        """
        self.history = self.reservation_stations.copy()

    def rewind(self):
        """ Used to reset the reservation stations back to the instruction before the branch occurred
        """
        self.reservation_stations = self.history.copy()
        self.num_filled_stations = sum([1 for key,val in self.reservation_stations.items() if val["busy"] == True])
        self.executing = False
        self.current_tag = None
    
    def read_cdb(self, bus_data):
        """ Read data on CDB and check if unit is looking for that value. Data bus formatted as {"dest":Destination, "value":Value}
        """
        for tag, station in self.reservation_stations.items():
            if station["qj"] == bus_data["dest"]:
                print("Station {} was waiting upon {} that is now updated to be {}".format(tag, station["qj"], bus_data["value"]))
                station["vj"] = bus_data["value"]
            if station["qk"] == bus_data["dest"]:
                print("Station {} was waiting upon {} that is now updated to be {}".format(tag, station["qk"], bus_data["value"]))
                station["vk"] = bus_data["value"]

    def __str__(self):
        if self.executing:
            output_string = "===================================================Integer Adder: Executing=================================================\n"
        else:
            output_string = "===================================================Integer Adder: Idle======================================================\n"

        output_string += "Tag\t\t|\tBusy\t|\tOp\t|\tvj\t|\tvk\t|\tqj\t|\tqk\t|\tvalue\n"
        output_string += "----------------------------------------------------------------------------------------------------------------------------------\n"
        for tag, value in self.reservation_stations.items():
            output_string += str(tag + "\t|\t" + str(value["busy"]) + "\t|\t" + str(value["op"]) + \
                "\t|\t" + str(value["vj"]) + "\t|\t" + str(value["vk"]) + "\t|\t" + str(value["qj"]) + \
                "\t|\t" + str(value["qk"]) + "\t|\t" + str(value["value"]) + "\n")
        output_string += "----------------------------------------------------------------------------------------------------------------------------------\n"
        output_string += "Result Buffer: {}\nReady Instruction Queue: {}".format(self.result_buffer, self.ready_queue)
        output_string += "\n==================================================================================================================================\n"
        return output_string

class ROB:
    def __init__(self, num_rob_entries, int_arf, fp_arf):
        self.num_entries = num_rob_entries
        self.fp_arf = fp_arf
        self.int_arf = int_arf
        self.rob = [0] * num_rob_entries
        for i in range(num_rob_entries):
            self.rob[i] = {"tag":"ROB{}".format(i+1),"type":None, "dest":None, "value":None, "finished":False}
        self.front = -1
        self.rear = -1

    def __str__(self): 
        output_string = "===================ROB====================\n"
        output_string += "Reg.\tType\tDest\tValue\tFinished\n"
        output_string += "------------------------------------------\n"
        if (self.rear >= self.front):  
            for i in range(self.front, self.rear + 1): 
                output_string += str(self.rob[i]) + "\n"  
        else: 
            for i in range(self.front, self.num_entries): 
                output_string += str(self.rob[i]) + "\n"
            for i in range(0, self.rear + 1): 
                output_string += str(self.rob[i]) + "\n"
        output_string += "==========================================\n"
        if ((self.rear + 1) % self.num_entries == self.front): 
            print("ROB is Full") 
        return output_string


    def enqueue(self, entry):
        """ Add an entry to the ROB, formatted as {"type": Add|Add.d|Sub|Sub.d|Mult.d|Ld|Sd|Beq|Bne, "dest":Destination}
        """
        if ((self.rear + 1) % self.num_entries == self.front):
            print("ROB is full!")
        elif self.front == -1:
            self.front = 0
            self.rear = 0
            entry["tag"] = "ROB{}".format(self.rear+1)
            self.rob[self.rear] = entry
        else:
            self.rear = (self.rear + 1) % self.num_entries
            entry["tag"] = "ROB{}".format(self.rear+1)
            self.rob[self.rear] = entry
    
    def dequeue(self):
        if self.front == -1:
            print("ROB is empty")
        elif self.front == self.rear:
            temp = self.rob[self.front]
            self.front = -1
            self.rear = -1
            return temp
        else:
            temp = self.rob[self.front]
            self.front = (self.front + 1) % self.num_entries
            return temp

    def read_cdb(self, bus_data):
        """ Read data on CDB and check if unit is looking for that value. Data bus formatted as {"dest":Destination, "value":Value}
        """
        for entry in self.rob:
            if entry["dest"] == bus_data["dest"]:
                entry["value"] = bus_data["value"]
                entry["finished"] = True
                if self.rob[self.front] == entry:
                    if entry["type"] == "Ld" or entry["type"] == "Sd":
                        print("Load/Store instruction ready to commit {} to load/store queue".format(entry))
                        self.mem_commit(bus_data["dest"])
                    else:
                        print("Ready to commit {} from ROB to ARF_FP and ARF_INT. **** TODO **** Don't forget to dequeue() and wipe result from RAT!".format(entry))
                        self.commit(bus_data["dest"])
    
    def commit(self, register_name):
        entry_index = self.rob.index(register_name)
        if self.rob[entry_index]["finished"] and self.rob[entry_index]["type"] not in ["Sd", "Ld"]:
            if "F" in self.rob[entry_index]["dest"]:
                print("Committing {} - {} to FP ARF".format(register_name, value))
                self.fp_arf[register_name] = value
                # Dequeue

            elif "R" in self.rob[entry_index]["dest"]:
                print("Committing {} - {} to INT ARF".format(register_name, value))
                self.int_arf[register_name] = value
                # Dequeue

    
    def mem_commit(self, register_name):
        if self.rob[register_name]["type"] in ["Sd", "Ld"]:
            print("Mem Committing {} - {} to Load/Store Queue")
            # TODO

    def request(self, register_name):
        if "ROB" in register_name:
            print("Requesting {} from the ROB registers".format(register_name))
            entry_index = self.rob.index(register_name)
            if self.rob[entry_index]["value"] == None:
                print("{} has no result, returning None".format(register_name))
            else:
                print("{} has value {}".format(register_name, self.rob[entry_index]["value"]))
                return self.rob[entry_index]["value"]
        elif "R" in register_name:
            print("Requesting {} from the INT ARF".format(register_name))
            return self.int_arf[register_name]
        elif "F" in register_name:
            print("Requesting {} from the FP ARF".format(register_name))
            return self.fp_arf[register_name]

class BTB:
    def __init__(self):
        self.entries = {i:False for i in range(8)}
        self.branch_pc = 0
        self.branch_address = 0
    
    def issue(self, address, current_pc, offset):
        """ Function to insert an instruction into the reservation station
        """
        if address < 0 or address > 8:
            raise SegFaultException(" Out-of-Bounds BTB Address: {} is not in range (0,7)".format(address))
        else:
            if self.entries[address] == True:
                print("Predict TAKEN")
                self.branch_pc = current_pc
                self.branch_address = address
                new_pc = current_pc + 4 + offset * 4
                print("Old PC: {}\tNew PC: {}".format(current_pc, new_pc))
                return new_pc
            else:
                print("Predict NOT TAKEN")
                self.branch_pc = current_pc
                return current_pc + 4
    
    def update(self):
        """ Flip Taken/Not Taken in relevant entry if misprediction occurs
        """
        print("Correcting misprediction and returning address of instruction after mispredicted branch")
        self.entries[self.branch_address] = not self.entries[self.branch_address]
        return self.branch_pc + 4

    def read_cdb(self, data_bus):
        """ Read data on CDB and check if unit is looking for that value. Data bus formatted as {"dest":Destination, "value":Value}
        """
        if self.entries[entry] != value:
            print("*MISPREDICTION* Stall a cycle to 1) Recover RAT 2) Reset Reservation Stations 3) Clear ROB entries past branch instruction")
        else:
            self.entries[entry] = value

# This only runs if we call `python3 functional_units.py` from the command line
if __name__ == "__main__":
    # Assume 16 maximum registers for the integer and floating_point register files
    int_arf = {"R{}".format(i):0 for i in range(1,33)}
    fp_arf = {"F{}".format(i):0.0 for i in range(1,33)}

    # Initialize ROB and provide it with the ARFs
    rob = ROB(4, fp_arf, int_arf)
    print(rob)
    rob.enqueue({"type":"Add.d", "dest":"R1"})
    print(rob)
    rob.enqueue({"type":"Sub.d", "dest":"R2"})
    print(rob)
    rob_output = rob.dequeue() # This contains the ROB entry tag to be purged from the RAT
    print(rob)
    print(rob_output)
