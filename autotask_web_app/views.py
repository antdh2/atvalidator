from django.shortcuts import render, redirect
from django.shortcuts import render_to_response
from django.contrib import messages
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.files import File
from django.utils.safestring import mark_safe

import time
import datetime
from datetime import datetime
from datetime import timedelta
import os
import re
import atws
import atws.monkeypatch.attributes
import account.views
import account.forms
import autotask_web_app.forms
import operator
import json
# import the wonderful decorator for stripe
from djstripe.decorators import subscription_payment_required
from . import atvar
from .models import Profile, Picklist, Validation, ValidationGroup, ValidationGroupRule, Entity, Company
from account.signals import user_logged_in


# Constants
at = None
accounts = None
step = 1


@receiver(post_save, sender=User)
def handle_user_save(sender, instance, created, **kwargs):
    if created:
        try:
            company = Company.objects.get(name="No Company")
        except:
            company = None
        if company:
            profile = Profile.objects.create(user=instance, company=company)
        else:
            company = Company.objects.create(name="No Company", password='')

############################################################
#
# All views must go inside of here
#
############################################################

def generate_entities(request, id):
    # entities_in_db = Entity.objects.filter(profile=request.user.profile)
    # for e in entities_in_db:
    #     e.delete()
    # First we must know if this user has a subscription equal to starter package
    if request.user.customer.current_subscription.plan == 'starter':
        entities_in_db = Entity.objects.filter(profile=request.user.profile)
        if not entities_in_db:
            for key, value in STARTER_ENTITIES.items():
                print(key + ": " + value)
                Entity.objects.create(name=key, profile=request.user.profile)
        if entities_in_db:
            for key, value in STARTER_ENTITIES.items():
                for entity in entities_in_db:
                    try:
                        t = Entity.objects.get(name=key, profile=request.user.profile)
                    except:
                        t = None
                    if t:
                        continue
                    else:
                        Entity.objects.create(name=key, profile=request.user.profile)
    if request.user.customer.current_subscription.plan == 'standard':
        entities_in_db = Entity.objects.filter(profile=request.user.profile)
        if not entities_in_db:
            for key, value in STANDARD_ENTITIES.items():
                print(key + ": " + value)
                Entity.objects.create(name=key, profile=request.user.profile)
        if entities_in_db:
            for key, value in STANDARD_ENTITIES.items():
                for entity in entities_in_db:
                    try:
                        t = Entity.objects.get(name=key, profile=request.user.profile)
                    except:
                        t = None
                    if t:
                        print(t.name)
                        continue
                    else:
                        Entity.objects.create(name=key, profile=request.user.profile)
    if request.user.customer.current_subscription.plan == 'professional':
        entities_in_db = Entity.objects.filter(profile=request.user.profile)
        if not entities_in_db:
            for key, value in PROFESSIONAL_ENTITIES.items():
                print(key + ": " + value)
                Entity.objects.create(name=key, profile=request.user.profile)
        if entities_in_db:
            for key, value in PROFESSIONAL_ENTITIES.items():
                for entity in entities_in_db:
                    try:
                        t = Entity.objects.get(name=key, profile=request.user.profile)
                    except:
                        t = None
                    if t:
                        continue
                    else:
                        Entity.objects.create(name=key, profile=request.user.profile)
    return redirect('input_validation', id)

def home(request):
    return render(request, 'home.html', {})

input_validation_dict = {}
@subscription_payment_required
def input_validation(request, id):
    page = 'validation'
    step = 1
    if request.user:
        at = autotask_login_function(request, request.user.profile.autotask_username, request.user.profile.autotask_password)
    try:
        existing_validation_groups = ValidationGroup.objects.filter(company=request.user.profile.company)
        existing_validations = []
        validations = Validation.objects.all()
        for v in validations:
            existing_validations.append(v)
    except:
        existing_validations = None
        existing_validation_groups = None
    entitytypes = Entity.objects.all
    try:
        entity_attributes = at.new(input_validation_dict['EntityName'])
    except:
        entity_attributes = None
    entity = None
    values = None
    selected_key = None
    if request.method == "POST":
        if request.POST.get('step1', False):
            step = 2
            entity = Entity.objects.get(name=request.POST['entitytype'])
            input_validation_dict['Entity'] = entity
            input_validation_dict['EntityName'] = request.POST['entitytype']
            validation_group = ValidationGroup.objects.create(company=request.user.profile.company, name=request.POST['validation-group-name'], entity=entity)
            input_validation_dict['ValidationGroupId'] = validation_group.id
            input_validation_dict['ValidationGroup'] = validation_group
            entity_attributes = at.new(input_validation_dict['EntityName'])
            return redirect('edit_validation_group', id, input_validation_dict['ValidationGroupId'])
            # return render(request, 'input_validation.html', {"page": page, "entitytypes": entitytypes, "OPERATORS": OPERATORS, "step": step, "entity_attributes": entity_attributes, "values": values, "selected_key": selected_key, "existing_validations": existing_validations, "input_validation_dict": input_validation_dict, "existing_validation_groups": existing_validation_groups})
        if request.POST.get('step2-keyselect', False):
            step = 3
            key = request.POST['key']
            selected_key = key
            values = Picklist.objects.filter(company=request.user.profile.company, key__icontains=input_validation_dict['EntityName'] + "_" + key)
            return render(request, 'input_validation.html', {"page": page, "entitytypes": entitytypes, "OPERATORS": OPERATORS, "step": step, "entity_attributes": entity_attributes, "values": values, "selected_key": selected_key, "existing_validations": existing_validations, "input_validation_dict": input_validation_dict, "existing_validation_groups": existing_validation_groups})
        if request.POST.get('step2', False):
            step = 3
            key = request.POST['selected_key']
            value = request.POST['value']
            operator = request.POST['operator']
            # We have to find the picklist from atvar to associate the right number to the validation
            # Validation object "value" should match the result of Picklist "key". ie. (atvar.)Ticket_Status_New on Validation should equal 1 on Picklist
            try:
                picklist_object = Picklist.objects.get(key=value)
                picklist = picklist_object.value
            except:
                picklist = -100
            entity = Entity.objects.get(name="Ticket")
            validation = Validation.objects.create(key=key, value=value, operator=operator, entity=entity, picklist_number=picklist, validation_group=input_validation_dict['ValidationGroup'])
            return render(request, 'input_validation.html', {"page": page, "entitytypes": entitytypes, "OPERATORS": OPERATORS, "step": step, "entity_attributes": entity_attributes, "existing_validations": existing_validations, "input_validation_dict": input_validation_dict, "existing_validation_groups": existing_validation_groups})
    return render(request, 'input_validation.html', {"page": page, "entitytypes": entitytypes, "OPERATORS": OPERATORS, "step": step, "entity_attributes": entity_attributes, "existing_validations": existing_validations, "input_validation_dict": input_validation_dict, "existing_validation_groups": existing_validation_groups})

