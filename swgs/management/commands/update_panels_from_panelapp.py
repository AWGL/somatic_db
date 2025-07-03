import datetime
import requests

from django.core.management.base import BaseCommand
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction

from swgs.models import *
from swgs.panels.panelapp_panels import germline_panels

def get_panel_from_api(base_url, panel_id):
        """
        Get the most recently signed off version of a given panel
        """

        # set up initial url
        endpoint = "panels/signedoff"
        url = f"{base_url}/{endpoint}/?panel_id={str(panel_id)}"
        
        # check that API has been queried succssfully with 200 code
        try:
            response = requests.get(url)
            response.raise_for_status()            
            return response.json()
            
        except requests.exceptions.HTTPError:
            raise requests.exceptions.HTTPError(f"Error querying API, {response.status_code} returned.") 
    
def get_panel_information(panel_json, expected_panel_name):
    """
    Get the panel version from the API response
    We want to check the names are the same, that the panel is signed off and when, and the version
    We also want to get the numbers of genes, regions and STRs to know which downstream queries to run
    """
    # get the desired information from the API response
    panel_name = panel_json["results"][0]["name"]
    panel_version = panel_json["results"][0]["version"]
    panel_signed_off = False
    number_of_genes = panel_json["results"][0]["stats"]["number_of_genes"]
    number_of_regions = panel_json["results"][0]["stats"]["number_of_regions"]
    number_of_strs = panel_json["results"][0]["stats"]["number_of_strs"]

    # check that the panel name is the same and panelapp haven't been changing panel ids
    if panel_name != expected_panel_name:
        raise Exception(f"Expected panel name {expected_panel_name} but got {panel_name} from API")
    
    panel_name = expected_panel_name.split(" ")[0]
    # the signed off tag is deep in a list of dictionaries
    # obtain the list of types dictionaries
    panel_types_info = panel_json["results"][0]["types"]
    # loop through these dictionaries, we're looking for key/value pair 'slug': 'gms-signed-off'
    try:
        for panel_types_dict in panel_types_info:
            if panel_types_dict["slug"] == "gms-signed-off":
                panel_signed_off = True
                break
    except KeyError:
        pass

    # we don't need to query genes/regions/strs if there are none on the panel
    query_genes = True
    query_regions = True
    query_strs = True
    if number_of_genes == 0:
        query_genes = False
    if number_of_regions == 0:
        query_regions = False
    if number_of_strs == 0:
        query_strs = False
    
    return panel_name, panel_signed_off, panel_version, query_genes, query_regions, query_strs

def get_or_create_panel(panel_name, panel_version):
    """
    Fetches or creates a Panel object from the database
    """
    try:
        panel_obj, created = Panel.objects.get_or_create(panel_name=panel_name, panel_version=panel_version)
        return panel_obj, created
    except MultipleObjectsReturned:
        # panels should have a unique name/version combination, error if not
        raise MultipleObjectsReturned("There should only be one configured version of each panel")

def get_previous_panel(panel_name):
    """
    Gets the previous version of the panel
    """
    try:
        panels = Panel.objects.filter(panel_name=panel_name).order_by('-panel_version')
        # highest panel version is the new panel, second highest is previous
        previous_panel = panels[1]
    except IndexError:
        # If there's an index error there is no previous panel
        previous_panel = None
    return previous_panel

def get_panel_contents_from_api(base_url, panel_id, endpoint):
    """
    Endpoint: must be genes, regions or strs
    Get genes, regions or STRs for a given panel
    GEL paginate their endpoint so you only get 100 results per query - you need to loop through
    """
    # set multiple queries to True so we can loop through as much as we need
    multiple_queries = True
    response_jsons = []

    # set up initial url
    url = f"{base_url}/panels/{str(panel_id)}/{endpoint}"
    
    while multiple_queries:
        # check that API has been queried succssfully with 200 code
        try:
            response = requests.get(url)
            response.raise_for_status()            
            response_json = response.json()
            response_jsons.append(response_json)
            url = response_json["next"]
            if not url:
                multiple_queries = False
            
        except requests.exceptions.HTTPError:
            raise requests.exceptions.HTTPError(f"Error querying API, {response.status_code} returned.") 
    
    # combine multiple responses into a single json if more than 1 
    initial_json = response_jsons[0]
    if len(response_jsons) == 1:
        return initial_json
    else:
        for j in response_jsons[1:]:
            initial_json["results"] += j["results"]
        return initial_json
    
