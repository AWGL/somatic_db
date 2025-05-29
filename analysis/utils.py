from .models import *
from .forms import NewVariantForm, SubmitForm, VariantCommentForm, FusionCommentForm

from django.utils import timezone
from django.db import transaction

import pybedtools
import re
import requests
import csv

def get_samples(samples):
    """
    Create context dictionary of all sample analyses for rendering the worksheet page

    """
    # adds a record for each panel analysis - i.e. if a sample has two panels
    # it will have two records
    sample_dict = {}
    for s in samples:
        sample_id = s.sample.sample_id

        # if there haven't been any panels for the sample yet, add new sample to dict
        if sample_id not in sample_dict.keys():

            sample_dict[sample_id] = {
                'sample_id': sample_id,
                'panels': [{
                    'analysis_id': s.pk,
                    'worksheet': s.worksheet,
                    'diagnostic': s.worksheet.diagnostic,
                    'assay': s.panel.get_assay_display(),
                    'panel': s.panel,
                    'status': s.get_status(),
                    'checks': s.get_checks(),
                }]
            }

        # if there are already panels for sample, add new panel to sample record
        else:
            sample_dict[sample_id]['panels'].append({
                    'analysis_id': s.pk,
                    'worksheet': s.worksheet,
                    'diagnostic': s.worksheet.diagnostic,
                    'assay': s.panel.get_assay_display(),
                    'panel': s.panel,
                    'status': s.get_status(),
                    'checks': s.get_checks(),
                }
            )

    return sample_dict


@transaction.atomic
def unassign_check(sample_analysis_obj):
    """
    Unassign a sample analysis so that if can be analysed by someone else, resets the check to begin from scratch

    """
    # get latest check
    all_checks = sample_analysis_obj.get_checks()
    latest_check = all_checks['current_check_object']
    current_status = sample_analysis_obj.get_status()

    # if resetting from 1st check, reset the tickbox for the paperwork check too
    if current_status == 'IGV check 1':
        sample_analysis_obj.paperwork_check = False

    # reset check
    latest_check.status = '-'
    latest_check.user = None
    latest_check.coverage_ntc_check = False
    latest_check.coverage_comment = ''
    latest_check.coverage_comment_updated = None
    latest_check.patient_info_check = False
    latest_check.manual_review_check = False
    latest_check.overall_comment = ''
    latest_check.overall_comment_updated = None
    latest_check.signoff_time = None
    latest_check.save()
    
    # get dna variant checks and reset
    variant_checks = VariantCheck.objects.filter(check_object=latest_check)
    for c in variant_checks:
        c.decision = '-'
        c.comment = ''
        c.comment_updated = None
        c.save()

    # get rna variant checks and reset
    fusion_checks = FusionCheck.objects.filter(check_object=latest_check)
    for c in fusion_checks:
        c.decision = '-'
        c.comment = ''
        c.comment_updated = None
        c.save()

    sample_analysis_obj.save()

    return True


@transaction.atomic
def reopen_check(user, sample_analysis_obj):
    """
    Allow the person who closed the case to reopen it to the previous check
    """
    # set sample analysis status back to pending
    sample_analysis_obj.sample_pass_fail = '-'
    sample_analysis_obj.save()

    # get the latest check
    all_checks = sample_analysis_obj.get_checks()
    latest_check = all_checks['current_check_object']

    latest_check.status = '-'
    latest_check.user = user
    latest_check.signoff_time = None
    latest_check.save()
    sample_analysis_obj.save()

    return True


def get_sample_info(sample_obj):
    """
    Get info for a specific sample to generate a part of the sample analysis context dictionary

    """
    # split the manual regions description if its part of the panel, otherwise make empty list
    if sample_obj.panel.manual_review_desc:
        manual_regions = sample_obj.panel.manual_review_desc.split('|')
    else:
        manual_regions = []

    sample_data = {
        'sample_pk': sample_obj.pk,
        'assay': sample_obj.panel.assay,
        'sample_id': sample_obj.sample.sample_id,
        'worksheet_id': sample_obj.worksheet.ws_id,
        'panel': sample_obj.panel.panel_name,
        'panel_obj': sample_obj.panel,
        'panel_manual_regions': manual_regions,
        'is_myeloid_referral': sample_obj.panel.show_myeloid_gaps_summary,
        'run_id': sample_obj.worksheet.run.run_id,
        'total_reads': sample_obj.total_reads,
        'total_reads_ntc': sample_obj.total_reads_ntc,
        'percent_reads_ntc': sample_obj.percent_reads_ntc(),
        'checks': sample_obj.get_checks(),
        'status': sample_obj.get_status(),
        'genome_build': sample_obj.genome_build,
        'test_code': sample_obj.panel.lims_test_code,
    }
    return sample_data


