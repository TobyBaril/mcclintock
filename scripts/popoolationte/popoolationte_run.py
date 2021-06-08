import os
import sys
import subprocess
import statistics
import traceback
import importlib.util as il
spec = il.spec_from_file_location("config", snakemake.params.config)
config = il.module_from_spec(spec)
sys.modules[spec.name] = config
spec.loader.exec_module(config)
sys.path.append(snakemake.config['args']['mcc_path'])
import scripts.mccutils as mccutils





def main():
    mccutils.log("popoolationte","running PopoolationTE")
    ref_fasta = snakemake.input.ref_fasta
    taxonomy = snakemake.input.taxonomy
    te_gff = snakemake.input.te_gff
    fq1 = snakemake.input.fq1
    fq2 = snakemake.input.fq2
    sam = snakemake.input.sam
    log = snakemake.params.log
    status_log = snakemake.params.status_log

    with open(log,"a") as l:
        l.write("reference fasta: "+ref_fasta+"\n")
        l.write("Taxonomy TSV: "+taxonomy+"\n")
        l.write("TE GFF: "+te_gff+"\n")
        l.write("fastq1: "+fq1+'\n')
        l.write("fastq2: "+fq2+"\n")
        l.write("SAM: "+sam+"\n")

    out_dir = snakemake.params.out_dir
    sample_name = snakemake.params.sample_name
    script_dir = snakemake.params.script_dir

    prev_step_succeeded = mccutils.check_status_file(status_log)
    if prev_step_succeeded:
        try:
            mccutils.log("popoolationte","getting read length")
            read_length = get_read_length(fq1, fq2)
            mccutils.log("popoolationte","calculating median insert size")
            median_insert_size = get_median_insert_size(sam)
            max_dist = int(median_insert_size * 3) +read_length
            mccutils.log("popoolationte","converting TE gff to PoPoolationTE known TE file")
            known_inserts = make_known_insert_file(te_gff, out_dir)
            mccutils.log("popoolationte","running the PoPoolationTE workflow scripts")
            run_popoolationte(sam, 
                            ref_fasta, 
                            taxonomy, 
                            read_length, 
                            median_insert_size, 
                            max_dist, 
                            known_inserts, 
                            script_dir, 
                            out_dir,
                            config.PARAMS,
                            log=log)

            mccutils.check_file_exists(snakemake.output[0])

            with open(status_log,"w") as l:
                    l.write("COMPLETED\n")
            mccutils.log("popoolationte","popoolationte run complete")

        except Exception as e:
            track = traceback.format_exc()
            print(track, file=sys.stderr)
            with open(log,"a") as l:
                print(track, file=l)
            with open(status_log,"w") as l:
                    l.write("FAILED\n")

            mccutils.run_command(["touch", snakemake.output[0]])
    else:
        mccutils.run_command(["touch", snakemake.output[0]])


