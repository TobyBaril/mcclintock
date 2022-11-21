import sys
import os
import json
import argparse
import re

def main():

    args = parse_args()

    config = {}
    
    ## parameters for the range of simulation
    config["submit"] = {
        "cov_range": args.covrange,
        "num_rep": args.numrep,
        "strand": args.strand
    }

    ## parameters for output path
    config["out"] = {
        "outdir": args.outdir
    }

    ## parameter for mcc installation
    config["mccdir"] = args.mcc

    ## parameters for simulation config
    config["config"] = {
        "family": args.family,
        "ins_bed": args.bed,
        "cfg_script": args.mcc+"/simulation/make_sim_config.py",
        "len_tsd": args.tsd
    }

    ## parameters for simulation script inputs
    config["in"] = {
        "cfg": args.outdir+"/config/run_simulation.json",
        "ref": args.reference,
        "consensus": args.consensus,
        "gff": args.locations,
        "tax": args.taxonomy,
        "script": args.mcc+"/simulation/mcclintock_simulation_snk.py"
    }

    ## parameters for simulation script
    config["simparams"] = {
        "runid": args.runid,
        "single": args.single,
        "length": args.length,
        "insertsize": args.insert,
        "error": args.error,
        "keep_intermediate": args.keep_intermediate,
        "simulator": args.sim,
        "mcc_version": 2
    }

    ## parameters for cluster job resources/envs
    config["resources"] = {
        "threads": args.threads,
        "mem": args.memory,
        "condaenv": "mcclintock",
        "renv": "mcc_analysis"
    }

    ## paths for analysis scripts
    config["analysis"] = {
        "summary": args.mcc+"/simulation/mcclintock_simulation_analysis.py",
        "r_vis_precision_recall": args.mcc+"/simulation/sim_r_vis_precision_recall.R",
        "r_vis_for_cov": args.mcc+"/simulation/sim_r_vis_for_cov.R"
    }

    ## parameters for simulation analysis
    config["analysisparams"] = {
        "exclude": args.exclude
    }
    
    with open(args.out, "w") as conf:
        json.dump(config, conf, indent=4)



    # # tsd length and targets for each family
    # for i in range(te_count):
    #     config['families'][args.family[i]] = {
    #         "TSD": args.tsd,
    #         "targets": args.bed[i]
    #     }
    
    # # Mcc path and methods
    # config['mcclintock'] = {
    #     "path": args.mcc,
    #     "methods": "ngs_te_mapper,ngs_te_mapper2,relocate,relocate2,temp,temp2,retroseq,popoolationte,popoolationte2,te-locate,teflon,tebreak"
    # }