def get_variant_info(sample_data, sample_obj):
    """
    Get information on all variants in a sample analysis to generate the variant portion of the context dictionary

    """
    # load in all variants in sample
    sample_variants = VariantPanelAnalysis.objects.filter(sample_analysis=sample_obj)

    # make empty variables for storing results
    variant_calls = []
    reportable_list = []
    filtered_list = []
    other_calls_list = []
    poly_count = 0
    artefact_count = 0


    # loop through each sample variant
    for sample_variant in sample_variants:

        # load instance of variant
        variant_obj = sample_variant.variant_instance.variant

        # get checks for each variant
        variant_checks = VariantCheck.objects.filter(variant_analysis=sample_variant).order_by('pk')
        variant_checks_list = [ v.get_decision_display() for v in variant_checks ]
        latest_check = variant_checks.latest('pk')

        # marker to tell whether a variant should be filtered downstream
        filter_call = False
        filter_reason = ''

        # get VAF and round to nearest whole number - used in artefact list so must be on top
        vaf = sample_variant.variant_instance.vaf()
        vaf_rounded = vaf.quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)

        # get poly/artefact lists relevent to this sample
        poly_lists = VariantList.objects.filter(genome_build=variant_obj.genome_build, list_type='P')
        artefact_lists = VariantList.objects.filter(genome_build=variant_obj.genome_build, list_type='A', assay = sample_obj.panel.assay)
        variant_lists = poly_lists | artefact_lists

        # get whether the variant falls within a poly/ artefact list
        for l in VariantToVariantList.objects.filter(variant=variant_obj):

            # if signed off and in one of the variant lists for this sample
            if l.signed_off() and (l.variant_list in variant_lists):

                # if its a poly
                if l.variant_list.list_type == 'P':
                    # set variables and update variant check
                    poly_count += 1
                    filter_call = True
                    filter_reason = 'Poly'
                    latest_check.decision = 'P'
                    latest_check.save()

                # if its an artefact
                elif l.variant_list.list_type == 'A':
                    # only add if above the VAF cutoff or there is no cutoff
                    if l.vaf_cutoff == None or l.vaf_cutoff == 0.0 or vaf < l.vaf_cutoff:
                        # set variables and update variant check
                        artefact_count += 1
                        filter_call = True
                        latest_check.decision = 'A'
                        latest_check.save()

                        # add VAF cutoff to reason for filtering
                        if vaf < l.vaf_cutoff:
                            vaf_cutoff_rounded = l.vaf_cutoff.quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)
                            filter_reason = f'Artefact at <{vaf_cutoff_rounded}% VAF'
                        else:
                            filter_reason = 'Artefact'

        # remove Not analysed from checks list
        variant_checks_analysed = []
        for c in variant_checks_list:
            if c != 'Not analysed':
                variant_checks_analysed.append(c)

        # do the last two checks agree?
        last_two_checks_agree = True
        if len(variant_checks_analysed) > 1:
            last2 = variant_checks_analysed[-2:]
            if last2[0] != last2[1]:
                last_two_checks_agree = False

        # if variant is to appear on report tab, add to list
        if sample_variant.variant_instance.get_final_decision_display() in ['Genuine']:
            reportable_list.append(variant_obj.variant)

        # list of other calls to go in the footer of the report
        if sample_variant.variant_instance.get_final_decision_display() in ['Miscalled', 'Failed call']:
            other_calls_list.append(f'{sample_variant.variant_instance.gene} {sample_variant.variant_instance.hgvs_c}')

        # get list of comments for variant
        variant_comments_list = []
        for v in variant_checks:
            if v.comment:
                variant_comments_list.append(
                    { 'comment': v.comment, 'user': v.check_object.user, 'updated': v.comment_updated, }
                )

        # load comments into variant comment form
        var_comment_form = VariantCommentForm(pk=latest_check.pk, comment=latest_check.comment)

        # split out transcript and c./p., wrap in try/except because sometimes its empty
        try:
            hgvs_c_short = sample_variant.variant_instance.hgvs_c.split(':')[1]
        except IndexError:
            hgvs_c_short = ''

        try:
            hgvs_p_short = sample_variant.variant_instance.hgvs_p.split(':')[1]
        except IndexError:
            hgvs_p_short = ''

        try:
            transcript = sample_variant.variant_instance.hgvs_c.split(':')[0]
        except IndexError:
            transcript = ''

        #Create a variant calls dictionary to pass to analysis-snvs.html
        variant_calls_dict = {
            'pk': sample_variant.pk,
            'variant_instance_pk': sample_variant.variant_instance.pk,
            'genomic': variant_obj.variant,
            'genome_build': variant_obj.genome_build,
            'igv_coords': variant_obj.variant.strip('ACGT>'),
            'gene': sample_variant.variant_instance.gene,
            'exon': sample_variant.variant_instance.exon,
            'hgvs_c': sample_variant.variant_instance.hgvs_c,
            'hgvs_p': sample_variant.variant_instance.hgvs_p,
            'hgvs_c_short': hgvs_c_short,
            'hgvs_p_short': hgvs_p_short,
            'transcript': transcript,
            'gnomad_popmax': sample_variant.variant_instance.gnomad_display(),
            'gnomad_link': sample_variant.variant_instance.gnomad_link(),
            'this_run': {
                'ntc': sample_variant.variant_instance.in_ntc,
                'alt_count_ntc': sample_variant.variant_instance.alt_count_ntc,
                'total_count_ntc': sample_variant.variant_instance.total_count_ntc,
                'vaf_ntc': sample_variant.variant_instance.vaf_ntc(),
            },   
            'vaf': {
                'vaf': vaf,
                'vaf_rounded': vaf_rounded,
                'total_count': sample_variant.variant_instance.total_count,
                'alt_count': sample_variant.variant_instance.alt_count,
            },
            'checks': variant_checks_list,
            'latest_check': latest_check,
            'latest_checks_agree': last_two_checks_agree,
            'comment_form': var_comment_form,
            'comments': variant_comments_list,
            'final_decision': sample_variant.variant_instance.get_final_decision_display(),
            'manual_upload': sample_variant.variant_instance.manual_upload,
        }

        # add to poly list if appears in the poly variant list, otherwise add to variant calls list
        if filter_call == True:
            filtered_list.append((variant_calls_dict, filter_reason))
        else:
            variant_calls.append(variant_calls_dict)

    # set true or false for whether there are reportable variants
    if len(reportable_list) == 0:
        no_calls = True
    else:
        no_calls = False

    # make list of other calls to go in footer of PDF report
    if len(other_calls_list) == 0:
        other_calls_text = 'None'
    else:
        other_calls_text = ', '.join(other_calls_list)

    # return as variantr data dictionary
    variant_data = {
        'variant_calls': variant_calls, 
        'filtered_calls': filtered_list,
        'poly_count': poly_count,
        'artefact_count': artefact_count,
        'no_calls': no_calls,
        'other_calls_text': other_calls_text,
        'check_options': VariantCheck.DECISION_CHOICES,
    }

    return variant_data