def edit_validation_group(request, id, validation_group_id):
    if request.user:
        at = autotask_login_function(request, request.user.profile.autotask_username, request.user.profile.autotask_password)
    step = 1
    validation_group = ValidationGroup.objects.get(id=validation_group_id)
    existing_validations = Validation.objects.filter(validation_group=validation_group_id)
    entity_attributes = at.new(validation_group.entity.name)
    try:
        validation_group_rule = ValidationGroupRule.objects.get(validation_group=validation_group_id)
    except:
        validation_group_rule = None
    values = None
    selected_key = None
    key = None
    if request.method == "POST":
        if request.POST.get('validation-group-rule-select', False):
            key = request.POST['key']
            selected_key = key
            values = Picklist.objects.filter(company=request.user.profile.company, key__icontains=validation_group.entity.name + "_" + key)
            return render(request, 'edit_validation_group.html', {"validation_group_rule": validation_group_rule, "OPERATORS": OPERATORS, "step": step, "entity_attributes": entity_attributes, "values": values, "selected_key": selected_key, "existing_validations": existing_validations, "validation_group": validation_group})
        if request.POST.get('step1-keyselect', False):
            step = 2
            key = request.POST['key']
            selected_key = key
            values = Picklist.objects.filter(company=request.user.profile.company, key__icontains=validation_group.entity.name + "_" + key)
            return render(request, 'edit_validation_group.html', {"validation_group_rule": validation_group_rule, "OPERATORS": OPERATORS, "step": step, "entity_attributes": entity_attributes, "values": values, "selected_key": selected_key, "existing_validations": existing_validations, "validation_group": validation_group})
        if request.POST.get('step2', False):
            key = request.POST['selected_key']
            value = request.POST['value']
            operator = request.POST['operator']
            mandatory = request.POST.get('mandatory', False)
            # We have to find the picklist from atvar to associate the right number to the validation
            # Validation object "value" should match the result of Picklist "key". ie. (atvar.)Ticket_Status_New on Validation should equal 1 on Picklist
            try:
                picklist_object = Picklist.objects.get(key=value)
                picklist = picklist_object.value
            except:
                picklist = -100
            validation = Validation.objects.create(key=key, value=value, operator=operator, entity=validation_group.entity, picklist_number=picklist, validation_group=validation_group, mandatory=mandatory)
            return render(request, 'edit_validation_group.html', {"validation_group_rule": validation_group_rule, "OPERATORS": OPERATORS, "step": step, "entity_attributes": entity_attributes, "values": values, "selected_key": selected_key, "existing_validations": existing_validations, "validation_group": validation_group})
        if request.POST.get('validationgrouprulesubmit', False):
            key = request.POST['selected_key']
            value = request.POST['value']
            operator = request.POST['operator']
            # We have to find the picklist from atvar to associate the right number to the validation
            # Validation object "value" should match the result of Picklist "key". ie. (atvar.)Ticket_Status_New on Validation should equal 1 on Picklist
            try:
                picklist_object = Picklist.objects.get(key=value)
                picklist = picklist_object.value
            except:
                picklist = -100
            validation_group_rule = ValidationGroupRule.objects.create(key=key, value=value, operator=operator, entity=validation_group.entity, picklist_number=picklist, validation_group=validation_group, company=request.user.profile.company)
            return render(request, 'edit_validation_group.html', {"validation_group_rule": validation_group_rule, "OPERATORS": OPERATORS, "step": step, "entity_attributes": entity_attributes, "values": values, "selected_key": selected_key, "existing_validations": existing_validations, "validation_group": validation_group})

    return render(request, 'edit_validation_group.html', {"validation_group_rule": validation_group_rule, "OPERATORS": OPERATORS, "step": step, "entity_attributes": entity_attributes, "values": values, "selected_key": selected_key, "existing_validations": existing_validations, "validation_group": validation_group})

def delete_validation_group(request, id):
    userid = request.user.id
    validation_group = ValidationGroup.objects.get(id=id)
    # We must validate that the validation group belongs to this user
    if validation_group.company == request.user.profile.company:
        validation_group.delete()
        messages.add_message(request, messages.SUCCESS, '{} validation group deleted.'.format(validation_group.name))
    else:
        messages.add_message(request, messages.ERROR, '{} is not your validation group.'.format(validation_group.name))
    return redirect('input_validation', userid)

def delete_validation(request, id):
    userid = request.user.id
    validation = Validation.objects.get(id=id)
    validation_group = ValidationGroup.objects.get(id=validation.validation_group.id)
    # We must validate that the validation belongs to this user
    if validation.validation_group == validation_group:
        validation.delete()
        messages.add_message(request, messages.SUCCESS, '{} validation deleted.'.format(validation.key + " " + validation.operator + " " + validation.value))
    else:
        messages.add_message(request, messages.ERROR, '{} is not your validation.'.format(validation.key + " " + validation.operator + " " + validation.value))
    return redirect('edit_validation_group', userid, validation_group.id)

