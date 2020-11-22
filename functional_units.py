import os
import sys
from reading_input import *

class Instruction():
    """ Basic class for the Instruction objects. Args formatted as [string op, string rs, string rt, string rd]
    """
    def __init__(self, *args):

        """ Initialization function for the Instruction object.
        Args:
            Depends upon whether R-type, I-type, J-type, or no-op
        """
        # NOOP
        self.string = ""
        if args[0] == "NOP":
            self.op = "NOP"
            self.string = "NOP"
            self.type = "NOP"
        else:
            # R-type instruction
            # args should be formatted as:
            # [string op, string rs, string rt,, string rd, string shamt, string funct]
            args = args[0] #  the instruction queue
            if args[0] in ["Add.d", "Add", "Sub", "Sub.d", "Mult.d"]:
                self.type = "r"
                self.op = args[0]
                self.rd = args[1].strip(",")
                self.rs = args[2].strip(",")
                self.rt = args[3].strip(",")
                self.string = ""
                for arg in args:
                    self.string += str(arg) + " "
            # I-type instruction
            # args should be formatted as:
            #   [string op, string rs, string rt, string address_immediate]
            elif args[0] in ["Beq", "Bne", "Ld", "Sd"]:
                self.type = "i"
                self.op = args[0]
                self.rs = args[1]
                if args[0] in ["Bne", "Beq"]:
                    self.rs = args[2].strip(",")
                    self.rt = args[3].strip(",")
                    self.addr_imm = args[3].strip(",")
                elif args[0] in ["Ld","Sd"]:
                    self.rd = args[2].split("(")[1].strip(")")
                    self.addr_imm = float(args[2].split("(")[0])
                elif args[0] in ["Addi"]:
                    self.rt = args[2].strip(",")
                    self.rs = args[3].strip(",")
                    self.addr_imm = args[3].strip(",")
                self.string = ""
                for arg in args:
                    self.string += str(arg) + " "
            # Addi instruction only
            elif args[0] == "Addi":
                self.type = "i"
                self.op = args[0] 
                self.rt = args[1].strip(",")
                self.rs = args[2].strip(",")
                self.addr_imm = args[3].strip(",")
                self.string = ""
                for arg in args:
                    self.string += str(arg) + " "

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
        self.total_instructions = len(self.instruction_list)

    def fetch(self, pc):
        """ Get the next instruction from the buffer
        """
        # If we reach the end of the instructions, return a NOP
        if pc == 4*len(self.instruction_list):
            print("NO MORE INSTRUCTIONS!")
            return Instruction(["NOP"])

        print("Get {} / 4".format(pc))
        return self.instruction_list[int(pc / 4)]


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

    def __init__(self, num_reservations_stations, cycles_in_ex, fu_number, rob):
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

        # Register the rob to make requests
        self.rob = rob

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
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "vk":None, "vj":None, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)
            elif instruction.op == "Div.d":
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
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
            if instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] == 10 and new_instruction_began != True:
                instruction["countdown"] -= 1
                new_instruction_began = True
            elif instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] < 10 and instruction["countdown"] != 0:
                instruction["countdown"] -= 1
            elif instruction["countdown"] == 0:
                print("{} finished!".format(tag))
                if instruction["op"] == "Mult.d":
                    answer = float(self.reservation_stations[tag]["vj"]) * float(self.reservation_stations[tag]["vk"])
                else:
                    answer = float(self.reservation_stations[tag]["vj"]) / float(self.reservation_stations[tag]["vk"])

                self.reservation_stations[tag]["value"] = answer
                self.result_buffer.append({"dest":self.reservation_stations[tag]["dest"],"value":answer,"op":self.reservation_stations[tag]["op"]})
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
        output_string = "===================================================FP Multiply Unit==============================================================================\n"
        output_string += "Tag\t\t|\tBusy\t|\tOp\t|\tvj\t|\tvk\t|\tqj     |    qk    |    Countdown   |   Destination\n"
        output_string += "-------------------------------------------------------------------------------------------------------------------------------------------------\n"
        for tag, value in self.reservation_stations.items():
            output_string += str(tag + "\t|\t" + str(value["busy"]) + "\t|\t" + str(value["op"]) + \
                "\t|\t" + str(value["vj"]) + "\t|\t" + str(value["vk"]) + "\t|\t" + str(value["qj"]) + \
                "    |   " + str(value["qk"]) + "  |       " + str(value["countdown"]) + "      |   " + str(value["dest"]) + "\n")
        output_string += "-------------------------------------------------------------------------------------------------------------------------------------------------\n"
        output_string += "Result Buffer: {}".format(self.result_buffer)
        output_string += "\n=================================================================================================================================================\n"
        return output_string