def get_fusion_info(sample_data, sample_obj):
    """
    Get information on all fusions in a sample analysis to generate the fusion portion of the context dictionary
    """

    fusions = FusionPanelAnalysis.objects.filter(sample_analysis=sample_obj)

    fusion_calls = []
    reportable_list = []
    filtered_list = []
    other_calls_list = []
    artefact_count = 0

    for fusion_object in fusions:

        # get checks for each variant
        fusion_checks = FusionCheck.objects.filter(fusion_analysis=fusion_object).order_by('pk')
        fusion_checks_list = [ v.get_decision_display() for v in fusion_checks ]
        latest_check = fusion_checks.latest('pk')

        # remove Not analysed from checks list
        fusion_checks_analysed = []
        for c in fusion_checks_list:
            if c != 'Not analysed':
                fusion_checks_analysed.append(c)

        # marker to tell whether a variant should be filtered downstream
        filter_call = False
        filter_reason = ''
        
        # do the last two checks agree?
        last_two_checks_agree = True
        if len(fusion_checks_analysed) > 1:
            last2 = fusion_checks_analysed[-2:]
            if last2[0] != last2[1]:
                last_two_checks_agree = False

        fusion_comment_form = FusionCommentForm(
            pk=latest_check.pk, 
            hgvs=fusion_object.fusion_instance.hgvs, 
            comment=latest_check.comment
        )

        # get list of comments for variant
        fusion_comments_list = []
        for v in fusion_checks:
            if v.comment:
                fusion_comments_list.append(
                    { 'comment': v.comment, 'user': v.check_object.user, 'updated': v.comment_updated, }
                )

        # if variant is to appear on report tab, add to list
        if fusion_object.fusion_instance.get_final_decision_display() in ['Genuine']:
            reportable_list.append(fusion_object)

        # list of other calls to go in the footer of the report
        if fusion_object.fusion_instance.get_final_decision_display() in ['Miscalled', 'Failed call']:
            other_calls_list.append(fusion_object.fusion_instance.fusion_genes.fusion_genes)

        # only get VAF when panel setting says so, otherwise return none
        panel = sample_obj.panel
        if panel.show_fusion_vaf:
            vaf = fusion_object.fusion_instance.vaf()
        else:
            vaf = None

        # get artefact lists relevant to this sample
        artefact_lists = VariantList.objects.filter(genome_build=sample_obj.genome_build, list_type='F', assay = sample_obj.panel.assay)

        # get fusions in artefact list
        for fusion_artefact in VariantToVariantList.objects.filter(fusion=fusion_object.fusion_instance.fusion_genes):

            # if signed off and in one of the variant lists for this sample
            if fusion_artefact.signed_off() and (fusion_artefact.variant_list in artefact_lists):

                # if it's an artefact
                if fusion_artefact.variant_list.list_type == 'F':
                    # set variables and update variant check
                    artefact_count += 1
                    filter_call = True
                    latest_check.decision = 'A'
                    latest_check.save()
                    filter_reason = 'Artefact'

        # combine all into context dict
        fusion_calls_dict = {
            'pk': fusion_object.pk,
            'fusion_instance_pk': fusion_object.fusion_instance.pk,
            'fusion_genes': fusion_object.fusion_instance.fusion_genes.fusion_genes,
            'fusion_hgvs': fusion_object.fusion_instance.hgvs,
            'fusion_supporting_reads': fusion_object.fusion_instance.fusion_supporting_reads,
            'vaf': vaf,
            'left_breakpoint': fusion_object.fusion_instance.fusion_genes.left_breakpoint,
            'right_breakpoint': fusion_object.fusion_instance.fusion_genes.right_breakpoint,
            'genome_build': fusion_object.fusion_instance.fusion_genes.genome_build,
            'this_run': {
                'ntc': fusion_object.fusion_instance.in_ntc,
            },
            'checks': fusion_checks_list,
            'latest_check': latest_check,
            'latest_checks_agree': last_two_checks_agree,
            'comment_form': fusion_comment_form,
            'comments': fusion_comments_list,
            'final_decision': fusion_object.fusion_instance.get_final_decision_display(),
            'manual_upload': fusion_object.fusion_instance.manual_upload
        }
        # add to artefact list if appears in the artefact list, otherwise add to the fusion calls list
        if filter_call == True:
            filtered_list.append((fusion_calls_dict, filter_reason))
        else:
            fusion_calls.append(fusion_calls_dict)

    # set true or false for whether there are reportable variants
    if len(reportable_list) == 0:
        no_calls = True
    else:
        no_calls = False

        # make list of other calls to go in footer of PDF report
    if len(other_calls_list) == 0:
        other_calls_text = 'None'
    else:
        other_calls_text = ', '.join(other_calls_list)

    fusion_data = {
        'fusion_calls': fusion_calls,
        'filtered_calls': filtered_list,
        'artefact_count': artefact_count,
        'no_calls': no_calls,
        'other_calls_text': other_calls_text,
        'check_options': FusionCheck.DECISION_CHOICES,
    }

    return fusion_data