@login_required(login_url='/account/login/')
def profile(request, id):
    page = 'profile'
    if int(request.user.id) != int(id):
        messages.add_message(request, messages.ERROR, "That's not your profile!.")
        return redirect('index')
    # First we must connect to autotask using valid credentials
    if request.method == "POST":
        if request.POST.get('joincompany', False):
            profile = Profile.objects.get(user_id=id)
            company = Company.objects.get(id=request.POST['join-company-id'], name=request.POST['join-company-name'], password=request.POST['join-company-password'])
            profile.company = company
            profile.save()
        if request.POST.get('leavecompany', False):
            profile = Profile.objects.get(user_id=id)
            # Set company to default "No Company"
            company = Company.objects.get(name="No Company")
            profile.company = company
            profile.save()
        if request.POST.get('createcompany', False):
            company = Company.objects.create(name=request.POST['create-company-name'], password=request.POST['create-company-password'])
            company.save()
            profile = Profile.objects.get(user_id=id)
            profile.company = company
            profile.save()
        if request.POST.get('editprofile', False):
            profile = Profile.objects.get(user_id=id)
            profile.first_name = request.POST['profile-firstname']
            profile.last_name = request.POST['profile-lastname']
            profile.about = request.POST['profile-about']
            profile.save()
            return render(request, 'account/profile.html', {"page": page, "profile": profile})
        if request.POST.get('autotasklogin', False):
            at = None
            username = request.POST['username']
            password = request.POST['password']
            at = autotask_login_function(request, username, password)
            user = request.POST['username'].split('@')
            resource = get_resource_from_username(user[0])
            profile = Profile.objects.get(user=request.user)
            profile.atresource_id = resource.id
            profile.save()
            if at:
                messages.add_message(request, messages.SUCCESS, 'Successfully logged in. You may now proceed to create a picklist module.')
                return render(request, 'index.html', {"profile": profile, "page": page, "at": at})
            else:
                return render(request, 'account/profile.html', {"page": page, "at": at, "profile": profile})
    return render(request, 'account/profile.html', {"page": page})

@login_required(login_url='/account/login/')
def index(request):
    try:
        page = 'index'
        accounts = None
        at = None
        if request.user:
            at = autotask_login_function(request, request.user.profile.autotask_username, request.user.profile.autotask_password)

        return render(request, 'index.html', {"accounts": accounts, "page": page, "at": at})
    except AttributeError:
        messages.add_message(request, messages.ERROR, 'No connection with Autotask. Please ensure your Autotask credentials are entered in your profile page.')
        return render(request, 'index.html', {"at": at, })


def ajax_create_ticket(request):
    if request.method == "POST":
        validation_group_rules = ValidationGroupRule.objects.filter(company=request.user.profile.company)
        response_data = {}

        response_data['AllocationCodeID'] = request.POST.get('AllocationCodeID')
        response_data['AssignedResourceID'] = request.POST.get('AssignedResourceID')
        response_data['AssignedResourceRoleID'] = request.POST.get('AssignedResourceRoleID')
        response_data['ContactID'] = request.POST.get('ContactID')
        response_data['Description'] = request.POST.get('Description')
        response_data['DueDateTime'] = request.POST.get('DueDateTime')
        response_data['EstimatedHours'] = request.POST.get('EstimatedHours')
        response_data['IssueType'] = request.POST.get('IssueType')
        response_data['Priority'] = request.POST.get('Priority')
        response_data['QueueID'] = request.POST.get('QueueID')
        response_data['ServiceLevelAgreementID'] = request.POST.get('ServiceLevelAgreementID')
        response_data['Status'] = request.POST.get('Status')
        response_data['SubIssueType'] = request.POST.get('SubIssueType')
        response_data['TicketType'] = request.POST.get('TicketType')
        response_data['Title'] = request.POST.get('Title')
        validated = validate_input(request, validation_group_rules)
        print(validated)
        # if validation fails then return to webpage with an error message (this is handled by function call)
        if not validated:
            django_messages = []

            for message in messages.get_messages(request):
                django_messages.append({
                    "level": message.level_tag,
                    "message": message.message,
                    "extra_tags": message.tags,
            })
            return HttpResponse(json.dumps(django_messages), content_type="application/json")
        return HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
        return HttpResponse(json.dumps({"nothing to see": "this isn't happening"}), content_type="application/json")

