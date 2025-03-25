from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

from analysis.models import *

import os
import csv
import json
import yaml
import pybedtools
import numpy as np
from datetime import datetime
from django.utils import timezone


class Command(BaseCommand):
    help = "Import a run"


    def add_gaps_from_list(self, gap, cutoff, new_gene_coverage_obj):
        """
        Use in coverage upload section to add specific gaps for a list in the coverage JSON
        TODO remove when coverage2json updated, called on lines 390, 400, 410
        """
        #if there is no cosmic percent or count present, make this 0 (so adding two numbers to the list)
        
        if len(gap) < 6:
            gap.append(None)
            gap.append(None)
    
        #if cosmic percent is NaN (because no cosmic annotations for that referral), make it 0 (html displays NA in these cases)
        if gap[6] is not None:
            if np.isnan(gap[6]):
                gap[6] = None
            
        new_gap_obj = GapsAnalysis(
            gene = new_gene_coverage_obj,
            hgvs_c = gap[3],
            chr_start = gap[0],
            pos_start = gap[1],
            chr_end = gap[0],
            pos_end = gap[2],
            coverage_cutoff = cutoff,
            percent_cosmic = gap[6],
        )
        new_gap_obj.save()


    def add_gaps_from_dict(self, gap, cutoff, new_gene_coverage_obj):
        """
        Use in coverage upload section to add specific gaps for a list in the coverage JSON
        """
        # handle weird inputs for COSMIC percent
        if 'percent_cosmic' not in gap.keys():
            perc_cosmic = None
        elif gap['percent_cosmic'] == 'N/A':
            perc_cosmic = None
        elif np.isnan(gap['percent_cosmic']):
            perc_cosmic = None
        else:
            perc_cosmic = gap['percent_cosmic']

        # handle weird inputs for COSMIC counts
        if 'counts_cosmic' not in gap.keys():
            counts_cosmic = None
        elif gap['counts_cosmic'] == 'N/A':
            counts_cosmic = None
        elif np.isnan(gap['counts_cosmic']):
            counts_cosmic = None
        else:
            counts_cosmic = gap['counts_cosmic']

        # add gap to database
        new_gap_obj = GapsAnalysis(
            gene = new_gene_coverage_obj,
            hgvs_c = gap['hgvs_c'],
            chr_start = gap['chr'],
            pos_start = gap['pos_start'],
            chr_end = gap['chr'],
            pos_end = gap['pos_end'],
            coverage_cutoff = cutoff,
            percent_cosmic = perc_cosmic,
            counts_cosmic = counts_cosmic,
        )
        new_gap_obj.save()


    def add_regions_from_list(self, region, hotspot, new_gene_coverage_obj):
        """
        Add specific regions (e.g. exons or codons) and their associated coverages
        TODO remove this when coverage2json updated, called on lines 372, 381
        """
        new_regions_obj = RegionCoverageAnalysis(
            gene = new_gene_coverage_obj,
            hgvs_c = region[3],
            chr_start = region[0],
            pos_start = region[1],
            chr_end = region[0],
            pos_end = region[2],
            hotspot = hotspot,
            average_coverage = region[4],
            percent_135x = region[6],
            percent_270x = region[5],
            ntc_coverage = region[7],
            percent_ntc = region[8],
        )
        new_regions_obj.save()


    def add_regions_from_dict(self, region, hotspot, new_gene_coverage_obj):
        """
        Add specific regions (e.g. exons or codons) and their associated coverages
        """
        percent_135x = region.get('percent_135', None)
        percent_270x = region.get('percent_270', None)
        percent_500x = region.get('percent_500', None)
        percent_1000x = region.get('percent_1000', None)

        new_regions_obj = RegionCoverageAnalysis(
            gene = new_gene_coverage_obj,
            hgvs_c = region['hgvs_c'],
            chr_start = region['chr'],
            pos_start = region['pos_start'],
            chr_end = region['chr'],
            pos_end = region['pos_end'],
            hotspot = hotspot,
            average_coverage = region['average_coverage'],
            percent_135x = percent_135x,
            percent_270x = percent_270x,
            percent_500x = percent_500x,
            percent_1000x = percent_1000x,
            ntc_coverage = region['ntc_coverage'],
            percent_ntc = region['percent_ntc'],
        )
        new_regions_obj.save()


    def add_arguments(self, parser):
        parser.add_argument('--run', nargs=1, type=str, required=True, help='Run ID')
        parser.add_argument('--worksheet', nargs=1, type=str, required=True, help='Worksheet')
        parser.add_argument('--assay', nargs=1, type=str, required=True, help='Assay')
        parser.add_argument('--sample', nargs=1, type=str, required=True, help='Sample ID')
        parser.add_argument('--panel', nargs=1, type=str, required=True, help='Name of virtual panel applied')
        parser.add_argument('--genome', nargs=1, type=str, required=True, help='Reference genome as GRCh37 or GRCh38')
        parser.add_argument('--debug', nargs=1, type=str, required=True, help='Show detailed logging')

        # SNV/ indel only
        parser.add_argument('--snvs', nargs=1, type=str, required=False, help='Path to SNVs CSV file')
        parser.add_argument('--snv_coverage', nargs=1, type=str, required=False, help='Path to coverage JSON file')

        # fusion only
        parser.add_argument('--fusions', nargs=1, type=str, required=False, help='Path to fusions CSV file')
        parser.add_argument('--fusion_coverage', nargs=1, type=str, required=False, help='sample and NTC coverage, seperated by commas')


    @transaction.atomic
    def handle(self, *args, **options):
        """
        Run sample upload script
        """

        # ---------------------------------------------------------------------------------------------------------
        # Setup
        # ---------------------------------------------------------------------------------------------------------

        # extract variables from argparse
        run_id = options['run'][0]
        ws = options['worksheet'][0]
        sample = options['sample'][0]
        debug_input = options['debug'][0]
        # convert string to boolean
        debug = bool(debug_input == 'True')

        # check assay is in list and use to extract variables
        assay = options['assay'][0]
        assay_choices = {
            'TSO500_DNA': '1',
            'TSO500_RNA': '2',
            'TSO500_ctDNA': '3',
            'GeneRead_CRM': '4',
            'GeneRead_BRCA': '5',
        }
        if assay not in assay_choices.keys():
            print(f'ERROR\t{datetime.now()}\timport.py\tUnknown assay - {assay}')
            raise IOError(f'ERROR\tUnknown assay - {assay}')

        # check genome build is in list
        genome = options['genome'][0]
        if genome == 'GRCh38':
            genome_build = 38
        elif genome == 'GRCh37':
            genome_build = 37
        else:
            raise IOError(f'Genome build {genome} is neither GRCh37 or GRCh38')

        # check that worksheet not already uploaded with another sequencing run
        exist_worksheets = Worksheet.objects.filter(ws_id = ws)

        if len(exist_worksheets) != 0:
            for worksheet in exist_worksheets:
                if worksheet.run.run_id != run_id:
                    raise IOError(f'Worksheet {ws} uploaded already on another sequencing run {worksheet.run.run_id}. Please edit worksheet ID and try again e.g. {ws}R')

        # current time for upload timestamps
        current_time = timezone.now()

        # ---------------------------------------------------------------------------------------------------------
        # Sample level objects
        # ---------------------------------------------------------------------------------------------------------

        # get panel object
        panel = options['panel'][0]
        panel_obj = Panel.objects.get(panel_name=panel, assay=assay_choices[assay], live=True, genome_build=genome_build)

        # make run
        new_run, created = Run.objects.get_or_create(run_id=run_id)

        # make ws
        new_ws, created = Worksheet.objects.get_or_create(
            ws_id=ws,
            run=new_run,
            assay=assay,
        )
        # only add timestamp when worksheet is initially created (dont update when a new sample added)
        if created:
            new_ws.upload_time = current_time

        new_ws.save()

        # make samples
        new_sample, created = Sample.objects.get_or_create(
            sample_id=sample,
        )

        # make sample analysis and checks
        new_sample_analysis = SampleAnalysis(
            worksheet=new_ws,
            sample=new_sample,
            panel=panel_obj,
            genome_build=genome_build,
            upload_time=current_time,
        )
        # add num reads if in panel settings
        if panel_obj.show_fusion_coverage:

            # get values from argparse and handle missing values
            total_cov, ntc_cov = options['fusion_coverage'][0].split(',')
            if total_cov == 'NA':
                total_cov = 0
            if ntc_cov == 'NA':
                ntc_cov = 0

            # add to model
            new_sample_analysis.total_reads = total_cov
            new_sample_analysis.total_reads_ntc = ntc_cov

        new_sample_analysis.save()

        new_check = Check(
            analysis=new_sample_analysis,
            stage='IGV',
            status='P',
        )
        new_check.save()
        
        # Specifies the cancer hotspots file for annotation
        if genome_build == "GRCh37":
            cancer_hotspots_file = "/roi/20220125_hotspots_all_37.bed"
        elif genome_build == "GRCh38":
            cancer_hotspots_file = "/roi/20220125_hotspots_all_38.bed"
        
        if not os.path.isfile(cancer_hotspots_file):
                print(f'ERROR\t{datetime.now()}\timport.py\t{cancer_hotspots_file} file does not exist')
                raise IOError(f'{cancer_hotspots_file} file does not exist')
        
        # ---------------------------------------------------------------------------------------------------------
        # SNVs and indels
        # ---------------------------------------------------------------------------------------------------------
        if panel_obj.show_snvs:

            # counter for logging
            snv_counter = 0
            print(f'INFO\t{datetime.now()}\timport.py\tUploading SNVs...')

            # files from argparse
            snvs_file = options['snvs'][0]
            coverage_file = options['snv_coverage'][0]

            # check that inputs are valid
            if not os.path.isfile(snvs_file):
                print(f'ERROR\t{datetime.now()}\timport.py\t{snvs_file} file does not exist')
                raise IOError(f'{snvs_file} file does not exist')
            if not os.path.isfile(coverage_file):
                print(f'ERROR\t{datetime.now()}\timport.py\t{coverage_file} file does not exist')
                raise IOError(f'{coverage_file} file does not exist')

            # get filepath for bed from panel model
            panel_bed_file = panel_obj.bed_file.path
            if not os.path.isfile(panel_bed_file):
                print(f'ERROR\t{datetime.now()}\timport.py\t{panel_bed_file} file does not exist')
                raise IOError(f'{panel_bed_file} file does not exist')

            # open bed file object
            panel_bed = pybedtools.BedTool(panel_bed_file)

            # pull cutoff from panel object
            vaf_threshold = panel_obj.vaf_cutoff

            # make variants and variant checks
            with open(snvs_file) as f:
                reader = csv.DictReader(f, delimiter='\t')

                for v in reader:

                    # format pos, chr, ref etc as genomic coords
                    genomic_coords = f"{v['chr'].strip('chr')}:{v['pos']}{v['ref']}>{v['alt']}"

                    # determine whether or not VAF is above threshold
                    vaf = float(v['vaf']) * 100
                    above_vaf_threshold = (vaf >= vaf_threshold)

                    # variant object is created for all variants across whole panel
                    new_var, created = Variant.objects.get_or_create(
                        variant = genomic_coords,
                        genome_build = genome_build,
                    )

                    ## check if variant is within the virtual panel
                    # format variant pos as a line of bed file 
                    variant_as_bed=f"{v['chr'].strip('chr')}\t{int(v['pos']) -1}\t{v['pos']}"
                    variant_bed_region = pybedtools.BedTool(variant_as_bed, from_string=True)

                    # boolean if variant overlaps with panel
                    overlaps_panel = len(panel_bed.intersect(variant_bed_region)) > 0

                    # if both booleans true, enter loop
                    if overlaps_panel and above_vaf_threshold:
                        if debug:
                            print(f'DEBUG\t{datetime.now()}\timport.py\tAdding variant: {v}')
                    
                        # if gnomad frequency not there, make it None
                        if 'gnomad_popmax_AF' not in v:
                            v['gnomad_popmax_AF'] = None
                            
                        if v['in_ntc'] == '':
                        	v['in_ntc'] = False

                        # boolean if variant overlaps with hotspot
                        overlaps_hotspots = len(hotspots_bed.intersect(variant_bed_region)) > 0

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
                            gnomad_popmax = v['gnomad_popmax_AF'],
                            is_hotspot = overlaps_hotspots,
                        )
                        
                        # For new database had to convert string to boolean
                        if v['in_ntc'] == 'False':
                            v['in_ntc'] = False
                        
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

                        # logging
                        snv_counter += 1
                        if debug:
                            print(f'DEBUG\t{datetime.now()}\timport.py\tVariant added successfully')

            # logging
            print(f'INFO\t{datetime.now()}\timport.py\tFinished uploading SNVs successfully - added {snv_counter} variant(s)')
            print(f'INFO\t{datetime.now()}\timport.py\tUploading coverage data...')


            # ---------------------------------------------------------------------------------------------------------
            # Coverage
            # ---------------------------------------------------------------------------------------------------------

            # make coverage data - coverage json is already filtered for panel
            with open(coverage_file, 'r') as f:
                coverage_dict = json.load(f)

            # get required coverage values from panel
            coverage_thresholds = panel_obj.depth_cutoffs.split(',')

            for g, values in coverage_dict.items():
                # get gene object
                gene, created = Gene.objects.get_or_create(gene=g)

                # get the coverage values, if they're missing default to none
                percent_135x = values.get('percent_135', None)
                percent_270x = values.get('percent_270', None)
                percent_500x = values.get('percent_500', None)
                percent_1000x = values.get('percent_1000', None)

                # save to db
                new_gene_coverage_obj = GeneCoverageAnalysis(
                    sample=new_sample_analysis,
                    gene=gene,
                    av_coverage=values['average_depth'],
                    percent_135x=percent_135x,
                    percent_270x=percent_270x,
                    percent_500x=percent_500x,
                    percent_1000x=percent_1000x,
                    av_ntc_coverage=values['average_ntc'],
                    percent_ntc=values['percent_ntc'],
                )
                new_gene_coverage_obj.save()

                # genescreen region
                if 'genescreen_regions' in values:
                    for r in values['genescreen_regions']:
                        if isinstance(r, list):
                            self.add_regions_from_list(r, 'G', new_gene_coverage_obj)

                        elif isinstance(r, dict):
                            self.add_regions_from_dict(r, 'G', new_gene_coverage_obj)


                # hotspot regions
                if 'hotspot_regions' in values:
                    for r in values['hotspot_regions']:
                        if isinstance(r, list):
                            self.add_regions_from_list(r, 'H', new_gene_coverage_obj)

                        elif isinstance(r, dict):
                            self.add_regions_from_dict(r, 'H', new_gene_coverage_obj)

                    # gaps 135x
                    if '135' in coverage_thresholds:
                        for gap in values['gaps_135']:
                            if isinstance(r, list):
                                self.add_gaps_from_list(gap, '135', new_gene_coverage_obj)

                            elif isinstance(r, dict):
                                self.add_gaps_from_dict(gap, '135', new_gene_coverage_obj)

                    # gaps 270x
                    if '270' in coverage_thresholds:
                        for gap in values['gaps_270']:
                            if isinstance(r, list):
                                self.add_gaps_from_list(gap, '270', new_gene_coverage_obj)

                            elif isinstance(r, dict):
                                self.add_gaps_from_dict(gap, '270', new_gene_coverage_obj)

                    # gaps 500
                    if '500' in coverage_thresholds:
                        for gap in values['gaps_500']:
                            if isinstance(r, list):
                                self.add_gaps_from_list(gap, '500', new_gene_coverage_obj)

                            elif isinstance(r, dict):
                                self.add_gaps_from_dict(gap, '500', new_gene_coverage_obj)

                    # gaps 1000x
                    if '1000' in coverage_thresholds:
                        for gap in values['gaps_1000']:
                            if isinstance(r, list):
                                self.add_gaps_from_list(gap, '1000', new_gene_coverage_obj)

                            elif isinstance(r, dict):
                                self.add_gaps_from_dict(gap, '1000', new_gene_coverage_obj)

            # logging
            print(f'INFO\t{datetime.now()}\timport.py\tFinished uploading coverage data successfully')


        # ---------------------------------------------------------------------------------------------------------
        # fusions
        # ---------------------------------------------------------------------------------------------------------

        if panel_obj.show_fusions:
            fusions_file = options['fusions'][0]

            # check that inputs are valid
            if not os.path.isfile(fusions_file):
                print(f'ERROR\t{datetime.now()}\timport.py\t{fusions_file} file does not exist')
                raise IOError(f'{fusions_file} file does not exist')

            # load in virtual panel, handle empty strings as they cant be split
            splicing, fusions = [], []
            if panel_obj.splice_genes:
                splicing = panel_obj.splice_genes.split(',')
            if panel_obj.fusion_genes:
                fusions = panel_obj.fusion_genes.split(',')
                
            # make panel dictionary
            virtual_panel = {
                'splicing': splicing,
                'fusions': fusions,
            }

            # logging
            fusion_counter = 0
            print(f'INFO\t{datetime.now()}\timport.py\tUploading fusions...')

            # load in fusion calls
            with open(fusions_file) as f:

                # make dictionary of calls and loop through
                reader = csv.DictReader(f, delimiter=',')
                for f in reader:

                    # sanitise the fusion input to prevent multiple fusions with the same breakpoints but different names
                    # we want to remove GENE1/GENE2 and GENE1--GENE2 and just have GENE1-GENE2
                    fusion_name = f['fusion']
                    sanitised_fusion_name = fusion_name.replace("/","-").replace("--","-")

                    # format fusion field and filter panel
                    in_panel = False
                        
                    # splice variants
                    if f['type'] == 'Splice':
                        # add exon number to gene name
                        fusion = f"{sanitised_fusion_name} {f['exons']}"

                        # check splicing gene list and set variable if matches
                        if 'splicing' in virtual_panel.keys():
                            if f['fusion'] in virtual_panel['splicing']:
                                in_panel = True

                    # gene fusions
                    elif f['type'] == 'Fusion':
                        # use pipeline output directly (will be GENE_A--GENE_B)
                        fusion = sanitised_fusion_name

                        # check fusion gene list and set variable if matches
                        for g in virtual_panel['fusions']:
                            if g in fusion:
                                in_panel = True

                    # add record for fusion (regardless of whether it's in the panel or not)
                    new_fusion, created = Fusion.objects.get_or_create(
                        fusion_genes = fusion,
                        left_breakpoint = f['left_breakpoint'],
                        right_breakpoint = f['right_breakpoint'],
                        genome_build = genome_build
                    )

                    # if the fusion was in the panel, make a fusion instance
                    if in_panel:
                        # logging
                        if debug:
                            print(f'DEBUG\t{datetime.now()}\timport.py\tAdding fusion: {f}')

                        # add fusion instance object
                        new_fusion_instance = FusionAnalysis(
                            sample = new_sample_analysis,
                            fusion_genes = new_fusion,
                            fusion_supporting_reads = f['fusion_supporting_reads'],
                            ref_reads_1 = f['reference_reads_1'],
                            fusion_caller = f['type'],
                            in_ntc = f['in_ntc'],
                        )
                        # some variables aren't always included in pipeline output (particularly for splice variants)
                        if f['reference_reads_2'] not in ['', 'NA']:
                            new_fusion_instance.ref_reads_2 = f['reference_reads_2']
                        if f['fusion_score'] != '':
                            new_fusion_instance.fusion_score = f['fusion_score']
                        if f['split_reads'] != '':
                            new_fusion_instance.split_reads = f['split_reads']
                        if f['split_reads'] != '':
                            new_fusion_instance.spanning_reads = f['spanning_reads']
                        new_fusion_instance.save()

                        # set up virtual panel
                        new_fusion_analysis = FusionPanelAnalysis(
                            sample_analysis = new_sample_analysis,
                            fusion_instance = new_fusion_instance,
                        )
                        new_fusion_analysis.save()

                        # set up check object
                        new_fusion_check = FusionCheck(
                            fusion_analysis = new_fusion_analysis,
                            check_object = new_check,
                        )
                        new_fusion_check.save()

                        # logging
                        fusion_counter += 1
                        if debug:
                            print(f'DEBUG\t{datetime.now()}\timport.py\tFusion added successfully')

                # logging
                print(f'INFO\t{datetime.now()}\timport.py\tFinished uploading successfully - added {fusion_counter} fusions(s)')

        # close
        print(f'INFO\t{datetime.now()}\timport.py\tFinished import.py script successfully')