def get_read_length(fq1, fq2):
    read1_length = 0
    with open(fq1, "r") as fq:
        for l, line in enumerate(fq):
            if l == 1:
                read1_length = len(line.replace("\n",""))
            elif l > 1:
                break
    
    read2_length = 0
    with open(fq2, "r") as fq:
        for l, line in enumerate(fq):
            if l == 1:
                read2_length = len(line.replace("\n",""))
            elif l > 1:
                break
    
    read_length = int((read1_length + read2_length)//2)

    return int(read_length)

def get_median_insert_size(sam):
    insert_sizes = []
    with open(sam,"r") as s:
        for line in s:
            split_line = line.split("\t")
            if len(split_line) >= 8:
                insert_size = int(split_line[8])
                if insert_size > 0:
                    insert_sizes.append(insert_size)
    
    insert_sizes.sort()
    median = statistics.median(insert_sizes)

    return int(median)

def make_known_insert_file(gff, out):
    out_file = out+"known-te-insertions.txt"
    with open(out_file,"w") as o:
        with open(gff,"r") as i:
            for line in i:
                if "#" not in line:
                    line = line.replace(";","\t")
                    line = line.replace("=","\t")
                    split_line = line.split("\t")
                    chrom = split_line[0]
                    strand = split_line[6]
                    start = split_line[3]
                    end = split_line[4]
                    insert = split_line[9]

                    if "-" in strand:
                        o.write("\t".join([chrom, "F", end, insert])+"\n")
                        o.write("\t".join([chrom, "R", start, insert])+"\n")
                    else:
                        o.write("\t".join([chrom, "F", start, insert])+"\n")
                        o.write("\t".join([chrom, "R", end, insert])+"\n")
    
    return out_file

def run_popoolationte(sam, reference, taxon, read_len, insert_size, max_dist, ref_inserts, script_dir, out_dir, params, 
                      log=None):

    mccutils.log("popoolationte","identify-te-insertsites.pl")
    insert_sites = out_dir+"te-fwd-rev.txt"
    command = ["perl", script_dir+"identify-te-insertsites.pl", 
                    "--input", sam, 
                    "--te-hierarchy-file", taxon, 
                    "--te-hierarchy-level", "family", 
                    "--narrow-range", str(read_len),
                    "--output", insert_sites,
                    "--insert-distance", str(insert_size), 
                    "--read-length", str(read_len)]
    
    for param in params["identify-te-insertsites.pl"].keys():
        command.append(param)
        command.append(str(params["identify-te-insertsites.pl"][param]))
    mccutils.run_command(command, log=log)

    mccutils.log("popoolationte","genomic-N-2gtf.pl")
    poly_n = out_dir+"poly_n.gtf"
    command = ["perl", script_dir+"genomic-N-2gtf.pl", "--input", reference]
    mccutils.run_command_stdout(command, poly_n, log=log)

    mccutils.log("popoolationte","crosslink-te-sites.pl")
    crosslinked = out_dir+"te-inserts.txt"
    command = ["perl", script_dir+"crosslink-te-sites.pl", 
                    "--directional-insertions", insert_sites, 
                    "--min-dist", str(read_len), 
                    "--max-dist", str(max_dist),
                    "--output", crosslinked,
                    "--poly-n", poly_n,
                    "--te-hierarchy", taxon,
                    "--te-hier-level", "family"]

    for param in params["crosslink-te-sites.pl"].keys():
        command.append(param)
        command.append(str(params["crosslink-te-sites.pl"][param]))
    mccutils.run_command(command, log=log)

    mccutils.log("popoolationte","update-teinserts-with-knowntes.pl")
    updated_inserts = out_dir+"te-insertions-updated.txt"
    command = ["perl", script_dir+"update-teinserts-with-knowntes.pl", 
                    "--known", ref_inserts,
                    "--output", updated_inserts, 
                    "--te-hierarchy-file", taxon,
                    "--te-hierarchy-level", "family",
                    "--max-dist", str(max_dist),
                    "--te-insertions", crosslinked]

    for param in params["update-teinserts-with-knowntes.pl"].keys():
        command.append(param)
        command.append(str(params["update-teinserts-with-knowntes.pl"][param]))
    mccutils.run_command(command, log=log)

    mccutils.log("popoolationte","estimate-polymorphism.pl")
    te_polymorphism = out_dir+"te-polymorphism"
    command = ["perl", script_dir+"estimate-polymorphism.pl", 
                    "--sam-file", sam,
                    "--te-insert-file", updated_inserts,
                    "--te-hierarchy-file", taxon,
                    "--te-hierarchy-level", "family",
                    "--output", te_polymorphism]

    for param in params["estimate-polymorphism.pl"].keys():
        command.append(param)
        command.append(str(params["estimate-polymorphism.pl"][param]))
    mccutils.run_command(command, log=log)

    mccutils.log("popoolationte","filter-teinserts.pl")
    filtered = out_dir+"te-poly-filtered.txt"
    command = ["perl", script_dir+"filter-teinserts.pl",
                    "--te-insertions", te_polymorphism,
                    "--output", filtered,
                    "--discard-overlapping"]

    for param in params["filter-teinserts.pl"].keys():
        command.append(param)
        command.append(str(params["filter-teinserts.pl"][param]))
    mccutils.run_command(command, log=log)

if __name__ == "__main__":                
    main()