# Simulation of McClintock 2.0
## Installation
* Install miniconda
```bash
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O $HOME//miniconda.sh
bash ~/miniconda.sh -b -p $HOME/miniconda # silent mode
echo "export PATH=\$PATH:\$HOME/miniconda/bin" >> $HOME/.bashrc # add to .bashrc
source $HOME/.bashrc
conda init
# close and re-open terminal
conda update conda
```

* Clone and install mcclintock 2.0
```bash
cd ~
git clone git@github.com:bergmanlab/mcclintock.git
cd mcclintock

# install and activate base mcclintock env
conda env create -f install/envs/mcclintock.yml --name mcclintock
conda activate mcclintock

# install mcclintock component environments
python mcclintock.py --install

conda deactivate mcclintock
```

* install and activate mcclintock sim environment
```
conda env create -f ~/git/mcclintock/auxiliary/simulation/mcc_sim.yml --name mcc_sim
conda activate mcc_sim
```

## Run simulation with test data
### Usage of [Simulation system](https://github.com/bergmanlab/mcclintock/blob/master/auxiliary/simulation/mcclintock_simulation.py)
```bash
$ python mcclintock_simulation.py -h
usage: McClintock Simulation [-h] -r REFERENCE -c CONSENSUS -g LOCATIONS -t TAXONOMY -j
                             CONFIG [-p PROC] [-o OUT] [-C COVERAGE] [-l LENGTH] [-i INSERT]
                             [-e ERROR] [-k KEEP_INTERMEDIATE] [--strand STRAND]
                             [--start START] [--end END] [--seed SEED] [--runid RUNID]
                             [--sim SIM] [-s] [--mcc_version MCC_VERSION]

Script to run synthetic insertion simulations to evaluate mcclintock component methods

optional arguments:
  -h, --help            show this help message and exit
  -r REFERENCE, --reference REFERENCE
                        A reference genome sequence in fasta format
  -c CONSENSUS, --consensus CONSENSUS
                        The consensus sequences of the TEs for the species in fasta format
  -g LOCATIONS, --locations LOCATIONS
                        The locations of known TEs in the reference genome in GFF 3 format.
                        This must include a unique ID attribute for every entry
  -t TAXONOMY, --taxonomy TAXONOMY
                        A tab delimited file with one entry per ID in the GFF file and two
                        columns: the first containing the ID and the second containing the TE
                        family it belongs to. The family should correspond to the names of
                        the sequences in the consensus fasta file
  -j CONFIG, --config CONFIG
                        A json config file containing information on TE family TSD size and
                        target sites
  -p PROC, --proc PROC  The number of processors to use for parallel stages of the pipeline
                        [default = 1]
  -o OUT, --out OUT     An output folder for the run. [default = '.']
  -C COVERAGE, --coverage COVERAGE
                        The target genome coverage for the simulated reads [default = 100]
  -l LENGTH, --length LENGTH
                        The read length of the simulated reads [default = 101]
  -i INSERT, --insert INSERT
                        The median insert size of the simulated reads [default = 300]
  -e ERROR, --error ERROR
                        The base error rate for the simulated reads [default = 0.01]
  -k KEEP_INTERMEDIATE, --keep_intermediate KEEP_INTERMEDIATE
                        This option determines which intermediate files are preserved after
                        McClintock completes [default: general][options: minimal, general,
                        methods, <list,of,methods>, all]
  --strand STRAND       The strand to insert the TE into [options=plus,minus][default = plus]
  --start START         The number of replicates to run. [default = 1]
  --end END             The number of replicates to run. [default = 300]
  --seed SEED           a seed to the random number generator so runs can be replicated
  --runid RUNID         a string to prepend to output files so that multiple runs can be run
                        at the same time without file name clashes
  --sim SIM             Short read simulator to use (options=wgsim,art) [default = wgsim]
  -s, --single          runs the simulation in single ended mode
  --mcc_version MCC_VERSION
                        Which version of McClintock to use for the simulation(1 or 2).
                        [default = 2]
```