create_ticket_dict = {}
@login_required(login_url='/account/login/')
def create_ticket(request, id):
    # First we must check we have a logged in user then ensure we're connected to AT
    if request.user:
        at = autotask_login_function(request, request.user.profile.autotask_username, request.user.profile.autotask_password)
    profile = Profile.objects.get(user=request.user)
    account_id = id
    ataccount = get_account(account_id)
    # Get all picklist objects
    contacts = get_contacts_for_account(account_id)
    ticket_types = get_ticket_type_picklist()
    issue_types = get_issue_type_picklist()
    sub_issue_types = get_sub_issue_type_picklist()
    slas = get_sla_picklist()
    account_types = get_account_types_picklist()
    statuses = get_status_picklist()
    priorities = get_priority_picklist()
    queue_ids = get_queueid_picklist()
    ticket_sources = get_ticket_source_picklist()
    resources = get_resources()
    roles = get_roles()
    services = get_contract_services(account_id)
    allocation_codes = get_allocation_codes()
    contracts = get_contracts(account_id)
    # Grab all validation group rules for this users company
    validation_group_rules = ValidationGroupRule.objects.filter(company=request.user.profile.company)
    validated = True
    if request.method == "POST":
        # Lets check if any of our validation groups are triggered
        validated = validate_input(request, validation_group_rules)
        # if validation fails then return to webpage with an error message (this is handled by function call)
        if not validated:
            return render(request, 'create_ticket.html', {"create_ticket_dict": create_ticket_dict, "contacts": contacts, "services": services, "allocation_codes": allocation_codes, "contracts": contracts, "roles": roles, "resources": resources, "account_types": account_types, "statuses": statuses, "priorities": priorities, "queue_ids": queue_ids, "ticket_sources": ticket_sources, "issue_types": issue_types, "sub_issue_types": sub_issue_types, "slas": slas, "ticket_types": ticket_types, "ataccount": ataccount})
        # if we pass validation, previous line of code is not run and a ticket is created
        # but first lets do some custom work
        # 1) logic for determining which contract to validate
        contract_name = request.POST['ContractID'].lower()
        print(contract_name)
        contract = get_contract_for_ticket(account_id, contract_name)
        print(contract)
        if contract:
            contract = contract
        else:
            contract = None
        new_ticket = ticket_create_new(True,
            AccountID = account_id,
            # AEMAlertID = request.POST['AEMAlertID'],
            AllocationCodeID = request.POST['AllocationCodeID'],
            AssignedResourceID = request.POST['AssignedResourceID'],
            AssignedResourceRoleID = request.POST['AssignedResourceRoleID'],
            # ChangeApprovalBoard = request.POST['ChangeApprovalBoard'],
            # ChangeApprovalStatus = request.POST['ChangeApprovalStatus'],
            # ChangeApprovalType = request.POST['ChangeApprovalType'],
            # ChangeInfoField1 = request.POST['ChangeInfoField1'],
            # ChangeInfoField2 = request.POST['ChangeInfoField2'],
            # ChangeInfoField3 = request.POST['ChangeInfoField3'],
            # ChangeInfoField4 = request.POST['ChangeInfoField4'],
            # ChangeInfoField5 = request.POST['ChangeInfoField5'],
            # CompletedDate = request.POST['CompletedDate'],
            ContactID = request.POST['ContactID'],
            # ContractID = contract.id,
            CreatorResourceID = profile.atresource_id,
            Description = request.POST['Description'],
            DueDateTime = request.POST['DueDateTime'],
            EstimatedHours = request.POST['EstimatedHours'],
            # FirstResponseDateTime = request.POST['FirstResponseDateTime'],
            # FirstResponseDueDateTime = request.POST['FirstResponseDueDateTime'],
            # HoursToBeScheduled = request.POST['HoursToBeScheduled'],
            # InstalledProductID = request.POST['InstalledProductID'],
            IssueType = request.POST['IssueType'],
            # LastActivityDate = request.POST['LastActivityDate'],
            # LastCustomerNotificationDateTime = request.POST['LastCustomerNotificationDateTime'],
            # LastCustomerVisibleActivityDateTime = request.POST['LastCustomerVisibleActivityDateTime'],
            # MonitorID = request.POST['MonitorID'],
            # MonitorTypeID = request.POST['MonitorTypeID'],
            # OpportunityId = request.POST['OpportunityId'],
            Priority = request.POST['Priority'],
            # ProblemTicketId = request.POST['ProblemTicketId'],
            # PurchaseOrderNumber = request.POST['PurchaseOrderNumber'],
            QueueID = request.POST['QueueID'],
            # Resolution = request.POST['Resolution'],
            # ResolutionPlanDateTime = request.POST['ResolutionPlanDateTime'],
            # ResolutionPlanDueDateTime = request.POST['ResolutionPlanDueDateTime'],
            # ResolvedDateTime = request.POST['ResolvedDateTime'],
            # ResolvedDueDateTime = request.POST['ResolvedDueDateTime'],
            # ServiceLevelAgreementHasBeenMet = request.POST['ServiceLevelAgreementHasBeenMet'],
            ServiceLevelAgreementID = request.POST['ServiceLevelAgreementID'],
            # Source = request.POST['Source'],
            Status = request.POST['Status'],
            SubIssueType = request.POST['SubIssueType'],
            # TicketNumber = request.POST['TicketNumber'],
            TicketType = request.POST['TicketType'],
            Title = request.POST['Title'],
            )
        messages.add_message(request, messages.SUCCESS, ('Ticket - ' + new_ticket.TicketNumber + ' - ' + new_ticket.Title + ' created.'))
    return render(request, 'create_ticket.html', {"create_ticket_dict": create_ticket_dict, "contacts": contacts, "services": services, "allocation_codes": allocation_codes, "contracts": contracts, "roles": roles, "resources": resources, "account_types": account_types, "statuses": statuses, "priorities": priorities, "queue_ids": queue_ids, "ticket_sources": ticket_sources, "issue_types": issue_types, "sub_issue_types": sub_issue_types, "slas": slas, "ticket_types": ticket_types, "ataccount": ataccount})

############################################################
#
# All custom methods in here (NO VIEWS)
#
############################################################


