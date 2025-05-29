from django.conf import settings
from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template import Context
from django.template.loader import get_template, render_to_string
from django.utils import timezone

from .forms import (NewVariantForm, SubmitForm, VariantCommentForm, CoverageCheckForm, FusionCommentForm, 
    SampleCommentForm, UnassignForm, PaperworkCheckForm, ConfirmPolyForm, ConfirmArtefactForm, AddNewPolyForm, AddNewArtefactForm, 
    ManualVariantCheckForm, ReopenSampleAnalysisForm, ChangeLimsInitials, EditedPasswordChangeForm, EditedUserCreationForm, 
    RunQCForm, ReopenRunQCForm, SendCheckBackForm, DetailsCheckForm, AddNewFusionArtefactForm, NewFusionForm, SampleQCForm, 
    SelfAuditSubmission)

from .utils import (get_samples, unassign_check, reopen_check, get_variant_info, get_coverage_data, get_sample_info, 
    get_fusion_info, get_poly_list, get_fusion_list, create_myeloid_coverage_summary, variant_format_check, 
    breakpoint_format_check, lims_initials_check, validate_variant)

from .models import *

import csv
import json
import os
import pdfkit
import datetime


def signup(request):
    """
    Allow users to sign up
    User accounts are inactive by default - an admin must activate it using the admin page.
    """

    signup_form = EditedUserCreationForm()
    warnings = []

    if request.method == 'POST':

        signup_form = EditedUserCreationForm(request.POST)

        if signup_form.is_valid():

            # get data from form
            username = signup_form.cleaned_data.get('username')
            raw_password = signup_form.cleaned_data.get('password1')
            lims_initials = signup_form.cleaned_data.get('lims_initials')

            # check if LIMS initials already exists
            initials_check, warning_message = lims_initials_check(lims_initials)

            if initials_check:
                # user is created on this save command
                signup_form.save()

                # edit user object
                user = authenticate(username=username, password=raw_password)
                user.is_active = False
                user.save()

                # add lims initials
                usersettings = UserSettings(
                    user = user,
                    lims_initials = lims_initials
                )
                usersettings.save()

                return redirect('home')

            # if LIMS initials already exists then throw an error
            else:
                warnings.append(warning_message)

        else:
            warnings.append('Could not create an account, check that your password meets the requirements below')

    return render(request, 'analysis/sign-up.html', {'signup_form': signup_form, 'warning': warnings})


@login_required
def home(request):
    """
    Landing page of webapp, contains search bar and quick links to other parts of the app
    """
    return render(request, 'analysis/home.html', {})


@login_required
def self_audit(request):
    """
    Page where staff can view checks they have previously performed between specified dates with a variety of filters.
    """
    # identify and store current user as a variable
    username = request.user.username

    #empty context dict
    context = {
        'self_audit_form': SelfAuditSubmission(),
        'check_data': [],
        'warning': [],
    }
    no_checks = 0
    all_check_data = []
    submit_check = False

    #  when button is pressed
    if request.method == 'POST':
        if 'which_assays' in request.POST:

            self_audit_form = SelfAuditSubmission(request.POST)
            if self_audit_form.is_valid():
                submit_check = self_audit_form.cleaned_data['submit_check']
                start_date = self_audit_form.cleaned_data['start_date']
                end_date = self_audit_form.cleaned_data['end_date']
                which_assays = self_audit_form.cleaned_data['which_assays']

                # filter to show only checks performed by current user
                checks = Check.objects.filter(user__username = username, status__in = ["C", "F"])
                for c in checks:

                    # include marker
                    include = True

                    # see if within date specified with drop down menus
                    within_date = c.signoff_time
                    within_date = within_date.date()
                    assay_type = c.analysis.panel.assay

                    if within_date == None:
                        include = False
                    else:
                        within_date = start_date <= within_date <= end_date
                        if within_date:
                            include = True
                        else:
                            include = False

                    # check that the correct assays are displayed
                    if assay_type in which_assays and include == True:
                        include = True
                    else:
                        include = False

                    # want to get check data here
                    if include:
                        no_checks += 1
                        check_data = {
                            'worksheet': c.analysis.worksheet.ws_id,
                            'assay': c.analysis.worksheet.assay,
                            'date_checked': c.signoff_time.strftime('%d-%b-%Y'),
                            'checker': username,
                            'sample': c.analysis.sample.sample_id,
                            'overall_comments': c.overall_comment,
                            'svd_link': f'{request.get_host()}/analysis/{c.analysis.id}#report',
                            'pk': c.pk,
                        }
                        all_check_data.append(check_data)

                context['no_checks'] = no_checks
                context['check_data'] = all_check_data

        if "download_submit" in request.POST:
            start_date = self_audit_form.cleaned_data['start_date']
            end_date = self_audit_form.cleaned_data['end_date']
            submit_check = self_audit_form.cleaned_data['submit_check']
            if submit_check != "1":
                context['warning'].append('Make sure you check the parameters are set and the tickboxes are ticked.')
                return render(request, 'analysis/self_audit.html', context)

            response = HttpResponse(content_type="text/csv")
            response[
                    "Content-Disposition"
            ] = f'attachment; filename={username}_{start_date}-{end_date}_checks.csv'

            fieldnames = [
                'worksheet',
                'assay',
                'date_checked',
                'checker',
                'sample',
                'overall_comments',
                'svd_link',
            ]

            writer = csv.DictWriter(response, fieldnames=fieldnames)
            writer.writeheader()

            for checks in all_check_data:
                del checks["pk"]  # remove pk as not needed in csv
                writer.writerow(checks)

            return response

        if submit_check != "1":
            context['warning'].append('Make sure you check the parameters are set and the tickboxes are ticked.')
            return render(request, 'analysis/self_audit.html', context)

    return render(request, 'analysis/self_audit.html', context)


