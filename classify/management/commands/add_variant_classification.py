from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from classify.models import ClassifyVariant, ManualVariantInstance, ManualVariant, Guideline


class Command(BaseCommand):
    help = "add a variant classification to the database"
    # TODO API call to variant validator to make sure input is accurate?

    def add_arguments(self, parser):
        parser.add_argument('--gene', nargs=1, type=str, required=True, help="")
        parser.add_argument('--hgvs_c', nargs=1, type=str, required=True, help="")
        parser.add_argument('--hgvs_p', nargs=1, type=str, required=True, help="")
        parser.add_argument('--genomic_coords', nargs=1, type=str, required=True, help="")
        parser.add_argument('--genome_build', nargs=1, type=str, required=True, help="")
        parser.add_argument('--guidelines', nargs=1, type=str, required=True, help="")

    @transaction.atomic
    def handle(self, *args, **options):

        # get args
        gene = options['gene'][0]
        hgvs_c = options['hgvs_c'][0]
        hgvs_p = options['hgvs_p'][0]
        genomic_coords = options['genomic_coords'][0]
        genome_build = options['genome_build'][0]

        # get or create a ClassifyVariant object
        classify_variant, created = ClassifyVariant.objects.get_or_create(
            gene=gene,
            hgvs_c=hgvs_c,
            hgvs_p=hgvs_p,
            genomic_coords=genomic_coords,
            genome_build=genome_build
        )
        if created:
            print(f'INFO\t{timezone.now()}\tadd_variant_classification.py\tCreated new ClassifyVariant: {classify_variant}')
        else:
            print(self.style.WARNING(f'WARN\t{timezone.now()}\tadd_variant_classification.py\tClassifyVariant already exists: {classify_variant}'))

        # create a ManualVariant
        # TODO add commands for these
        manual_variant = ManualVariant.objects.create(
            sample_id = "test",
            panel = "test"
        )

        # get guideline obj
        guideline_obj = Guideline.objects.get(guideline=options['guidelines'][0])

        # create a ClassifyVariantInstance
        manual_variant_instance = ManualVariantInstance.objects.create(
            variant=classify_variant,
            guideline=guideline_obj,
            variant_instance=manual_variant
        )
        print(f'INFO\t{timezone.now()}\tCreated new ClassifyVariantInstance: {manual_variant_instance}')

        # create a Check object
        manual_variant_instance.make_new_check()

        # success message
        print(self.style.SUCCESS(f'SUCCESS\t{timezone.now()}\tadd_variant_classification.py\tVariant classification added successfully.'))
