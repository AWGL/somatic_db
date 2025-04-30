# Description:
# Periodic script for adding variants and fusions (called in the last 28 days) to poly and artefacts lists if they meet the required number of checks
#
# Date: 28/02/2025 - AW
# Use: python manage.py shell save_polys_artefacts (with somatic_variant_db env activated)
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings

import datetime
from analysis.models import SampleAnalysis, VariantList, VariantToVariantList, VariantInstance, Variant, Fusion, FusionAnalysis
from django.utils import timezone


class Command(BaseCommand):
    
    def save_variant_to_list(self, variant, variant_obj, created, build, fusion):
        """
        takes a variant, its variant object, created (bool) and build list and saves it to the given build list
        """
        build_list = VariantList.objects.get(name=build)
        if fusion:
            variant_list, created = VariantToVariantList.objects.get_or_create(fusion=variant_obj, variant_list=build_list)
        else:
            variant_list, created = VariantToVariantList.objects.get_or_create(variant=variant_obj, variant_list=build_list)
        if created:
            # if the poly list instance is newly created, add user info
            variant_list.upload_user = self.user
            variant_list.upload_time = timezone.now()
            variant_list.upload_comment = 'Auto-uploaded by bioinformatics'
            variant_list.save()
            print(f"INFO\t{timezone.now()}\t{variant} added to {build_list.name}")
        else:
            print(f"INFO\t{timezone.now()}\t{variant} already present in {build_list.name}")
    
    @transaction.atomic
    def handle(self, *args, **options):
        # set global variables
        self.user = User.objects.get(username='admin')
        required_checks = 2
        query_days = 28
        upload_days = 100
        # set date range
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=query_days)
        filter_date = end_date - datetime.timedelta(days=upload_days)
        print(f"date range = {start_date} - {end_date}, i.e. last {query_days} days")

        #Get all sample analyses
        sas = SampleAnalysis.objects.filter(
            worksheet__diagnostic=True,
            upload_time__gt=filter_date)

        # create empty lists for polys and artefacts
        polys = []
        artefacts = []

        # define dectionaries used for build list sorting
        poly_variant_list_dict = {
            37: "build_37_polys",
            38: "build_38_polys"
                                }

        variant_artefact_dict = {
            "TSO500_ctDNA": "TSO500_ctDNA_b37_artefacts",
            "TSO500_DNA": "TSO500_DNA_b38_artefacts",
            "GeneRead_CRM": "GeneRead_CRM_b37_artefacts",
            "GeneRead_BRCA": "GeneRead_BRCA_b37_artefacts"
        }

        fusion_artefact_dict = {
            "TSO500_ctDNA": "TSO500_ctDNA_b37_fusion_artefacts",
            "TSO500_RNA": "TSO500_RNA_b37_fusion_artefacts"
        }

        # Loop over SampleAnalysis objects
        for sa in sas:
            # Get all IGV checks
            checks = sa.get_checks()['all_checks']
            sample = sa.sample
            assay = sa.worksheet.assay

            # Use date of first check therefore will be after go live
            # if the check is between the dates, get it
            if checks[0].signoff_time != None:
                # print("check not none")
                within_timeframe = start_date <= checks[0].signoff_time.date() <= end_date
                if within_timeframe:

                    # get in-date VariantInstance objects
                    variant_instances = VariantInstance.objects.filter(sample = sample)
                            
                    # Get checks
                    for v in variant_instances:
                        # Get decision, variant string, genome build, set fusion_boolean to False
                        decision = v.final_decision
                        variant = v.variant.variant
                        genome_build = v.variant.genome_build
                        fusion_boolean = False
                        # Get or create variant object
                        variant_obj, created = Variant.objects.get_or_create(variant=variant)
                        # If poly save varaint to poly list
                        if decision == "P":
                            # Check if variant has sufficient number of checks
                            polys.append(variant)
                            if polys.count(variant) >= required_checks:
                                self.save_variant_to_list(
                                    variant,
                                    variant_obj,
                                    created,
                                    poly_variant_list_dict[genome_build],
                                    fusion_boolean
                                    )
                            else:
                                # Print variant to console if insufficient checks
                                print(f"INFO\t{timezone.now()}\t{variant}, seen fewer times than required ({required_checks}), not added to list")
                            # If artefact save to artefacts list
                        elif decision == "A":
                            artefacts.append(variant)
                            if artefacts.count(variant) >= required_checks:
                                self.save_variant_to_list(
                                    variant,
                                    variant_obj,
                                    created,
                                    variant_artefact_dict[assay],
                                    fusion_boolean
                                    )
                            else:
                                # Print variant to console if insufficient checks
                                print(f"INFO\t{timezone.now()}\t{variant}, seen fewer times than required ({required_checks}), not added to list")

                    # get in-date FusionAnalysis objects
                    fusion_analysis = FusionAnalysis.objects.filter(sample = sa)

                    if fusion_analysis.count() > 0:  
                        # Get checks
                        for f in fusion_analysis:
                            # Get decision, variant string, genome build, set fusion_boolean to False
                            decision = f.final_decision
                            fusion = f.fusion_genes.fusion_genes
                            genome_build = f.fusion_genes.genome_build
                            fusion_boolean = True

                            # Get or create variant object
                            fusion_obj, created = Fusion.objects.get_or_create(fusion_genes=fusion)
                            # If artefact save to artefacts list
                            if decision == "A":
                                # Check if variant has sufficient number of checks
                                artefacts.append(fusion)
                                if artefacts.count(fusion) >= required_checks:
                                    self.save_variant_to_list(
                                        fusion,
                                        fusion_obj,
                                        created,
                                        fusion_artefact_dict[assay],
                                        fusion_boolean
                                        )
                                else:
                                    # Print variant to console if insufficient checks
                                    print(f"INFO\t{timezone.now()}\t{fusion}, seen fewer times than required ({required_checks}), not added to list")      