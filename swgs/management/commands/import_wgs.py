import datetime
import glob
import json

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction

from swgs.models import *

class Command(BaseCommand):


    def add_arguments(self, parser):
        """
        Adds arguments for the command, works like argparse
        """
        parser.add_argument("--directory", help="Directory where all jsons are stored", required=True)

    def find_file(self, filepath):
        files_found = glob.glob(filepath)
        if len(files_found) == 0:
            raise FileNotFoundError(f"Could not find {filepath}")
        elif len(files_found) > 1:
            raise FileExistsError(f"Multiple files for this json - please check")
        else:
            return files_found[0]
    
    def find_all_files(self, directory):
        
        patient_json = self.find_file(f"{directory}/*_patient_info.json")
        qc_json = self.find_file(f"{directory}/*_overall_qc.json")
        coverage_json = self.find_file(f"{directory}*_coverage.json")
        germline_snv_json = self.find_file(f"{directory}/*_germline_snv.json")
        somatic_snv_json = self.find_file(f"{directory}/*_somatic_snv.json")
        germline_cnv_json = self.find_file(f"{directory}/*_germline_cnv.json")
        somatic_cnv_json = self.find_file(f"{directory}/*_somatic_cnv.json")
        germline_sv_json = self.find_file(f"{directory}/*_germline_sv.json")
        somatic_sv_json = self.find_file(f"{directory}/*_somatic_sv.json")
        somatic_fusion_json = self.find_file(f"{directory}/*_somatic_fusion.json")
        return patient_json, qc_json, germline_snv_json, somatic_snv_json, germline_cnv_json, somatic_cnv_json, germline_sv_json, somatic_sv_json, somatic_fusion_json, coverage_json

    def update_vep_annotations(self, vep_annotations_model, vep_dictionary, transcript):
        """
        Updates the VEP annotations
        vep_annotations_model - either the GermlineVepAnnotations or SomaticVEPAnnotations model instance
        """
        # we may have information for one or more transcripts
        # create the Gene, Transcript and VEPAnnotations models
        # get the gene/transcript objects then remove the gene field
        vep_annotations_info = vep_dictionary["vep_annotations"]
        gene_obj, created = Gene.objects.get_or_create(gene=vep_annotations_info["gene"])
        transcript_obj, created = Transcript.objects.get_or_create(transcript=transcript, gene=gene_obj)
        vep_annotations_info["transcript"] = transcript_obj
        vep_annotations_info.pop("gene")
        # get the vep consequences for later then remove the field
        vep_consequences = vep_annotations_info["consequence"].split("&")
        vep_annotations_info.pop("consequence")
        vep_annotations_obj = vep_annotations_model.objects.create(**vep_annotations_info)

        # get the annotation consequences and add. these should all be in fixtures as the info is taken from VEP - something has gone very wrong if there's a novel one
        for vep_consequence in vep_consequences:
            try:
                consequence_obj = VEPAnnotationsConsequence.objects.get(consequence=vep_consequence)
                vep_annotations_obj.consequence.add(consequence_obj)
            except ObjectDoesNotExist:
                # there shouldn't be VEP consequences we don't know about
                raise ObjectDoesNotExist(f"No configured VEP consequence for {vep_consequence}- has VEP been updated?")
            except MultipleObjectsReturned:
                # there also shouldn't be more than one
                raise MultipleObjectsReturned(f"More than one configured VEP consequence for {vep_consequence}")

        # get or create pubmed object(s) and add
        pubmed_annotations = vep_dictionary["vep_annotations_pubmed"]
        for k, v in pubmed_annotations.items():
            if k != "":
                pubmed_obj, created = VEPAnnotationsPubmed.objects.get_or_create(**v)
                vep_annotations_obj.pubmed_id.add(pubmed_obj)
                
        # get or create existing variations object(s) and add
        existing_variation_annotation = vep_dictionary["vep_annotations_existing_variation"]
        for k, v in existing_variation_annotation.items():
            if k != "":
                existing_variation_obj, created = VEPAnnotationsExistingVariation.objects.get_or_create(**v)
                vep_annotations_obj.existing_variation.add(existing_variation_obj)
    
        return vep_annotations_obj

        #TODO get or create clinvar object(s) and add
        #TODO get or create cancer hotspots object(s) and add


    def update_variant_obj(self, variant_json, cnv_snv_sv, variant_model, variant_instance_model, vep_annotations_model, genome_build_obj, patient_analysis_obj):
        """
        Adds a CNV, SNV or SV
        variant - relevant file
        cnv_snv_sv - string: 'cnv', 'snv' or 'sv'
        variant_instance_model: base model to be updated
        vep_annotations_model: vep annotations to be updated
        """

        # change snv formatting to match the json
        if cnv_snv_sv == "snv":
            cnv_snv_sv = "variant"

        # Add CNV/SVs
        # load in the  CNV/SV data from the variant json
        with open(variant_json) as f:
            all_variants = json.load(f)

        print(f"Updating {len(all_variants)} variants")

        # loop through the germline CNV/SVs and add to the database
        for variant_dict in all_variants:
            
            # get or create the cnv_sv object
            variant_info = variant_dict[cnv_snv_sv]
            variant_info["genome_build"] = genome_build_obj

            if cnv_snv_sv == "cnv" or cnv_snv_sv == "sv":
                # find all the gene objects in the genes list
                genes_list = []
                for gene in variant_dict[f"{cnv_snv_sv}"]["gene"]:
                    gene_obj, _ = Gene.objects.get_or_create(gene=gene)
                    genes_list.append(gene_obj)
                variant_info.pop("gene")
                # change the key name for model upload
                variant_info["variant"] = variant_info[cnv_snv_sv]
                variant_info.pop(cnv_snv_sv)
                # get the SV/CNV type
                cnv_sv_type_obj, _ = CnvSvType.objects.get_or_create(type=variant_info["type"])
                variant_info["type"] = cnv_sv_type_obj
            
            variant_obj, created = variant_model.objects.get_or_create(**variant_dict[cnv_snv_sv])

            if cnv_snv_sv == "cnv" or cnv_snv_sv == "sv":
                for gene in genes_list:
                    variant_obj.genes.add(gene)

            # get or create cnv instance
            variant_instance_info = variant_dict[f"abstract_{cnv_snv_sv}_instance"]
            variant_instance_info[cnv_snv_sv] = variant_obj
            variant_instance_info["patient_analysis"] = patient_analysis_obj
            cnv_sv_instance_obj = variant_instance_model.objects.create(**variant_instance_info)

            # we may have information for one or more transcripts
            # create the Gene, Transcript and VEPAnnotations models
            for transcript, vep_dictionary in variant_dict["vep_annotations"].items():
                germline_vep_annotations_obj = self.update_vep_annotations(vep_annotations_model, vep_dictionary, transcript)
                # Add VEP annotations to germline variant instance
                cnv_sv_instance_obj.vep_annotations.add(germline_vep_annotations_obj)

    def update_fusion_obj(self, somatic_fusion_json, patient_analysis_obj):
        """
        Creates the models for somatic fusions to link two breakends
        """

        with open(somatic_fusion_json) as f:
            all_fusions = json.load(f)

        for fusion in all_fusions:
            breakpoint_obj_1 = SomaticSvInstance.objects.get(sv__variant=fusion["sv"], patient_analysis=patient_analysis_obj)
            breakpoint_obj_2 = SomaticSvInstance.objects.get(sv__variant=fusion["mate"], patient_analysis=patient_analysis_obj)

            # create new fusion object
            #TODO make naming be good
            fusion_name = f"{breakpoint_obj_1.get_pick_gene()}::{breakpoint_obj_2.get_pick_gene()}"
            Fusion.objects.create(fusion_name=fusion_name, breakpoint1=breakpoint_obj_1, breakpoint2=breakpoint_obj_2, fusion_type=fusion["fusion_type"])

    def update_coverage_obj(self, coverage_json, patient_analysis_obj):
        """
        Creates the models for coverage instances
        """

        with open(coverage_json) as f:
            coverage = json.load(f)
        
        for gene in coverage:
            gene_obj, _ = Gene.objects.get_or_create(gene=gene)
            coverage_info = coverage[gene]
            coverage_info["gene"] = gene_obj
            coverage_info["patient_analysis"] = patient_analysis_obj
            GeneCoverageInstance.objects.create(**coverage_info)

    @transaction.atomic
    def handle(self, *args, **options):

        print(f"Importing WGS data {datetime.datetime.today()}")

        # get arguments from options
        patient_json, qc_json, germline_snv_json, somatic_snv_json, germline_cnv_json, somatic_cnv_json, germline_sv_json, somatic_sv_json, somatic_fusion_json, coverage_json = self.find_all_files(options["directory"])

        # load in the patient info json
        with open(patient_json, "r") as f:
            patient_info_dict = json.load(f)
        
        print(f"Importing data for {patient_info_dict['run_id']}")
        print("Creating sample objects")
        
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
        print("Creating QC objects")
        qc_somatic_vaf_distribution_obj, created = QCSomaticVAFDistribution.objects.get_or_create(**overall_qc_dict["somatic_vaf_distribution"])
        qc_tumour_in_normal_contamination_obj, created = QCTumourInNormalContamination.objects.get_or_create(**overall_qc_dict["tinc"])
        qc_germline_cnv_quality_obj, created = QCGermlineCNVQuality.objects.get_or_create(**overall_qc_dict["germline_cnv_qc"])
        qc_low_tumour_sample_quality_obj, created = QCLowQualityTumourSample.objects.get_or_create(**overall_qc_dict["low_quality_tumour_sample_qc"])
        qc_tumour_ntc_contamination_obj, created = QCNTCContamination.objects.get_or_create(**overall_qc_dict["tumour_sample_ntc_contamination"])
        qc_germline_ntc_contamination_obj, created = QCNTCContamination.objects.get_or_create(**overall_qc_dict["sample_ntc_contamination"])
        qc_relatedness_obj, created = QCRelatedness.objects.get_or_create(**overall_qc_dict["somalier_qc"])
        qc_tumour_purity_obj, created = QCTumourPurity.objects.get_or_create(**overall_qc_dict["tumour_purity"])

        # get or create the patient analysis object
        print("Creating patient analysis object")
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
            relatedness=qc_relatedness_obj,
            tumour_purity=qc_tumour_purity_obj
        )

        # fetch the genome build - SWGS is only build 38
        genome_build_obj, created = GenomeBuild.objects.get_or_create(genome_build="GRCh38")
        
        # update coverage
        print("Updating coverage")
        self.update_coverage_obj(coverage_json, patient_analysis_obj)

        # update germline snvs
        print("Updating germline SNVs")
        self.update_variant_obj(germline_snv_json, "snv", Variant, GermlineVariantInstance, GermlineVEPAnnotations, genome_build_obj, patient_analysis_obj)
        # update somatic snvs
        print("Updating somatic SNVs")
        self.update_variant_obj(somatic_snv_json, "snv", Variant, SomaticVariantInstance, SomaticVEPAnnotations, genome_build_obj, patient_analysis_obj)
        # update germline cnvs
        print("Updating germline CNVs")
        self.update_variant_obj(germline_cnv_json, "cnv", CnvSv, GermlineCnvInstance, GermlineVEPAnnotations, genome_build_obj, patient_analysis_obj)
        # update somatic cnvs
        print("Updating somatic CNVs")
        self.update_variant_obj(somatic_cnv_json, "cnv", CnvSv, SomaticCnvInstance, SomaticVEPAnnotations, genome_build_obj, patient_analysis_obj)
        # update germline svs
        print("Updating germline SVs")
        self.update_variant_obj(germline_sv_json, "sv", CnvSv, GermlineSvInstance, GermlineVEPAnnotations, genome_build_obj, patient_analysis_obj)
        # update somatic svs
        print("Updating somatic SVs")
        self.update_variant_obj(somatic_sv_json, "sv", CnvSv, SomaticSvInstance, SomaticVEPAnnotations, genome_build_obj, patient_analysis_obj)
        # update somatic fusions
        print("Updating somatic fusions")
        self.update_fusion_obj(somatic_fusion_json, patient_analysis_obj)

        print("Update complete")
            