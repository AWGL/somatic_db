import csv
import datetime
import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.utils import timezone

from .models import *
from .forms import *
from .utils import *

@login_required
def home_swgs(request):
    """
    """
    return render(request, 'swgs/home.html', {})

@login_required
def view_runs(request):
    """
    View runs / worksheets
    """

    # get all the runs
    runs = Run.objects.all().order_by("-run")
    runs_list = []
    for run in runs:
        run_dict = {
            "run": run.run,
            "worksheet": run.worksheet,
            "patient_analyses": run.get_patient_analysis()
        }
        runs_list.append(run_dict)

    # context dictionary
    context = {
        'runs': runs_list
    }

    return render(request, "swgs/view_runs.html", context)

@login_required
def view_panels(request):
    """
    View panels, panel update pages
    """
    
    # get all the panels
    panels = Panel.objects.all().order_by("panel_name")
    germline_panel_list = []
    somatic_panel_list = []
    other_panel_list = []
    for panel in panels:
        panel_dict = {
            "panel_id": panel.id,
            "panel_name": panel.display_panel_name(),
            "is_active": panel.panel_approved
        }
        if panel.panel_name.startswith("germline"):
            germline_panel_list.append(panel_dict)
        elif panel.panel_name.startswith("somatic"):
            somatic_panel_list.append(panel_dict)
        else:
            other_panel_list.append(panel_dict)

    # get all the indications
    indications = Indication.objects.all().order_by("indication")
    indications_list = []
    for indication in indications:
        indication_dict = {
            "indication_id": indication.id,
            "indication": indication.indication
        }
        indications_list.append(indication_dict)

    context = {
        "germline_panels": germline_panel_list,
        "somatic_panels": somatic_panel_list,
        "other_panels": other_panel_list,
        "indications": indications_list
    }

    return render(request, "swgs/view_panels.html", context)


@login_required
def view_panel(request, panel_id):
    """
    Display the genes in a panel, 
    """

    panel = Panel.objects.get(id=panel_id)

    panel_dict = {
        "panel_name": panel.display_panel_name(),
        "panel_notes": panel.panel_notes,
        "genes": panel.get_gene_names(),
        "somatic_or_germline": panel.display_somatic_or_germline(),
        "type": panel.get_type()
    }

    context = {
        "panel_dict": panel_dict,
        "update_panel_notes_form": UpdatePanelNotesForm(
            panel_notes=panel.panel_notes
        )
    }
    
    if "panel_notes" in request.POST:
        update_panel_notes_form = UpdatePanelNotesForm(request.POST, panel_notes=panel_dict["panel_notes"])

        if update_panel_notes_form.is_valid():
            updated_notes = update_panel_notes_form.cleaned_data["panel_notes"]
            Panel.objects.filter(id=panel_id).update(panel_notes=updated_notes)
            panel = Panel.objects.get(id=panel_id)
            context["update_panel_notes_form"] = UpdatePanelNotesForm(
                panel_notes = panel.panel_notes
            )

    return render(request, "swgs/view_panel.html", context)


@login_required
def view_indication(request, indication_id):
    """
    display information about an indication
    """
    indication = Indication.objects.get(id=indication_id)
    
    genes_and_panels = indication.get_all_genes_and_panels()

    indication_dict = {
        "indication_name": indication.indication,
        "genes_and_panels": genes_and_panels,
        "display_genes": indication.display_genes(genes_and_panels)
    }

    context = {
        "indication_dict": indication_dict
    }

    return render(request, "swgs/view_indication.html", context)