def get_coverage_data(sample_obj, depth_cutoffs):
    """
    Get information on the coverage in a sample analysis to generate the coverage portion of the context dictionary

    """
    # get list of target depths from panel object
    target_depths = depth_cutoffs.split(',')

    # will set to true in loop below when it hits a gap
    gaps_present_135 = False
    gaps_present_270 = False
    gaps_present_500 = False
    gaps_present_1000 = False

    # create a coverage dictionary
    coverage_data = {
        'regions': {},
        'depth_cutoffs': target_depths,
    }
    gene_coverage_analysis_obj = GeneCoverageAnalysis.objects.filter(sample=sample_obj).order_by('gene')

    for gene_coverage_obj in gene_coverage_analysis_obj:

        regions = []
        coverage_regions_analysis_obj = RegionCoverageAnalysis.objects.filter(gene=gene_coverage_obj)
        for region in coverage_regions_analysis_obj:
            regions_dict = {
                'hgvs_c': region.hgvs_c,
                'average_coverage': region.average_coverage,
                'hotspot_or_genescreen': region.get_hotspot_display(),
                'percent_135x': region.percent_135x,
                'percent_270x': region.percent_270x,
                'percent_500x': region.percent_500x,
                'percent_1000x': region.percent_1000x,
                'ntc_coverage': region.ntc_coverage,
                'percent_ntc': region.percent_ntc,
            }
            regions.append(regions_dict)

        # create a dictionary of gaps in the sample for the given gene, split by depths
        gaps_135, gaps_270, gaps_500, gaps_1000 = [], [], [], []

        gaps_analysis_obj = GapsAnalysis.objects.filter(gene=gene_coverage_obj)
        for gap in gaps_analysis_obj:

            # error handling for COSMIC numbers as zero evaluates to None
            if gap.percent_cosmic != None or gap.percent_cosmic == 0:
                percent_cosmic = str(gap.percent_cosmic) + '%'
            else:
                percent_cosmic = 'N/A'

            if gap.counts_cosmic != None or gap.counts_cosmic == 0:
                counts_cosmic = str(gap.counts_cosmic)
            else:
                counts_cosmic = 'N/A'

            # make temp dict of info for each gap
            gaps_dict = {
                'genomic': gap.genomic(),
                'gene': gap.hgvs_c.split('(')[0],
                'hgvs_transcript': gap.hgvs_c.split('(')[1].split(')')[0],
                'hgvs_c': gap.hgvs_c.split(':')[1],
                'percent_cosmic': percent_cosmic,
                'counts_cosmic': counts_cosmic,
            }

            # add the dict to the list for the correct coverage cutoff
            # gaps at 135x
            if gap.coverage_cutoff == 135:
                gaps_present_135 = True
                gaps_135.append(gaps_dict)

            # gaps at 270x
            elif gap.coverage_cutoff == 270:
                gaps_present_270 = True
                gaps_270.append(gaps_dict)

            # gaps at 500x
            elif gap.coverage_cutoff == 500:
                gaps_present_500 = True
                gaps_500.append(gaps_dict)

            # gaps at 1000x
            elif gap.coverage_cutoff == 1000:
                gaps_present_1000 = True
                gaps_1000.append(gaps_dict)

        # combine gaps and regions dictionaries
        gene_dict = {
            'av_coverage': gene_coverage_obj.av_coverage,
            'percent_135x': gene_coverage_obj.percent_135x,
            'percent_270x': gene_coverage_obj.percent_270x,
            'percent_500x': gene_coverage_obj.percent_500x,
            'percent_1000x': gene_coverage_obj.percent_1000x,
            'av_ntc_coverage': gene_coverage_obj.av_ntc_coverage,
            'percent_ntc': gene_coverage_obj.percent_ntc,
            'regions': regions,
            'gaps_135': gaps_135,
            'gaps_270': gaps_270,
            'gaps_500': gaps_500,
            'gaps_1000': gaps_1000,
        }

        coverage_data['regions'][gene_coverage_obj.gene.gene] = gene_dict
        coverage_data['gaps_present_135'] = gaps_present_135
        coverage_data['gaps_present_270'] = gaps_present_270
        coverage_data['gaps_present_500'] = gaps_present_500
        coverage_data['gaps_present_1000'] = gaps_present_1000

    return coverage_data


