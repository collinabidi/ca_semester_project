import re

class input_parser():
    def __init__(self, filename):
        # open text_file-- feel dree to adjust file path to fit your computer
        # readInput = open("input.txt", "r")  # this is what it was before
        readInput = open(filename, "r")
        f = readInput.readlines()

        # set counters
        tRow = 0  # start counting rows of table at 0 because the first one is a header
        entry = 1  # count the number of entries; only two are expected: ROB and CBD
        r1m2 = 1  # conter to know if it is a resiter value or a memory value
        regN = 0  # index counter for number of registers to create regNames and regInitials
        memN = 0  # index counter for number of adresses to create memNames and memInitials
        instN = 0  # index counter for number of instructions
        # set expected entries
        self.ROBe = 0
        self.CBDe = 0
        # Seeds for register, memory adresses and instruction lists
        limit = 100
        self.regNames = [-1]*limit  # str
        self.regInitials = [-1]*limit  # integers and floats
        self.memLocs = [0]*limit  # whole numbers... could make 0s -1s?
        self.memInitials = [0]*limit  # integers and floats... could make 0s -1s?

        def createInstDic(instV, N):  # function for subdictionary of instructions with type, destination register, input1 and 2
            instS[instN] = {}  # create new sub dictionary each time new instruction is in the text file
            # instructions like branchs only have 2 inputs
            separate = instV[0].strip().split(' ')
            instS[N]['instType'] = separate[0]
            instS[N]['input1'] = separate[1]
            if len(instV[1].strip().split('(')) > 1:  # ld/sd have an input (an address and an offset) have 3 inputs
                ldsd = instV[1].strip().split('(')
                instS[N]['input2'] = ldsd[0]
                instS[N]['input3'] = ldsd[1].replace(')', '')
            else:
                    instS[N]['input2'] = instV[1]
            if len( instV) > 3: # intructions that go in the adder (add, mult, sub)
                input2 = v[2]
                instS[N]['input3'] = v[2]

        instS = {}  #create dictionary for instN instructions
        for line in f:
            # splits each line in tabs to pull out values from table
            v = line.strip().split('\t')  # outputs each line in text file

            # create dictionary to access data
            if len(v) > 1:  # checking if line has data in it--- the \t split looks for
                # table values
                data = v[1::]  # removing the labels (first column) in the text file
                if tRow > 0:  # not evaluating the header
                    nrg = data[0]  # number of registers
                    cie = data[1]  # cycles in ex.
                    cim = data[2]  # cycles in memory
                    nfu = data[3]  # number of floating units
                    # create dictionary for each reservation station
                    if tRow == 1:
                        self.intA = {}  # create empty dictionary called interger adder
                        for number in ["nrg", "cie", "cim", "nfu"]:  # grabs numbers in table row corresponding to col labels
                            self.intA[number] = eval(number)
                    elif tRow == 2:
                        self.FPA = {}  # create empty dictionary floating point adder
                        for number in ["nrg", "cie", "cim", "nfu"]:
                            self.FPA[number] = eval(number)
                    elif tRow == 3:
                        self.FPM = {}  # Floating point multiplier
                        for number in ["nrg", "cie", "cim", "nfu"]:
                            self.FPM[number] = eval(number)
                    elif tRow == 4:
                        self.LSU = {}  #
                        for number in ["nrg", "cie", "cim", "nfu"]:
                            self.LSU[number] = eval(number)
                tRow += 1  # read next line in table
            else:  # analyzing all the lines that were not separated by tabs
                v = line.strip().split(',')
                if len(v) > 1:  # only analyzing lines with data inside
                    if r1m2 == 1:  # REGISTER VALUES corresponding to their names
                        for register in v:  # go through each index in list v
                            regV = register.strip().split('=')  # new register value
                            self.regNames[regN] = regV[0]
                            self.regInitials[regN] = regV[1]
                            regN += 1  # counts the number of given registers
                    elif r1m2 == 2:  # MEMORY VALUES corresponding to their names
                        for memory in v:  # go through each index in list v
                            memV = memory.strip().split('=')  # new memory value
                            self.memLocs[memN] = int(memV[0][4])
                            self.memInitials[memN] = memV[1]
                            memN += 1  # counts the number of given addresses
                    elif r1m2 > 2:  # INSTRUCTION SET IS HERE
                        # print(v)
                        # INTRUCTION TYPE and DESTINATION Register is in v[0], so separate
                        if len(v) > 1:  # the instruction is not a NOP, it can be adder, sub, mult, branch or ld/sd
                            createInstDic( v, instN)
                        else:  # The instruction is a NOP-- no inputs needed
                            instTypes[instN] = 'NOP'
                            Rds[instN] = 'NOP'

                        instN += 1

                    r1m2 += 1  # switching to r1m2=2, meaning second row which is memory
                else:
                    v = line.strip().split('=')
                    if len(v) > 1:
                        if entry == 1:
                            self.ROBe = v[1]
                        else:
                            self.CBDe = v[1]
                        entry += 1  # counter must stay with this indentation to match if else statement entry

        # Assume reg is always on line 9
        # Assume memory is always on line 10
        memory_line = f[9]
        register_line = f[8]
        memory_string = memory_line.strip("\n").split(",")
        register_string = register_line.strip("\n").split(",")
        self.memory = [0] * 256
        self.registers = {}
        for val in memory_string:
            temp = re.findall(r'\d+', val.split("=")[0])
            memloc = int(temp[0])
            if "." in val.split("=")[1]:
                memval = float(val.split("=")[1])
            else:
                memval = int(val.split("=")[1])
            self.memory[memloc] = memval
        for val in register_string:
            regname = val.split("=")[0]
            if "R" in regname:
                regval = int(val.split("=")[1])
            else:
                regval = float(val.split("=")[1])
            self.registers[regname] = regval
        # Eliminate trailing -1s in refNames and regInitials and redefine list

        def elimNegTrail (trailingL):  #function that eliminates trailing
            indexL = 0
            for val in trailingL:
                if isinstance(val, int):
                    trailingL = trailingL[0:indexL]
                    return trailingL
                indexL += 1
        self.regNames = elimNegTrail(self.regNames)
        self.regInitials = elimNegTrail(self.regInitials)

        #make ARF int and floating point regNames and regInitials
        #print(self.regInitials)
        print (self.regNames[0][0] == 'R')
        #self.ARFNamesI =


"""
# # Adders are dictionaries
inputparsed = input_parser("input.txt")

print(inputparsed.intA)
print(inputparsed.FPA)
print(inputparsed.FPM)
print(inputparsed.LSU)

print("Registers: {}".format(inputparsed.registers))
print("Memory initialized as a 256-long list: {}".format(inputparsed.memory))

# instructions
#print(instS)

RAT = {"R1":"ARF1", "R2":"ARF2"}
RAT["R1"] = "ROB1"

INT_ARF = {"R1":1, "R2":3}
FP_ARF = {"F1":1.8, "F2":3.1}
"""