def validate_input(request, valgrouprules):
    error_message = []
    validated = True
    # Grab all validation group rules from function input (all of these are specific to users company)
    validation_group_rules = valgrouprules
    for v in validation_group_rules:
        # For straight up strings
        # This segment of code is ONLY triggered when the validation trigger is a string matching a strings
        # e.g. "Title" == "MOT Ticket" rather than the other scenario which is "QueueID" = 28723212
        if OPERATORS[v.operator](request.POST[v.key], v.value):
            # If the rule has triggered - lets get all validations for this rules group
            error_message.append("<strong>Validation Group " + "''" + v.validation_group.name + "''" + " has been triggered by the following rule</strong><br>" + v.key + " " + v.operator + " " + v.value + ".<br>" + "<small>Validation errors will appear below</small><br><br>")
            validations = Validation.objects.filter(validation_group=v.validation_group)
            # Now we cycle through each validation and check if it is true or not
            for validation in validations:
                # First we want to check whether or not the validation is enforced or not
                if validation.mandatory:
                    # If it is, we need to check whether this is a picklist entity or not, -100 means it isn't and value must be a string
                    if validation.picklist_number == -100:
                        # If the user input is equal to the validation value (eg. Title = "MOT Ticket")
                        if request.POST[validation.key] == validation.value:
                            # Then we display a success message and skip the rest of the loop for performance
                            pass
                        # If this condition is false then the validation failed and we need to set validated to False and display a helpful error message
                        # Below line equates to eg. "Title" == "MOT Tic" when it should be "MOT Ticket"
                        if not OPERATORS[validation.operator](request.POST[validation.key].lower(), validation.value):
                            error_message.append("<div class='note note-danger'><strong>ERROR:</strong> " + validation.key + " not valid.<br><small>" + validation.key + " must be " + validation.operator + " " + validation.value + "</small></div>")
                    # We also need to check if the validation IS from an Autotask picklist (ie. predetermined values imported from AT db)
                    # Unlike non-picklist entities these are ALWAYS numbers
                    elif validation.picklist_number != -100:
                        # Using a try catch block because we can get invalid literal for int() with base 10 errors due to HTML inputting empty values as ""
                        # which causes the int() function to throw a hissy fit as "" is clearly not an integer.
                        try:
                            # Below equasion would read as "QueueID" == "29736321" a rather simple check
                            # If it's failed validation, set validated to say so and display an error message
                            if not OPERATORS[validation.operator](int(request.POST[validation.key]), validation.picklist_number):
                                validated = False
                                error_message.append("<div class='note note-danger'><strong>ERROR:</strong> " + validation.key + " not valid.<br><small>" + validation.key + " must be " + validation.operator + " " + validation.value + "</small></div>")
                        # As explained above if user input has a select vvalue for e.g which has been left unselected, the POST values will be ""
                        # but we can handle this nicely by saying to the user they forgot to select something which needs to be validated
                        except:
                            error_message.append("<div class='note note-danger'><strong>ERROR:</strong> " + validation.key + " is empty or not selected.<br><small>" + validation.key + " must be " + validation.operator + " " + validation.value + "</small></div>")
                            print("invalid literal for int() with base 10:")
                            validated = False
                # Now if the validation is NOT mandatory, we do the same again but with different error messages
                else:
                    if validation.picklist_number == -100:
                        if request.POST[validation.key] == validation.value:
                            pass
                        if not OPERATORS[validation.operator](request.POST[validation.key].lower(), validation.value):
                            validated = False
                            error_message.append("<div class='note note-warning'><strong>WARNING:</strong> " + validation.key + " may be incorrect.<br><small>" + validation.key + " should be " + validation.operator + " " + validation.value + "<br>Please be aware that this request may be incorrect yet has still been processed as it has been marked as not mandatory." + "</small></div>")
                    elif validation.picklist_number != -100:
                        try:
                            if not OPERATORS[validation.operator](int(request.POST[validation.key]), validation.picklist_number):
                                validated = False
                                error_message.append("<div class='note note-warning'><strong>WARNING:</strong> " + validation.key + " may be incorrect.<br><small>" + validation.key + " should be " + validation.operator + " " + validation.value + "<br>Please be aware that this request may be incorrect yet has still been processed as it has been marked as not mandatory." + "</small></div>")
                        except:
                            error_message.append("<div class='note note-warning'><strong>WARNING:</strong> " + validation.key + " may be incorrect.<br><small>" + validation.key + " should be " + validation.operator + " " + validation.value + "<br>Please be aware that this request may be incorrect yet has still been processed as it has been marked as not mandatory." + "</small></div>")
                            print("invalid literal for int() with base 10: 234")
        # IF we do not have a string match, we then need to check if there is a picklist match
        # e.g checking that a dropdown box matches - "QueueID" == 28723212 would be read as 28723212 == 28723212
        # When using int() we must use a try catch block to process the error if user hasnt selected the appropriate drop down
        try:
            if OPERATORS[v.operator](int(request.POST[v.key]), v.picklist_number):
                error_message.append("<strong>Validation Group " + "''" + v.validation_group.name + "''" + " has been triggered by the following rule</strong><br>" + v.key + " " + v.operator + " " + v.value + ".<br>" + "<small>Validation errors will appear below</small><br><br>")
                # If the rule has triggered - lets get all validations for this rules group
                validations = Validation.objects.filter(validation_group=v.validation_group)
                # Now we cycle through each validation and check if it is true or not
                for validation in validations:
                    # First we want to check whether or not the validation is enforced or not
                    if validation.mandatory:
                        # If it is, we need to check whether this is a picklist entity or not, -100 means it isn't and value must be a string
                        if validation.picklist_number == -100:
                            # If the user input is equal to the validation value (eg. Title = "MOT Ticket")
                            if request.POST[validation.key] == validation.value:
                                # Then we display a success message and skip the rest of the loop for performance
                                pass
                            # If this condition is false then the validation failed and we need to set validated to False and display a helpful error message
                            # Below line equates to eg. "Title" == "MOT Tic" when it should be "MOT Ticket"
                            if not OPERATORS[validation.operator](request.POST[validation.key].lower(), validation.value):
                                validated = False
                                error_message.append("<div class='note note-danger'><strong>ERROR:</strong> " + validation.key + " not valid.<br><small>" + validation.key + " must be " + validation.operator + " " + validation.value + "</small></div>")
                        # We also need to check if the validation IS from an Autotask picklist (ie. predetermined values imported from AT db)
                        # Unlike non-picklist entities these are ALWAYS numbers
                        elif validation.picklist_number != -100:
                            # Using a try catch block because we can get invalid literal for int() with base 10 errors due to HTML inputting empty values as ""
                            # which causes the int() function to throw a hissy fit as "" is clearly not an integer.
                            try:
                                # Below equasion would read as "QueueID" == "29736321" a rather simple check
                                # If it's failed validation, set validated to say so and display an error message
                                if not OPERATORS[validation.operator](int(request.POST[validation.key].lower()), validation.picklist_number):
                                    validated = False
                                    error_message.append("<div class='note note-danger'><strong>ERROR:</strong> " + validation.key + " not valid.<br><small>" + validation.key + " must be " + validation.operator + " " + validation.value + "</small></div>")
                            # As explained above if user input has a select vvalue for e.g which has been left unselected, the POST values will be ""
                            # but we can handle this nicely by saying to the user they forgot to select something which needs to be validated
                            except:
                                error_message.append("<div class='note note-danger'><strong>ERROR:</strong> " + validation.key + " is empty or not selected.<br><small>" + validation.key + " must be " + validation.operator + " " + validation.value + "</small></div>")
                                print("invalid literal for int() with base 10:")
                                validated = False
                    # Now if the validation is NOT mandatory, we do the same again but with different error messages
                    else:
                        if validation.picklist_number == -100:
                            print(request.POST[validation.key])
                            if request.POST[validation.key] == validation.value:
                                pass
                            if not OPERATORS[validation.operator](request.POST[validation.key].lower(), validation.value):
                                validated = False
                                error_message.append("<div class='note note-warning'><strong>WARNING:</strong> " + validation.key + " may be incorrect.<br><small>" + validation.key + " should be " + validation.operator + " " + validation.value + "<br>Please be aware that this request may be incorrect yet has still been processed as it has been marked as not mandatory." + "</small></div>")
                        elif validation.picklist_number != -100:
                            try:
                                if not OPERATORS[validation.operator](int(request.POST[validation.key].lower()), validation.picklist_number):
                                    validated = False
                                    error_message.append("<div class='note note-warning'><strong>WARNING:</strong> " + validation.key + " may be incorrect.<br><small>" + validation.key + " should be " + validation.operator + " " + validation.value + "<br>Please be aware that this request may be incorrect yet has still been processed as it has been marked as not mandatory." + "</small></div>")
                            except:
                                error_message.append("<div class='note note-warning'><strong>WARNING:</strong> " + validation.key + " may be incorrect.<br><small>" + validation.key + " should be " + validation.operator + " " + validation.value + "<br>Please be aware that this request may be incorrect yet has still been processed as it has been marked as not mandatory." + "</small></div>")
                                print("invalid literal for int() with base 10: 555555")
                                print(error_message['6'])
                                validated = False
        except:
            print("invalid literal for int() with base 10: rule trigger not a match")

    cleaned_error_message = ""
    for msg in error_message:
        cleaned_error_message += msg
    messages.add_message(request, messages.INFO, mark_safe(cleaned_error_message))
    return validated