def myeloid_add_to_dict(input_dict, anno):
    """
    Create a dictionary from the output in the create_myeloid_coverage_summary function in the 
    format:

        gene: {
            transcript: [regions]
        }...
    """

    # extract gene, exon and reference sequence from the input annotation
    gene_and_ref, exon = anno.split(':')
    exon = exon.replace('_', ' ')
    gene = gene_and_ref.split('(')[0]
    ref = gene_and_ref.split('(')[1]. split(')')[0]

    # if the gene is already in the dictionary
    if gene in input_dict.keys():

        # if the transcript is already in the dictionary, append to list
        if ref in input_dict[gene].keys():
            input_dict[gene][ref].append(exon)

        # otherwise make a new list for that transcript
        else:
            input_dict[gene][ref] = [exon]

    # if the gene isnt in the dict yet, add to dict
    else:
        input_dict[gene] = {ref: [exon]}

    return input_dict


def myeloid_format_output(input_dict):
    """
    Format the output of the dictionary created in the create_myeloid_coverage_summary function 
    into a sentence suitable for reporting

    """

    # a list of transcripts that aren't primary transcripts, these will be added after the gene in brackets
    # (primary transcripts aren't included)
    alt_transcripts = ['NM_153759.3', 'NM_001122607.1']

    # list to store output
    out_list = []

    # loop through each transcript within each gene
    for gene, values in sorted(input_dict.items()):
        for transcript, regions in values.items():

            # split the annotations into codons or exons and add exon/codon number to lists
            codons = []
            exons = []
            for r in regions:
                region = r.split(' ')[0]
                num = r.split(' ')[1]
                if region == 'exon':
                    exons.append(int(num))
                elif region == 'codon':
                    codons.append(num)

            # empty list to build output
            all_regions_list = []

            # add codons to list first, if there are any (these arent sorted if there are multiple)
            if codons:
                all_codons = f'codon {", ".join(codons)}'
                all_regions_list.append(all_codons)

            # add exons to list if there are any
            if exons:

                # handle pluralisation of word exon
                if len(exons) == 1:
                    all_exons = 'exon '
                else:
                    all_exons = 'exons '

                # sort and concatenate all exons
                exons_str = [str(exon) for exon in sorted(exons)]
                all_exons += ', '.join(exons_str)

                # add to list
                all_regions_list.append(all_exons)

            # combine codon and exon lists into one
            all_regions = ', '.join(all_regions_list)

            # add to the output list. if the transcript isnt a primary transcript, add the transcript ID in brackets after the gene name
            if transcript in alt_transcripts:
                out_list.append(f'{gene} ({transcript}) {all_regions}')
            else:
                out_list.append(f'{gene} {all_regions}')

    # format the output list as a sentence. If empty then return N/A
    if len(out_list) == 0:
        formatted_output = 'N/A'
    else:
        formatted_output = '; '.join(out_list) + '.'

    return formatted_output


