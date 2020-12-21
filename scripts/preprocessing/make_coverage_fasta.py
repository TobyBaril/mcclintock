#!/usr/bin/env python3

import sys
import os
from Bio import SeqIO
import traceback
try:
    sys.path.append(snakemake.config['args']['mcc_path'])
    import scripts.fix_fasta as fix_fasta
    import scripts.mccutils as mccutils
except Exception as e:
    track = traceback.format_exc()
    print(track, file=sys.stderr)
    print("ERROR...unable to locate required external scripts at: "+snakemake.config['args']['mcc_path']+"/scripts/", file=sys.stderr)
    sys.exit(1)


def main():
    mccutils.log("processing","making coverage fasta")
    mcc_out = snakemake.params.out
    run_id = snakemake.params.run_id
    try:
        length = 80
        if snakemake.params.coverage_fasta == "None":
            mccutils.run_command(["touch", snakemake.output.coverage_fasta])
        else:
            fasta3 = snakemake.params.coverage_fasta
            lines = fix_fasta.fix_fasta_lines(fasta3, length)
            write_fasta(lines, snakemake.output.coverage_fasta)
    
    except Exception as e:
        track = traceback.format_exc()
        print(track, file=sys.stderr)
        print("ERROR...failed to create coverage fasta, check the formatting of :", snakemake.params.coverage_fasta, file=sys.stderr)
        mccutils.remove(snakemake.output[0])
        sys.exit(1)        

    mccutils.log("processing","coverage fasta created")
        


def write_fasta(lines, fasta):
    with open(fasta, "w") as out:
        for line in lines:
            out.write(line+"\n")

if __name__ == "__main__":                
    main()