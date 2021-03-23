import os
import sys
import subprocess
import traceback
import importlib.util as il
spec = il.spec_from_file_location("config", snakemake.params.config)
config = il.module_from_spec(spec)
sys.modules[spec.name] = config
spec.loader.exec_module(config)
sys.path.append(snakemake.config['args']['mcc_path'])
import scripts.mccutils as mccutils




def main():
    
    bam = snakemake.input.bam
    twobit = snakemake.input.twobit
    consensus = snakemake.input.consensus
    ref_te_bed = snakemake.input.ref_te_bed
    taxonomy = snakemake.input.taxonomy
    median_insert_size_file = snakemake.input.median_insert_size
    log = snakemake.params.log
    with open(log,"a") as l:
        l.write("BAM: "+bam+"\n")
        l.write("2bit: "+twobit+"\n")
        l.write("consensus fasta: "+consensus+"\n")
        l.write("reference TE BED: "+ref_te_bed+"\n")
        l.write("Taxonomy TSV: "+taxonomy+"\n")


    threads = snakemake.threads
    out_dir = snakemake.params.out_dir
    scripts_dir = snakemake.params.scripts_dir
    sample_name = snakemake.params.sample_name
    status_log = snakemake.params.status_log

    try:
        # ensures intermediate files from previous runs are removed
        for f in os.listdir(out_dir):
            mccutils.remove(out_dir+"/"+f)

        mccutils.log("temp","running TEMP Module")
        median_insert_size = get_median_insert_size(median_insert_size_file)
        run_temp_insertion(bam, scripts_dir, consensus, ref_te_bed, taxonomy, median_insert_size, threads, out_dir, log)
        run_temp_absence(bam, scripts_dir, consensus, ref_te_bed, twobit, taxonomy, median_insert_size, threads, out_dir, log)
        mccutils.check_file_exists(snakemake.output[0])
        mccutils.check_file_exists(snakemake.output[1])
        with open(status_log,"w") as l:
            l.write("COMPLETED\n")
        
        mccutils.log("temp","TEMP run complete")
    
    except Exception as e:
        track = traceback.format_exc()
        print(track, file=sys.stderr)
        with open(log,"a") as l:
            print(track, file=l)
        mccutils.log("temp","TEMP run failed")
        with open(status_log,"w") as l:
            l.write("FAILED\n")

        mccutils.run_command(["touch", snakemake.output[0]])
        mccutils.run_command(["touch", snakemake.output[1]])



def get_median_insert_size(infile):
    median_insert_size = 0
    with open(infile,"r") as inf:
        for line in inf:
            insert = line.split("=")[1]
            insert = insert.replace("\n","")
            median_insert_size = int(float(insert))
    
    return median_insert_size

    
def run_temp_insertion(bam, scripts, consensus, te_bed, taxonomy, median_insert_size, threads, out, log):
    mccutils.log("temp","running TEMP non-reference insertion prediction", log=log)
    command = [
        "bash", scripts+"TEMP_Insertion.sh", 
            "-x", str(config.TEMP_Insertion['x']), 
            "-i", bam, 
            "-s", scripts, 
            "-r", consensus, 
            "-t", te_bed, 
            "-u", taxonomy, 
            "-m", str(config.TEMP_Insertion['m']),
            "-f", str(median_insert_size),
            "-c", str(threads),
            "-o", out
    ]

    mccutils.run_command(command, log=log)


def run_temp_absence(bam, scripts, consensus, te_bed, twobit, taxonomy, median_insert_size, threads, out, log):
    mccutils.log("temp","running TEMP reference insertion absence prediction", log=log)
    command = [
        "bash", scripts+"TEMP_Absence.sh",
            "-i", bam,
            "-s", scripts,
            "-r", te_bed,
            "-t", twobit,
            "-f", str(median_insert_size),
            "-c", str(threads),
            "-o", out
    ]

    mccutils.run_command(command, log=log)


if __name__ == "__main__":                
    main()