def ataccount(request, id):
    account_id = id
    ataccount = get_account(account_id)
    tickets = get_tickets_for_account(account_id)
    ticket_account_name = resolve_account_name_from_id(account_id)
    ticket_info = get_ticket_info(tickets)
    return render(request, 'account.html', {"ataccount": ataccount, "tickets": tickets, "ticket_account_name": ticket_account_name,  "TICKET_SOURCES": TICKET_SOURCES})


def check_account_exists(account_name):
    aquery = atws.Query('Account')
    aquery.WHERE('AccountName',aquery.Equals,account_name)
    accounts = at.query(aquery).fetch_all()
    if accounts:
        return True
    else:
        return False

def get_contact_for_account(account_id):
    tquery = atws.Query('Contact')
    tquery.WHERE('AccountID',tquery.Equals,account_id)
    contact = at.query(tquery).fetch_one()
    return contact

def get_contacts_for_account(account_id):
    tquery = atws.Query('Contact')
    tquery.WHERE('AccountID',tquery.Equals,account_id)
    contact = at.query(tquery).fetch_all()
    return contact


def get_account(account_id):
    # Then we need to grab a query object using autotask wrapper
    query = atws.Query('Account')
    # Then filter what we want the query object to grab using SQL
    query.WHERE('id',query.Equals,account_id)
    # Assign the generator from query object to a list which we can interact with
    accounts = at.query(query).fetch_one()
    return accounts

def get_tickets_for_account(account_id):
    tquery = atws.Query('Ticket')
    tquery.WHERE('AccountID',tquery.Equals,account_id)
    tickets = at.query(tquery).fetch_all()
    return tickets

def get_ticket_from_id(ticket_id):
    tquery = atws.Query('Ticket')
    tquery.WHERE('id',tquery.Equals,ticket_id)
    ticket = at.query(tquery).fetch_one()
    return ticket


def get_ticket_info(tickets):
    # tickets variable is entered as a LIST of tickets
    # each LIST of tickets have the tuples so I need to loop through each LIST and then unpack into a dict
    ticket_info = {}
    for ticket in tickets:
        i = 0
        for field, value in ticket:
            try:
                ticket_info.update({field:value})
            except ValueError:
                print("Some error with unpacking tuple")
    return ticket_info

def get_individual_ticket_info(ticket):
    ticket_info = {}
    for field, value in ticket:
        try:
            ticket_info.update({field:value})
        except ValueError:
            print("Some error with unpacking tuple")
    return ticket_info

def resolve_account_name(string):
    aquery = atws.Query('Account')
    aquery.WHERE('AccountName',aquery.Contains,string)
    accounts = at.query(aquery).fetch_all()
    return accounts

def resolve_account_id(string):
    aquery = atws.Query('Account')
    aquery.WHERE('AccountName',aquery.Equals,string)
    accounts = at.query(aquery).fetch_one()
    for field, value in accounts:
        if field == "id":
            acc_id = value
        else:
            acc_id = None
        return acc_id

def resolve_account_name_from_id(account_id):
    aquery = atws.Query('Account')
    aquery.WHERE('id',aquery.Equals,account_id)
    accounts = at.query(aquery).fetch_one()
    for field, value in accounts:
        if field == "AccountName":
            account_name = value
            return account_name


def get_resource_from_id(resource_id):
    aquery = atws.Query('Resource')
    aquery.WHERE('id',aquery.Equals,resource_id)
    resource = at.query(aquery).fetch_one()
    return resource

def get_resource_from_username(username):
    aquery = atws.Query('Resource')
    aquery.WHERE('UserName',aquery.Equals,username)
    resource = at.query(aquery).fetch_one()
    return resource

def get_contact_for_ticket(contact_id):
    aquery = atws.Query('Contact')
    aquery.WHERE('id',aquery.Equals,contact_id)
    contact = at.query(aquery).fetch_one()
    return contact

def autotask_login_function(request, username, password):
    try:
        global at
        at_username = username
        at_password = password
        profile = Profile.objects.get(user=request.user)
        profile.autotask_username = username
        profile.autotask_password = password
        profile.save()
        at = atws.connect(username=profile.autotask_username,password=profile.autotask_password)
        return at
    except NameError:
        messages.add_message(request, messages.ERROR, 'Something went wrong')
    except ValueError:
        messages.add_message(request, messages.ERROR, 'Autotask username/password incorrect')





