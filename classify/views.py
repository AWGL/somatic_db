from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required

from .models import *
from .forms import *

from analysis.models import VariantPanelAnalysis

import json


# Create your views here.
@login_required
def view_classifications(request):
    """ """
    new_classifications_form = NewClassification()

    context = {
        "classifications": ClassifyVariantInstance.objects.all(),
        "new_form": new_classifications_form,
    }

    # when buttons are pressed
    if request.method == "POST":

        # only one button at the mo
        new_classifications_form = NewClassification(request.POST)
        if new_classifications_form.is_valid():
            # get variant instance
            var_inst = VariantPanelAnalysis(id=60)  # TODO this is hardcoded for testing
            var, _ = ClassifyVariant.objects.get_or_create(
                gene = "TET2",
                hgvs_c = "NM_001127208.3:c.4139A>G",
                hgvs_p = "NP_001120680.1:p.His1380Arg",
                genomic_coords = "4:105269704A>G",
                genome_build = 38,
            )
            guideline_obj = Guideline.objects.get(pk=2) #TODO hardcoded for testing
            new_var_obj = AnalysisVariantInstance(
                variant=var,
                variant_instance=var_inst,
                guideline=guideline_obj
            )
            new_var_obj.save()
            new_var_obj.make_new_check()

            context["classifications"] = ClassifyVariantInstance.objects.all()

    return render(request, "classify/all_classifications.html", context)


@login_required
def classify(request, classification):
    """
    Page to perform classifications
    """
    # load in classification and check objects from url args
    classification_obj = ClassifyVariantInstance.objects.get(id=classification)
    current_check_obj = classification_obj.get_latest_check()

    # load context from classification obj
    recent_classification, needs_review = classification_obj.get_most_recent_full_classification()
    context = {
        "sample_info": classification_obj.get_sample_info(),
        "variant_info": classification_obj.variant.get_variant_info(),
        "classification_info": classification_obj.get_classification_info(),
        "previous_classifications": {
            "all": classification_obj.get_all_previous_classifications(),
            "recent": recent_classification,
            "recent_needs_review": needs_review,
        },
    }

    # assign user
    if classification_obj.get_status() != "Complete":
        if current_check_obj.user == None:
            current_check_obj.user = request.user
            current_check_obj.save()

        if current_check_obj.user != request.user:
            raise PermissionDenied()

        group_name = classification_obj.guideline.signed_off_group.name
        signed_off = current_check_obj.user.groups.filter(name=group_name).exists()
        if not signed_off:
            context["warning"] = ["You are not currently signed off, this check will be flagged as a training check and will require a third check"]

    # load in forms and add to context
    previous_class_choices = classification_obj.get_previous_classification_choices()
    classification_options = classification_obj.guideline.create_final_classification_tuple()
    context["forms"] = {
        "complete_check_info_form": CompleteCheckInfoForm(),
        "complete_previous_class_form": CompletePreviousClassificationsForm(previous_class_choices=previous_class_choices),
        "complete_classification_form": CompleteClassificationForm(classification_options=classification_options),
        "complete_analysis_form": CompleteAnalysisForm(),
        "reopen_check_info_form": ReopenCheckInfoForm(),
        "reopen_previous_class_form": ReopenPreviousClassificationsForm(),
        "reopen_classification_form": ReopenClassificationForm(),
        "reopen_analysis_form": ReopenAnalysisForm(),
    }

    # ------------------------------------------------------------------------
    # when buttons are pressed
    if request.method == "POST":

        # button to confirm sample/variant tab has been checked
        if "complete_check_info_form" in request.POST:
            complete_check_info_form = CompleteCheckInfoForm(request.POST)
            if complete_check_info_form.is_valid():
                current_check_obj.complete_info_tab()
                return redirect("perform-classification", classification)

        # button to reset sample/patient info tab
        if "reopen_check_info_form" in request.POST:
            reopen_check_info_form = ReopenCheckInfoForm(request.POST)
            if reopen_check_info_form.is_valid():
                current_check_obj.reopen_info_tab()
                return redirect("perform-classification", classification)

        # button to select to use a previous classification or start a new one
        if "use_previous_class" in request.POST:
            complete_previous_class_form = CompletePreviousClassificationsForm(
                request.POST, previous_class_choices=previous_class_choices
            )
            if complete_previous_class_form.is_valid():
                use_previous = complete_previous_class_form.cleaned_data["use_previous_class"]
                if use_previous == "previous":
                    reuse_classification_obj = recent_classification
                elif use_previous == "new":
                    reuse_classification_obj = None
                current_check_obj.complete_previous_class_tab(reuse_classification_obj)
                return redirect("perform-classification", classification_obj.pk)

        # button to revert previous/new classification form
        if "reopen_previous_class_form" in request.POST:
            reopen_previous_class_form = ReopenPreviousClassificationsForm(request.POST)
            if reopen_previous_class_form.is_valid():
                current_check_obj.reopen_previous_class_tab()
                return redirect("perform-classification", classification)

        # button to complete classification
        if "complete_classification" in request.POST:
            complete_classification_form = CompleteClassificationForm(request.POST, 
                                                                      classification_options=classification_options)
            if complete_classification_form.is_valid():
                override = complete_classification_form.cleaned_data["override"]
                current_check_obj.complete_classification_tab(override)
                return redirect("perform-classification", classification)

        # button to reopen classification
        if "reopen_classification_check" in request.POST:
            reopen_classification_form = ReopenClassificationForm(request.POST)
            if reopen_classification_form.is_valid():
                current_check_obj.reopen_classification_tab()
                return redirect("perform-classification", classification)

        # button to finish check
        if "complete_analysis_form" in request.POST:
            complete_analysis_form = CompleteAnalysisForm(request.POST)
            if complete_analysis_form.is_valid():
                next_step = complete_analysis_form.cleaned_data["next_step"]
                updated, err = classification_obj.signoff_check(
                    current_check_obj, next_step
                )
                if updated:
                    return redirect("view-all-classifications")
                else:
                    context["warning"] = [err]

        # button to reopen a closed analysis
        if "reopen_analysis_form" in request.POST:
            reopen_analysis_form = ReopenAnalysisForm(request.POST)
            if reopen_analysis_form.is_valid():
                updated, err = classification_obj.reopen_analysis(request.user)
                if updated:
                    return redirect("view-all-classifications")
                else:
                    context["warning"] = [err]

    return render(request, "classify/classify_base.html", context)


