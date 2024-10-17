import csv
import datetime

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from .models import *
from .forms import *

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
        "somatic_or_germline": panel.display_somatic_or_germline()
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
def view_patient_analysis(request, patient_id):
    """
    View variants in a PatientAnalysis
    """

    download_csv_form = DownloadCsvForm()

    patient_analysis = PatientAnalysis.objects.get(id=patient_id)

    germline_snvs_query = GermlineVariantInstance.objects.filter(patient_analysis=patient_analysis)
    somatic_snvs_query = SomaticVariantInstance.objects.filter(patient_analysis=patient_analysis)
    germline_snvs_tier_one = []
    germline_snvs_tier_three = []
    somatic_snvs_tier_one = []
    somatic_snvs_tier_two = []

    for v in somatic_snvs_query:
        variant = v.variant.variant
        gnomad = v.gnomad_popmax_af
        vaf = float(v.af) * 100
        vep_annotations = v.vep_annotations.first()
        hgvsc = vep_annotations.hgvsc
        hgvsp = vep_annotations.hgvsp
        gene = vep_annotations.transcript.gene.gene
        consequences = vep_annotations.consequence.all()
        impacts = list(set(consequence.impact.impact for consequence in consequences))
        consequences = [c.consequence for c in consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(consequences)
        force_display = v.force_display()

        # handle gnomad
        if float(gnomad) == -1:
            gnomad_formatted = "Not in Gnomad"
        else:
            gnomad_formatted = f"{gnomad:.3f}%"

        # make variant dict
        variant_dict = {
                "pk": variant,
                "gnomad": gnomad_formatted,
                "vaf": f"{vaf:.2f}",
                "hgvsc": hgvsc,
                "hgvsp": hgvsp,
                "gene": gene,
                "consequence": consequences_formatted,
                "force_display": force_display
            }

        # lose >5% in gnomad and modifier only variants
        if float(gnomad) >= 0.05 or (len(impacts) == 1 and impacts[0] == "MODIFIER"):
            if not force_display:
                continue

        # Put in tier list
        if v.display_in_tier_zero():
            variant_dict["tier"] = "0"
            somatic_snvs_tier_one.append(variant_dict)
        elif v.display_in_tier_one():
            variant_dict["tier"] = "1"
            somatic_snvs_tier_one.append(variant_dict)
        elif v.display_in_tier_two():
            variant_dict["tier"] = "2"
            somatic_snvs_tier_two.append(variant_dict)
        else:
            pass

    for v in germline_snvs_query:
        variant = v.variant.variant
        gnomad = v.gnomad_popmax_af
        vaf = float(v.af) * 100
        vep_annotations = v.vep_annotations.first()
        hgvsc = vep_annotations.hgvsc
        hgvsp = vep_annotations.hgvsp
        gene = vep_annotations.transcript.gene.gene
        consequences = vep_annotations.consequence.all()
        impacts = list(set(consequence.impact.impact for consequence in consequences))
        consequences = [c.consequence for c in consequences]
        consequences_formatted = [c.replace("_", " ") for c in consequences]
        consequences_formatted = " | ".join(consequences)
        force_display = v.force_display()

        # handle gnomad
        if float(gnomad) == -1:
            gnomad_formatted = "Not in Gnomad"
        else:
            gnomad_formatted = f"{gnomad:.3f}%"

        # make variant dict
        variant_dict = {
                "pk": variant,
                "gnomad": gnomad_formatted,
                "vaf": f"{vaf:.2f}",
                "hgvsc": hgvsc,
                "hgvsp": hgvsp,
                "gene": gene,
                "consequence": consequences_formatted,
                "force_display": force_display
            }

        # lose >5% in gnomad and modifier only variants
        if float(gnomad) >= 0.05 or (len(impacts) == 1 and impacts[0] == "MODIFIER"):
            if not force_display:
                continue

        # Put in tier list
        if v.display_in_tier_zero():
            variant_dict["tier"] = "0"
            germline_snvs_tier_one.append(variant_dict)
        elif v.display_in_tier_one():
            variant_dict["tier"] = "1"
            germline_snvs_tier_one.append(variant_dict)
        elif v.display_in_tier_three():
            variant_dict["tier"] = "3"
            germline_snvs_tier_three.append(variant_dict)
        else:
            pass
    
    context = {
        "form": download_csv_form,
        "patient_analysis": patient_analysis,
        "somatic_snvs_tier_one": somatic_snvs_tier_one,
        "somatic_snvs_tier_two": somatic_snvs_tier_two,
        "germline_snvs_tier_one": germline_snvs_tier_one,
        "germline_snvs_tier_three": germline_snvs_tier_three
    }

    # Download a csv
    if request.POST:

        today = datetime.date.today().strftime("%Y%m%d")
        filename = f"{patient_analysis.tumour_sample.sample_id}_{patient_analysis.germline_sample.sample_id}_{today}"
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
    