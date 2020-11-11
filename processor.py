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
        self.reorder_buf = ROB(int(initr.ROBe), 32, 32) # HARD CODE? Are num registers param'd?

        self.func_units = [LoadStoreQueue(256, initr.LSU["nrg"], initr.LSU["cim"], self.reorder_buf, initr.CBDe, config=initr.memory),
                           FPAdder(int(initr.FPA["nrg"]), int(initr.FPA["cie"]), int(initr.FPA["nfu"]), self.reorder_buf),
                           FPMultiplier(int(initr.FPM["nrg"]), int(initr.FPM["cie"]), int(initr.FPM["nfu"]), self.reorder_buf),
                           IntegerAdder(int(initr.intA["nrg"]), int(initr.intA["cie"]), int(initr.intA["nfu"]), self.reorder_buf) ]

        self.brnch_trnsl_buf = BTB(self.reorder_buf, self.reg_alias_tbl,
                                   self.func_units[3], self.func_units[1],
                                   self.func_units[2])

        cdb_subs = [self.brnch_trnsl_buf, self.reorder_buf]
        for opr in self.func_units:
            cdb_subs.append(opr)

        self.CDB = CommonDataBus(self.func_units, cdb_subs)

        # finish references to all components still needing it.
        # ==========REGISTER ALIAS TABLE============
        self.reg_alias_tbl.instr_queue = self.instr_buf
        self.reg_alias_tbl.rob = self.reorder_buf
        self.reg_alias_tbl.func_units["LSQ"] = self.func_units[0]
        self.reg_alias_tbl.func_units["FPA"] = self.func_units[1]
        self.reg_alias_tbl.func_units["FPM"] = self.func_units[2]
        self.reg_alias_tbl.func_units["INT"] = self.func_units[3]
        self.reg_alias_tbl.func_units["BTB"] = self.brnch_trnsl_buf

        # ========== REORDER BUFFER =============
        # self.reorder_buf.rat = self.reg_alias_tbl
        # self.reorder_buf.lsu = self.func_unit[0]

    def sys_print(self, out_file=None):
        return


    def run_code():
        # run the heartbeat loop
        while("Instruction buffer and ROB are not empty"):
            cycle_count += 1
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
    my_processor = Processor("test_files\\test1.txt")
    #my_processor.run_code()
