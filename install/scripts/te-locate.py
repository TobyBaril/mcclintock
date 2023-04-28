import sys
import os
sys.path.append(snakemake.config['paths']['mcc_path'])
import scripts.mccutils as mccutils

def main():
    mccutils.remove(snakemake.params.tar)
    download_success = mccutils.download(snakemake.params.url, snakemake.params.tar, md5=snakemake.params.md5, max_attempts=3)

    if not download_success:
        print("TE-Locate download failed... exiting...")
        sys.exit(1)


    command = ["tar", "-xvf", snakemake.params.tar, "-C", snakemake.config['paths']['install']+"/tools/te-locate/"]
    mccutils.run_command(command, log=snakemake.params.log)

    # write version to file
    with open(snakemake.config['paths']['install']+"/tools/te-locate/version.log","w") as version:
        version.write(snakemake.params.md5)

if __name__ == "__main__":                
    main()