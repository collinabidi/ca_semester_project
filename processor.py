# Main driver and heartbeat code

class Processor:
    def __init__(self, config_file, verbose=False):
        self.cycle_count = 0
        # initialize all components here
        # 1. Get input data from config file

        # 2. Initialize every component with references to the other components 
        return


    def run_code():
        # run the heartbeat loop
        while("Instruction buffer and ROB are not empty"):
            cycle_count += 1
            #InstructionBuffer.tick() //Fetch decode?
            #RAT.tick()
            #BTB.tick()

            #fpmult.tick()
            #intaddr.tick()
            #fpaddr.tick()
            #lsq.tick()

            #cdb.tick()
            """ If the BTB mispredicted, the rewind can be triggered here internally
                cdb->btb.read_cdb()->btb.component_ref.rewind()
            """

            #ROB.tick()

            #print system state


if __name__ == "__main__":
    # decode command line args
    my_processor = Processor()
    my_processor.run_code()
