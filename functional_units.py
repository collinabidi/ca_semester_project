import os
import sys
from reading_input import *

class Instruction():
    """ Basic class for the Instruction objects. Args formatted as [string op, string rs, string rt, string rd]
    """
    def __init__(self, *args, pc=None):

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
            self.pc = pc
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
                self.pc = pc
                self.string = ""
                for arg in args:
                    self.string += str(arg) + " "
            # I-type instruction
            # args should be formatted as:
            #   [string op, string rs, string rt, string address_immediate]
            elif args[0] in ["Beq", "Bne", "Ld", "Sd"]:
                self.type = "i"
                self.op = args[0]
                self.pc = pc
                self.rt = args[1].strip(",")
                if args[0] in ["Bne", "Beq"]:
                    self.rs = args[2].strip(",")
                    self.addr_imm = args[3].strip(",")
                elif args[0] in ["Ld","Sd"]:
                    self.rs = args[2].split("(")[1].strip(")")
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
                self.pc = pc
                self.op = args[0]
                self.rt = args[1].strip(",")
                self.rs = args[2].strip(",")
                self.addr_imm = args[3].strip(",")
                self.string = ""
                for arg in args:
                    self.string += str(arg) + " "

    def __str__(self):
        return self.string + "\tPC: {}".format(self.pc)

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
            self.instruction_list[i] = Instruction(inst.strip("\n").strip(",").split(" "), pc=i*4)
        self.index = 0
        self.total_instructions = len(self.instruction_list)
        self.out_of_bounds_hit = False

    def fetch(self, pc):
        """ Get the next instruction from the buffer
        """
        # If we reach the end of the instructions, return a NOP
        if pc == 4*len(self.instruction_list):
            print("NO MORE INSTRUCTIONS!")
            self.out_of_bounds_hit = True
            return Instruction(["NOP"])

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
        self.last_issued = None
        self.size = num_reservations_stations
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
        if self.num_filled_stations >= self.size:
            return Warning("Reservation Station of FPMultiplier {} is full".format(self.fu_number))
        else:
            # Generate tag and fill station
            free_stations = [tag for tag, values in self.reservation_stations.items() if values["busy"] == False]
            tag = free_stations[0]
            self.last_issued = tag
            self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "vk":None, "vj":None, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd, "instruction":instruction}
            self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
            self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)
            self.num_filled_stations += 1
            if self.num_filled_stations == self.size:
                print("FP Multiplier {} is now full!".format(self.fu_number))
        return None

    def deliver(self):
        """ Deliver the result to the CDB and remove it from the buffer
        """
        return self.result_buffer.pop(0)

    def tick(self, tracker):
        """ Go forward once cycle and perform calculations. Add a waiting instruction to be executed. If a station is done, put result on output buffer
        """
        new_instruction_began = False
        for tag, instruction in self.reservation_stations.items():
            if self.last_issued != tag:
                if instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] == self.cycles_in_ex and new_instruction_began != True:
                    instruction["countdown"] -= 1
                    new_instruction_began = True
                    tracker.update("execute", {"pc":instruction["instruction"].pc})
                elif self.last_issued == tag:
                    self.last_issued = None
                elif instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] < self.cycles_in_ex and instruction["countdown"] != 0:
                    instruction["countdown"] -= 1
                elif instruction["countdown"] == 0:
                    answer = float(self.reservation_stations[tag]["vj"]) * float(self.reservation_stations[tag]["vk"])
                    self.reservation_stations[tag]["value"] = answer
                    self.result_buffer.append({"dest":self.reservation_stations[tag]["dest"],"value":answer,"op":self.reservation_stations[tag]["op"]})
                    self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "value":None, "countdown":self.cycles_in_ex, "dest":None}
                    self.num_filled_stations -= 1
            else:
                self.last_issued = None

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

    def read_cdb(self, bus_data, tracker=None):
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
        self.last_issued = None
        self.size = num_reservations_stations
        for i in range(num_reservations_stations):
            tag = "FPADD_{}_{}".format(str(fu_number), str(i))
            self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "value":None, "countdown":self.cycles_in_ex, "dest":None, "instruction":None}

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
        if self.num_filled_stations >= self.size:
            return Warning("Reservation Station of FPAdder {} is full".format(self.fu_number))
        else:
            tag = [tag for tag, values in self.reservation_stations.items() if values["busy"] == False][0]
            self.last_issued = tag
            if instruction.op == "Add.d":
                # Add.d: Fd = Fs + Ft
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd, "instruction":instruction}
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)

            elif instruction.op == "Sub.d":
                # Sub.d: Fd = Fs - Ft
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd, "instruction":instruction}
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)

            self.num_filled_stations += 1

        if self.num_filled_stations == self.size:
            print("FP Adder {} is now full!".format(self.fu_number))
        return None

    def deliver(self):
        return self.result_buffer.pop(0)

    def tick(self, tracker):
        """ Go forward once cycle and perform calculations. Add a waiting instruction to be executed. If a station is done, put result on output buffer
        """
        # Let ready instructions operate
        new_instruction_began = False
        for tag, instruction in self.reservation_stations.items():
            if tag != self.last_issued:
                if instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] == self.cycles_in_ex and new_instruction_began != True:
                    instruction["countdown"] -= 1
                    new_instruction_began = True
                    tracker.update("execute", {"pc":instruction["instruction"].pc})
                elif instruction["vj"] != None and instruction["vk"] != None and instruction["countdown"] < self.cycles_in_ex and instruction["countdown"] != 0:
                    instruction["countdown"] -= 1
                elif instruction["countdown"] == 0:
                    # Calculate value
                    if instruction["op"] == "Add.d":
                        answer = float(self.reservation_stations[tag]["vj"]) + float(self.reservation_stations[tag]["vk"])
                    else:
                        answer = float(self.reservation_stations[tag]["vk"]) - float(self.reservation_stations[tag]["vj"])

                    self.reservation_stations[tag]["value"] = answer
                    self.result_buffer.append({"dest":self.reservation_stations[tag]["dest"],"value":answer,"op":self.reservation_stations[tag]["op"]})
                    self.reservation_stations[tag] = {"busy":False, "op":None,"vj":None, "vk":None, "qj":None, "qk":None, "value":None, "countdown":self.cycles_in_ex, "dest":None}
                    self.num_filled_stations -= 1
                elif instruction["qj"] != None or instruction["qk"] != None:
                    print("{} still waiting on {} or {}".format(tag, instruction["qj"], instruction["qk"]))

            self.last_issued = None

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

    def read_cdb(self, bus_data, tracker=None):
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
        self.last_issued = None
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
            # Flag marks reservation station as just issued, so don't execute during next tick() cycle
            tag = [tag for tag, values in self.reservation_stations.items() if values["busy"] == False][0]
            self.last_issued = tag
            if instruction.op == "Add":
                # Add: Rd = Rs + Rt
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "vj":None, "vk":None, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd, "instruction":instruction}
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)
            elif instruction.op == "Sub":
                # Sub: Rd = Rs - Rt
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "vj":None, "vk":None, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rd, "instruction":instruction}
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)
            elif instruction.op == "Addi":
                # Addi: Rt = Rs + imm
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":None,"vk":None, "vj":instruction.addr_imm, "countdown":self.cycles_in_ex, "value":None, "dest":instruction.rt, "instruction":instruction}
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
            elif instruction.op in ["Bne", "Beq"]:
                # Bne: Rt != Rs? via subtraction
                # Beq: Rt == Rs? via subtraction
                self.reservation_stations[tag] = {"busy":True, "op":instruction.op, "qk":instruction.rs, "qj":instruction.rt, "vj":None, "vk":None, "countdown":self.cycles_in_ex, "value":None, "dest":"BTB", "instruction":instruction}
                self.reservation_stations[tag]["vk"] = self.rob.request(instruction.rs)
                self.reservation_stations[tag]["vj"] = self.rob.request(instruction.rt)

            self.num_filled_stations += 1

        if self.num_filled_stations == self.size:
            print("Integer Adder {} is full!".format(self.fu_number))
        return None

    def tick(self, tracker):
        """ Go forward once cycle and perform calculations. Add a waiting instruction to be executed. If a station is done, put result on output buffer
        """
        # Check for ready instructions and add to queue
        for tag, instruction in self.reservation_stations.items():
            if instruction["vj"] != None and instruction["vk"] != None and tag not in self.ready_queue and tag != self.last_issued:
                self.ready_queue.append(tag)
                #print("!EXECUTE BEGAN: {}".format(instruction["instruction"]))
                tracker.update("execute", {"pc":instruction["instruction"].pc})
            elif tag == self.last_issued:
                self.last_issued = None

        if self.countdown != 0 and self.executing == True:
            self.countdown -= 1
        elif self.countdown == 0 and self.executing == True:
            # Calculate answer
            if self.reservation_stations[self.current_tag]["op"] == "Add" or self.reservation_stations[self.current_tag]["op"] == "Addi":
                answer = int(self.reservation_stations[self.current_tag]["vj"]) + int(self.reservation_stations[self.current_tag]["vk"])
            else:
                # Sub OR Bne OR Beq
                answer = int(self.reservation_stations[self.current_tag]["vk"]) - int(self.reservation_stations[self.current_tag]["vj"])

            self.reservation_stations[self.current_tag]["value"] = answer
            
            # Put answer on result_buffer
            self.result_buffer.append({"dest":self.reservation_stations[self.current_tag]["dest"],"value":answer,"op":self.reservation_stations[self.current_tag]["op"]})
            
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

    def read_cdb(self, bus_data, tracker=None):
        """ Read data on CDB and check if unit is looking for that value. Data bus formatted as {"dest":Destination, "value":Value}
        """
        for tag, station in self.reservation_stations.items():
            if station["qj"] == bus_data["dest"]:
                station["vj"] = bus_data["value"]
            if station["qk"] == bus_data["dest"]:
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
        self.int_arf = {"R{}".format(i):0 for i in range(0,int_arf)}
        self.fp_arf = {"F{}".format(i):0.0 for i in range(0,fp_arf)}
        self.rob = [0] * num_rob_entries
        for i in range(num_rob_entries):
            self.rob[i] = {"tag":"ROB{}".format(i+1),"op":None, "dest":None, "value":None, "finished":False, "instruction":None}
        self.front = -1
        self.rear = -1
        self.rob_empty = True
        self.last_wb = None
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

    def tick(self, tracker):
        # Special case: Sd needs to check the LSQ to set it's finished status
        if self.rob[self.front]["op"] == "Sd":
            if self.LSQ.check_mem_commit(self.rob[self.front]["tag"]) == True:
                self.rob[self.front]["finished"] = True

        # Check to see if the entry at the head is ready to commit. If so, commit/mem_commit and dequeue it
        if self.rob[self.front]["finished"] == True:
            entry = self.rob[self.front]
            if self.last_wb != entry["tag"]:
                if entry["op"] == "Ld" or entry["op"] == "Sd":
                    tracker.update("commit",{"pc":entry["instruction"].pc}) #@Collin - changed this from "memory" to "commit"
                    self.mem_commit(entry)
                    return self.dequeue()
                else:
                    tracker.update("commit",{"pc":entry["instruction"].pc})
                    self.commit(entry)
                    return self.dequeue()
        self.last_wb = None

    def enqueue(self, entry):
        """ Add an entry to the ROB, formatted as
            {"op": Add|Add.d|Sub|Sub.d|Mult.d|Ld|Sd|Beq|Bne, "dest":Destination, "instruction":Instruction}
        """
        self.rob_empty = False
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
        """ Remove an entry to the ROB, returns the popped entry as
            {"op": Add|Add.d|Sub|Sub.d|Mult.d|Ld|Sd|Beq|Bne, "dest":Destination, "instruction":Instruction}
        """
        if self.front == -1:
            print("ROB is empty")
        elif self.front == self.rear:
            self.rob_empty = True
            temp = self.rob[self.front]
            self.front = -1
            self.rear = -1
            return temp
        else:
            temp = self.rob[self.front]
            self.front = (self.front + 1) % self.num_entries
            return temp

    def read_cdb(self, bus_data, tracker=None):
        """ Read data on CDB and check if unit is looking for that value. Data bus formatted as
            {"dest":Destination, "value":Value, "instruction":Instruction}
        """
        for entry in self.rob:
            if entry["tag"] == bus_data["dest"]:
                entry["value"] = bus_data["value"]
                entry["finished"] = True
                tracker.update("wrtback", {"pc":entry["pc"]})
                self.last_wb = entry["tag"]

    def commit(self, entry):
        if entry["finished"] and entry["op"] not in ["Sd"]:
            if "F" in entry["dest"]:
                self.fp_arf[entry["dest"]] = entry["value"]
            elif "R" in entry["dest"]:
                self.int_arf[entry["dest"]] = entry["value"]
            self.RAT.commit_update(entry["tag"])

    def mem_commit(self, entry):
        if entry["op"] in ["Sd", "Ld"]:
            if entry["op"] == "Ld":
                if "F" in entry["dest"]:
                    self.fp_arf[entry["dest"]] = entry["value"]
                elif "R" in entry["dest"]:
                    self.int_arf[entry["dest"]] = entry["value"]
                self.RAT.commit_update(entry["tag"])
            self.LSQ.mem_commit(entry["tag"])

    def request(self, register_name):
        if "ROB" in register_name:
            matching_entry = next((entry for entry in self.rob if entry["tag"] == register_name), None)
            if matching_entry == None or "value" not in matching_entry.keys():
                return None
            else:
                return matching_entry["value"]
        elif "R" in register_name:
            return self.int_arf[register_name]
        elif "F" in register_name:
            return self.fp_arf[register_name]

    def register_arfs(self, int_arf, fp_arf):
        """ Initializes the FP ARF and INT ARF values based on what comes from the input file
        """
        for key, value in int_arf.items():
            self.int_arf[key] = value
        for key, value in fp_arf.items():
            self.fp_arf[key] = value
        
        # Register un-writeable R0
        self.int_arf["R0"] = 0

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
        self.rear = self.rear_copy