def ajax_num_assigned_user(request, user_pk):
    """
    AJAX call for the number of uncompleted checks assigned to a user
    Loaded in the background when the home page is loaded
    """
    if request.is_ajax():
        # get user object and work out count of uncompleted checks assigned to user
        user_obj = get_object_or_404(User, pk=user_pk)
        num_checks = Check.objects.filter(user=user_obj, status='-').count()

        # sort out css colouring, green if no checks, yellow if one or more
        if num_checks == 0:
            css_class = 'success'
        else:
            css_class = 'warning'

        # return as json object
        out_dict = {
            'num_checks': num_checks,
            'css_class': css_class,
        }

        return JsonResponse(out_dict)


def ajax_num_pending_worksheets(request):
    """
    AJAX call for the number of uncompleted worksheets
    Loaded in the background when the home page is loaded
    TODO this isnt being called anymore because it might be causing the database to be slow, will test on live database
    """
    if request.is_ajax():
        # get all worksheets then filter for only ones that have a current IGV check in them
        all_worksheets = Worksheet.objects.filter(signed_off=True, diagnostic=True).order_by('-run')
        pending_worksheets = [w for w in all_worksheets if 'IGV' in w.get_status()]
        num_pending = len(pending_worksheets)

        # sort out css colouring, green if no checks, yellow if one or more
        if num_pending == 0:
            css_class = 'success'
        else:
            css_class = 'warning'

        # return as json object
        out_dict = {
            'num_pending': num_pending,
            'css_class': css_class,
        }

        return JsonResponse(out_dict)


def ajax_num_worksheet_qc(request):
    """
    AJAX call for the number of worksheets waiting on bioinformatics QC
    Loaded in the background when the home page is loaded
    """
    if request.is_ajax():
        # get all worksheets that havent been signed off yet
        num_pending = Worksheet.objects.filter(signed_off=False).count()

        # sort out css colouring, green if no checks, yellow if one or more
        if num_pending == 0:
            css_class = 'success'
        else:
            css_class = 'warning'

        # return as json object
        out_dict = {
            'num_pending': num_pending,
            'css_class': css_class,
        }

        return JsonResponse(out_dict)


def ajax_autocomplete(request):
    """
    Get a list of worksheets for autocompleting the search bar on the home page
    """
    if request.is_ajax():
        # get search term from ajax
        query_string = request.GET.get('term', '')

        # list to store results plus counter that will control return of results when max limit is reached
        results = []
        counter = 0
        max_results = 10

        # use to search for worksheets - limit to max results variable as we'd never return more than that
        ws_queryset = Worksheet.objects.filter(signed_off=True, ws_id__icontains=query_string)[:max_results]
        run_id_query = Worksheet.objects.filter(signed_off=True, run__run_id__icontains=query_string)[:max_results]

        # process query results from worksheet/ run objects
        for record in ws_queryset | run_id_query:
            results.append({
                'ws': record.ws_id,
                'run': record.run.run_id,
                'sample': None,
            })
            counter += 1

            # return as soon as max length reached to speed up query
            if counter == max_results:
                data = json.dumps(results)
                return HttpResponse(data, 'application/json')


        # process query results from sample objects - this wil only query if the above returns less then the max query size
        sample_queryset = Sample.objects.filter(sample_id__icontains=query_string)[:max_results]

        for record in sample_queryset:
            for ws in record.get_worksheets():
                if ws.signed_off:
                    results.append({
                        'ws': ws.ws_id,
                        'run': ws.run.run_id,
                        'sample': record.sample_id,
                    })
                    counter += 1

                    # return as soon as max length reached to speed up query
                    if counter == max_results:
                        data = json.dumps(results)
                        return HttpResponse(data, 'application/json')


        # return to template if total number less than max query size
        data = json.dumps(results)
        return HttpResponse(data, 'application/json')


@login_required
def view_worksheets(request, query):
    """
    Displays all worksheets and links to the page to show all samples 
    within the worksheet

    """
    # check if user is in the qc user group
    in_qc_user_group = request.user.groups.filter(name='qc_signoff').exists()

    # based on URL, do a different query
    # 30 most recent worksheets
    if query == 'recent':
        worksheets = Worksheet.objects.filter(signed_off=True, diagnostic=True).order_by('-run')[:30]
        filtered = True

    # all worksheets that arent diagnostic
    elif query == 'training':
        worksheets = Worksheet.objects.filter(signed_off=True, diagnostic=False).order_by('-run')
        filtered = True

    # all diagnostic worksheets with an IGV check still open
    elif query == 'pending':
        all_worksheets = Worksheet.objects.filter(signed_off=True, diagnostic=True).order_by('-run')
        worksheets = [w for w in all_worksheets if w.get_status() == 'IGV checking']
        filtered = True

    # worksheets waiting on bioinformatics QC
    elif query == 'qc':
        worksheets = Worksheet.objects.filter(signed_off=False).order_by('-run')
        filtered = True

    # all worksheets
    elif query == 'all':
        worksheets = Worksheet.objects.all().order_by('-run')
        filtered = False

    # any other string will be chnaged to most recent, if left blank then it'll throw a 404 error
    else:
        return redirect('view_worksheets', 'recent')


    # Two seperate lists so that diagnostics runs appear first
    diagnostics_ws_list = []
    other_ws_list = []

    for w in worksheets:
        # if first two characters are digits, add to diagnostics list, otherwise add to other list
        samples = w.get_samples()
        status = w.get_status()
        if w.diagnostic:
            diagnostics_ws_list.append({
                'worksheet_id': w.ws_id,
                'signed_off': w.signed_off,
                'diagnostic': True,
                'run_id': w.run.run_id,
                'assay': w.assay,
                'status': status,
                'samples': samples
            })
        else:
            other_ws_list.append({
                'worksheet_id': w.ws_id,
                'signed_off': w.signed_off,
                'diagnostic': False,
                'run_id': w.run.run_id,
                'assay': w.assay,
                'status': status,
                'samples': samples
            })

    ws_list = diagnostics_ws_list + other_ws_list

    context = {
        'worksheets': ws_list,
        'filtered': filtered,
        'query': query,
        'in_qc_user_group': in_qc_user_group,
    }

    return render(request, 'analysis/view_worksheets.html', context)


