# Main driver and heartbeat code
from RAT import RegisterAliasTable
from cdb import CommonDataBus
from functional_units import *
from memory import *
from reading_input import input_parser


class Processor:
    def __init__(self, config_file, verbose=False):

        initr = input_parser(config_file)
        self.cycle_count = 0

        # initialize all components here
        self.instr_buf = InstructionBuffer(config_file)
        self.reg_alias_tbl = RegisterAliasTable()
        self.reorder_buf = ROB(initr.ROBe, 32, 32) # HARD CODE? Are num registers param'd?
        self.brnch_trnsl_buf = BTB()

        self.func_units = [LoadStoreQueue(256, initr.LSU["nrg"], initr.LSU["cim"], self.reorder_buf, config=self.memory),
                           FPAdder(intir.FPA["nrg"], initr.FPA["cie"], intir.FPA["nfu"]),
                           FPMultiplier(initr.FPM["nrg"], initr.FPM["cie"], initr.FPM["nfu"]),
                           IntegerAdder(initr.IntA["nrg"], initr.IntA["cie"], initr.IntA["nfu"]) ]

        cdb_subs = [self.BTB, self.ROB]
        for opr in self.func_units:
            cdb_subs.append(opr)

        self.CDB = CommonDataBus(self.op_units, self.cdb_subs)

        # finish references to all components still needing it.
        # ==========REGISTER ALIAS TABLE============
        self.reg_alias_tbl.instr_queue = self.instr_buf
        self.reg_alias_tbl.func_units["LSQ"] = self.func_units[0]
        self.reg_alias_tbl.func_units["FPA"] = self.func_units[1]
        self.reg_alias_tbl.func_units["FPM"] = self.func_units[2]
        self.reg_alias_tbl.func_units["INT"] = self.func_units[3]
        self.reg_alias_tbl.func_units["INT"] = self.brnch_trnsl_buf

        # ==========BRANCH TRANSLATION BUFFER=========

        # ========== REORDER BUFFER =============
        # self.reg_alias = self.reg_alias_tbl

    def sys_print(self, out_file=None):
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
    #my_processor.run_code()
