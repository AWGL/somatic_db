import argparse
import json

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from swgs.models import *

test_germline_variant_json = "/home/na282549/code/somatic_db/test_23M19452_germline_variants.json"
test_qc_json = "/home/na282549/code/somatic_db/Test_overall_qc.json"
test_somatic_variant_json = "/home/na282549/code/somatic_db/test_23M19453_somatic_variants.json"
test_patient_json = "/home/na282549/code/somatic_db/example_patient_info.json"

class Command(BaseCommand):

    def add_arguments(self, parser):
        """
        Adds arguments for the command, works like argparse
        """
        parser.add_argument("--patient_json", help="Path to *_patient_info.json", required=True)
        parser.add_argument("--qc_json", help="Path to *_overall_qc.json", required=True)
        parser.add_argument("--germline_snv_json", help="Path to *_germline_snvs.json", required=True)
        parser.add_argument("--somatic_snv_json", help="Path to *_somatic_snvs.json", required=True)
        

    @transaction.atomic
    def handle(self, *args, **options):

        # get arguments from options
        patient_json = options["patient_json"]
        qc_json = options["qc_json"]
        germline_snv_json = options["germline_snv_json"]
        somatic_snv_json = options["somatic_snv_json"]

        # load in the patient info json
        with open(patient_json, "r") as f:
            patient_info_dict = json.load(f)
        
        # create a patient object with a standin NHS number - this can be input by the scientists in SVD
        patient_obj = Patient.objects.create()

        # get or create the tumour sample
        tumour_sample_obj, created = Sample.objects.get_or_create(sample_id=patient_info_dict["tumour_sample_id"])

        # get or create the germline sample if it's being used
        germline_sample_obj, created = Sample.objects.get_or_create(sample_id=patient_info_dict["germline_sample_id"])

        # get or create the indication
        indication_obj, created = Indication.objects.get_or_create(indication=patient_info_dict["indication"])

        # get or create the run
        run_obj, created = Run.objects.get_or_create(run=patient_info_dict["run_id"], worksheet=patient_info_dict["worksheet_id"])

        # load in the qc data from the json file
        with open(qc_json, "r") as f:
            overall_qc_dict = json.load(f)

        # parse the json file so the PASS/FAIL/WARN choices fit in the choicefield
        for quality_dict in overall_qc_dict.values():
            if quality_dict["status"] == "PASS":
                quality_dict["status"] = "P"
            if quality_dict["status"] == "WARN":
                quality_dict["status"] = "W"
            if quality_dict["status"] == "FAIL":
                quality_dict["status"] = "F"
        
        # get or create QC objects for each metric
        qc_somatic_vaf_distribution_obj, created = QCSomaticVAFDistribution.objects.get_or_create(**overall_qc_dict["somatic_vaf_distribution"])
        qc_tumour_in_normal_contamination_obj, created = QCTumourInNormalContamination.objects.get_or_create(**overall_qc_dict["tinc"])
        qc_germline_cnv_quality_obj, created = QCGermlineCNVQuality.objects.get_or_create(**overall_qc_dict["germline_cnv_qc"])
        qc_low_tumour_sample_quality_obj, created = QCLowQualityTumourSample.objects.get_or_create(**overall_qc_dict["low_quality_tumour_sample_qc"])
        qc_tumour_ntc_contamination_obj, created = QCNTCContamination.objects.get_or_create(**overall_qc_dict["tumour_sample_ntc_contamination"])
        qc_germline_ntc_contamination_obj, created = QCNTCContamination.objects.get_or_create(**overall_qc_dict["sample_ntc_contamination"])
        qc_relatedness_obj, created = QCRelatedness.objects.get_or_create(**overall_qc_dict["somelier_qc"])

        # get or create the patient analysis objcet
        patient_analysis_obj, created = PatientAnalysis.objects.get_or_create(
            patient=patient_obj,
            tumour_sample=tumour_sample_obj,
            germline_sample=germline_sample_obj,
            indication=indication_obj,
            run=run_obj,
            somatic_vaf_distribution=qc_somatic_vaf_distribution_obj,
            tumour_in_normal_contamination=qc_tumour_in_normal_contamination_obj,
            germline_cnv_quality=qc_germline_cnv_quality_obj,
            low_quality_tumour_sample=qc_low_tumour_sample_quality_obj,
            tumour_ntc_contamination=qc_tumour_ntc_contamination_obj,
            germline_ntc_contamination=qc_germline_ntc_contamination_obj,
            relatedness=qc_relatedness_obj
        )

        # fetch the genome build - SWGS is only build 38
        genome_build, created = GenomeBuild.objects.get_or_create(genome_build="GRCh38")

        # Add Germline SNVs
        # load in the germline variant data from the variant json
        with open(germline_snv_json) as f:
            germline_variant_dict = json.load(f)
        
        # loop through the germline SNVs and add to database
        for variant_dict in germline_variant_dict.values():

            # get or create the variant object
            variant_info = variant_dict["variant"]
            variant_info["genome_build"] = genome_build
            variant_obj, created = Variant.objects.get_or_create(**variant_info)
            
            # get or create variant instance
            variant_instance_info = variant_dict["abstract_variant_instance"]
            variant_instance_info["variant"] = variant_obj
            variant_instance_info["patient_analysis"] = patient_analysis_obj
            germline_variant_instance_obj, created = GermlineVariantInstance.objects.get_or_create(**variant_instance_info)
            
            # we may have information for one or more transcripts
            # create the Gene, Transcript and VEPAnnotations models
            for transcript, vep_dictionary in variant_dict["vep_annotations"].items():
                vep_annotations_info = vep_dictionary["vep_annotations"]
                gene_obj, created = Gene.objects.get_or_create(gene=vep_annotations_info["gene"])
                transcript_obj, created = Transcript.objects.get_or_create(transcript=transcript, gene=gene_obj)
                vep_annotations_info["transcript"] = transcript_obj
                vep_annotations_info.pop("gene")
                germline_vep_annotations_obj, created = GermlineVEPAnnotations.objects.get_or_create(**vep_annotations_info)

                # get or create pubmed object(s) and add
                pubmed_annotations = vep_dictionary["vep_annotations_pubmed"]
                for k, v in pubmed_annotations.items():
                    if k != "":
                        pubmed_obj, created = VEPAnnotationsPubmed.objects.get_or_create(**v)
                        germline_vep_annotations_obj.pubmed_id.add(pubmed_obj)
                        
                # get or create existing variations object(s) and add
                existing_variation_annotation = vep_dictionary["vep_annotations_existing_variation"]
                for k, v in existing_variation_annotation.items():
                    if k != "":
                        existing_variation_obj, created = VEPAnnotationsExistingVariation.objects.get_or_create(**v)
                        germline_vep_annotations_obj.existing_variation.add(existing_variation_obj)

                #TODO get or create clinvar object(s) and add

                # Add VEP annotations to germline variant instance
                germline_variant_instance_obj.vep_annotations.add(germline_vep_annotations_obj)

        # Add Somatic SNVs
        # load in the somatic snv data from the variant json 
        with open(somatic_snv_json) as f:
            somatic_variant_dict = json.load(f)
        
        # loop through the somatic SNVs and add to the database
        for variant_dict in somatic_variant_dict.values():
            # get or create the variant object
            variant_info = variant_dict["variant"]
            variant_info["genome_build"] = genome_build
            variant_obj, created = Variant.objects.get_or_create(**variant_info)
            
            # get or create variant instance
            variant_instance_info = variant_dict["abstract_variant_instance"]
            variant_instance_info["variant"] = variant_obj
            variant_instance_info["patient_analysis"] = patient_analysis_obj
            somatic_variant_instance_obj, created = SomaticVariantInstance.objects.get_or_create(**variant_instance_info)
            
            # we may have information for one or more transcripts
            # create the Gene, Transcript and VEPAnnotations models
            for transcript, vep_dictionary in variant_dict["vep_annotations"].items():
                vep_annotations_info = vep_dictionary["vep_annotations"]
                gene_obj, created = Gene.objects.get_or_create(gene=vep_annotations_info["gene"])
                transcript_obj, created = Transcript.objects.get_or_create(transcript=transcript, gene=gene_obj)
                vep_annotations_info["transcript"] = transcript_obj
                vep_annotations_info.pop("gene")
                somatic_vep_annotations_obj, created = SomaticVEPAnnotations.objects.get_or_create(**vep_annotations_info)

                # get or create pubmed object(s) and add
                pubmed_annotations = vep_dictionary["vep_annotations_pubmed"]
                for k, v in pubmed_annotations.items():
                    if k != "":
                        pubmed_obj, created = VEPAnnotationsPubmed.objects.get_or_create(**v)
                        somatic_vep_annotations_obj.pubmed_id.add(pubmed_obj)
                        
                # get or create existing variations object(s) and add
                existing_variation_annotation = vep_dictionary["vep_annotations_existing_variation"]
                for k, v in existing_variation_annotation.items():
                    if k != "":
                        existing_variation_obj, created = VEPAnnotationsExistingVariation.objects.get_or_create(**v)
                        somatic_vep_annotations_obj.existing_variation.add(existing_variation_obj)

                #TODO get or create cancer hotspots object(s) and add

                # Add VEP annotations to germline variant instance
                somatic_variant_instance_obj.vep_annotations.add(somatic_vep_annotations_obj)