class FPAdder:
    """ The FPAdder class encapsulates all functionality of the parameterizable hardware Floating Point Adder.
    """

    def __init__(self, num_reservations_stations, cycles_in_ex, fu_number, rob):
        """ Initialization function for the FPAdder to specify parameters.
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

        # Register the rob to make requests
        self.rob = rob

    def issue(self, instruction):
        """ Function to insert an instruction into the reservation station
        """
        # Check if there's enough room in the reservation stations
        if self.num_filled_stations >= len(self.reservation_stations):
            return Warning("Reservation Station of FPAdder {} is full".format(self.fu_number))
        else:
            tag = [tag for tag, values in self.reservation_stations.items() if values["busy"] == False][0]
            if instruction.op == "Add.d":
                # Add.d: Fd = Fs + Ft
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)

            elif instruction.op == "Sub.d":
                # Sub.d: Fd = Fs - Ft
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)
                
            self.num_filled_stations += 1

        if self.num_filled_stations == len(self.reservation_stations):
            print("FP Adder {} is now full!".format(self.fu_number))
        return self.num_filled_stations == len(self.reservation_stations)

    def deliver(self):
        return self.result_buffer.pop(0)

    def tick(self):
        """ Go forward once cycle and perform calculations. Add a waiting instruction to be executed. If a station is done, put result on output buffer
        """
        # Let ready instructions operate
        new_instruction_began = False
        for tag, instruction in self.reservation_stations.items():
            if instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] == 10 and new_instruction_began != True:
                instruction["countdown"] -= 1
                new_instruction_began = True
            elif instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] < 10 and instruction["countdown"] != 0:
                instruction["countdown"] -= 1
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
        output_string = "===================================================FP Adder Unit====================================================================================\n"
        output_string += "Tag\t\t|\tBusy\t|\tOp\t|\tvj\t|\tvk\t|\tqj      |    qk      |     value     |     Countdown\n"
        output_string += "----------------------------------------------------------------------------------------------------------------------------------------------------\n"
        for tag, value in self.reservation_stations.items():
            output_string += str(tag + "\t|\t" + str(value["busy"]) + "\t|\t" + str(value["op"]) + \
                "\t|\t" + str(value["vj"]) + "\t|\t" + str(value["vk"]) + "\t|\t" + str(value["qj"]) + \
                "    |    " + str(value["qk"]) + "     |     " + str(value["value"]) + "     |     " + str(value["countdown"]) + "\n")
        output_string += "----------------------------------------------------------------------------------------------------------------------------------------------------\n"
        output_string += "Result Buffer: {}".format(self.result_buffer)
        output_string += "\n====================================================================================================================================================\n"
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
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "vj":None, "vk":None, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                print("Checking ROB for {}".format(instruction.rs))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                print("Checking ROB for {}".format(instruction.rt))
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)
            elif instruction.op == "Sub":
                # Sub: Rd = Rs - Rt
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "vj":None, "vk":None, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd}
                print("Checking ROB for {}".format(instruction.rs))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                print("Checking ROB for {}".format(instruction.rt))
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)
            elif instruction.op == "Addi":
                # Addi: Rt = Rs + imm
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":None,"vk":0, "vj":instruction.addr_imm, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rt}
                print("Checking ROB for {}".format(instruction.rs))
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
            elif instruction.op == "Subi":
                # Addi: Rt = Rs - imm
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":None,"vk":0, "vj":instruction.addr_imm, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rt}
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

        output_string += "Tag\t\t|\tBusy\t|\tOp\t|\tvj\t|\tvk\t|\tqj      |    qk    |     value\n"
        output_string += "----------------------------------------------------------------------------------------------------------------------------\n"
        for tag, value in self.reservation_stations.items():
            output_string += str(tag + "\t|\t" + str(value["busy"]) + "\t|\t" + str(value["op"]) + \
                "\t|\t" + str(value["vj"]) + "\t|\t" + str(value["vk"]) + "\t| \t" + str(value["qj"]))
            output_string += "    |    " + str(value["qk"]) + "    |    " + str(value["value"]) + "\n"
        output_string += "----------------------------------------------------------------------------------------------------------------------------\n"
        output_string += "Result Buffer: {}\nReady Instruction Queue: {}".format(self.result_buffer, self.ready_queue)
        output_string += "\n============================================================================================================================\n"
        return output_string

class ROB:
    def __init__(self, num_rob_entries, int_arf, fp_arf):
        self.num_entries = num_rob_entries
        self.int_arf = {"R{}".format(i):0 for i in range(1,int_arf)}
        self.fp_arf = {"F{}".format(i):0.0 for i in range(1,fp_arf)}
        self.rob = [0] * num_rob_entries
        for i in range(num_rob_entries):
            self.rob[i] = {"tag":"ROB{}".format(i+1),"op":None, "dest":None, "value":None, "finished":False}
        self.front = -1
        self.rear = -1
        self.LSQ = None
        self.RAT = None

    def __str__(self):
        output_string = "===================ROB====================\n"
        output_string += "Reg.\tOp\tDest\tValue\tFinished\n"
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

    def tick(self):
        # Check to see if the entry at the head is ready to commit. If so, commit/mem_commit and dequeue it
        #print("ROB Instruction in the front: {}".format(self.rob[self.front]))
        if self.rob[self.front]["finished"] == True:
            entry = self.rob[self.front]
            if entry["op"] == "Ld" or entry["op"] == "Sd":
                self.mem_commit(entry)
                self.dequeue()
            else:
                self.commit(entry)
                self.dequeue()

    def enqueue(self, entry):
        """ Add an entry to the ROB, formatted as {"op": Add|Add.d|Sub|Sub.d|Mult.d|Ld|Sd|Beq|Bne, "dest":Destination}
        """
        if ((self.rear + 1) % self.num_entries == self.front):
            print("ROB is full!")
            return None
        elif self.front == -1:
            self.front = 0
            self.rear = 0
            entry["tag"] = "ROB{}".format(self.rear+1)
            entry["finished"] = False
            self.rob[self.rear] = entry
        else:
            self.rear = (self.rear + 1) % self.num_entries
            entry["tag"] = "ROB{}".format(self.rear+1)
            entry["finished"] = False
            self.rob[self.rear] = entry
        return self.rob[self.rear]["tag"]

    def dequeue(self):
        """ Remove an entry to the ROB, returns the popped entry as {"op": Add|Add.d|Sub|Sub.d|Mult.d|Ld|Sd|Beq|Bne, "dest":Destination}
        """
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
            if entry["tag"] == bus_data["dest"]:
                entry["value"] = bus_data["value"]
                entry["finished"] = True
                print("!WB {}".format(entry))

    def commit(self, entry):
        if entry["finished"] and entry["op"] not in ["Sd", "Ld"]:
            if "F" in entry["dest"]:
                print("!COMMIT {}".format(entry))
                self.fp_arf[entry["dest"]] = entry["value"]
            elif "R" in entry["dest"]:
                print("!COMMIT {}".format(entry))
                self.int_arf[entry["dest"]] = entry["value"]
            self.RAT.commit_update(entry["tag"])

    def mem_commit(self, register_name):
        if entry["op"] in ["Sd", "Ld"]:
            print("!COMMIT {}".format(entry))
            self.LSQ.mem_commit(entry["tag"])

    def request(self, register_name):
        if "ROB" in register_name:
            #print("Requesting {} from the ROB registers".format(register_name))
            entry_index = self.rob.index(register_name)
            if self.rob[entry_index]["value"] == None:
                #print("{} has no result, returning None".format(register_name))
                return None
            else:
                #print("{} has value {}".format(register_name, self.rob[entry_index]["value"]))
                return self.rob[entry_index]["value"]
        elif "R" in register_name:
            #print("Requesting {} from the INT ARF".format(register_name))
            return self.int_arf[register_name]
        elif "F" in register_name:
            #print("Requesting {} from the FP ARF".format(register_name))
            return self.fp_arf[register_name]

    def register_arfs(self, int_arf, fp_arf):
        """ Initializes the FP ARF and INT ARF values based on what comes from the input file
        """
        for key, value in int_arf.items():
            #print("Registering {} - {}".format(key, value))
            self.int_arf[key] = value
        for key, value in fp_arf.items():
            #print("Registering {} - {}".format(key, value))
            self.fp_arf[key] = value

        print("INT ARF: {}\nFP ARF: {}".format(self.int_arf, self.fp_arf))

    def save_state(self):
        """ Saves a copy of the rob. Needs to be called when a branch instruction is issued from instruction buffer
        """
        self.history = self.rob.copy()
        self.front_copy = self.front
        self.rear_copy = self.rear

    def rewind(self):
        """ Resets the rob back to the instruction before the branch occurred
        """
        self.rob = self.history.copy()
        self.front = self.front_copy
        self.rear = self.rear

class BTB:
    def __init__(self, rob, rat, int_adders, fp_adders, fp_multipliers):
        self.entries = {i:False for i in range(8)}
        self.branch_pc = 0
        self.branch_entry = -1
        self.correct = None
        self.new_pc = 0

        # Register any unit that needs to have save_state() or rewind() called
        self.rob = rob
        self.rat = rat
        self.int_adders = int_adders
        self.fp_adders = fp_adders
        self.fp_multipliers = fp_multipliers

    def __str__(self):
        output_string = "========= BTB ==========\n"
        output_string += "Entry\tTaken\tIn Use\n"
        output_string += "-----------------------\n"
        for entry, taken in self.entries.items():
            output_string += "{}\t{}".format(entry, taken)
            if self.branch_entry == entry:
                output_string += "\tYES"
            output_string += "\n"
        output_string += "========================\n"
        return output_string

    def fetch_pc(self):
        if self.branch_entry != -1:
            return None
        else:
            return self.new_pc

    def issue(self, instruction, current_pc):
        """ Function to issue instruction to the BTB. Will return value of predicted PC
        """
        if instruction.op not in ["Bne", "Beq"]:
            raise Warning("This is not a Branch instruction!")
        else:
            # Issue save_state() to all relevant units
            self.rob.save_state()
            self.rat.save_state()
            for int_adder in self.int_adders:
                int_adder.save_state()
            for fp_adder in self.fp_adders:
                fp_adder.save_state()
            for fp_multiplier in self.fp_multipliers:
                fp_multiplier.save_state()
            self.rs = instruction.rs
            self.rt = instruction.rt
            self.predicted_offset = int(instruction.addr_imm)
            self.branch_entry = current_pc % 8
            # Make prediction and return predicted PC
            if self.entries[current_pc % 8] == True:
                print("Predict TAKEN")
                self.branch_pc = current_pc
                self.prediction = True
                new_pc = current_pc + self.predicted_offset * 4
                #print("Old PC: {}\tNew PC: {}".format(current_pc, new_pc))
                self.new_pc = new_pc
            else:
                print("Predict NOT TAKEN")
                self.prediction = False
                self.branch_pc = current_pc
                self.new_pc = current_pc + 4

    def tick(self):
        """ Will check for misprediction, correct prediction, or no prediction and issue PC accordingly
        """
        if self.correct is False:
            print("***MISPREDICTION*** Stall a cycle")
            self.correct = None
            self.branch_entry = -1
            # Call rewind on all relevant units
            self.rob.rewind()
            self.rat.rewind()
            for int_adder in self.int_adders:
                int_adder.rewind()
            for fp_adder in self.fp_adders:
                fp_adder.rewind()
            for fp_multiplier in self.fp_multipliers:
                fp_multiplier.rewind()
        elif self.correct is True:
            print("Branch resolution: correct prediction. PC going to {}*4 + 4".format(self.predicted_offset))
            # Reset all values if prediction is good
            self.correct = None
            self.rt = None
            self.rs = None
            self.branch_entry = -1

        if self.branch_entry == -1:
            self.new_pc += 4

    def read_cdb(self, data_bus):
        """ Read data on CDB and check if unit is looking for that value. Data bus formatted as {"dest":Destination, "value":Value, "op":Type of Instruction}
        """
        keys = list(data_bus.keys())
        if len(data_bus) > 0 and "op" in keys:
            if data_bus["op"] == "Beq":
                if self.prediction and data_bus["value"] == 0:
                    # Good prediction
                    #print("Good prediction")
                    self.correct = True
                else:
                    # Bad prediction
                    #print("Bad prediction")
                    self.correct = False
                    self.entries[self.branch_entry] = not self.entries[self.branch_entry]
            elif data_bus["op"] == "Bne":
                if self.prediction and data_bus["value"] != 0:
                    # Good prediction
                    self.correct = True
                else:
                    # Bad prediction
                    self.correct = False
                    self.entries[self.branch_entry] = not self.entries[self.branch_entry]

# This only runs if we call `python3 functional_units.py` from the command line
if __name__ == "__main__":
    # Assume 16 maximum registers for the integer and floating_point register files
    int_arf = {"R{}".format(i):0 for i in range(1,33)}
    fp_arf = {"F{}".format(i):0.0 for i in range(1,33)}

    # Initialize BTB and provide it with the relevant FUs
    # Bad RAT to just test stuff
    class RAT:
        def __init__(self):
            self.ree = 0
        def rewind(self):
            return True
        def save_state(self):
            return True
            
    rat = RAT()
    rob = ROB(4, int_arf, fp_arf)
    int_adders = [IntegerAdder(2, 2, i, rob) for i in range(2)]
    fp_adders = [FPAdder(2, 2, i, rob) for i in range(2)]
    fp_multipliers = [FPMultiplier(2, 2, i, rob) for i in range(2)]
    btb = BTB(rob, rat, int_adders, fp_adders, fp_multipliers)

    # Tick BTB
    current_pc = 0
    print(btb)
    btb.tick()
    print(btb)
    current_pc += 1

    # Issue instruction to BTB
    sample_branch = Instruction(["Beq", "R1", "R2", "3"])
    print("Instruction: {}".format(sample_branch))
    btb.issue(sample_branch, current_pc)
    print(btb)
    btb.tick()
    print(btb)
    current_pc += 1

    btb.tick()
    print(btb)
    current_pc += 1

    # BTB gets result from CDB that IS NOT what it's looking for
    btb.read_cdb({"dest":"R1", "value":10,"op":"Addi"})
    btb.tick()
    print(btb)
    current_pc += 1

    # BTB gets result from CDB that IS what it's looking for
    btb.read_cdb({"dest":"R1", "value":0,"op":"Beq"})
    btb.tick()
    print(btb)
    current_pc += 1

    btb.tick()
    print(btb)
    current_pc += 1