class BTB:
    def __init__(self, rob, rat, int_adders, fp_adders, fp_multipliers):
        self.entries = {i:False for i in range(8)}
        self.branch_pc = 0
        self.branch_entry = -1
        self.correct = None
        self.new_pc = 0
        self.predicted_offset = 0
        self.actual_result = None
        self.f_stall = False
        self.current_instruction = None

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

    def fetch_pc(self, f_stall=False):
        if self.branch_entry != -1 or f_stall == True:
            self.f_stall = f_stall
            return None

        elif self.branch_entry == -1 and f_stall == False:
            self.f_stall = f_stall
            return self.new_pc

    def issue(self, instruction, current_pc):
        """ Function to issue instruction to the BTB. Will return value of predicted PC
        """
        if instruction.op not in ["Bne", "Beq"]:
            raise Warning("This is not a Branch instruction!")
        else:
            # Issue save_state() to all relevant units
            print(">>>>>>>>>>>> SAVE STATE <<<<<<<<<<<<")
            self.rob.save_state()
            self.rat.save_state()
            for _, int_adder in self.int_adders.items():
                int_adder.save_state()
            for _, fp_adder in self.fp_adders.items():
                fp_adder.save_state()
            for _, fp_multiplier in self.fp_multipliers.items():
                fp_multiplier.save_state()
            self.rs = instruction.rs
            self.rt = instruction.rt
            self.current_instruction = instruction
            self.predicted_offset = int(instruction.addr_imm)
            self.branch_entry = current_pc % 8

            # Make prediction based on what's in the BTB entry PC
            if self.entries[current_pc % 8] == True:
                # Predict taken
                self.branch_pc = self.new_pc
                self.prediction = True
                self.predicted_pc = self.new_pc + 4 + self.predicted_offset * 4
            else:
                # Predict not taken
                self.branch_pc = self.new_pc
                self.prediction = False
                self.predicted_pc = self.new_pc + 4

    def tick(self, tracker=None):
        """ Will check for misprediction, correct prediction, or no prediction and issue PC accordingly
        """
        if self.correct is None:
            if self.branch_entry == -1 and not self.f_stall:
                self.new_pc = self.new_pc + 4
            elif self.branch_entry != -1 or self.f_stall:
                self.new_pc = self.new_pc
        elif self.correct is False:
            tracker.update("wrtback", {"pc":self.current_instruction.pc})
            self.current_instruction = None
            self.correct = None
            self.entries[self.branch_entry] = not self.entries[self.branch_entry]
            self.branch_entry = -1
            if self.actual_result == True:
                self.new_pc = self.branch_pc + self.predicted_offset * 4 + 4
            else:
                self.new_pc = self.branch_pc + 4
            self.actual_result = None
            # Call rewind on all relevant units
            """
            self.rob.rewind()
            self.rat.rewind()
            for int_adder in self.int_adders:
                int_adder.rewind()
            for fp_adder in self.fp_adders:
                fp_adder.rewind()
            for fp_multiplier in self.fp_multipliers:
                fp_multiplier.rewind()
            """
        elif self.correct is True:
            # Reset all values if prediction is good
            tracker.update("wrtback", {"pc":self.current_instruction.pc})
            self.current_instruction = None
            self.correct = None
            self.branch_entry = -1
            # Branch actually taken
            if self.actual_result == True:
                self.new_pc = self.branch_pc + self.predicted_offset * 4 + 4
            else: # Branch not actually taken
                self.new_pc = self.branch_pc + 4
            self.actual_result = None

    def read_cdb(self, data_bus, tracker=None):
        """ Read data on CDB and check if unit is looking for that value. Data bus formatted as
        {"dest":Destination, "value":Value, "op":Type of Instruction}
        """
        if len(data_bus) > 0 and "op" in list(data_bus.keys()) and data_bus["op"] in ["Beq","Bne"]:
            if data_bus["op"] == "Beq":
                if data_bus["value"] == 0:
                    # Beq Taken
                    self.actual_result = True
                else:
                    # Beq Not Taken
                    self.actual_result = False
            elif data_bus["op"] == "Bne":
                if data_bus["value"] != 0:
                    # Bne Taken
                    self.actual_result = True
                else:
                    # Bne Not Taken
                    self.actual_result = False

            # See if we were right
            if self.actual_result == self.prediction:
                self.correct = True
            elif self.actual_result != self.prediction:
                self.correct = False
