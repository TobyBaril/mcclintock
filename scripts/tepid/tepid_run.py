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
    ref_fasta = snakemake.input.ref_fasta
    fq1 = snakemake.input.fq1
    fq2 = snakemake.input.fq2
    te_gff = snakemake.input.te_gff
    te_taxonomy = snakemake.input.te_taxonomy

    threads = snakemake.threads

    median_insert_size_file = snakemake.input.median_insert_size
    raw_fq2 = snakemake.params.raw_fq2
    ref_name = snakemake.params.ref_name
    out_dir = snakemake.params.out_dir
    log = snakemake.params.log
    status_log = snakemake.params.status_log


    try:
        # ensures intermediate files from previous runs are removed
        for f in os.listdir(out_dir):
            mccutils.remove(out_dir+"/"+f)

        median_insert_size = ""
        with open(median_insert_size_file,"r") as median_insert:
            for line in median_insert:
                line = line.split("=")[1].replace("\n","")
                median_insert_size = line

        is_paired = True
        if raw_fq2 == "False":
            is_paired = False
        
        mccutils.log("tepid","indexing reference", log=log)
        index_ref(ref_fasta, ref_name, out_dir, log=log)
        mccutils.log("tepid","making TEPID reference TE bed")
        te_bed = make_te_bed(te_gff, te_taxonomy, out_dir)

        mccutils.log("tepid","mapping reads", log=log)
        if is_paired:
            bam, split_bam = map_reads(fq1, fq2, ref_name, median_insert_size, out_dir, threads=threads, paired=True, log=log)
        else:
            bam, split_bam = map_reads(fq1, fq2, ref_name, median_insert_size, out_dir, threads=threads, paired=False, log=log)

        mccutils.log("tepid","discovering variants", log=log)
        discover_variants(ref_name, bam, split_bam, te_bed, out_dir, threads=threads, log=log)
        mccutils.log("tepid","TEPID run complete")
    
    except Exception as e:
        track = traceback.format_exc()
        print(track, file=sys.stderr)
        with open(log,"a") as l:
            print(track, file=l)
        mccutils.log("tepid","TEPID run failed")
        with open(status_log,"w") as l:
            l.write("FAILED\n")

        mccutils.run_command(["touch", snakemake.output[0]])
        mccutils.run_command(["touch", snakemake.output[1]])
        mccutils.run_command(["touch", snakemake.output.insertions_support])
        mccutils.run_command(["touch", snakemake.output.deletions_support])

def index_ref(fasta, ref_name, out, log=None):
    try:
        os.chdir(out)
        fasta_no_path = fasta.split("/")[-1]
        fasta_copy = out+"/"+fasta_no_path
        mccutils.run_command(["cp", fasta, fasta_copy])

        mccutils.run_command(["bowtie2-build", fasta_copy, ref_name], log=log)
        mccutils.run_command(["yaha", "-g", fasta_copy], log=log)

        mccutils.check_file_exists(out+"/"+ref_name+".X15_01_65525S")
    
    except Exception as e:
        track = traceback.format_exc()
        print(track, file=sys.stderr)
        print("ERROR...Failed to index reference fasta:"+fasta_copy+" ...exiting...", file=sys.stderr)
        sys.exit(1)

def make_te_bed(gff, taxonomy, out):
    te_to_family = {}
    with open(taxonomy,"r") as tsv:
        for line in tsv:
            split_line = line.split("\t")
            te_to_family[split_line[0]] = split_line[1].replace("\n","")

    te_bed = out+"/te.bed"
    with open(te_bed, "w") as out_bed:
        with open(gff, "r") as g:
            for line in g:
                split_line = line.split("\t")
                chrom = split_line[0]
                start = split_line[3]
                end = split_line[4]
                strand = split_line[6]
                info = split_line[8]
                split_info = info.split(";")
                te_name = ""
                for i in split_info:
                    if "ID=" in i:
                        te_name = i.split("=")[1].replace("\n","")
                
                family = te_to_family[te_name]
                out_line = "\t".join([chrom, start, end, strand, te_name, family, family])
                out_bed.write(out_line+"\n")
    
    return te_bed

def map_reads(fq1, fq2, ref_name, median_insert_size, out, threads=1, paired=True, log=None):
    os.chdir(out)
    if paired:
        command = ["tepid-map", 
                        "-x", out+"/"+ref_name, 
                        "-y", out+"/"+ref_name+".X15_01_65525S", 
                        "-p", str(threads), 
                        "-s", median_insert_size,
                        "-n", ref_name,
                        "-1", fq1,
                        "-2", fq2 ]
    else:
        command = ["tepid-map-se", 
                        "-x", out+"/"+ref_name, 
                        "-y", out+"/"+ref_name+".X15_01_65525S", 
                        "-p", str(threads), 
                        "-n", ref_name,
                        "-q", fq1]

    mccutils.run_command(command, log=log)

    bam = out+"/"+ref_name+".bam"
    split_bam = out+"/"+ref_name+".split.bam"
    mccutils.check_file_exists(bam)
    mccutils.check_file_exists(split_bam)

    return bam, split_bam 


def discover_variants(ref_name, bam, split_bam, te_bed, out, threads=1, log=None):
    os.chdir(out)
    command = ["tepid-discover",
                    "-p", str(threads),
                    "-n", ref_name,
                    "-c", bam,
                    "-s", split_bam,
                    "-t", te_bed]

    mccutils.run_command(command, log=log)

    if not os.path.exists(snakemake.output[0]):
        mccutils.run_command(["touch", snakemake.output[0]])
    if not os.path.exists(snakemake.output[2]):
        mccutils.run_command(["touch", snakemake.output[2]])
    mccutils.check_file_exists(snakemake.output[1])

if __name__ == "__main__":                
    main()