@login_required
def view_samples(request, worksheet_id=None, user_pk=None):
    """
    Displays a list of samples from either:
     - a worksheet: all samples on a worksheet
     - a user: all samples assigned to a user
    Only one of the optional args will ever be passed in, each from different URLs, 
    this will control whether a worksheet or a user is displayed
    """
    # check if user is in the qc user group
    in_qc_user_group = request.user.groups.filter(name='qc_signoff').exists()

    # start context dictionary
    context = {
        'unassign_form': UnassignForm(),
        'check_form': PaperworkCheckForm(),
        'reopen_analysis_form': ReopenSampleAnalysisForm(),
        'reopen_qc_form': ReopenRunQCForm(),
        'in_qc_user_group': in_qc_user_group,
    }

    # error if both variables used, shouldnt be able to do this
    if user_pk and worksheet_id:
        raise Http404('Invalid URL, both worksheet_id and user_pk were parsed')

    # if all samples per user required
    elif user_pk:

        # get user object to get list of checks, then get the related samples
        user_obj = get_object_or_404(User, pk=user_pk)
        user_checks = Check.objects.filter(user=user_obj, status='-')
        samples = [c.analysis for c in user_checks]

        # get template specific variables needed for context
        context['template'] = 'user'
        context['username'] = user_obj.username
        context['samples'] = get_samples(samples)

    # if all samples on a worksheet required
    elif worksheet_id:

        # get list of samples
        samples = SampleAnalysis.objects.filter(worksheet = worksheet_id)

        # get template specific variables needed for context
        ws_obj = Worksheet.objects.get(ws_id = worksheet_id)
        context['template'] = 'worksheet'
        context['worksheet'] = worksheet_id
        context['diagnostic'] = ws_obj.diagnostic
        context['run_id'] = ws_obj.run
        context['assay'] = ws_obj.assay
        context['signed_off'] = ws_obj.signed_off
        context['samples'] = get_samples(samples)

        if ws_obj.signed_off:
            context['signoff_user'] = ws_obj.signed_off_user
            context['signoff_time'] = ws_obj.signed_off_time
            context['ws_pass_fail'] = ws_obj.get_auto_qc_pass_fail_display()
            context['autoqc_link'] = f'{settings.AUTOQC_URL}/{ws_obj.auto_qc_pk}'
        else:
            context['qc_form'] = RunQCForm()

    # error if neither variables available
    else:
        raise Http404('Invalid URL, neither worksheet_id or user_pk were parsed')


    ####################################
    #  If any buttons are pressed
    ####################################

    if request.method == 'GET':

        # whole worksheet coverage tsv download
        if 'download-run-coverage' in request.GET:

            # Create a Django response object, and specify content_type as tsv
            filename = f"{worksheet_id}_coverage.tsv"
            response = HttpResponse(content_type='text/tab-separated-values')
            response['Content-Disposition'] = f'attachment; filename={filename}'

            # Create a CSV writer object and write the header
            writer = csv.writer(response, delimiter='\t')
            writer.writerow([
                'Sample ID',
                'Panel',
                'Gene',
                'Percent Coverage 135x',
                'Percent Coverage 270x',
                'Percent Coverage 500x',
                'Percent Coverage 1000x',
            ])

            # loop through all samples and load in sample data
            for sample in samples:
                sample_data = get_sample_info(sample)

                # only process samples that look at SNVs
                if sample_data['panel_obj'].show_snvs == True:
                    coverage_data = get_coverage_data(sample, sample_data['panel_obj'].depth_cutoffs)

                    # Making sure the sample ID isn't repeated in the csv
                    sample_id_written = False

                    # output % coverage per gene at each coverage threshold
                    for gene, coverage in coverage_data['regions'].items():

                        # set sample and panel output based on if its the first occurance for the sample
                        if not sample_id_written:
                            sample_id_out = sample_data['sample_id']
                            panel_out = sample_data['panel']
                            sample_id_written = True

                        else:
                            sample_id_out = ''
                            panel_out = ''

                        # write to file
                        writer.writerow([
                            sample_id_out,
                            panel_out,
                            gene,
                            coverage['percent_135x'],
                            coverage['percent_270x'],
                            coverage['percent_500x'],
                            coverage['percent_1000x'],
                        ])

            return response

    if request.method == 'POST':
        # if unassign modal button is pressed
        if 'unassign' in request.POST:
            unassign_form = UnassignForm(request.POST)
            if unassign_form.is_valid():
                # get sample analysis pk from form
                sample_pk = unassign_form.cleaned_data['unassign']
                sample_analysis_obj = SampleAnalysis.objects.get(pk=sample_pk)

                # get latest check and reset
                unassign_check(sample_analysis_obj)

                # redirect to force refresh, otherwise form could accidentally be resubmitted when refreshing the page
                if context['template'] == 'worksheet':
                    return redirect('view_ws_samples', worksheet_id)
                elif context['template'] == 'user':
                    return redirect('view_user_samples', user_pk)

        # if reopen analysis modal button is pressed
        if 'reopen_analysis' in request.POST:
            reopen_analysis_form = ReopenSampleAnalysisForm(request.POST)
            if reopen_analysis_form.is_valid():
                # get sample analysis pk from form
                sample_pk = reopen_analysis_form.cleaned_data['reopen_analysis']
                sample_analysis_obj = SampleAnalysis.objects.get(pk=sample_pk)

                # reopen the check
                current_user = request.user
                reopen_check(current_user, sample_analysis_obj)

                # redirect to force refresh
                return redirect('view_ws_samples', worksheet_id)

        # if someone starts a first check
        if 'paperwork_check' in request.POST:
            check_form = PaperworkCheckForm(request.POST)
            if check_form.is_valid():
                # get sample analysis pk from form
                sample_pk = check_form.cleaned_data['sample']
                sample_analysis_obj = SampleAnalysis.objects.get(pk=sample_pk)

                # set the check to true and redirect to the sample
                sample_analysis_obj.paperwork_check = True
                sample_analysis_obj.save()

                return redirect('analysis_sheet', sample_analysis_obj.pk)

        # if QC signoff form submitted
        if 'qc_result' in request.POST:
            qc_form = RunQCForm(request.POST)
            if qc_form.is_valid():
                # update values
                cleaned_data = qc_form.cleaned_data
                ws_obj.qc_signoff(True, timezone.now(), request.user, cleaned_data['qc_result'], cleaned_data['auto_qc_pk'])

                # redirect to force refresh
                return redirect('view_ws_samples', worksheet_id)

        # if QC reopened
        if 'reopen_qc' in request.POST:
            reopen_qc_form = ReopenRunQCForm(request.POST)
            if reopen_qc_form.is_valid():

                # remove QC values - individual samples aren't reset in case we have to reopen midway through analysis
                ws_obj.reset_qc_signoff()

                # redirect to force refresh
                return redirect('view_ws_samples', worksheet_id)

    return render(request, 'analysis/view_samples.html', context)


