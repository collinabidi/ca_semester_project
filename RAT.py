from functional_units import *
from readingInput import input_parser

# Initialize the processor and all functional units
instruction_buffer = InstructionBuffer(r"C:\Users\HP\github\ca_semester_project\input.txt")
#instruction_buffer = InstructionBuffer("input.txt")

# create object called inputs to access regNames and regInitials
inputs = input_parser(r"C:\Users\HP\github\ca_semester_project\input.txt")

### useful for debugging
### printer to know what is in the instruction buffer
# for i, instruction in enumerate(instruction_buffer):
#     print("i = {}: value = {}".format(i, instruction))
#     print(instruction.__dict__)
#     print("Instruction rs: {}".format(instruction.rs))


#inputparsed = input_parser("input.txt")
int_adder = IntegerAdder(int(inputs.intA['nrg']), int(inputs.intA['cie']), int(inputs.intA['nfu']))
#double check intention with Collin: arent these random values that can be replaced with input.txt?




for i in range(0, 10): ### what are these random ticks for?????/
    int_adder.tick()

# Issue instruction to fp_adder functional unit
""" #can be used for testing
# fake values into integer adder for debugging and testing
int_adder.issue({"op":"ADD","vj":10, "vk":5, "qj":None, "qk":None, "dest":"F1"})

int_adder.issue({"op":"ADD","vj":3, "vk":6, "qj":None, "qk":None, "dest":"ROB2"})

int_adder.tick()
#
# int_adder.tick()
#
""" # cleaning up RAT

######################### RAT ops really start #################################
# create free pool
# make 32 trasnsition registers (will probably not need more)
# transition registers from freepool are differentiated by 'X'
freePool = []  #  provides extra registers for renaming, called X

# makes both floating point RAT and integer RAT
# organizes registers with initialized values and replaces with new free pool registers
intRAT = []
floRAT = []

regLim = 32 - 1
### monitor freePool to make sure limit is not exceeded
freePLim = 100

# Create RAT that holds label of registers
for i in range(0,regLim):#could potentially change this limit to number of instructions in queue because transition registers will not exceed queue
    # Separate floating from interger VALUEs
    intRAT.append("R" + str(i))
    floRAT.append("F" + str(i))

# Create freePool that generates 100 extra registers for renaming
for i in range(0,freePLim):#could potentially change this limit to number of instructions in queue because transition registers will not exceed queue
    freePool.append("X" + str(i))# need a lot of freepool values, so arbitraty multiplier, 15


intRATvals = [[]]*regLim
floRATvals = [[]]*regLim

intRATrenamed = [[]]*regLim
floRATrenamed = [[]]*regLim

#registers
# print(freePool)
# print(intRAT)
# print(floRAT)

# Get initialized values from readingInput
# print(inputs.ARFI)
# print(inputs.ARFF)

#initialize intRAT
RATindexI = 0
for register in intRAT:
    # checks if initial registerName corresponds with register in
    for initialR in inputs.ARFI: # all initialized values are in architechture register!!!!!
        if register == initialR :
            print(RATindexI)
            intRATvals[RATindexI] = inputs.ARFI[register] #set register value to RAT value storage
            intRATrenamed[RATindexI] = freePool.pop()
    RATindexI += 1
# good for checking
print(intRATvals)
print(intRATrenamed)
print(intRAT) ## checked to make sure matched with input.txt

# #initialize floRAT
RATindexF = 0
for register in floRAT:
    # checks if initial registerName corresponds with register in
    for initialR in inputs.ARFF: # all initialized values are in architechture register!!!!!
        if register == initialR :
            print(RATindexF)
            floRATvals[RATindexF] = inputs.ARFF[register] #set register value to RAT value storage
            floRATrenamed[RATindexF] = freePool.pop()
    RATindexF += 1
#good for checking
print(floRATvals)
print(floRATrenamed)
print(floRAT) ## checked to make sure matched with input.txt


##################### Register Renamimg Once Ticking starts ####################
# Rename register everytime
# Get instruction queue registers

# get updated adder results from floating_units.py
# This will give you a dictionary: for example, {"dest","ROB1":"answer":10.3} would be the output for an operation with
# destination ROB1 and value 10.3

#it is initializer to grab results from functional units
#result = int_adder.deliver() #could delete
instructionN = 1
for instruction in instruction_buffer:
    # If there's room in the IntAdder and instruction is Add or Sub, issue it!
    if instruction.op == "Sub" or instruction.op == "Add" and int_adder.num_filled_stations < len(int_adder.reservation_stations):
        int_adder.issue({"op":instruction.op,"vj":10, "vk":20, "qj":instruction.rs, "qk":instruction.rt, "dest":instruction.rd})
    destName = instruction.rd
    Name = destName[0]
    # Replace rename registers is similar to initializer, but doesnt access ARF from readingIput.py
    # Accesses functional_units.py

    #CHECK IF result["answer is int or float"] ? and make if stament in instruction queue loop
    if Name == "R":  # check if register is int or float by
        #INT
        RATindexI = 0
        renameName= destName  # string numeric value of register to be renamed
        for register in intRAT:
            # checks if initial registerName corresponds with register in

            #### potential bug! ?will work because there is only one instruction, but what if there are more than 1 results ready to go?
            ####for initialR in destName: # all initialized values are in architechture register!!!!!
            if register == renameName:
                print(register, renameName)
                intRATvals[RATindexI] = destName #set register value to RAT value storage with rename value called result["answer"]
                intRATrenamed[int(renameName[1])] = freePool.pop()  ### ???? check here for why its overwriting additional values with X freePool registers
            RATindexI += 1

            print(intRATvals)
            print(intRATrenamed)
            print(intRAT) ## checked to make sure matched with input.txt
            print(instructionN,"***************************************")
    elif Name == "F":
        # Connect RAT to instruction queue to rename the register with X value

        # issueQ = Instruction() #from functional unit
        # print(issueQ.args[1])

        # Replace X value with register result after adder calculated
        #FLOAT
        RATindexF = 0
        renameName= destName  # string numeric value of register to be renamed
        for register in floRAT:
            # checks if initial registerName corresponds with register in

            #### potential bug! ?will work because there is only one instruction, but what if there are more than 1 results ready to go?
            ####for initialR in destName: # all initialized values are in architechture register!!!!!
            if register == renameName:
                floRATvals[RATindexF] = result["answer"] #set register value to RAT value storage with rename value called result["answer"]
                floRATrenamed[int(renameName[1])] = freePool.pop()
            RATindexF += 1

        print(floRATvals)
        print(floRATrenamed)
        print(floRAT) ## checked to make sure matched with input.txt
    else:
        print("Warning: this instruction is not an add or subtract")


    # Tick to next instruction
    int_adder.tick()
    instructionN += 1




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