def ticket_create_new(validated, **kwargs):
    new_ticket = at.new('Ticket')
    new_ticket.AccountID = kwargs.get('AccountID', None)
    new_ticket.AEMAlertID = kwargs.get('AEMAlertID', None)
    new_ticket.AllocationCodeID = kwargs.get('AllocationCodeID', None)
    new_ticket.AssignedResourceID = kwargs.get('AssignedResourceID', None)
    new_ticket.AssignedResourceRoleID = kwargs.get('AssignedResourceRoleID', None)
    new_ticket.ChangeApprovalBoard = kwargs.get('ChangeApprovalBoard', None)
    new_ticket.ChangeApprovalStatus = kwargs.get('ChangeApprovalStatus', None)
    new_ticket.ChangeApprovalType = kwargs.get('ChangeApprovalType', None)
    new_ticket.ChangeInfoField1 = kwargs.get('ChangeInfoField1', None)
    new_ticket.ChangeInfoField2 = kwargs.get('ChangeInfoField2', None)
    new_ticket.ChangeInfoField3 = kwargs.get('ChangeInfoField3', None)
    new_ticket.ChangeInfoField4 = kwargs.get('ChangeInfoField4', None)
    new_ticket.ChangeInfoField5 = kwargs.get('ChangeInfoField5', None)
    new_ticket.CompletedDate = kwargs.get('CompletedDate', None)
    new_ticket.ContactID = kwargs.get('ContactID', None)
    new_ticket.ContractID = kwargs.get('ContractID', None)
    new_ticket.CreatorResourceID = kwargs.get('CreatorResourceID', None)
    new_ticket.Description = kwargs.get('Description', None)
    new_ticket.DueDateTime = kwargs.get('DueDateTime', None)
    new_ticket.FirstResponseDateTime = kwargs.get('FirstResponseDateTime', None)
    new_ticket.FirstResponseDueDateTime = kwargs.get('FirstResponseDueDateTime', None)
    new_ticket.HoursToBeScheduled = kwargs.get('HoursToBeScheduled', None)
    new_ticket.InstalledProductID = kwargs.get('InstalledProductID', None)
    new_ticket.IssueType = kwargs.get('IssueType', None)
    new_ticket.LastActivityDate = kwargs.get('LastActivityDate', None)
    new_ticket.LastCustomerNotificationDateTime = kwargs.get('LastCustomerNotificationDateTime', None)
    new_ticket.LastCustomerVisibleActivityDateTime = kwargs.get('LastCustomerVisibleActivityDateTime', None)
    new_ticket.MonitorID = kwargs.get('MonitorID', None)
    new_ticket.MonitorTypeID = kwargs.get('MonitorTypeID', None)
    new_ticket.OpportunityId = kwargs.get('OpportunityId', None)
    new_ticket.Priority = kwargs.get('Priority', None)
    new_ticket.ProblemTicketId = kwargs.get('ProblemTicketId', None)
    new_ticket.PurchaseOrderNumber = kwargs.get('PurchaseOrderNumber', None)
    new_ticket.QueueID = kwargs.get('QueueID', None)
    new_ticket.Resolution = kwargs.get('Resolution', None)
    new_ticket.ResolutionPlanDateTime = kwargs.get('ResolutionPlanDateTime', None)
    new_ticket.ResolutionPlanDueDateTime = kwargs.get('ResolutionPlanDueDateTime', None)
    new_ticket.ResolvedDateTime = kwargs.get('ResolvedDateTime', None)
    new_ticket.ResolvedDueDateTime = kwargs.get('ResolvedDueDateTime', None)
    new_ticket.ServiceLevelAgreementHasBeenMet = kwargs.get('ServiceLevelAgreementHasBeenMet', None)
    new_ticket.ServiceLevelAgreementID = kwargs.get('ServiceLevelAgreementID', None)
    new_ticket.Source = kwargs.get('Source', None)
    new_ticket.Status = kwargs.get('Status', None)
    new_ticket.SubIssueType = kwargs.get('SubIssueType', None)
    new_ticket.TicketNumber = kwargs.get('TicketNumber', None)
    new_ticket.TicketType = kwargs.get('TicketType', None)
    new_ticket.Title = kwargs.get('Title', None)
    ticket = at.create(new_ticket).fetch_one()
    return ticket



def contact_create_new(validated, **kwargs):
    new_contact = at.new('Contact')
    new_contact.FirstName = kwargs.get('FirstName', None)
    new_contact.LastName = kwargs.get('LastName', None)
    new_contact.EMailAddress = kwargs.get('EMailAddress', None)
    new_contact.AddressLine = kwargs.get('AddressLine', None)
    new_contact.AddressLine1 = kwargs.get('AddressLine1', None)
    new_contact.City = kwargs.get('City', None)
    new_contact.ZipCode = kwargs.get('ZipCode', None)
    new_contact.Phone = kwargs.get('Phone', None)
    new_contact.AccountID = kwargs.get('AccountID', None)
    new_contact.Active = 1
    contact = at.create(new_contact).fetch_one()
    return contact




def get_contract_for_ticket(account_id, contract_name):
    aquery = atws.Query('Contract')
    aquery.WHERE('AccountID',aquery.Equals,account_id)
    aquery.WHERE('ContractName',aquery.Equals,contract_name)
    contract = at.query(aquery).fetch_one()
    return contract


def get_resources():
    aquery = atws.Query('Resource')
    aquery.WHERE('id',aquery.GreaterThan,0)
    resources = at.query(aquery).fetch_all()
    return resources

def get_roles():
    aquery = atws.Query('Role')
    aquery.WHERE('id',aquery.GreaterThan,0)
    roles = at.query(aquery).fetch_all()
    return roles

def get_contracts(account_id):
    aquery = atws.Query('Contract')
    aquery.WHERE('AccountID',aquery.Equals,account_id)
    contracts = at.query(aquery).fetch_all()
    return contracts

def get_all_contracts():
    aquery = atws.Query('Contract')
    aquery.WHERE('AccountID',aquery.GreaterThan,-1)
    aquery.WHERE('Status',aquery.Equals,1)
    contracts = at.query(aquery).fetch_all()
    return contracts

def get_allocation_codes():
    aquery = atws.Query('AllocationCode')
    aquery.WHERE('UseType',aquery.Equals,1)
    allocation_codes = at.query(aquery).fetch_all()
    return allocation_codes

def get_contract_services(account_id):
    aquery = atws.Query('ContractService')
    aquery.WHERE('id',aquery.Equals,account_id)
    services = at.query(aquery).fetch_all()
    return services



def get_ticket_type_picklist():
    ticket_types = Picklist.objects.filter(key__icontains="Ticket_TicketType")
    return ticket_types

def get_issue_type_picklist():
    issue_types = Picklist.objects.filter(key__icontains="Ticket_IssueType")
    return issue_types

