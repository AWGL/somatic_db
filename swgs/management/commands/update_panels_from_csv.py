import datetime

from django.core.management.base import BaseCommand
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction

from swgs.models import *

def create_panel(panel_name, panel_version):
    """
    Fetches or creates a Panel object from the database
    """
    panel_obj = Panel.objects.create(panel_name=panel_name, panel_version=panel_version)
    return panel_obj

def get_previous_panel(panel_name):
    """
    Gets the previous version of the panel
    """
    # try/except because an IndexError will be thrown for panels not already in the database
    try:
        panels = Panel.objects.filter(panel_name=panel_name).order_by('-panel_version')
        # highest panel version is the previous panel
        previous_panel = panels[0]
    except IndexError:
        # If there's an index error there is no previous panel
        previous_panel = None
    return previous_panel

def add_genes_to_panel(panel_obj, list_of_genes):
    """
    Add genes to a Panel object
    """
    for gene in list_of_genes:
        gene_obj, created = Gene.objects.get_or_create(gene=gene)
        panel_obj.genes.add(gene_obj)

class Command(BaseCommand):

    def add_arguments(self, parser):
        """
        Adds arguments for the command, works like argparse
        """
        parser.add_argument("--panel_csv", 
                            help="Path to the csv file(s) for your panel(s). These should be formatted one gene per line with no headers",
                            nargs="+")
        parser.add_argument("--panel_name",
                            help="The name(s) of your panel(s) (optional) - script will default the panel name to the prefix of the .csv file",
                            nargs="+",
                            required=False)
        parser.add_argument("--germline_or_somatic",
                            help="A list of 'germline' or 'somatic' for each panel. Script will default to somatic unless this is supplied",
                            nargs="+",
                            required=False)
        
    @transaction.atomic
    def handle(self, *args, **options):

        # Get the date
        today = datetime.date.today().strftime("%Y-%m-%d")

        # get arguments from options
        panel_csvs = options["panel_csv"]

        try:
            panel_names = options["panel_names"]
            # if panel names are provided, check they're provided for all the csvs
            if len(panel_names) != len(panel_csvs):
                raise Exception("Names not provided for every panel - either provide a panel name for every panel or provide no panel names, script will default to the csv file prefixes")
            
            else:
                updated_panel_names = panel_names

        # otherwise get the panel names from the csv names
        except KeyError:

            updated_panel_names = []

            for csv in panel_csvs:
                panel_name = csv.split("/")[-1].split(".")[0]
                updated_panel_names.append(panel_name)

        try:
            germline_or_somatic = options["germline_or_somatic"]
            # if germline_or_somatic is provided, check they're provided for all the panel names
            print(updated_panel_names, germline_or_somatic)
            if len(updated_panel_names) != len(germline_or_somatic):
                raise Exception("Germline or somatic not provided for every panel - either provide this information or script will default to somatic for all panels")
            else:
                updated_panel_names = [f"{germline_or_somatic[i]}_{updated_panel_names[i]}" for i in range(len(updated_panel_names))]
        
        # otherwise everything is somatic
        except TypeError:

            updated_panel_names = [f"somatic_{panel_name}" for panel_name in updated_panel_names]

        # make a dictionary
        panels = dict(zip(updated_panel_names, panel_csvs))

        # loop through csvs and make new panels
        for panel_name, panel_csv in panels.items():
            
            print(f"Performing panel update for {panel_name}")

            # try to get the previous panel so we know the version for the new panel
            previous_panel = get_previous_panel(panel_name)

            # if there's no previous panel, set as v1
            if previous_panel is None:
                panel_version = 1
                old_panel_genes = []

            else:
                panel_version = previous_panel.panel_version + 1
                old_panel_genes = [gene.gene for gene in previous_panel.genes.all()]

            # create a new panel
            panel_obj = create_panel(panel_name, panel_version)
            panel_notes = []
            panel_notes.append(f"Panel updated on {today}")

            # get the gene list from the csv
            with open(panel_csv, "r") as f:
                gene_list = f.readlines()
                gene_list = [gene.rstrip() for gene in gene_list]
            
            # add the genes to the panel
            add_genes_to_panel(panel_obj, gene_list)

            # get the gene list for the new and old panels to compare and make sure there are differences
            new_panel_genes = gene_list
            genes_added = [gene for gene in new_panel_genes if gene not in old_panel_genes]
            genes_removed = [gene for gene in old_panel_genes if gene not in new_panel_genes]

            # if there are no genes added or removed we don't want to update the panel
            if len(genes_added) == 0 and len(genes_removed) == 0:
                print(f"New panel for {panel_name} identical to previous version, skipping update")
                panel_obj.delete()

            else:
                try:
                    panel_notes.append(f"Panel updated from {str(previous_panel.panel_version)}")
                except AttributeError:
                    panel_notes.append("New panel")
                panel_notes.append(f"New genes added: {', '.join(genes_added)}")
                panel_notes.append(f"Genes removed: {', '.join(genes_removed)}")

            #TODO handle STRs and regions? possibly separately it looks like somatic genes have SNVs and CNVs separately

            # Update the panel notes
            panel_notes = "\n".join(panel_notes)
            panel_obj.panel_notes = panel_notes
            panel_obj.save()

            