def ajax_classify(request):
    """
    Generates new chunks of HTML for the classification summary boxes on the classify tab (within a div called class-box).
    Called in JS at bottom of classify_classify.html
    """
    if request.is_ajax():
        # get variables from AJAX input
        selections = json.loads(request.POST.get("selections"))
        check_pk = request.POST.get("check_pk")

        # load variables needed for new display
        current_check_obj = Check.objects.get(id=check_pk)
        current_check_obj.update_codes(selections)
        score, final_class = current_check_obj.update_classification()
        codes_by_category = current_check_obj.classification.get_codes_by_category()

        # empty dict for new html
        data = {}

        # make new classification box and add to results dict
        class_box_context = {
            "current_score": score,
            "current_class": final_class,
        }
        class_box_html = render_to_string(
            "classify/ajax/classification.html", class_box_context
        )
        data["class_box"] = class_box_html

        # make the code summary and complete true/false segments for each category of code and add to results dict
        for category, value in codes_by_category.items():

            # summary of codes applied
            html = render_to_string(
                "classify/ajax/category_summary.html",
                {"applied_codes": value["applied_codes"]},
            )
            data[f'codes_summary_{value["slug"].replace("-", "_")}'] = html

            # complete yes/no
            html = render_to_string(
                "classify/ajax/category_complete.html", {"complete": value["complete"]}
            )
            data[f'complete_{value["slug"].replace("-", "_")}'] = html

        return JsonResponse(data)