@login_required
def analysis_sheet(request, sample_id):
    """
    Display coverage and variant metrics to allow checking of data 
    in IGV

    """
    # load sample object
    sample_obj = SampleAnalysis.objects.get(pk = sample_id)

    # load in data that is common to both RNA and DNA workflows
    sample_data = get_sample_info(sample_obj)
    current_step_obj = sample_data['checks']['current_check_object']

    # error if the paperwork check hasnt been done, except from QC step
    if (sample_obj.paperwork_check == False) and ('QC' not in sample_data['status']):
        raise Http404("Paperwork hasn't been checked")

    # assign to whoever clicked the sample and reload check objects
    if sample_obj.sample_pass_fail == '-':
        if current_step_obj.user == None:
            current_step_obj.user = request.user
            current_step_obj.save()
            sample_data['checks'] = sample_obj.get_checks()

        if current_step_obj.user != request.user:
            raise PermissionDenied()
        
    # set up context dictionary
    context = {
        'success': [],
        'warning': [],
        'sample_data': sample_data,
        'new_variant_form': NewVariantForm(),
        'new_fusion_form': NewFusionForm(),
        'manual_check_form': ManualVariantCheckForm(regions=sample_data['panel_manual_regions']),
        'submit_form': SubmitForm(),
        'sample_comment_form': SampleCommentForm(
            comment=current_step_obj.overall_comment,
            pk=current_step_obj.pk, 
        ),
        'demographics_form': DetailsCheckForm(info_check=current_step_obj.patient_info_check),
        'coverage_check_form': CoverageCheckForm(
            pk=current_step_obj.pk, 
            comment=current_step_obj.coverage_comment,
            ntc_check=current_step_obj.coverage_ntc_check,
        ),
        'send_back_form': SendCheckBackForm(),
        'sample_qc_form': SampleQCForm(),
    }

    # pull out coverage summary for myeloid, otherwise return false
    if sample_data['is_myeloid_referral']:
        myeloid_coverage_summary = create_myeloid_coverage_summary(sample_obj)
    else:
        myeloid_coverage_summary = False

    # SNV workflow
    if sample_data['panel_obj'].show_snvs == True:
        context['variant_data'] = get_variant_info(sample_data, sample_obj)
        context['coverage_data'] = get_coverage_data(sample_obj, sample_data['panel_obj'].depth_cutoffs)
        context['myeloid_coverage_summary'] = myeloid_coverage_summary

    # fusion workflow
    if sample_data['panel_obj'].show_fusions == True:
        context['fusion_data'] = get_fusion_info(sample_data, sample_obj)

        
    ####################################
    #  If any buttons are pressed
    ####################################

    # download PDF reports
    if request.method == 'GET':

        if 'download-report' in request.GET:
            filename = f"{context['sample_data']['worksheet_id']}_{context['sample_data']['sample_id']}_{context['sample_data']['panel']}.pdf"

            # find the template and render it.
            template = get_template('analysis/download_report.html')
            html = template.render(context)

            # create a pdf, options taken from https://wkhtmltopdf.org/usage/wkhtmltopdf.txt
            options = {
                'orientation': 'Landscape',
                'footer-left': f'Sample - {context["sample_data"]["sample_id"]}',
                'footer-center': f'Worksheet - {context["sample_data"]["worksheet_id"]} ({context["sample_data"]["panel_obj"].get_assay_display()})',
                'footer-right': 'Page [page] of [topage]',
                'footer-line': '',
                'footer-font-size': '10',
                'footer-spacing': '10',
                'page-size': 'Letter',
                'margin-top': '2cm',
                'margin-right': '2cm',
                'margin-bottom': '3cm',
                'margin-left': '2cm',
                'encoding': 'UTF-8',
            }
            pdf = pdfkit.from_string(html, options=options)

            # Create a Django response object, and specify content_type as pdf
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename={filename}'

            return response

        if 'download-xml' in request.GET:
            # create XML from template and context info
            filename = f"{context['sample_data']['worksheet_id']}_{context['sample_data']['sample_id']}_{context['sample_data']['panel']}.xml"
            template = get_template('analysis/lims_xml.xml')
            html = template.render(context)

            # return XML
            response = HttpResponse(html, content_type='application/xml')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response


    # submit buttons
    if request.method == 'POST':

        # if patient demographiocs check is completed
        if 'patient_demographics' in request.POST:
            demographics_form = DetailsCheckForm(request.POST, info_check=current_step_obj.patient_info_check)
            if demographics_form.is_valid():
                # update check
                Check.objects.filter(pk=current_step_obj.pk).update(
                    patient_info_check=demographics_form.cleaned_data['patient_demographics'],
                )
                # reload sample data
                context['sample_data'] = get_sample_info(sample_obj)
                current_step_obj = context['sample_data']['checks']['current_check_object']
                context['demographics_form'] = DetailsCheckForm(info_check=current_step_obj.patient_info_check)

        # if bioinformatics QC fail form submitted
        if 'fail_reason' in request.POST:
            sample_qc_form = SampleQCForm(request.POST)
            if sample_qc_form.is_valid():

                # work out if this is 1st or 2nd check
                current_step_obj = context['sample_data']['checks']['current_check_object']
                if context['sample_data']['checks']['previous_check_object']:
                    next_step = 'finalise'
                else:
                    next_step = 'extra_check'

                # update models
                current_step_obj.overall_comment = sample_qc_form.cleaned_data['fail_reason']
                current_step_obj.overall_comment_updated = timezone.now()
                current_step_obj.save()
                current_step_obj.finalise('Q', next_step, request.user)

                return redirect('view_ws_samples', sample_data['worksheet_id'])

        # comments submit button
        if 'variant_comment' in request.POST:
            var_comment_form = VariantCommentForm(request.POST, pk=request.POST['pk'], comment=request.POST['variant_comment'])
            if var_comment_form.is_valid():

                new_var_data = var_comment_form.cleaned_data
                new_comment = new_var_data['variant_comment']
                pk = new_var_data['pk']

                # update comment
                VariantCheck.objects.filter(pk=pk).update(
                    comment=new_comment,
                    comment_updated=timezone.now(),
                )

                # reload variant data
                context['variant_data'] = get_variant_info(sample_data, sample_obj)

        # if button for manaully scrolling in IGV is clicked
        if 'variants_checked' in request.POST:
            manual_check_form = ManualVariantCheckForm(request.POST, regions=sample_data['panel_manual_regions'])

            if manual_check_form.is_valid():
                current_step_obj.manual_review_check = True
                current_step_obj.save()
                context['sample_data'] = get_sample_info(current_step_obj.analysis)

        # coverage comments button
        if 'coverage_comment' in request.POST:
            new_comment = request.POST['coverage_comment']
            try:
                if request.POST['ntc_checked'] == 'on':
                    ntc_checked = True
            except:
                ntc_checked = False
            pk = request.POST['pk']

            # update comment
            Check.objects.filter(pk=request.POST['pk']).update(
                coverage_comment=new_comment,
                coverage_comment_updated=timezone.now(),
                coverage_ntc_check=ntc_checked,
            )

            # reload sample data
            context['sample_data'] = get_sample_info(sample_obj)
            current_step_obj = context['sample_data']['checks']['current_check_object']
            context['coverage_check_form'] = CoverageCheckForm(
                pk=current_step_obj.pk, 
                comment=current_step_obj.coverage_comment,
                ntc_check=current_step_obj.coverage_ntc_check,
            )

        # fusion comments submit button
        if 'fusion_comment' in request.POST:
            new_comment = request.POST['fusion_comment']
            hgvs = request.POST['hgvs']
            pk = request.POST['pk']

            # update comment
            fusion_check_obj = FusionCheck.objects.get(pk=request.POST['pk'])
            fusion_check_obj.comment=request.POST['fusion_comment']
            fusion_check_obj.comment_updated=timezone.now()

            # update fusion HGVS
            fusion_instance = fusion_check_obj.fusion_analysis.fusion_instance
            fusion_instance.hgvs = hgvs

            # save objects to database
            fusion_check_obj.save()
            fusion_instance.save()
            
            # reload variant data
            context['fusion_data'] = get_fusion_info(sample_data, sample_obj)


        # if add new variant form is clicked
        if 'chrm' in request.POST:
            new_variant_form = NewVariantForm(request.POST)

            if new_variant_form.is_valid():

                new_variant_data = new_variant_form.cleaned_data

                #Get variant together from components
                new_variant = f"{new_variant_data['chrm']}:{new_variant_data['position']}{new_variant_data['ref'].upper()}>{new_variant_data['alt'].upper()}"
                
                variant_check, warning_message = variant_format_check(new_variant_data['chrm'], new_variant_data['position'], new_variant_data['ref'], new_variant_data['alt'], sample_obj.panel.bed_file.path, new_variant_data['total_reads'], new_variant_data['alt_reads'])
                
                if not variant_check:
                    context['warning'].append(warning_message)

                else:
                
                    #Lock to same genome build as sample_analysis 
                    new_variant_object, created = Variant.objects.get_or_create(
                        variant = new_variant,
                        genome_build = sample_obj.genome_build,

                    )
                    new_variant_object.save()
                    new_variant_instance_object = VariantInstance(
                        variant = new_variant_object,
                        gene = new_variant_data['gene'],
                        exon = new_variant_data['exon'],
                        hgvs_c = new_variant_data['hgvs_c'],
                        hgvs_p = new_variant_data['hgvs_p'],
                        sample = sample_obj.sample, 
                        total_count = new_variant_data['total_reads'], 
                        alt_count = new_variant_data['alt_reads'], 
                        in_ntc = new_variant_data['in_ntc'], 
                        manual_upload = True,
                    )
                    new_variant_instance_object.save()
                    new_variant_panel_object = VariantPanelAnalysis(
                        variant_instance=new_variant_instance_object, 
                        sample_analysis=sample_obj
                    )
                    new_variant_panel_object.save()
                    new_variant_check_object = VariantCheck(
                        variant_analysis=new_variant_panel_object, 
                        check_object=sample_obj.get_checks().get('current_check_object')
                    )
                    new_variant_check_object.save()

                    # redirect to same page (if you just reload comtext then form will be resubmitted on refresh)
                    return redirect('analysis_sheet', sample_id)

        # if add new fusion form is clicked
        if 'fusion_genes' in request.POST:
            new_fusion_form = NewFusionForm(request.POST)

            if new_fusion_form.is_valid():

                new_fusion_data = new_fusion_form.cleaned_data

                breakpoint_check, warning_message = breakpoint_format_check(
                    new_fusion_form.cleaned_data['left_breakpoint'],
                    new_fusion_form.cleaned_data['right_breakpoint']
                )

                if not breakpoint_check:

                    context['warning'].append(warning_message)

                else:

                    # Create new Fusion object with same genome build as SampleAnalysis
                    new_fusion_object, created = Fusion.objects.get_or_create(
                        fusion_genes=new_fusion_data['fusion_genes'],
                        left_breakpoint=new_fusion_data['left_breakpoint'],
                        right_breakpoint=new_fusion_data['right_breakpoint'],
                        genome_build=sample_obj.genome_build
                    )
                    new_fusion_object.save()

                    # Create new FusionAnalysis object
                    # Set ref_reads_1 as 0 for RNA as not needed
                    if new_fusion_form.cleaned_data['ref_reads_1']:
                        ref_reads_1 = new_fusion_form.cleaned_data['ref_reads_1']
                    else:
                        ref_reads_1 = 0

                    new_fusion_analysis_object = FusionAnalysis(
                        fusion_genes=new_fusion_object,
                        sample=sample_obj,
                        hgvs=new_fusion_data['hgvs'],
                        in_ntc=new_fusion_data['in_ntc'],
                        ref_reads_1=ref_reads_1,
                        fusion_supporting_reads=new_fusion_data['fusion_supporting_reads'],
                        manual_upload=True,
                        fusion_caller="Manual"
                    )
                    new_fusion_analysis_object.save()

                    # Create new FusionPanelAnalysis object
                    new_fusion_panel_analysis_object = FusionPanelAnalysis(
                        fusion_instance=new_fusion_analysis_object,
                        sample_analysis=sample_obj
                    )
                    new_fusion_panel_analysis_object.save()

                    # Create new FusionCheck object
                    new_fusion_check_object = FusionCheck(
                        fusion_analysis=new_fusion_panel_analysis_object,
                        check_object=sample_obj.get_checks().get('current_check_object')
                    )
                    new_fusion_check_object.save()

                    # redirect to same page (if you just reload comtext then form will be resubmitted on refresh)
                    return redirect('analysis_sheet', sample_id)

        # overall sample comments form
        if 'sample_comment' in request.POST:
            new_comment = request.POST['sample_comment']
            pk = request.POST['pk']

            # update comment
            Check.objects.filter(pk=pk).update(
                overall_comment=new_comment,
                overall_comment_updated=timezone.now(),
            )

            # reload sample data
            context['sample_data'] = get_sample_info(sample_obj)
            current_step_obj = context['sample_data']['checks']['current_check_object']
            context['sample_comment_form'] = SampleCommentForm(
                comment=current_step_obj.overall_comment,
                pk=current_step_obj.pk, 
            )

        # if send check back form is clicked
        if 'send_back_check' in request.POST:
            send_back_form = SendCheckBackForm(request.POST)
            if send_back_form.is_valid():
                # delete current check
                current_check_obj = context['sample_data']['checks']['current_check_object']
                current_check_obj.delete()

                # reopen previous check
                previous_check_obj = context['sample_data']['checks']['previous_check_object']
                reopen_check(previous_check_obj.user, sample_obj)

                return redirect('view_ws_samples', sample_data['worksheet_id'])

        # if finalise check submit form is clicked
        if 'next_step' in request.POST:
            submit_form = SubmitForm(request.POST)
            if submit_form.is_valid():
                pass_fail = submit_form.cleaned_data['analysis_pass_fail']
                next_step = submit_form.cleaned_data['next_step']
                current_step_obj.finalise(pass_fail, next_step, request.user)
                return redirect('view_ws_samples', sample_data['worksheet_id'])

    # render the pages
    return render(request, 'analysis/analysis_sheet.html', context)