### Example of running new simulation system on McC 2.0
* Firstly, create config files as input for the simulation script.
  * `config/tRNA.json` is used to simulate biological TE insertion preference in yeast.
  * `config/non_TE.json` is used to simulate random TE insertion into unique regions.
```bash
conda activate mcc_sim
out_dir=/path/to/output/dir
mkdir -p $out_dir
cd $out_dir
python ~/mcclintock/auxiliary/simulation/make_new_sim_config.py ~/mcclintock
config=${out_dir}/config/tRNA.json
```
* Run simulation script for one synthetic sample

```bash
conda activate mcc_sim
python ~/mcclintock/auxiliary/simulation/mcclintock_simulation.py  \
-r ~/mcclintock/test/sacCer2.fasta \
  -c ~/mcclintock/test/sac_cer_TE_seqs.fasta \
  -g ~/mcclintock/test/reference_TE_locations.gff \
  -t ~/mcclintock/test/sac_cer_te_families.tsv \
  -p 4 \
  --coverage 100 \
  --length 101 \
  --insert 300 \
  --error 0.01 \
  --keep_intermediate minimal \
  -j ${config} \
  --start 1 \
  --end 1 \
  --seed 1 \
  --sim art \
  --mcc_version 2 \
  -o ${out_dir}/ &> ${out_dir}/logs/sample1.log
```

* Run simulation script in a loop for 300 synthetic samples. 
  * This would take a while. It's recommended to run each simulated sample in paralell, or submit as separate jobs to a cluster.

```bash
for i in {1..300}
do
      qsub=${out_dir}"/scripts/qsub_script"${i}"_p.sh"

      echo "#!/bin/bash" > $qsub
      echo "#SBATCH --job-name=sim_${i}_100x_p" >> $qsub
      echo "#SBATCH --partition=batch" >> $qsub
      echo "#SBATCH --nodes=1" >> $qsub
      echo "#SBATCH --tasks-per-node="$cores >> $qsub
      echo "#SBATCH --mem=20G" >> $qsub
      echo "#SBATCH --time=72:00:00" >> $qsub
      echo "#SBATCH --mail-type=END,FAIL" >> $qsub
      echo "#SBATCH --mail-user=${SLURM_JOB_USER}@uga.edu" >> $qsub
      echo "#SBATCH --output=/dev/null" >> $qsub
      echo "#SBATCH --export=NONE" >> $qsub

      CONDA_BASE=$(conda info --base)
      echo "CONDA_BASE=$(conda info --base)" >> $qsub
      echo "source ${CONDA_BASE}/etc/profile.d/conda.sh" >> $qsub
      echo "conda activate mcc_sim" >> $qsub

      echo "python ~/mcclintock/auxiliary/simulation/mcclintock_simulation.py  \\" >> $qsub
      echo "-r ~/mcclintock/test/sacCer2.fasta \\" >> $qsub
      echo "-c ~/mcclintock/test/sac_cer_TE_seqs.fasta \\" >> $qsub
      echo "-g ~/mcclintock/test/reference_TE_locations.gff \\" >> $qsub
      echo "-t ~/mcclintock/test/sac_cer_te_families.tsv \\" >> $qsub
      echo "-p 4 \\" >> $qsub
      echo "--coverage 100 \\" >> $qsub
      echo "--length 101 \\" >> $qsub
      echo "--insert 300 \\" >> $qsub
      echo "--error 0.01 \\" >> $qsub
      echo "--keep_intermediate minimal \\" >> $qsub
      echo "-j ${config} \\" >> $qsub
      echo "--start ${i} \\" >> $qsub
      echo "--end ${i} \\" >> $qsub
      echo "--seed ${i} \\" >> $qsub
      echo "--sim art \\" >> $qsub
      echo "--mcc_version 2 \\" >> $qsub
      echo "-o ${out_dir} &> ${out_dir}/log/mcclintock_ins_sim_${i}_plus.oe" >> $qsub

      sbatch $qsub
done
```