@login_required
def view_patient_analysis(request, patient_analysis_id):
    """
    View variants in a PatientAnalysis
    """

    # Set up forms
    download_csv_form = DownloadCsvForm()

    # Get patient analysis by ID
    patient_analysis_obj = PatientAnalysis.objects.get(id=patient_analysis_id)
    
    # Get information for details and QC page
    patient_analysis_info_dict = patient_analysis_obj.create_patient_analysis_info_dict()
    patient_analysis_qc_dict = patient_analysis_obj.create_qc_dict()

    check_options = AbstractVariantInstance.OUTCOME_CHOICES
    #TODO most of this can be moved to the models

    # Germline SNV tiering
    germline_snvs_query = GermlineVariantInstance.objects.filter(patient_analysis=patient_analysis_obj)
    germline_snvs_tier_one, germline_snvs_tier_three = germline_snv_tiering(germline_snvs_query)

    # Somatic SNV tiering
    somatic_snvs_query = SomaticVariantInstance.objects.filter(patient_analysis=patient_analysis_obj)
    somatic_snvs_tier_one, somatic_snvs_tier_two = somatic_snv_tiering(somatic_snvs_query)

    # Germline SV/CNV Tiering
    germline_cnvs_query = GermlineCnvInstance.objects.filter(patient_analysis=patient_analysis_obj)
    germline_svs_query = GermlineSvInstance.objects.filter(patient_analysis=patient_analysis_obj)

    # Somatic SV/CNV Tiering
    # Somatic Fusion Tiering
    somatic_cnvs_query = SomaticCnvInstance.objects.filter(patient_analysis=patient_analysis_obj)
    somatic_svs_query = SomaticSvInstance.objects.filter(patient_analysis=patient_analysis_obj)
    
    context = {
        "form": download_csv_form,
        "patient_analysis": patient_analysis_obj,
        "patient_analysis_info_dict": patient_analysis_info_dict,
        "patient_analysis_qc_dict": patient_analysis_qc_dict,
        "somatic_snvs_tier_one": somatic_snvs_tier_one,
        "somatic_snvs_tier_two": somatic_snvs_tier_two,
        "germline_snvs_tier_one": germline_snvs_tier_one,
        "germline_snvs_tier_three": germline_snvs_tier_three,
        "check_options": check_options
    }

    # Download a csv
    if request.POST:

        today = datetime.date.today().strftime("%Y%m%d")
        filename = f"{patient_analysis_obj.tumour_sample.sample_id}_{patient_analysis_obj.germline_sample.sample_id}_{today}"
        response = HttpResponse(content_type = "text/csv")
        response["Content-Disposition"] = f"attachement; filename={filename}"
        
        somatic_snvs = somatic_snvs_tier_one + somatic_snvs_tier_two
        germline_snvs = germline_snvs_tier_one + germline_snvs_tier_three

        csv_writer = csv.writer(response)
        header_line = ["Germline_or_Somatic", "Variant", "Gene", "Tier", "Consequence", "HGVSC", "HGVSP", "VAF", "GnomAD"]
        csv_writer.writerow(header_line)
        for variant in somatic_snvs:
            if variant["tier"] != "None":
                csv_writer.writerow(["somatic", variant["pk"], variant["gene"], variant["tier"], variant["consequence"], variant["hgvsc"], variant["hgvsp"], f"{variant['vaf']}%", variant["gnomad"]])
        for variant in germline_snvs:
            if variant["tier"] != "None":
                csv_writer.writerow(["germline", variant["pk"], variant["gene"], variant["tier"], variant["consequence"], variant["hgvsc"], variant["hgvsp"], f"{variant['vaf']}%", variant["gnomad"]])

        return response

    return render(request, "swgs/view_patient_analysis.html", context)

def ajax(request):
    """
    Ajax handling of the variant check submission
    """

    if request.is_ajax():
        
        selections = json.loads(request.POST.get('selections'))
        patient_pk = request.POST.get('patient_analysis_pk')
        
        for variant in selections:
                
                #Get decision
                decision = selections[variant][1]['genuine_dropdown']

                #Get variant object - use type marker to determine what kind of check and then create check object
                type = selections[variant][0]
                
                if type == "germline":

                    variant_obj = GermlineVariantInstance.objects.get(id=variant)
                    check_obj = GermlineIGVCheck.objects.create(variant_instance = variant_obj,
                                                                 decision = decision,
                                                                 user = request.user,
                                                                 check_date = timezone.now())
                    check_obj.save()
                   
                elif type == "somatic":

                    variant_obj = SomaticVariantInstance.objects.get(id=variant)
                    check_obj = SomaticIGVCheck.objects.create(variant_instance = variant_obj,
                                                               decision = decision,
                                                               user = request.user,
                                                               check_date = timezone.now())
                    check_obj.save()

                #Update status of variant_obj - ie complete if last two checks matching
                variant_obj.update_status()

        return JsonResponse({"status": "success", "redirect_url": f"/swgs/view_patient_analysis/{patient_pk}"})

    return JsonResponse({"status": "error"}, status=400)
    