def ajax_finalise_check(request):
    """
    AJAX call to check patient demographics are filled in
    """
    if request.is_ajax():
        # load in variables from AJAX
        pk = request.GET.get('current_check')
        option_selected = request.GET.get('option_selected')

        # get check object from query
        current_check_obj = Check.objects.get(id=pk)

        # call finalise check command
        data = current_check_obj.finalise_checks(option_selected)

        return HttpResponse(data, 'application/json')


def ajax(request):
    """
    Handles the submission of the genuine/ artefact etc dropdown box
    """
    if request.is_ajax():

        sample_pk = request.POST.get('sample_pk')
        sample_obj = SampleAnalysis.objects.get(pk = sample_pk)

        selections = json.loads(request.POST.get('selections'))
        variant_type = request.POST.get('variant_type')

        if variant_type == 'snv':
            for variant in selections:
                variant_obj = VariantPanelAnalysis.objects.get(pk=variant)
                current_check = variant_obj.get_current_check()

                new_choice = selections[variant]['genuine_dropdown']
                current_check.decision = new_choice
                current_check.save()

        elif variant_type == 'fusion':
            for variant in selections:
                fusion_obj = FusionPanelAnalysis.objects.get(pk=variant)
                current_check = fusion_obj.get_current_check()

                new_choice = selections[variant]['genuine_dropdown']
                current_check.decision = new_choice
                current_check.save()

        # dont think this redirect is doing anything but there needs to be a HTML response
        # actual reidrect is handled inside AJAX call in analysis-snvs.html
        return redirect('analysis_sheet', sample_pk)


