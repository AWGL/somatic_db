
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

from analysis.models import *

import os
import csv
import json
import pybedtools


class Command(BaseCommand):
    help = "Import a DNA run"

    def add_arguments(self, parser):
        parser.add_argument('--run', nargs=1, type=str, required=True, help='Run ID')
        parser.add_argument('--worksheet', nargs=1, type=str, required=True, help='Worksheet')
        parser.add_argument('--sample', nargs=1, type=str, required=True, help='Sample ID')
        parser.add_argument('--panel', nargs=1, type=str, required=True, help='Name of virtual panel applied')
        parser.add_argument('--variants', nargs=1, type=str, required=True, help='Path to variants CSV file')
        parser.add_argument('--coverage', nargs=1, type=str, required=True, help='Path to coverage JSON file')


    @transaction.atomic
    def handle(self, *args, **options):
        """
        Run sample upload script
        """
        # extract variables from argparse
        variants_file = options['variants'][0]
        coverage_file = options['coverage'][0]
        run_id = options['run'][0]
        ws = options['worksheet'][0]
        sample = options['sample'][0]
        panel = options['panel'][0]

        # hard coded variables
        dna_or_rna = 'DNA'
        assay = 'TSO500'
        panel_folder = settings.ROI_PATH_DNA
        panel_bed_file = f'{panel_folder}/{panel}.bed' 

        # check that inputs are valid
        if not os.path.isfile(variants_file):
            raise IOError(f'{variants_file} file does not exist')
        if not os.path.isfile(coverage_file):
            raise IOError(f'{coverage_file} file does not exist')
        if not os.path.isfile(panel_bed_file):
            raise IOError(f'{panel_bed_file} file does not exist')

        # get panel object TODO - add error if doesnt exist
        panel_obj = Panel.objects.get(panel_name=panel, dna_or_rna='DNA')

        # open bed file object
        panel_bed = pybedtools.BedTool(panel_bed_file)

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
        )
        new_sample_analysis.save()

        new_check = Check(
            analysis=new_sample_analysis,
            stage='IGV',
            status='P',
        )
        new_check.save()


        # make variants and variant checks
        with open(variants_file) as f:
            reader = csv.DictReader(f, delimiter='\t')

            for v in reader:

                # format pos, chr, ref etc as genomic coords
                genomic_coords = f"{v['chr'].strip('chr')}:{v['pos']}{v['ref']}>{v['alt']}"

                # determine whether or not VAF is above threshold
                vaf = float(v['vaf']) * 100
                above_vaf_threshold = (vaf >= 1.4)

                # variant object is created for all variants across whole panel
                new_var, created = Variant.objects.get_or_create(
                    genomic_37 = genomic_coords,
                    genomic_38 = None,
                )

                ## check if variant is within the virtual panel
                # format variant pos as a line of bed file 
                variant_as_bed=f"{v['chr'].strip('chr')}\t{int(v['pos']) -1}\t{v['pos']}"
                variant_bed_region = pybedtools.BedTool(variant_as_bed, from_string=True)

                # boolean if variant overlaps with panel
                overlaps_panel = len(panel_bed.intersect(variant_bed_region)) > 0

                # if both booleans true, enter loop
                if overlaps_panel and above_vaf_threshold:
                    print(v)

                    # make new instance of variant
                    new_var_instance = VariantInstance(
                        sample = new_sample,
                        variant = new_var,
                        gene = v['gene'],
                        exon = v['exon'],
                        hgvs_c = v['hgvs_c'],
                        hgvs_p = v['hgvs_p'],
                        total_count = v['depth'],
                        alt_count = v['alt_reads'],
                        in_ntc = v['in_ntc'],
                    )

                    # add NTC read counts if the variant is seen in the NTC
                    if v['in_ntc']:
                        new_var_instance.total_count_ntc = v['ntc_depth']
                        new_var_instance.alt_count_ntc = v['ntc_alt_reads']

                    new_var_instance.save()

                    # put on panel
                    new_var_panel_analysis = VariantPanelAnalysis(
                        sample_analysis = new_sample_analysis,
                        variant_instance = new_var_instance,
                    )
                    new_var_panel_analysis.save()

                    # add check
                    new_var_check = VariantCheck(
                        variant_analysis=new_var_panel_analysis,
                        check_object=new_check,
                    )
                    new_var_check.save()

        # make coverage data - coverage json is already filtered for panel
        with open(coverage_file, 'r') as f:
            coverage_dict = json.load(f)


        for g, values in coverage_dict.items():

            gene, created = Gene.objects.get_or_create(gene=g)

            new_gene_coverage_obj = GeneCoverageAnalysis(
                sample=new_sample_analysis,
                gene=gene,
                av_coverage=values['average_depth'],
                percent_270x=values['percent_270'],
                percent_135x=values['percent_135'],
                av_ntc_coverage=values['average_ntc'],
                percent_ntc=values['percent_ntc'],
            )
            new_gene_coverage_obj.save()


            # hotspot regions
            for r in values['hotspot_regions']:
                new_regions_obj = RegionCoverageAnalysis(
                    gene=new_gene_coverage_obj,
                    hgvs_c=r[3],
                    chr_start=r[0],
                    pos_start=r[1],
                    chr_end=r[0],
                    pos_end=r[2],
                    hotspot='H',
                    average_coverage=r[4],
                    percent_270x=r[5],
                    percent_135x=r[6],
                    ntc_coverage=r[7],
                    percent_ntc=r[8],
                )
                new_regions_obj.save()

            # genescreen regions
            for r in values['genescreen_regions']:
                new_regions_obj = RegionCoverageAnalysis(
                    gene=new_gene_coverage_obj,
                    hgvs_c=r[3],
                    chr_start=r[0],
                    pos_start=r[1],
                    chr_end=r[0],
                    pos_end=r[2],
                    hotspot='G',
                    average_coverage=r[4],
                    percent_270x=r[5],
                    percent_135x=r[6],
                    ntc_coverage=r[7],
                    percent_ntc=r[8],
                )
                new_regions_obj.save()
        
            # TODO - add cosmic to this when integrated into pipeline
            for gap in values['gaps_135']:
                new_gap_obj = GapsAnalysis(
                    gene=new_gene_coverage_obj,
                    hgvs_c=gap[3],
                    chr_start=gap[0],
                    pos_start=gap[1],
                    chr_end=gap[0],
                    pos_end=gap[2],
                    coverage_cutoff=135,
                )
                new_gap_obj.save()


            for gap in values['gaps_270']:
                new_gap_obj = GapsAnalysis(
                    gene=new_gene_coverage_obj,
                    hgvs_c=gap[3],
                    chr_start=gap[0],
                    pos_start=gap[1],
                    chr_end=gap[0],
                    pos_end=gap[2],
                    coverage_cutoff=270,
                )
                new_gap_obj.save()
