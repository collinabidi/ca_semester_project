from functional_units import *

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
