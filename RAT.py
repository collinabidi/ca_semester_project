# create free pool
# make 101 trasnsition registers (will probably not need more)
# transition registers from freepool are differentiated by 'X'
freePool = []
register_placeholder = []
for i in range(0,32):#could potentially change this limit to number of instructions in queue because transition registers will not exceed queue
    freePool.append("X" + str(i))
    register_placeholder.append("R" + str(i))

#register

print(freePool)
print(register_placeholder)