def create_myeloid_coverage_summary(sample_obj):
    """
    Pull all regions (i.e. exons or hotspots) from all genes and format into a coverage summary sentence
    for copying into the report

    """

    # create empty dicts for storing output
    regions_with_zero = {}
    regions_with_less_270 = {}

    # get all gene coverage objects
    gene_coverage_analysis_obj = GeneCoverageAnalysis.objects.filter(sample=sample_obj)

    # loop through each region within each gene
    for gene_coverage_obj in gene_coverage_analysis_obj:
        coverage_regions_analysis_obj = RegionCoverageAnalysis.objects.filter(gene=gene_coverage_obj)
        for region_obj in coverage_regions_analysis_obj:

            # pull out the percent coverage at 270X and HGVS annotations
            cov = region_obj.percent_270x
            anno = region_obj.hgvs_c

            # only enter loop if coverage is less than 100% at 270X
            if cov < 100:

                # if no coverage at all at 270X
                if cov == 0:
                    myeloid_add_to_dict(regions_with_zero, anno)

                # if coverage is between 0-100% at 270X
                else:
                    myeloid_add_to_dict(regions_with_less_270, anno)

    # reformat as a sentence for output and add to output dictionary
    myeloid_coverage_summary = {
            'summary_0x': myeloid_format_output(regions_with_zero),
            'summary_270x': myeloid_format_output(regions_with_less_270),
        }

    return myeloid_coverage_summary


def get_poly_list(poly_list_obj, user):
    """
    get all polys and split into a list of confirmed polys and 
    a list of polys that need checking

    """
    # get all variant objects from the poly list
    variants = VariantToVariantList.objects.filter(variant_list=poly_list_obj).order_by("variant__variant")

    # make empty lists before collecting data from loop
    confirmed_list = []
    checking_list = []

    for n, v in enumerate(variants):
        # get gene info
        variant_instances = VariantInstance.objects.filter(variant=v.variant)
        genes = []
        hgvs_cs = []
        hgvs_ps = []
        for annotation in variant_instances:
            genes.append(annotation.gene)
            hgvs_cs.append(annotation.hgvs_c)
            hgvs_ps.append(annotation.hgvs_p)
        
        # tidy up vaf formatting
        if v.vaf_cutoff == None or v.vaf_cutoff == 0:
            vaf_cutoff = 'N/A'
        else:
            vaf_cutoff = str(v.vaf_cutoff.quantize(decimal.Decimal('1'), rounding=decimal.ROUND_HALF_UP)) + '%'

        # format variant info info dictionary 
        formatted_variant = {
            'counter': n,
            'variant_pk': v.id,
            'variant': v.variant.variant,
            'genome_build': v.variant.genome_build,
            'gene': ' | '.join(set(genes)),
            'hgvs_c': ' | '.join(set(hgvs_cs)),
            'hgvs_p': ' | '.join(set(hgvs_ps)),
            'upload_user': v.upload_user,
            'upload_time': v.upload_time,
            'upload_comment': v.upload_comment,
            'vaf_cutoff': vaf_cutoff,
            'check_user': v.check_user,
            'check_time': v.check_time,
            'check_comment': v.check_comment,
        }

        # add polys with two checks to the confirmed list
        if v.signed_off():
            confirmed_list.append(formatted_variant)

        # otherwise add to the checking list
        else:
            # check if the current user is the person who submitted the poly
            # if it is then disable the button to sign off
            if user == v.upload_user:
                formatted_variant['able_to_sign_off'] = False
            else:
                formatted_variant['able_to_sign_off'] = True

            # add to checking list
            checking_list.append(formatted_variant)

    return confirmed_list, checking_list


