# Description:
# Periodic script for adding variants and fusions (called in the last 28 days) to poly and artefacts lists if they meet the required number of checks
#
# Date: 28/02/2025 - AW
# Use: python manage.py shell < /u01/apps/svd/somatic_db/queries/periodic_polys_artefacts.py (with somatic_variant_db env activated)

from django.contrib.auth.models import User
import datetime
from analysis.models import SampleAnalysis, VariantList, VariantToVariantList, VariantPanelAnalysis, Variant, Fusion, FusionPanelAnalysis
from django.utils import timezone

# set global variables
user = User.objects.get(username='admin')
required_checks = 2
query_days = 28

# set date range
end_date = datetime.date.today()
start_date = end_date - datetime.timedelta(days=query_days)
print(f"date range = {start_date} - {end_date}, i.e. last {query_days} days")

#Get all sample analyses
samples = SampleAnalysis.objects.all()

# create empty lists for variants and fusions
variants = []
fusions = []

# define dectionaries used for build list sorting
poly_variant_list_dict = {37: "build_37_polys",
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


def save_variant_to_list(variant, variant_obj, created, build, fusion):
    """
    takes a variant, its variant object, created (bool) and build list and saves it to the given build list
    """
    # point to global variables
    global VariantToVariantList
    global VariantList
    global timezone
    global user
    polys_to_add = []
    build_list = VariantList.objects.get(name=build)
    if fusion:
        variant_list, created = VariantToVariantList.objects.get_or_create(fusion=variant_obj, variant_list=build_list)
    else:
        variant_list, created = VariantToVariantList.objects.get_or_create(variant=variant_obj, variant_list=build_list)
    if created:
        polys_to_add.append(variant)
        # if the poly list instance is newly created, add user info
        variant_list.upload_user = user
        variant_list.upload_time = timezone.now()
        variant_list.upload_comment = 'Auto-uploaded by bioinformatics'
        variant_list.save()
        print(f"INFO\t{timezone.now()}\t{variant} added to {build_list.name}")
    else:
        print(f"INFO\t{timezone.now()}\t{variant} already present in {build_list.name}")


# Loop over samples
for s in samples:
    # Get all IGV checks
    checks = s.get_checks()['all_checks']
    assay = s.worksheet.assay
    # Use date of first check therefore will be after go live
    # if the check is between the dates, get it
    if checks[0].signoff_time != None:
        # print("check not none")
        within_timeframe = start_date <= checks[0].signoff_time.date() <= end_date
        if within_timeframe:

            # Now we know the checks for the sample analysis were in the date range, get variant panel analysis for that sample analysis
            variant_analyses = VariantPanelAnalysis.objects.filter(sample_analysis = s)
                    
            # Get checks
            for v in variant_analyses:
                variant_checks = v.get_all_checks()
                
                # Get decision for each check
                for result in variant_checks:
                    # Get variant string, genome build, set fusion_boolean to False
                    variant = result.variant_analysis.variant_instance.variant.variant
                    genome_build = result.variant_analysis.variant_instance.variant.genome_build
                    fusion_boolean = False
                    # Add variant string to variants list
                    variants.append(variant)
                    # Get or create variant object
                    variant_obj, created = Variant.objects.get_or_create(variant=variant[0])
                    # Check if variant has sufficient number of checks
                    if variants.count(variant) >= required_checks:
                        # If poly save varaint to poly list
                        if result.get_decision_display() == "Poly":
                            save_variant_to_list(variant, variant_obj, created, poly_variant_list_dict[genome_build], fusion_boolean)
                        # If artefact save to artefacts list
                        elif result.get_decision_display() == "Artefact":
                            save_variant_to_list(variant, variant_obj, created, variant_artefact_dict[assay], fusion_boolean)
                    # Print variant to console if insufficient checks
                    else:
                        print(f"INFO\t{timezone.now()}\t{variant}, seen fewer times than required ({required_checks}), not added to list")
            
            # For the sample analyses were in the date range, get fusion panel analyses for that sample analysis
            fusion_analyses = FusionPanelAnalysis.objects.filter(sample_analysis = s)
                    
            # Get checks
            for f in fusion_analyses:
                fusion_checks = f.get_all_checks()
                
                # Get decision for each check
                for result in fusion_checks:
                    # Get fusion string, genome build, set fusion_boolean to True
                    fusion = result.fusion_analysis.fusion_instance.fusion_genes.fusion_genes
                    genome_build = result.fusion_analysis.fusion_instance.fusion_genes.genome_build
                    fusion_boolean = True
                    # Add fusion string to fusions list
                    fusions.append(fusion)
                    # Get or create fusion object
                    fusion_obj, created = Fusion.objects.get_or_create(fusion_genes=fusion)
                    # Check if fusion has sufficient number of checks
                    if fusions.count(fusion) >= required_checks:
                        # If artefact save varaint to artefacts list
                        if result.decision == "A":
                            save_variant_to_list(fusion, fusion_obj, created, fusion_artefact_dict[assay], fusion_boolean)
                    # Print fusion to console if insufficient checks
                    else:
                        print(f"INFO\t{timezone.now()}\t{fusion}, seen fewer times than required ({required_checks}), not added to list")