def get_sub_issue_type_picklist():
    sub_issue_types = Picklist.objects.filter(key__icontains="Ticket_SubIssueType")
    return sub_issue_types

def get_sla_picklist():
    slas = Picklist.objects.filter(key__icontains="Ticket_ServiceLevelAgreementID")
    return slas

def get_ticket_source_picklist():
    ticket_sources = Picklist.objects.filter(key__icontains="Ticket_Source")
    return ticket_sources

def get_queueid_picklist():
    queue_ids = Picklist.objects.filter(key__icontains="Ticket_QueueID")
    return queue_ids

def get_priority_picklist():
    priorities = Picklist.objects.filter(key__icontains="Ticket_Priority")
    return priorities

def get_status_picklist():
    statuses = Picklist.objects.filter(key__icontains="Ticket_Status")
    return statuses

def get_account_types_picklist():
    account_types = Picklist.objects.filter(key__icontains="Account_AccountType")
    return account_types

############################################################
#
# This is for the picklist module
#
############################################################

def create_picklist(request):
    picklist_messages = []
    if request.user.profile.company == None or request.user.profile.company.name == "No Company" or request.user.profile.company.id == 1:
        return False
    string = "create_picklist_module --username {} --password {} atvar-{}.py".format(request.user.profile.autotask_username, request.user.profile.autotask_password, request.user.profile.company.id)
    picklist_messages.append("<div class='note note-info'>Creating picklist...this can take a while depending on the size of your database.</div>")
    os.system(string)
    picklist_messages.append("<div class='note note-info'>Created picklist module for company {} </div>".format(request.user.profile.company.name))
    return True


def create_picklist_database(request):
    picklist_messages = []
    created = False
    if request.user.profile.company == None or request.user.profile.company.name == "No Company" or request.user.profile.company.id == 1:
        messages.add_message(request, messages.ERROR, 'You must create/join a company and have valid Autotask credentials before creating a picklist.')
        return redirect('index')
    # First we must delete any existing picklists or they will be added to exponentially
    picklist_messages.append("<div class='note note-info'>Deleting existing picklist database...</div>")
    picklists = Picklist.objects.filter(company=request.user.profile.id)
    for picklist in picklists:
        picklist.delete()
    # string = "create_picklist_module --username {} --password {} atvar-{}.py".format(request.user.profile.autotask_username, request.user.profile.autotask_password, request.user.profile.company.id)
    picklist_messages.append("<div class='note note-info'>Creating picklist...this can take a while depending on the size of your database.</div>")
    # os.system(string)
    picklist_messages.append("<div class='note note-info'>Created picklist module for company {} </div>".format(request.user.profile.company.name))
    file = open('atvar-{}.py'.format(request.user.profile.company.id), 'r')
    picklist_messages.append("<div class='note note-info'>Writing new picklist entities into database...</div>")
    for line in file.readlines():
        # Split the line by whitespace giving ['Account_TerritoryID_Local', '=', '29682778']
        line_array = line.split()
        # Set the key to array index 0 to get left side of string, ie. Account_TerritoryID_Local
        db_key = line_array[0]
        # Now select third element in index 2, ie. 29682778
        db_value = line_array[2]
        Picklist.objects.create(company=request.user.profile.company, key=db_key, value=db_value)
    picklist_messages.append("<div class='note note-success'>Added all picklist entities to database</div>")
    cleaned_picklist_message = ''
    for msg in picklist_messages:
        cleaned_picklist_message += msg
    messages.add_message(request, messages.WARNING, mark_safe(cleaned_picklist_message))
    # return redirect('profile', request.user.id)


def ajax_create_picklist(request):
    if request.method == "POST":
        create_picklist_database(request)
        django_messages = []
        for message in messages.get_messages(request):
            django_messages.append({
                "level": message.level_tag,
                "message": message.message,
                "extra_tags": message.tags,
        })
        return HttpResponse(json.dumps(django_messages), content_type="application/json")
    else:
        return HttpResponse(json.dumps({"nothing to see": "this isn't happening"}), content_type="application/json")


def create_picklist_dict(dict_name, index, regex):
    file = open('atvar.py', 'r')
    for line in file.readlines():
        my_line = line
        if re.search(regex, line):
            line_array = line.split()
            # This splits the left side of the equasion into an array seperated by underscore
            dict_key_parse = line_array[0].split("_", 3)
            # Then we grab the specific array we want for key name
            dict_key = dict_key_parse[index] # we want 2
            # Now to build the atvar string and we must convert to int for conditions to work
            dict_value = int(line_array[2])
            dict_name[dict_key] = dict_value
    return dict_name



OPERATORS = {
    "+": operator.add,
    "-": operator.sub,
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}



RESOURCE_ROLES = {
    "Engineer": 29682834,
    "Admin": 29683587,
    "Home User Engineer": 29683586,
    "Sales": 29683582,
}


STARTER_ENTITIES = {
    "Ticket": "Ticket",
}

STANDARD_ENTITIES = {
    "Ticket": "Ticket",
    "Contact": "Contact",
    "Contract": "Contract",
    "Invoice": "Invoice",
}

PROFESSIONAL_ENTITIES = {
    "Ticket": "Ticket",
    "Contact": "Contact",
    "Contract": "Contract",
    "Invoice": "Invoice",
    "Product": "Product",
    "Quote": "Quote",
    "Opportunity": "Opportunity",
    "Appointment": "Appointment",
    "Task": "Task",
}




############################################################
#
# This is for overriding default user signup behaviour
#
############################################################

class LoginView(account.views.LoginView):

    form_class = account.forms.LoginEmailForm


class SignupView(account.views.SignupView):

   form_class = autotask_web_app.forms.SignupForm
   #
   def after_signup(self, form):
       self.create_profile(form)
       super(SignupView, self).after_signup(form)

   def create_profile(self, form):
       profile = self.created_user.profile  # replace with your reverse one-to-one profile attribute
       profile.first_name = form.cleaned_data["first_name"]
       profile.last_name = form.cleaned_data["last_name"]
       profile.email = form.cleaned_data["email"]
       profile.save()

   def generate_username(self, form):
        # do something to generate a unique username (required by the
        # Django User model, unfortunately)
        username = form.cleaned_data['email']
        return username