def get_fusion_list(artefact_list_obj, user):
    """
    get all polys and split into a list of confirmed fusion artefacts and a list of fusion artefacts that need checking

    """
    # get all variant objects from the poly list
    fusions = VariantToVariantList.objects.filter(variant_list=artefact_list_obj).order_by("fusion__left_breakpoint")

    # make empty lists before collecting data from loop
    confirmed_list = []
    checking_list = []

    for n, f in enumerate(fusions):

        # format variant info info dictionary 
        formatted_variant = {
            'counter': n,
            'variant_pk': f.id,
            'fusion': f.fusion.fusion_genes,
            'left_breakpoint': f.fusion.left_breakpoint,
            'right_breakpoint': f.fusion.right_breakpoint,
            'genome_build': f.fusion.genome_build,
            'upload_user': f.upload_user,
            'upload_time': f.upload_time,
            'upload_comment': f.upload_comment,
            'check_user': f.check_user,
            'check_time': f.check_time,
            'check_comment': f.check_comment,
        }

        # add polys with two checks to the confirmed list
        if f.signed_off():
            confirmed_list.append(formatted_variant)

        # otherwise add to the checking list
        else:
            # check if the current user is the person who submitted the poly
            # if it is then disable the button to sign off
            if user == f.upload_user:
                formatted_variant['able_to_sign_off'] = False
            else:
                formatted_variant['able_to_sign_off'] = True

            # add to checking list
            checking_list.append(formatted_variant)

    return confirmed_list, checking_list


def if_nucleotide(string):
    """
    Function to check if nucleotide is a string
    """
    check = True
    for char in string:
    
        if char not in 'ATCGN':
        
            check = False
            
    return check


def if_chrom(string):
    """
    Function to check if chromosome is 1-22 or X/Y
    """
    chroms = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "X", "Y"]
    if string in chroms:
        return True
    else:
        return False


def variant_format_check(chrm, position, ref, alt, panel_bed_path, total_reads, alt_reads):
    """
    Function to check if format of a manually entered variant is correct
    """

    #Check the chromosome is sensible
    chrm_check = if_chrom(chrm)
    if not chrm_check:

        return False, f'{chrm} is not a chromosome - please correct. Do not include "chr" in this box.'
    
    #Check position is right genome build and panel
    #Get overlap with panel bed to check genome build (check below)
    panel_bed_file = panel_bed_path
    panel_bed = pybedtools.BedTool(panel_bed_file)
    variant_as_bed=f"{chrm}\t{int(position)-1}\t{position}"
    variant_bed_region = pybedtools.BedTool(variant_as_bed, from_string=True)
    overlaps_panel = len(panel_bed.intersect(variant_bed_region)) > 0
    
    #If the coordinates are in the wrong genome build - check they overlap with bed (calculated above)
    if overlaps_panel == 0:

        #Check to see if the coordinate is an overlapping/intronic variant within a maximum acceptable distance. absolute_distance returns a generator object
        max_acceptable_distance = 100
        minimum_distance = max_acceptable_distance + 1 # outside of panel - will fail unless the varaint is close to the bed file
        for region in panel_bed:
            if variant_bed_region[0].chrom == region.chrom:
                distance_downstream = abs(region.start - variant_bed_region[0].start)
                distance_upstream = abs(region.end - variant_bed_region[0].end)
                if distance_downstream < minimum_distance:
                    minimum_distance = distance_downstream
                if distance_upstream < minimum_distance:
                    minimum_distance = distance_upstream

        if minimum_distance > max_acceptable_distance:
            
            #Coordinates are not close to any of the BED regions - return error
            return False, 'Genomic coordinates given are not on the panel - Have you used coordinates for the correct genome build?'
                
    #Check ref/alt format (check below)
    ref_check = if_nucleotide(ref)
    alt_check = if_nucleotide(alt)
    
    #Error out if the REF or ALT has non NGS characters (calculated above)
    if not ref_check or not alt_check:
                
        return False, 'Ref or Alt nucleotide is not A,T,C or G - please correct'
                
    #Error out if total depth is set to zero
    if total_reads == 0:
                      	
        return False, 'Total read counts can not be zero'
                
    #Error out if alt read depth is set to zero
    if alt_reads == 0:
                
        return False, 'Alt read counts can not be zero'

    return True, ''


def if_breakpoint(breakpoint:str):
    """
    Checks that a breakpoints has been entered correctly as chromosome coordinates
    """

    expected_format = r'chr([0-9]{1,2}|X|Y):[0-9]+'

    if re.fullmatch(expected_format, breakpoint):
        return True
    else:
        return False

      