@login_required
def view_polys(request, list_name):
    """
    Page to view all confirmed polys and add and check new ones

    """
    # get poly list and pull out list of confirmed polys and polys to be checked
    poly_list = VariantList.objects.get(name=list_name, list_type='P')
    confirmed_list, checking_list = get_poly_list(poly_list, request.user)

    # set genome build
    genome = poly_list.genome_build

    # make context dictionary
    context = {
        'success': [],
        'warning': [],
        'list_name': list_name,
        'genome_build': genome,
        'confirmed_list': confirmed_list,
        'checking_list': checking_list,
        'confirm_form': ConfirmPolyForm(),
        'add_new_form': AddNewPolyForm(),
    }

    #----------------------------------------------------------
    #  If any buttons are pressed
    if request.method == 'POST':

        # if confirm poly button is pressed
        if 'variant_pk' in request.POST:

            confirm_form = ConfirmPolyForm(request.POST)
            if confirm_form.is_valid():

                # get form data
                variant_pk = confirm_form.cleaned_data['variant_pk']
                comment = confirm_form.cleaned_data['comment']

                # update poly list
                variant_to_variant_list_obj = VariantToVariantList.objects.get(pk=variant_pk)
                variant_to_variant_list_obj.check_user = request.user
                variant_to_variant_list_obj.check_time = timezone.now()
                variant_to_variant_list_obj.check_comment = comment
                variant_to_variant_list_obj.save()

                # get genomic coords for confirmation popup
                variant_obj = variant_to_variant_list_obj.variant
                variant = variant_obj.variant

                # reload context
                confirmed_list, checking_list = get_poly_list(poly_list, request.user)
                context['confirmed_list'] = confirmed_list
                context['checking_list'] = checking_list
                context['success'].append(f'Variant {variant} added to poly list')

        # if add new poly button is pressed
        if 'chrm' in request.POST:
            add_new_form = AddNewPolyForm(request.POST)

            if add_new_form.is_valid():

                # get form data
                chrm = add_new_form.cleaned_data['chrm']
                position = add_new_form.cleaned_data['position']
                ref = add_new_form.cleaned_data['ref']
                alt = add_new_form.cleaned_data['alt']
                comment = add_new_form.cleaned_data['comment']
            
                # check variant format is correct using variant validator
                build = 'GRCh' + str(genome)
                validation_error = validate_variant(chrm, position, ref, alt, build)
                if validation_error:
                    context['warning'].append(f'{validation_error}')
                else:
                    variant = chrm + ':' + str(position) + ref + '>' + alt

                    # load in variant and variant to list objects
                    variant_obj, _ = Variant.objects.get_or_create(variant=variant, genome_build=genome)
                    variant_to_variant_list_obj, created = VariantToVariantList.objects.get_or_create(
                        variant_list = poly_list,
                        variant = variant_obj,
                    )

                    # add user info if a new model is created
                    if created:
                        variant_to_variant_list_obj.upload_user = request.user
                        variant_to_variant_list_obj.upload_time = timezone.now()
                        variant_to_variant_list_obj.upload_comment = comment
                        variant_to_variant_list_obj.save()

                        # give success message
                        context['success'].append(f'Variant {variant} added to poly checking list')

                    # throw error if already in poly list
                    else:
                        context['warning'].append(f'Variant {variant} is already in the poly list')

                    # reload context
                    confirmed_list, checking_list = get_poly_list(poly_list, request.user)
                    context['confirmed_list'] = confirmed_list
                    context['checking_list'] = checking_list

    # render the page
    return render(request, 'analysis/view_polys.html', context)