def parse_args():
    parser = argparse.ArgumentParser(prog='make_snakemake_config.py', description="Create config file in json format for snakemake pipeline that runs simulation framework.")

    ## required ##
    parser.add_argument("--family", type=str, nargs='+', help="List of TE families. Required.", required=True)
    parser.add_argument("--bed", type=str, nargs='+', help="List of candidate insertion region files in bed format for each TE family, respectively. Or one bed file for all TE families. Required.", required=True)
    parser.add_argument("--mcc", type=str, help="Path to local McClintock repo. Required.", required=True)
    parser.add_argument("--out", type=str, help="File name of the output json. Required.", required=True)
    parser.add_argument("--outdir", type=str, help="Output directory for all simulation results. Required.", required=True)
    parser.add_argument("--reference", type=str, help="[McClintock option] A reference genome sequence in fasta format. Required.", required=True)
    parser.add_argument("--consensus", type=str, help="[McClintock option] The consensus sequences of the TEs for the species. Required.", required=True)
    parser.add_argument("--locations", type=str, help="[McClintock option] The locations of known TEs in the reference genome in GFF 3 format. Required.", required=True)
    parser.add_argument("--taxonomy", type=str, help="[McClintock option] A tab delimited file with one entry per ID. Required.", required=True)


    ## optional ##
    parser.add_argument("--tsd", type=int, help="Integer for length of target site duplication in bp. Default is 5 bp.", default=5, required=False)
    parser.add_argument("--covrange", type=int, nargs='+', help="List of ingeters for tested coverage range. Default is 3 6 12 25 50 100. ", default=[3,6,12,25,50,100], required=False)
    parser.add_argument("--numrep", type=int, help="Integer of replicate counts for each coverage and each strand. Default is 30.", default=30, required=False)
    parser.add_argument("--strand", type=str, nargs='+', help="List of strands for simulation. 'forward' and 'reverse' are allowed. Default is both strands.", default=["forward","reverse"], required=False)
    ## read simulataion options from mcclintock_simulation.py ##
    parser.add_argument("--length", type=int, help="The read length of the simulated reads [default = 101]", default=101, required=False)
    parser.add_argument("--insert", type=int, help="The median insert size of the simulated reads [default = 300]", default=300, required=False)
    parser.add_argument("--error", type=float, help="The base error rate for the simulated reads [default = 0.01]", default=0.01, required=False)
    parser.add_argument("--keep_intermediate", type=str, help="This option determines which intermediate files are preserved after McClintock completes [default: minimal][options: minimal, general, methods, <list,of,methods>, all]", default="minimal", required=False)
    parser.add_argument("--runid", type=str, help="(not recommended) a string to prepend to output files so that multiple runs can be run at the same time without file name clashes", required=False)
    parser.add_argument("--sim", type=str, help="Short read simulator to use (options=wgsim,art) [default = art]", default="art", required=False)
    parser.add_argument("--single", action="store_true", help="runs the simulation in single ended mode", required=False)
    ## resources options ##
    parser.add_argument("--threads", type=int, help="The number of processors to use for individual cluster jobs. [default = 4]", default=4, required=False)
    parser.add_argument("--memory", type=str, help="The number of memory in 'G' to use for individual cluster jobs. [default = '20G']", default="20G", required=False)
    ## resources options ##
    parser.add_argument("--exclude", type=str, help="BED file of regions in which predictions will be excluded from counts (ex. low recombination regions), for analysis script.", required=False)


    args = parser.parse_args()

    ## required ##
    # parse te families and bed
    if not len(args.family) == len(args.bed):
        if not len(args.bed) == 1:
            sys.exit("ERROR: One candidate insertion region file must be specified for each TE family. Or one bed file for all TE families. \n")
        else:
            bed = os.path.abspath(args.bed[0])
            args.bed.extend([bed] * (len(args.family) - 1))
    else:
        for i in range(len(args.family)):
            args.bed[i] = os.path.abspath(args.bed[i])

    # parse mcc install path
    args.mcc = os.path.abspath(args.mcc)
    
    # parse output path for the json config
    args.out = os.path.abspath(args.out)

    # parse output folder of simulation results
    args.outdir = os.path.abspath(args.outdir)

    # parse reference
    args.reference = os.path.abspath(args.reference)

    # parse consensus
    args.consensus = os.path.abspath(args.consensus)

    # parse locations
    args.locations = os.path.abspath(args.locations)

    # parse taxonomy
    args.taxonomy = os.path.abspath(args.taxonomy)

    ## optional ##
    # parse strand
    strands = ["forward","reverse"]
    for option in args.strand:
        if option not in strands:
            sys.stderr.write("Only 'forward' and/or 'reverse' are allowed for --strand option.")
            sys.exit(1)

    # parse simulator
    simulators = ["wgsim", "art"]
    if args.sim not in simulators:
        sys.stderr.write("Only 'wgsim' or 'art' are allowed for --sim option.")
        sys.exit(1)

    # parse memory
    if re.search("G$", args.memory) is None:
        sys.stderr.write("Only memory in 'G' is allowed for --memory option, i.e, '20G'")
        sys.exit(1)

    # parse exclude
    if args.exclude is not None:
        args.exclude = os.path.abspath(args.exclude)
    
    return args



if __name__ == "__main__":
    main()