def breakpoint_format_check(left_breakpoint:str, right_breakpoint:str):
    """
    Checks both breakpoints for manual fusions and raises a warning if one or more is incorrect
    """

    left_breakpoint_check = if_breakpoint(left_breakpoint)
    right_breakpoint_check = if_breakpoint(right_breakpoint)
    left_chrom_check = if_chrom(left_breakpoint.split(":")[0][3:])
    right_chrom_check = if_chrom(right_breakpoint.split(":")[0][3:])

    # Error if left breakpoint incorrectly formatted
    if not left_breakpoint_check or not left_chrom_check:
        return False, 'Left breakpoint not formatted using genomic co-ordinates, please correct'
    
    # Error if right breakpoint incorrectly formatted
    if not right_breakpoint_check or not right_chrom_check:
        return False, 'Right breakpoint not formatted using genomic co-ordinates, please correct'
    
    # Otherwise the breakpoints are formatted correctly
    return True, ''


def lims_initials_check(lims_initials:str):
    """
    Checks that LIMS initials are unique in the database
    """
    all_user_settings = UserSettings.objects.all()
    all_lims_initials = [u.lims_initials for u in all_user_settings]

    if lims_initials in all_lims_initials:
        return False, f'Initials {lims_initials} already used by another user'
    else:
        return True, ''


def validate_variant(chrm, position, ref, alt, build):
    '''
    Submits a new poly/artefact to Variant Validator to check it is correctly formatted
    '''
    # Check chromosome
    chrm_check = if_chrom(chrm)
    if not chrm_check:
        return f'{chrm} is not a chromosome - please correct. Do not include "chr" in this box.'

    # Check ref
    check_ref = if_nucleotide(ref)
    if not check_ref:
        return f'Ref must consist only of A, T, C, and G - please correct ref: {ref}'
    
    # Check alt
    check_alt = if_nucleotide(alt)
    if not check_alt:
        return f'Alt must consist only of A, T, C, and G - please correct alt: {alt}'

    # Concatenate variant name
    variant = chrm + ':' + str(position) + ref + '>' + alt

    # Access Variant Validator API
    try:
        response = requests.get(f'https://rest.variantvalidator.org/VariantValidator/variantvalidator/{build}/{variant}/mane_select')
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
         error = f'HTTP Request failed: {e} Please reattempt submission.'
         return error
    vv_json = response.json()

    # Set up which warnings need reporting.
    warning_patterns = [r'.*Variant reference.*does not agree with reference.*',
                        r'.*lies outside the reference sequence.*',
                        r'.*outside the boundaries.*',
                        r'.*Uncertain positions.*',
                        r'.*expected the character.*',
                        r'.*No transcripts found that fully overlap.*',
                        r'.*None of the specified transcripts.*fully overlap.*']

    # Check for warnings where reference base provided is not correct
    warnings = ''
    for transcript in vv_json:
        if 'validation_warning_' in transcript:
            for warning in vv_json[transcript]['validation_warnings']:
                for pattern in warning_patterns:
                    if re.search(pattern, warning):
                        warnings += (warning + '; ')
            if warnings:
                return ('Variant Validator Warnings: ' + warnings.strip())
    
    # Check for warnings where variant provided is not in any transcript, e.g. intergenic
    for transcript in vv_json:
        if 'intergenic_variant_' in transcript:
            for warning in vv_json[transcript]['validation_warnings']:
                for pattern in warning_patterns:
                    if re.search(pattern, warning):
                        warnings += (warning + '; ')
            if warnings:
                return ('Variant Validator Warnings: ' + warnings.strip())

    # Create list of preferred transcripts
    preferred_transcript_list = []
    with open('roi/preferred_transcripts.txt') as tsv:
        reader = csv.DictReader(tsv, delimiter='\t')
        for row in reader:
            preferred_transcript_list.append(row['Transcript'])

    # Check for warnings for variants that have a preferred transcript (not mane select)
    not_mane = False
    for transcript in vv_json:
        for pref_transcript in preferred_transcript_list:
            if pref_transcript in transcript:
                not_mane = True
                for warning in vv_json[transcript]['validation_warnings']:
                    for pattern in warning_patterns:
                        if re.search(pattern, warning):
                            warnings += (transcript + ': ' + warning + '; ')
    if not_mane:
        if warnings:
            return ('Variant Validator Warnings: ' + warnings.strip())
        else:
            return None
    
    
    # Check warnings for variants where we use the mane select transcript
    mane_warning = False
    for transcript in vv_json:
        if transcript == 'flag' or transcript == 'metadata':
            pass
        else:
            if vv_json[transcript]['annotations']['mane_select'] == True:
                mane_warning = True
                for warning in vv_json[transcript]['validation_warnings']:
                    for pattern in warning_patterns:
                        if re.search(pattern, warning):
                            warnings += transcript + ': ' + warning + '\n'
    if mane_warning:
        if warnings:
            return('Variant Validator Warnings: ' + warnings.strip())
        else:
            return None
        
    # If json file had some sort of unexpected structure, return this so we can investigate
    else:
        return 'Unexpected Error, contact Bioinformatics'