@login_required
def view_artefacts(request, list_name):
    """
    Page to view all confirmed artefacts and add and check new ones

    """
    # get artefact list and pull out list of confirmed polys and polys to be checked
    artefact_list = VariantList.objects.get(name=list_name, list_type='A')
    confirmed_list, checking_list = get_poly_list(artefact_list, request.user)

    # set genome build
    genome = artefact_list.genome_build
    if genome == 37:
        build_tag = 'info'
    elif genome == 38:
        build_tag = 'success'
    assay = artefact_list.get_assay_display()

    # make context dictionary
    context = {
        'success': [],
        'warning': [],
        'list_name': list_name,
        'genome_build': genome,
        'build_tag': build_tag,
        'assay': assay,
        'confirmed_list': confirmed_list,
        'checking_list': checking_list,
        'confirm_form': ConfirmArtefactForm(),
        'add_new_form': AddNewArtefactForm(),
    }

    #----------------------------------------------------------
    #  If any buttons are pressed
    if request.method == 'POST':

        # if confirm poly button is pressed
        if 'variant_pk' in request.POST:

            confirm_form = ConfirmArtefactForm(request.POST)
            if confirm_form.is_valid():

                # get form data
                variant_pk = confirm_form.cleaned_data['variant_pk']
                comment = confirm_form.cleaned_data['comment']

                # update artefact list
                variant_to_variant_list_obj = VariantToVariantList.objects.get(pk=variant_pk)
                variant_to_variant_list_obj.check_user = request.user
                variant_to_variant_list_obj.check_time = timezone.now()
                variant_to_variant_list_obj.check_comment = comment
                variant_to_variant_list_obj.save()

                # get genomic coords for confirmation popup
                variant_obj = variant_to_variant_list_obj.variant
                variant = variant_obj.variant

                # reload context
                confirmed_list, checking_list = get_poly_list(artefact_list, request.user)
                context['confirmed_list'] = confirmed_list
                context['checking_list'] = checking_list
                context['success'].append(f'Variant {variant} added to artefact list')

        # if add new artefact button is pressed
        if 'chrm' in request.POST:
            add_new_form = AddNewArtefactForm(request.POST)

            if add_new_form.is_valid():

                # get form data
                chrm = add_new_form.cleaned_data['chrm']
                position = add_new_form.cleaned_data['position']
                ref = add_new_form.cleaned_data['ref']
                alt = add_new_form.cleaned_data['alt']
                vaf_cutoff = add_new_form.cleaned_data['vaf_cutoff']
                comment = add_new_form.cleaned_data['comment']

                # Check variant format is correct using variant validator
                build = 'GRCh' + str(genome)
                validation_error = validate_variant(chrm, position, ref, alt, build)
                if validation_error:
                    context['warning'].append(f'{validation_error}')
                else:


                    # load in variant and variant to list objects
                    variant_obj, _ = Variant.objects.get_or_create(variant=variant, genome_build=genome)
                    variant_to_variant_list_obj, created = VariantToVariantList.objects.get_or_create(
                        variant_list = artefact_list,
                        variant = variant_obj,
                        )

                    # add user info if a new model is created
                    if created:
                        variant_to_variant_list_obj.upload_user = request.user
                        variant_to_variant_list_obj.upload_time = timezone.now()
                        variant_to_variant_list_obj.upload_comment = comment
                        variant_to_variant_list_obj.vaf_cutoff = vaf_cutoff
                        variant_to_variant_list_obj.save()

                       # give success message
                        context['success'].append(f'Variant {variant} added to artefact checking list')

                    # throw error if already in poly list
                    else:
                        context['warning'].append(f'Variant {variant} is already in the artefact list')

                    # reload context
                    confirmed_list, checking_list = get_poly_list(artefact_list, request.user)
                    context['confirmed_list'] = confirmed_list
                    context['checking_list'] = checking_list

    # render the page
    return render(request, 'analysis/view_artefacts.html', context)


