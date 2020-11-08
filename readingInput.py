# open text_file-- feel dree to adjust file path to fit your computer
# readInput = open("input.txt", "r")  # this is what it was before
readInput = open(r"C:\Users\HP\github\ca_semester_project\input.txt", "r")
f = readInput.readlines()

# set counters
tRow = 0  # start counting rows of table at 0 because the first one is a header
entry = 1  # count the number of entries; only two are expected: ROB and CBD
r1m2 = 1  # conter to know if it is a resiter value or a memory value
regN = 0  # index counter for number of registers to create regNames and regInitials
memN = 0  # index counter for number of adresses to create memNames and memInitials
instN = 0  # index counter for number of instructions
# set expected entries
ROBe = 0
CBDe = 0
# Seeds for register, memory adresses and instruction lists
limit = 4
regNames = [[]]*limit  # str
regInitials = [[]]*limit  # integers and floats
memLocs = [[]]*limit  # whole numbers
memInitials = [[]]*limit  # integers and floats

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
                intA = {}  # create empty dictionary called interger adder
                for number in ["nrg", "cie", "cim", "nfu"]:  # grabs numbers in table row corresponding to col labels
                    intA[number] = eval(number)
            elif tRow == 2:
                FPA = {}  # create empty dictionary floating point adder
                for number in ["nrg", "cie", "cim", "nfu"]:
                    FPA[number] = eval(number)
            elif tRow == 3:
                FPM = {}  # Floating point multiplier
                for number in ["nrg", "cie", "cim", "nfu"]:
                    FPM[number] = eval(number)
            elif tRow == 4:
                LSU = {}  #
                for number in ["nrg", "cie", "cim", "nfu"]:
                    LSU[number] = eval(number)
        tRow += 1  # read next line in table
    else:  # analyzing all the lines that were not separated by tabs
        v = line.strip().split(',')
        if len(v) > 1:  # only analyzing lines with data inside
            if r1m2 == 1:  # REGISTER VALUES corresponding to their names
                for register in v:  # go through each index in list v
                    regV = register.strip().split('=')  # new register value
                    regNames[regN] = regV[0]
                    regInitials[regN] = regV[1]
                    regN += 1  # counts the number of given registers
            elif r1m2 == 2:  # MEMORY VALUES corresponding to their names
                for memory in v:  # go through each index in list v
                    memV = memory.strip().split('=')  # new memory value
                    memLocs[memN] = int(memV[0][4])
                    memInitials[memN] = memV[1]
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
                    ROBe = v[1]
                else:
                    CBDe = v[1]
                entry += 1  # counter must stay with this indentation to match if else statement entry

# # Adders are dictionaries
# print(intA['nrg'])
# print(FPA)
# print(FPM)
# print(LSU)
#
# # Entries are just numbers/varibles
#print(ROBe, CBDe)

# Registers and memory addresses
print(regNames, regInitials)
print(memLocs, memInitials)
# reg = {} #not sure if needed
# for regName in enumerate(regNames):
#      reg[regName] = regInitials[regName]
# mem = {}
# for memLoc in enumerate(memLocs):
#     mem[memLoc] = memInitials[memLoc]

# instructions
print(instS)
