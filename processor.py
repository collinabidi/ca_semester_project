<<<<<<< Updated upstream
import argparse
from functional_units import *
from memory import *
from RAT import *
from reading_input import input_parser

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--input", type=str)
    return parser.parse_args()
=======
# Main driver and heartbeat code
from RAT import RegisterAliasTable
from cdb import CommonDataBus
from functional_units import *
from memory import *

>>>>>>> Stashed changes

class Processor:
    def __init__(self, config_file, verbose=False):
        self.cycle_count = 0

        # initialize all components here
        self.RAT = RegisterAliasTable()
        self.ROB = None
        self.BTB = None

        self.op_units = [LoadStoreQueue("mem_size", "q_len", "cyc_mem"),
                        "FP_Addr",
                        "FP_Mult",
                        "IntAddr..."]

        cdb_subs = [self.BTB, self.ROB]
        for opr in self.op_units:
            cdb_subs.append(opr)

        self.CDB = CommonDataBus(self.op_units, self.cdb_subs)


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
    args = parse_args()
    filename = args.input
    output_filename = args.input.split(".")[0] + "_output.txt"
    verbose = args.verbose

    my_processor = Processor()
    my_processor.run_code()
