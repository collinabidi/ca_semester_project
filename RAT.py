from functional_units import *
from readingInput import input_parser

print("Testing operation of all classes defined in functional_units.py")

# Initialize the processor and all functional units
instruction_buffer = InstructionBuffer(r"C:\Users\HP\github\ca_semester_project\input.txt")
#instruction_buffer = InstructionBuffer("input.txt")

for i, instruction in enumerate(instruction_buffer):
    print("i = {}: value = {}".format(i, instruction))
    print(instruction.__dict__)
    print("Instruction rs: {}".format(instruction.rs))

int_adder = IntegerAdder(3, 2, 1)

# Issue instruction to fp_adder functional unit

int_adder.issue({"op":"ADD","vj":10, "vk":5, "qj":None, "qk":None, "dest":"F1"})

int_adder.issue({"op":"ADD","vj":3, "vk":6, "qj":None, "qk":None, "dest":"ROB2"})

int_adder.tick()
#
# int_adder.tick()
#
# int_adder.tick()
#
# int_adder.tick()
#
# int_adder.tick()
#
# int_adder.tick()
#
# int_adder.tick()
#
# int_adder.tick()


# This will give you a dictionary: for example, {"dest","ROB1":"answer":10.3} would be the output for an operation with
# destination ROB1 and value 10.3
result = int_adder.deliver()
print("First result: {}".format(result))
print(result["dest"])
print(result["answer"])


# create free pool
# make 32 trasnsition registers (will probably not need more)
# transition registers from freepool are differentiated by 'X'
freePool = []  #  provides extra registers for renaming, called X

# makes both floating point RAT and integer RAT
# organizes registers with initialized values and replaces with new free pool registers
intRAT = []
floRAT = []

for i in range(0,31):#could potentially change this limit to number of instructions in queue because transition registers will not exceed queue
    freePool.append("X" + str(i))
    intRAT.append("R" + str(i))
    floRAT.append("F" + str(i))

#register

print(freePool)
print(intRAT)
print(floRAT)

for i in range (0, 2):
    instruction = instruction_buffer[i]
    print(instruction.rd)
print(result["dest"])

#if there is a result intadder