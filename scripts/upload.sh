
echo -e "INFO\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\tFound new samples file - "$1

for s in $(cat $1); do
    # get path where samples file is located
    data_folder=$(dirname $1)
    data_file=$(basename $1)

    # get common variables
    sample_id=$(echo $s | cut -d, -f1)
    ws=$(echo $s | cut -d, -f2)
    assay=$(echo $s | cut -d, -f3)
    referral=$(echo $s | cut -d, -f4)
    run=$(echo $s | cut -d, -f5)
    genome=$(echo $s | cut -d, -f6)

    # DNA specific variables
    if [ "$assay" == 'DNA' ]; then 
        assay="TSO500_DNA"
    fi

    # RNA specific variables - TODO-reorder in pipeline so that run and genome are the same order as DNA
    if [ "$assay" == 'RNA' ]; then 
        assay="TSO500_RNA"
        cov=$(echo $s | cut -d, -f5)
        ntc_cov=$(echo $s | cut -d, -f6)
        run=$(echo $s | cut -d, -f7)
        genome=$(echo $s | cut -d, -f8)
    fi

    # check if run ID not given on sample list, take from command line (so old style upload will still work for older runs). If reference genome not given, make GRCh37 - again for old runs
    if [ -z "$run" ]; then run=$2; fi
    if [ -z "$run" ]; then
        echo -e "ERROR\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\tNo run ID found, exiting script"
        exit 1
    fi
    if [ -z "$genome" ]; then genome="GRCh37"; fi

    # log to terminal
    echo "------------------------------------------------------------------------------------------------------------"
    echo -e "INFO\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\tStarting database upload for "$sample_id
    echo -e "INFO\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\t - Sample ID:    "$sample_id
    echo -e "INFO\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\t - Run ID:       "$run
    echo -e "INFO\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\t - Worksheet ID: "$ws
    echo -e "INFO\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\t - Assay:        "$assay
    echo -e "INFO\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\t - Referral:     "$referral
    echo -e "INFO\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\t - Input folder: "$data_folder
    echo -e "INFO\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\t - Input file:   "$data_file
    echo -e "INFO\t"$(date +"%Y-%m-%d %T.%6N")"\tupload.sh\tLaunching import.py script"

    # run once with all flags, specific requirements for each assay handled in python script
    python manage.py import \
      --run $run \
      --worksheet $ws \
      --assay $assay \
      --sample $sample_id \
      --panel $referral \
      --genome $genome \
      --snvs "$data_folder"/"$sample_id"_variants.tsv \
      --snv_coverage "$data_folder"/"$sample_id"_"$referral"_coverage.json \
      --fusions "$data_folder"/"$sample_id"_fusion_check.csv \
      --fusion_coverage "$cov","$ntc_cov" \
      --msi "$data_folder"/"$sample_id"_msi.txt \
      --debug False

    echo "------------------------------------------------------------------------------------------------------------"

done
