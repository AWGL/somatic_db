
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

from analysis.models import *

import os
import csv
import yaml


class Command(BaseCommand):
    help = "Import a RNA run"

    def add_arguments(self, parser):
        parser.add_argument('--run', nargs=1, type=str, required=True, help='Run ID')
        parser.add_argument('--worksheet', nargs=1, type=str, required=True, help='Worksheet')
        parser.add_argument('--sample', nargs=1, type=str, required=True, help='Sample ID')
        parser.add_argument('--panel', nargs=1, type=str, required=True, help='Name of virtual panel applied')
        parser.add_argument('--fusions', nargs=1, type=str, required=True, help='Path to variants CSV file')
        parser.add_argument('--coverage', nargs=1, type=str, required=True, help='Path to coverage JSON file')


    @transaction.atomic
    def handle(self, *args, **options):

        # extract variables from argparse
        fusions_file = options['fusions'][0]
        #coverage_file = options['coverage'][0]
        run_id = options['run'][0]
        ws = options['worksheet'][0]
        sample = options['sample'][0]
        panel = options['panel'][0]

        # TODO temporary - input coverage values as comma seperated list
        total_cov, ntc_cov = options['coverage'][0].split(',')
        percent_reads_ntc=int((int(ntc_cov) / int(total_cov))*100)


        # hard coded variables
        dna_or_rna = 'RNA'
        assay = 'TSO500'
        panels_file = settings.ROI_PATH_RNA

        # check that inputs are valid
        if not os.path.isfile(fusions_file):
            raise IOError(f'{fusions_file} file does not exist')
        #if not os.path.isfile(coverage_file):
        #    raise IOError(f'{coverage_file} file does not exist')
        if not os.path.isfile(panels_file):
            raise IOError(f'{panels_file} file does not exist')

        # load in virtual panel
        with open(panels_file) as f:
            referrals = yaml.load(f, Loader=yaml.FullLoader)
        virtual_panel = referrals[panel]


        # get panel object
        panel_obj = Panel.objects.get(panel_name=panel, dna_or_rna=dna_or_rna)

        # make run
        new_run, created = Run.objects.get_or_create(run_id=run_id)

        # make ws
        new_ws = Worksheet(
            ws_id=ws,
            run=new_run,
            assay=assay,
        )
        new_ws.save()

        # make samples
        new_sample, created = Sample.objects.get_or_create(
            sample_id=sample,
            sample_type=dna_or_rna,
        )

        # make sample analysis and checks
        new_sample_analysis = SampleAnalysis(
            worksheet=new_ws,
            sample=new_sample,
            panel=panel_obj,
            total_reads=total_cov,
            total_reads_ntc=ntc_cov,
            percent_reads_ntc=percent_reads_ntc,
        )
        new_sample_analysis.save()

        new_check = Check(
            analysis=new_sample_analysis,
            stage='IGV',
            status='P',
        )
        new_check.save()



        with open(fusions_file) as f:
            reader = csv.DictReader(f, delimiter=',')
            for f in reader:

                # format fusion field and filter panel
                in_panel = False
                
                if f['type'] == 'Splice':
                    fusion = f"{f['fusion']} {f['exons']}"

                    if 'splicing' in virtual_panel.keys():
                        if f['fusion'] in virtual_panel['splicing']:
                            in_panel = True


                elif f['type'] == 'Fusion':
                    fusion = f['fusion']

                    for g in virtual_panel['fusions']:
                        if g in fusion:
                            in_panel = True

                new_fusion, created = Fusion.objects.get_or_create(
                    fusion_genes = fusion,
                    left_breakpoint = f['left_breakpoint'],
                    right_breakpoint = f['right_breakpoint'],
                )


                # make fusions
                if in_panel:
                    print(fusion)
                    #TODO change hard coded variables - they should be optional
                    new_fusion_instance = FusionAnalysis(
                        sample = new_sample_analysis,
                        fusion_genes = new_fusion,
                        fusion_supporting_reads = f['fusion_supporting_reads'],
                        ref_reads_1 = f['reference_reads_1'],
                        fusion_caller = f['type'],
                        in_ntc = f['in_ntc'],
                    )
                    # splice variants only have one reference value, fusions have two (one per gene)
                    if f['type'] == 'Fusion':
                        new_fusion_instance.ref_reads_2 = f['reference_reads_2']
                        new_fusion_instance.fusion_score = f['fusion_score']
                        new_fusion_instance.split_reads = f['split_reads']
                        new_fusion_instance.spanning_reads = f['spanning_reads']
                    new_fusion_instance.save()

                    new_fusion_analysis = FusionPanelAnalysis(
                        sample_analysis = new_sample_analysis,
                        fusion_instance = new_fusion_instance,
                    )
                    new_fusion_analysis.save()

                    new_fusion_check = FusionCheck(
                        fusion_analysis = new_fusion_analysis,
                        check_object = new_check,
                    )
                    new_fusion_check.save()