@login_required
def view_fusion_artefacts(request, list_name):
    """
    Page to view all confirmed artefacts and add and check new ones

    """
    # get artefact list and pull out list of confirmed polys and polys to be checked
    artefact_list = VariantList.objects.get(name=list_name, list_type='F')
    confirmed_list, checking_list = get_fusion_list(artefact_list, request.user)

    # set genome build
    genome = artefact_list.genome_build
    if genome == 37:
        build_tag = 'info'
    elif genome == 38:
        build_tag = 'success'
    assay = artefact_list.get_assay_display()

    # make context dictionary
    context = {
        'success': [],
        'warning': [],
        'list_name': list_name,
        'genome_build': genome,
        'build_tag': build_tag,
        'assay': assay,
        'confirmed_list': confirmed_list,
        'checking_list': checking_list,
        'confirm_form': ConfirmArtefactForm(),
        'add_new_form': AddNewFusionArtefactForm(),
    }

    #----------------------------------------------------------
    #  If any buttons are pressed
    if request.method == 'POST':

        # if confirm poly button is pressed
        if 'variant_pk' in request.POST:

            confirm_form = ConfirmArtefactForm(request.POST)
            if confirm_form.is_valid():

                # get form dataNCOA4/RET and CCDC6--RETNCOA4/RET and CCDC6--RET
                variant_pk = confirm_form.cleaned_data['variant_pk']
                comment = confirm_form.cleaned_data['comment']

                # update artefact list
                variant_to_variant_list_obj = VariantToVariantList.objects.get(pk=variant_pk)
                variant_to_variant_list_obj.check_user = request.user
                variant_to_variant_list_obj.check_time = timezone.now()
                variant_to_variant_list_obj.check_comment = comment
                variant_to_variant_list_obj.save()

                # get genomic coords for confirmation popup
                fusion_obj = variant_to_variant_list_obj.fusion
                fusion = fusion_obj.fusion_genes

                # reload context
                confirmed_list, checking_list = get_fusion_list(artefact_list, request.user)
                context['confirmed_list'] = confirmed_list
                context['checking_list'] = checking_list
                context['success'].append(f'Fusion {fusion} added to artefact list')

        # if add new artefact button is pressed
        if 'left_breakpoint' in request.POST:
            add_new_form = AddNewFusionArtefactForm(request.POST)

            if add_new_form.is_valid():

                # get form data
                left_breakpoint = add_new_form.cleaned_data['left_breakpoint']
                right_breakpoint = add_new_form.cleaned_data['right_breakpoint']
                comment = add_new_form.cleaned_data['comment']

                # wrap in try/ except to handle when a variant doesnt match the input
                try:
                    # load in fusion and variant to list objects
                    fusion_obj = Fusion.objects.get(left_breakpoint=left_breakpoint, right_breakpoint=right_breakpoint)

                    variant_to_variant_list_obj, created = VariantToVariantList.objects.get_or_create(
                        variant_list = artefact_list,
                        fusion = fusion_obj,
                    )

                    fusion = fusion_obj.fusion_genes

                    # add user info if a new model is created
                    if created:
                        variant_to_variant_list_obj.upload_user = request.user
                        variant_to_variant_list_obj.upload_time = timezone.now()
                        variant_to_variant_list_obj.upload_comment = comment
                        variant_to_variant_list_obj.save()

                        # give success message
                        context['success'].append(f'Fusion {fusion} added to artefact checking list')

                    # throw error if already in poly list
                    else:
                        context['warning'].append(f'Fusion {fusion} is already in the artefact list')

                    # reload context
                    confirmed_list, checking_list = get_fusion_list(artefact_list, request.user)
                    context['confirmed_list'] = confirmed_list
                    context['checking_list'] = checking_list

                # throw error if there isnt a variant matching the input
                except Fusion.DoesNotExist:
                    context['warning'].append(f'Cannot find fusion, have you entered the correct breakpoints?')

    # render the page
    return render(request, 'analysis/view_fusion_artefacts.html', context)

@login_required
def options_page(request):
    """
    Display a page of all other options e.g. poly lists
    """
    variant_lists = VariantList.objects.all()
    return render(request, 'analysis/options_page.html', {'variant_lists': variant_lists})


@login_required
def user_settings(request):
    """
    Display a page of user setting options
    """
    context = {
        'lims_form': ChangeLimsInitials(),
        'self_audit_form': SelfAuditSubmission(),
        'warning': []
    }

    #----------------------------------------------------------
    #  If any buttons are pressed
    if request.method == 'POST':

        # if LIMS initials button is pressed
        if 'lims_initials' in request.POST:

            lims_form = ChangeLimsInitials(request.POST)
            if lims_form.is_valid():

                # get form data and change LIMS data
                new_lims_initials = lims_form.cleaned_data['lims_initials']

                # check if LIMS initials are already in the database

                initials_check, warning_message = lims_initials_check(new_lims_initials)

                if not initials_check:

                    context['warning'].append(warning_message)

                else:

                    # update value if it already exists
                    try:
                        request.user.usersettings.lims_initials = new_lims_initials
                        request.user.usersettings.save()

                    # add new record if it doesnt exist
                    except ObjectDoesNotExist:
                        user = UserSettings(
                            user = request.user,
                            lims_initials = new_lims_initials
                        )
                        user.save()

    return render(request, 'analysis/user_settings.html', context)


@login_required
def change_password(request):
    """
    Form to change the password for the logged in user
    """
    password_form = EditedPasswordChangeForm(request.user)
    warning, success = [], []

    context = {
        'password_form': password_form,
        'warning': warning,
        'success': success,
    }

    #----------------------------------------------------------
    #  If any buttons are pressed
    if request.method == 'POST':

        # if password reset button is pressed
        if 'old_password' in request.POST:

            password_form = EditedPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():

                # get new password
                password_form.save()
                new_password = password_form.cleaned_data['new_password1']

                # reset password
                request.user.set_password(new_password)
                request.user.save()

                # prevent user from being logged out
                update_session_auth_hash(request, password_form.user)
                success.append('Password changed')

            # show any form validation errors
            else:
                context['password_form'] = password_form
                warning.append("Couldn't change password, please fix errors in form below")

    return render(request, 'analysis/change_password.html', context)