def get_list_of_genes(genes_dictionary):
    """
    Get the HGNC gene symbol and review status from the API response
    We only want green genes (could change this in the future to include amber etc.)
    """
    # initate a list of genes
    genes = []

    for gene in genes_dictionary["results"]:
        # get HGNC gene symbol and evidence
        gene_symbol = gene["gene_data"]["hgnc_symbol"]
        evidence = gene["evidence"]

        # Only include green genes
        if "Expert Review Green" in evidence:
            genes.append(gene_symbol)
    
    return genes

def add_genes_to_panel(panel_obj, list_of_genes):
    """
    Add genes to a Panel object
    """
    for gene in list_of_genes:
        gene_obj, created = Gene.objects.get_or_create(gene=gene)
        panel_obj.genes.add(gene_obj)

class Command(BaseCommand):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = "https://panelapp.genomicsengland.co.uk/api/v1"

    def add_arguments(self, parser):
        """
        Adds arguments for the command, works like argparse
        """
        parser.add_argument("--panels", help="Dictionary of panelapp panels, with id as key, and a dictionary of name and germline_or_somatic as value. Defaults to the fixture in SVD", default=germline_panels)

    @transaction.atomic
    def handle(self, *args, **options):
        
        # Get the date
        today = datetime.date.today().strftime("%Y-%m-%d")

        # get arguments from options
        panels = options["panels"]

        for panel_id, panel_info in panels.items():

            panel_name = panel_info["name"]
            print(f"Performing panel update for {panel_name}")
            
            germline_or_somatic = panel_info["germline_or_somatic"]

            # get the most recent version info about the panel from the API
            panel_api_response = get_panel_from_api(self.base_url, panel_id)

            # get the relevant information from the json
            panel_name, panel_signed_off, panel_version, query_genes, query_regions, query_strs = get_panel_information(
                panel_api_response, panel_name
            )

            # if the panel's not signed off, we won't update with this information
            if not panel_signed_off:
                print(f"Panel {panel_name} not signed off")
                continue

            # see if we already have this panel in the database
            updated_panel_name = panel_name.replace(" ", "_").lower()
            created_panel_name = f"{germline_or_somatic}_{updated_panel_name}"
            panel_obj, created = get_or_create_panel(created_panel_name, panel_version)
            
            if created:
                # Get previous panel to compare and update panel notes
                previous_panel = get_previous_panel(created_panel_name)

                panel_notes = []
                panel_notes.append(f"Panel updated on {today}")

                if query_genes:

                    print(f"Getting genes for {panel_name}")

                    genes_content = get_panel_contents_from_api(self.base_url, panel_id, "genes")
                    genes = get_list_of_genes(genes_content)
                    add_genes_to_panel(panel_obj, genes)

                    # For new panels, list the genes added
                    if not previous_panel:
                        panel_notes.append("New panel")
                        panel_notes.append(f"New genes added: {', '.join(genes)}")
                    
                    else:
                        # get list of genes from old panel
                        previous_genes = previous_panel.genes.all()
                        previous_genes = [gene.gene for gene in previous_genes]
                        # work out genes added and removed
                        genes_added = [gene for gene in genes if gene not in previous_genes]
                        genes_removed = [gene for gene in previous_genes if gene not in genes]
                        panel_notes.append(f"Panel updated from {str(previous_panel.panel_version)}")
                        panel_notes.append(f"New genes added: {', '.join(genes_added)}")
                        panel_notes.append(f"Genes removed: {', '.join(genes_removed)}")

                else:
                    
                    print(f"No genes on {panel_name}")
                    panel_notes.append("No genes to add")
                
                #TODO handle regions in panels
                if query_regions:

                    print(f"Getting regions for {panel_name}")

                    regions_content = get_panel_contents_from_api(self.base_url, panel_id, "regions")

                else:
                    
                    print(f"No regions on {panel_name}")
                    panel_notes.append("No regions to add")

                #TODO handle STRs in panels
                if query_strs:

                    print(f"Getting STRs for {panel_name}")

                    strs_content = get_panel_contents_from_api(self.base_url, panel_id, "strs")

                else:

                    print(f"No STRs on {panel_name}")
                    panel_notes.append("No STRs to add")

                # Update the panel notes
                panel_notes = "\n".join(panel_notes)
                panel_obj.panel_notes = panel_notes
                panel_obj.save()

            else:

                print(f"No update for {panel_name}")
