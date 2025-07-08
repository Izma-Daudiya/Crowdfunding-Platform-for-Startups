from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from .models import *
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.utils.timezone import now
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum, Count
from django.db import transaction
import re
from django.core.validators import validate_email
import razorpay
from django.conf import settings 
import time
from django.urls import reverse, resolve
from django.urls.exceptions import Resolver404
from .utils import check_and_update_campaign_status

# Create your views here.
def home(request):
    # Fetch the user's role if logged in
    if 'log_id' in request.session:
        user_id = request.session['log_id']
        try:
            user_details = UserDetails.objects.get(user_id=user_id)
            user_role = user_details.role
            request.session['log_role'] = user_role
        except UserDetails.DoesNotExist:
            user_role = None
    else:
        user_role = None

    # To see all category projects
    fetchcatdata = Category.objects.all()
    
    # Fetch active top 3 projects 
    projects = ProjectDetails.objects.filter(status="active").order_by('campaign_end_date')[:4]

     # Prefetch investment data for all projects
    project_ids = projects.values_list('id', flat=True)
    investments = Investment.objects.filter(
        project_id__in=project_ids,
        status__in=['pending', 'released']
    ).values('project_id').annotate(
        total_pledged=Sum('amount'),
        backers_count=Count('user_id', distinct=True)
    )

    # Create a dictionary for quick lookup
    investment_data = {item['project_id']: item for item in investments}

    # Calculate days remaining for each project
    for project in projects:
        today = date.today()
        days_remaining = (project.campaign_end_date - today).days
        project.days_remaining = max(days_remaining, 0)  # Ensure it's not negative

        # Add investment metrics
        project_investment = investment_data.get(project.id, {})
        project.total_pledged = project_investment.get('total_pledged', 0)
        project.backers_count = project_investment.get('backers_count', 0)
        
        # Calculate funding percentage (fixed min() usage)
        funding_goal = project.startup_id.amount_to_raise
        if funding_goal > 0:
            raw_percentage = (project.total_pledged / funding_goal) * 100
            project.funding_percentage = min(round(raw_percentage, 2), 100)
        else:
            project.funding_percentage = 0
            

    users = UserDetails.objects.count()

    # Count total approved investors (Business Backers)
    business_backers_count = UserDetails.objects.filter(
        role='investor', 
        status='approved'
    ).count()

    # reviews = Review.objects.select_related('user_id').all().order_by('-date')[:4]
    # reviews = Review.objects.select_related(
    #     'user_id',
    #     'user_id__userdetails'  # This joins the UserDetails table
    # ).order_by('-date')[:4]

    # Calculate statistics for counters
    # 1. Projects Completed (Funded projects)
    funded_projects_count = ProjectDetails.objects.filter(status='funded').count()
    
    # 2. Raised to Date (Total amount raised across all projects)
    total_raised = Investment.objects.filter(
        status__in=['pending', 'released']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Convert to thousands if needed (86k format)
    total_raised_in_k = round(total_raised / 1000, 0) if total_raised >= 1000 else total_raised
    
    # 3. Happy Customers (Approved users)
    happy_customers_count = UserDetails.objects.filter(status='approved').count()

    context = {
        'user_role': user_role,
        'category': fetchcatdata,
        'projects': projects,
        "users": users,
        'business_backers_count': business_backers_count,
        # 'reviews': reviews,
        'funded_projects_count': funded_projects_count,
        'total_raised': total_raised,
        'total_raised_in_k': total_raised_in_k,
        'happy_customers_count': happy_customers_count,
    }
    return render(request, "index.html", context)

def register(request):
    return render(request, "login-register.html")

def login(request):
    return render(request, "login.html")

def fetchregisterdata(request):
    # fetch
    username = request.POST.get("username")
    email = request.POST.get("email")
    phone = request.POST.get("phone")
    password = request.POST.get("password")
    policy_agreed = request.POST.get("login-register__policy")

    errors = {}

    # Validate Username
    if not username:
        errors["username"] = "Username cannot be empty."
    elif not re.match(r'^[A-Za-z]+(?:\s[A-Za-z]+)*$', username):
        errors["username"] = "Username must contain only letters and spaces."
    elif len(username) < 3 or len(username) > 30:
        errors["username"] = "Username must be 3-30 characters long."

     # Validate Email
    if not email:
        errors["email"] = "Email cannot be empty."
    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        errors["email"] = "Please enter a valid email address."

    # Validate Phone
    if not phone:
        errors["phone"] = "Phone number cannot be empty."
    elif not re.match(r'^[6789]\d{9}$', phone):
        errors["phone"] = "Phone number should start with 6, 7, 8, or 9 and must be 10 digits long."

    # Validate Password
        if not password:
            errors["password"] = "Password cannot be empty."
        elif not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', password):
            errors["password"] = "Password must be 8 characters long, including one uppercase, one lowercase, one digit, and one special character."

    if not policy_agreed:
        errors["policy"] = "You must accept the privacy policy."

    if errors:
        return render(request, "login-register.html", {"errors": errors, "submitted": True})
    else:
        # insert
        insert = Register(username=username, email=email, phone=phone, password=password)
        insert.save()
        return render(request, "login.html")

def checklogindata(request):
    email = request.POST.get("email")
    password = request.POST.get("password")

    errors ={}

    if not email:
        errors["email"] = "Email is required."

    if not password:
        errors["password"] = "Password is required."

    if  errors:
        return render(request, "login.html", {"errors": errors, "submitted": True})
    
    # Select * from tablename where email=email and password=password
    try:
        userdata = Register.objects.get(email=email, password=password)

        # Fetch user details
        # user_details = UserDetails.objects.get(user_id=userdata.id)

        # Session
        request.session["log_id"] = userdata.id
        request.session["log_username"] = userdata.username
        request.session["log_email"] = userdata.email
        # Fetch the user's role if logged in
        if 'log_id' in request.session:
            user_id = request.session['log_id']
            try:
                user_details = UserDetails.objects.get(user_id=user_id)
                user_role = user_details.role
                request.session["log_role"] = user_role
            except UserDetails.DoesNotExist:
                user_role = None
        else:
            user_role = None

        # request.session["log_role"] = user_details.role
    except:
        userdata = None

    if userdata is not None:
        return redirect("/")
    else:
        messages.error(request, "Invalid email or password")

    return render(request, "login.html")


def logout(request):
    # Delete session
    del request.session["log_id"]
    del request.session["log_username"]
    del request.session["log_email"]
    if 'log_role' in request.session:
        del request.session["log_role"]
    return redirect("/")

def fetchUserDetail(request):
    # fetch
    photo = request.FILES['photo']
    linkedin_url = request.POST.get("linkedin_url")
    dob = request.POST.get("dob")
    location = request.POST.get("location")
    aadhar_card = request.FILES['aadhar_card']
    role = request.POST.get("role")
    experience = request.POST.get("experience")

    errors = {}

    # LinkedIn URL Validation
    try:
        URLValidator()(linkedin_url)
        if "linkedin.com/in/" not in linkedin_url:
            errors["linkedin_url"] = "Please enter a valid LinkedIn URL."
    except ValidationError:
        errors["linkedin_url"] = "Please enter a valid LinkedIn URL."

    # Role Validation
    if not role:
        errors["role"] = "Please choose a role."

    # Location Validation
        if not location:
            errors["location"] = "Please choose a state."

    # Aadhar Card Validation
        if not aadhar_card:
            errors["aadhar_card"] = "Aadhar card is required."
        elif aadhar_card.size > 25 * 1024 * 1024:
            errors["aadhar_card"] = "File size must not exceed 25MB."
    
    # Date of Birth Validation
        if not dob:
            errors["dob"] = "Date of Birth is required."
        else:
            dob_date = timezone.datetime.strptime(dob, "%Y-%m-%d").date()
            min_age_date = timezone.now().date() - timedelta(days=365 * 18)
            if dob_date > min_age_date:
                errors["dob"] = "You must be at least 18 years old."

    # Experience Validation
        if not experience:
            errors["experience"] = "Experience is required."

    # Photo Validation (Optional)
        if not photo:
            errors["photo"] = "Photo is required."
        elif photo.size > 25 * 1024 * 1024:
            errors["photo"] = "File size must not exceed 25MB."

    if errors:
        return render(request, "userdetail.html", {"errors": errors})
    else:    
        # fetch foreign key data
        user_id = request.session["log_id"]

        # insert data into userdetail model
        insertquery = UserDetails(user_id=Register(id=user_id), loc_id=Location(id=location), photo=photo,
                                linkedin_url=linkedin_url, dob=dob, aadhar_card=aadhar_card, role=role,
                                experience=experience)
        insertquery.save()
        return redirect("/user_validity")

def user_validity(request):
    log_id = request.session.get("log_id")
    if not log_id:
        messages.error(request, "Please log in first.")
        return redirect("/login")
    
    try:
        user = Register.objects.get(id=log_id)
        user_details = UserDetails.objects.get(user_id=user)
        context = {
            "user": user_details,
            "status": user_details.status
        }

        # Redirect to success page if approved
        if user_details.status == "approved":
            return redirect("/user_profile", context)
        
        # Render the status page
        return render(request, "user_validity.html", context)

    except UserDetails.DoesNotExist:
        messages.error(request, "Please fill out your user details first.")
        return redirect("/userdetail")

def startupDetail(request):
    # fetch data
    category = request.POST.get("category")
    startup_name = request.POST.get("startup_name")
    location = request.POST.get("location")
    creation_date = request.POST.get("creation_date")
    phone = request.POST.get("phone")
    website_url = request.POST.get("website_url")
    startup_email = request.POST.get("startup_email")
    amount_to_raise = request.POST.get("amount_to_raise")
    equity_offer = request.POST.get("equity")
    funding_goal = request.POST.get("funding_goal")
    description = request.POST.get("description")

    errors = {}

    # Validate Category
    if not category:
        errors['category'] = "Category is required."

    # Validate Startup Name
        if not startup_name:
            errors['startup_name'] = "Startup name is required."
        elif len(startup_name) < 3 or len(startup_name) > 50:
            errors['startup_name'] = "Startup name must be 3-50 characters long."
    
    # Validate Location
        if not location:
            errors['location'] = "Location is required."

    # Validate Creation Date
        if not creation_date:
            errors['creation_date'] = "Creation date is required."
        else:
            from datetime import date
            if date.fromisoformat(creation_date) > date.today():
                errors['creation_date'] = "Creation date cannot exceed the current date."

    # Validate Phone Number (Indian)
        if not phone:
            errors['phone'] = "Phone number is required."
        elif not re.match(r'^[6-9]\d{9}$', phone):
            errors['phone'] = "Please enter a valid Indian phone number."

    # Validate Website URL
        if not website_url:
            errors['website_url'] = "Website URL is required."
        else:
            try:
                URLValidator()(website_url)
            except ValidationError:
                errors['website_url'] = "Please enter a valid website URL."

    # Validate Email
        if not startup_email:
            errors['startup_email'] = "Email is required."
        else:
            try:
                validate_email(startup_email)
            except ValidationError:
                errors['startup_email'] = "Please enter a valid email address."

    # Validate Amount to Raise
        if not amount_to_raise:
            errors['amount_to_raise'] = "Amount to raise is required."

    # Validate Equity Offer
        if not equity_offer:
            errors['equity'] = "Equity offer is required."

     # Validate Funding Goal
        if not funding_goal:
            errors['funding_goal'] = "Funding goal is required."

     # Validate Description
        if not description:
            errors['description'] = "Description is required."

    if errors:
        return render(request, 'startup.html', {'errors': errors})
    else:
        # fetch foreign key data
        user_id = request.session["log_id"]

        # insert query
        insertquery = Startup(user_id=Register(id=user_id), cat_id=Category(id=category), loc_id=Location(id=location),
                                    startup_name=startup_name, creation_date=creation_date, phone=phone,
                                    website_url=website_url, startup_email=startup_email, amount_to_raise=amount_to_raise,
                                    equity_offer=equity_offer, funding_goal=funding_goal, description=description)
        insertquery.save()

        startupid = insertquery.id
        print(startupid)
        context = {
            "sid": startupid
        }
        return render(request, "documents.html", context)

def startup_status(request):
    log_id = request.session.get("log_id")
    if not log_id:
        messages.error(request, "Please log in first.")
        return redirect("/login")
    
    try:
        user = Register.objects.get(id=log_id)
        startup_details = Startup.objects.get(user_id=user)
        context = {
            "status": startup_details.status
        }

        # Redirect to success page if approved
        if startup_details.status == "approved":
            # return redirect("/startup_status", context)
            return render(request, "startup_status.html", context)
        
        # Render the status page
        return render(request, "startup_status.html", context)

    except Startup.DoesNotExist:
        messages.error(request, "Please fill out your startup details first.")
        return redirect("/startup")


def documentDetails(request):
    # fetch
    financial_statements = request.FILES["financial_statements"]
    business_plan = request.FILES["business_plan"]
    pitch_deck = request.FILES["pitch_deck"]
    startup_id = request.POST.get("sid")

    errors = {}

    if not financial_statements:
        errors["financial_statements"] = "Financial statements are required."
    elif financial_statements.size > 25 * 1024 * 1024:
        errors["financial_statements"] = "File size must not exceed 25MB."

    if not business_plan:
        errors["business_plan"] = "Business plan is required."
    elif business_plan.size > 25 * 1024 * 1024: 
        errors["business_plan"] = "File size must not exceed 25MB."

    if not pitch_deck:
        errors["pitch_deck"] = "Pitch deck is required."
    elif pitch_deck.size > 25 * 1024 * 1024:
        errors["pitch_deck"] = "File size must not exceed 25MB."

    if errors:
        return render(request, "documents.html", {"errors": errors, })
    else:
        # fetch foreign key data
        user_id = request.session["log_id"]

        request.session["log_startup_id"] = startup_id

        # insert
        insert = Document(user_id=Register(id=user_id), startup_id=Startup(id=startup_id),
                        financial_statements=financial_statements,
                        business_plan=business_plan, pitch_deck=pitch_deck)
        insert.save()
        return redirect("/startup_status")

def projectDetails(request):
    # fetch
    title = request.POST.get("title")
    min_investment = request.POST.get("min_investment")
    max_investment = request.POST.get("max_investment")
    campaign_start_date = request.POST.get("campaign_start_date")
    campaign_end_date = request.POST.get("campaign_end_date")
    project_image = request.FILES["image_url"]
    description = request.POST.get("description")

    # fetch foreign key data
    user_id = request.session["log_id"]
    
    startup_id = request.session.get("log_startup_id")  # Fetch startup_id from session
    print(user_id, startup_id)


    # Check if startup is registered
    try:
        sid = Startup.objects.get(id=startup_id)  # Fetch startup details
    except:
        messages.error(request, "Startup not found. Please register the startup first.")
        return render(request, "startup.html")  # Redirect to startup registration page

    errors = {}

    if not title:
        errors[title] = "Title is required."
    elif len(title) < 3 or len(title) > 50:
        errors[title] = "Title must be 3-50 characters long."

    # Validate Minimum Investment
        try:
            min_investment = float(min_investment)
            if min_investment <= 0:
                errors['min'] = 'Minimum investment must be greater than 0.'
        except (ValueError, TypeError):
            errors['min'] = 'Minimum investment must be a valid number.'

    # Validate Maximum Investment
        try:
            max_investment = float(max_investment)
            if max_investment <= 0:
                errors['max'] = 'Maximum investment must be greater than 0.'
        except (ValueError, TypeError):
            errors['max'] = 'Maximum investment must be a valid number.'

    # Ensure Minimum Investment ≤ Maximum Investment
        if 'min' not in errors and 'max' not in errors:
            if min_investment > max_investment:
                errors['min'] = 'Minimum investment cannot be greater than maximum investment.'
                errors['max'] = 'Maximum investment cannot be less than minimum investment.'


    # Validate investment amounts against startup's amount_to_raise
        if 'min' not in errors and 'max' not in errors:
            if min_investment > sid.amount_to_raise:
                errors['min'] = 'Minimum investment cannot exceed the startup\'s funding goal.'
            if max_investment > sid.amount_to_raise:
                errors['max'] = 'Maximum investment cannot exceed the startup\'s funding goal.'

    # Validate Campaign Dates
        try:
            campaign_start_date = datetime.strptime(campaign_start_date, "%Y-%m-%d").date()
            campaign_end_date = datetime.strptime(campaign_end_date, "%Y-%m-%d").date()


            if campaign_start_date and campaign_start_date < datetime.today().date():
                errors['start_date'] = 'Start date cannot be in the past.'
            if campaign_start_date and campaign_end_date and campaign_end_date <= campaign_start_date:
                errors['end_date'] = 'End date must be after start date.'
            if campaign_start_date and campaign_end_date:
                min_end_date = campaign_start_date + timedelta(days=90)  # 3 months after start date
                if campaign_end_date < min_end_date:
                    errors['end_date'] = 'End date must be at least 3 months after start date.'
        except (ValueError, TypeError):
            errors['start_date'] = 'Invalid date format.'



     # Validate Image (Max 25MB)
        if not project_image:
            errors['image'] = 'Image is required.'
        elif project_image.size > 25 * 1024 * 1024:  # 25MB
            errors['image'] = 'Image size must not exceed 25MB.'

    # Validate Description
        if not description:
            errors['description'] = 'Description is required.'


    if errors:
            return render(request, 'project.html', {'errors': errors})

    # insert
    insert = ProjectDetails(user_id=Register(id=user_id), startup_id=Startup(id=startup_id), title=title,
                            description=description, image_url=project_image,
                            campaign_start_date=campaign_start_date, campaign_end_date=campaign_end_date,
                            minimum_investment=min_investment, maximum_investment=max_investment)
    insert.save()

    messages.success(request, "Project created successfully")
    return redirect("/projects")

def page404(request):
    return render(request, "404.html")

def about(request):
    return render(request, "about.html")

def cart(request):
    return render(request, "cart.html")

def checkout(request):
    return render(request, "checkout.html")

def contact(request):
    return render(request, "contact.html")

def events(request):
    return render(request, "events.html")

def eventslist(request):
    return render(request, "events-list.html")

def eventscarousel(request):
    return render(request, "events-carousel.html")

def eventdetails(request):
    return render(request, "event-details.html")

def faqs(request):
    return render(request, "faq.html")

def gallery(request):
    return render(request, "gallery.html")

def gallerycarousel(request):
    return render(request, "gallery-carousel.html")

def news(request):
    return render(request, "news.html")

def newscarousel(request):
    return render(request, "news-carousel.html")

def newsdetails(request):
    return render(request, "news-details.html")

def newssidebar(request):
    return render(request, "news-sidebar.html")

def partner(request):
    return render(request, "partner.html")

def productdetails(request):
    return render(request, "product-details.html")

def products(request):
    return render(request, "products.html")

def projectcarousel(request):
    return render(request, "project-carousel.html")

def team(request):
    return render(request, "team.html")

def teamcarousel(request):
    return render(request, "team-carousel.html")

def testimonials(request):
    return render(request, "testimonials.html")

def testimonialscarousel(request):
    return render(request, "testimonials-carousel.html")

def userdetail(request, user_id=None):
    log_id = request.session.get("log_id")  # Fetch log_id from session

    if not log_id:
        messages.error(request, "Login First")
        return redirect("/login")

    # If user_id is provided, fetch details for that user (for viewing other users' profiles)
    if user_id:
        try:
            user = Register.objects.get(id=user_id)
            user_details = UserDetails.objects.get(user_id=user)
            context = {
                "user": user_details
            }
            return render(request, "profile.html", context)  # Render profile page for the specified user
        except (Register.DoesNotExist, UserDetails.DoesNotExist):
            messages.error(request, "User details not found")
            return redirect("/")

    # Check if UserDetails already exist for the user
    try:
        user = Register.objects.get(id=log_id)
        user_details = UserDetails.objects.get(user_id=user)
        context = {
            "user": user_details
        }
        return render(request, "profile.html", context)  # Redirect to user validity page
    except UserDetails.DoesNotExist:
        pass  # Proceed to render the userdetail page

    location = Location.objects.all()
    context = {
        "loc": location
    }
    return render(request, "userdetail.html", context)

def startup(request):
    log_id = request.session.get("log_id")  # Fetch log_id from session

    if not log_id:
        messages.error(request, "Login First")
        return redirect("/login")
    
    # Check if the user has filled out UserDetails
    try:
        user_details = UserDetails.objects.get(user_id=log_id)
        if user_details.status != "approved":
            messages.error(request, "You cannot register startup cause may be your account is not verified.")
            return redirect("/user_validity")
    except UserDetails.DoesNotExist:
        messages.error(request, "Please fill out your user details first.")
        return redirect("/userdetail")
    
    # Check if the user is an Entrepreneur
    if user_details.role != 'entrepreneur':
        messages.error(request, "Only Entrepreneurs can register a startup.")
        return redirect("/") 

    # Check if Startup already exist for the user
    try:
        user = Register.objects.get(id=log_id)
        startup_details = Startup.objects.get(user_id=user)
        return redirect("/startup_status")  # Redirect to startup status page
    except Startup.DoesNotExist:
        pass  # Proceed to render the userdetail page

    fetchcatdata = Category.objects.all()
    location = Location.objects.all()
    context = {
        "allcatdata": fetchcatdata,
        "loc": location
    }
    return render(request, "startup.html", context)

def documents(request):
    return render(request, "documents.html")

def project(request):
    log_id = request.session.get("log_id")  # Fetch log_id from session

    if not log_id:
        messages.error(request, "Login First")
        return redirect("/login")

    try:
        user = UserDetails.objects.get(user_id=log_id)
        if user.status != "approved":
            messages.error(request, "You cannot register startup cause may be your account is not verified.")
            return redirect("/user_validity")
    except UserDetails.DoesNotExist:
        messages.error(request, "User details not found. Please complete your profile.")
        return redirect("/userdetail")  # Redirect to user details page

    # Check if the user is an entrepreneur
    if user.role != 'entrepreneur':
        messages.error(request, "Investors cannot create projects.")
        return redirect("/")  # Redirect to home page

    # If logged in, fetch the first startup associated with the user
    try:
        user = Register.objects.get(id=log_id)
        startup = Startup.objects.filter(user_id=user).first()
        if not startup:
            messages.error(request, "No startup found for the logged-in user")
            return redirect("/startup")  # Redirect to a page to create a new startup
        if startup.status != "approved":
            messages.error(request, "You cannot create project cause your startup is not verified yet.")
            return redirect("/startup_status")
    except Register.DoesNotExist:
        messages.error(request, "Login First")
        return redirect("/login")  # Redirect to login if user is not found
    
    # If project already exists for the startup, redirect to manage_campaign
    try:
        project = ProjectDetails.objects.get(startup_id=startup)
        if project.status == "active":
            messages.success(request, "You have already created a project.")
            return redirect("/manage_campaign")
        if project.status != "active":
            messages.error(request, "You project is may be funed or closed.")
            return redirect("/project_status")
    except ProjectDetails.DoesNotExist:
        pass

    context = {
        "sid": startup
    }
    return render(request, "project.html", context)

def project_status(request):
    log_id = request.session.get("log_id")
    if not log_id:
        messages.error(request, "Please log in first.")
        return redirect("/login")
    
    try:
        user = Register.objects.get(id=log_id)
        project_details = ProjectDetails.objects.get(user_id=user)
        context = {
            "status": project_details.status
        }

        # Redirect to manage campaign page if active
        if project_details.status == "active":
            return redirect("/manage_campaign")
        
        # Render the status page
        return render(request, "project_status.html", context)

    except ProjectDetails.DoesNotExist:
        messages.error(request, "Please fill out your project details first.")
        return redirect("/project")
    
def projects(request):
    # Get current date for comparison
    today = date.today()
    
    # FIRST: Update all fully funded projects to 'funded' status BEFORE any filtering
    # Get all active projects
    all_active_projects = ProjectDetails.objects.select_related('startup_id').filter(
        status='active',
        startup_id__status='approved'
    )
    
    # Get investment data for ALL active projects
    all_project_ids = all_active_projects.values_list('id', flat=True)
    all_investments = Investment.objects.filter(
        project_id__in=all_project_ids,
        status__in=['pending', 'released']
    ).values('project_id').annotate(
        total_pledged=Sum('amount')
    )
    
    # Check which projects are fully funded
    projects_to_fund = []
    for project_id, total_pledged in [(inv['project_id'], inv['total_pledged']) for inv in all_investments if inv['total_pledged'] is not None]:
        try:
            project = all_active_projects.get(id=project_id)
            funding_goal = project.startup_id.amount_to_raise
            if funding_goal > 0 and total_pledged >= funding_goal:
                projects_to_fund.append(project_id)
        except ProjectDetails.DoesNotExist:
            continue
    
    # Update fully funded projects
    if projects_to_fund:
        ProjectDetails.objects.filter(id__in=projects_to_fund).update(status='funded')
    
    # SECOND: Update expired projects
    ProjectDetails.objects.filter(
        campaign_end_date__lt=today,  # End date is in the past
        status='active'  # Only update active projects
    ).update(status='closed')  # Change status to closed
    
    # Get all filter parameters
    sort_by = request.GET.get('sort_by')
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search')
    
    # Check if searching - if so, include both active and funded projects
    if search_query:
        # When searching, include both active and funded projects
        fetchProjectDetails = ProjectDetails.objects.select_related('startup_id').filter(
            startup_id__status='approved',
            status__in=['active', 'funded'],  # Include both active and funded
            campaign_start_date__lte=today  # Campaign has started
        )
        
        # Apply search query
        fetchProjectDetails = fetchProjectDetails.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )
        no_results = not fetchProjectDetails.exists()
    else:
        # Not searching, proceed with normal filtering
        if sort_by == 'funded':
            # For funded projects view
            fetchProjectDetails = ProjectDetails.objects.select_related('startup_id').filter(
                startup_id__status='approved',
                status='funded'
            )
        else:
            # Default view - only active projects that haven't ended
            fetchProjectDetails = ProjectDetails.objects.select_related('startup_id').filter(
                startup_id__status='approved',
                campaign_start_date__lte=today,  # Campaign has started
                campaign_end_date__gt=today,    # Campaign hasn't ended yet
                status='active'                 # Status is still active
            )
        
        # Apply additional filters
        if sort_by == 'a_to_z':
            fetchProjectDetails = fetchProjectDetails.order_by('title')
        elif sort_by == 'new_and_noteworthy':
            thirty_days_ago = datetime.now() - timedelta(days=30)
            fetchProjectDetails = fetchProjectDetails.filter(campaign_start_date__gte=thirty_days_ago)[:10]
        elif category_filter:
            fetchProjectDetails = fetchProjectDetails.filter(startup_id__cat_id=category_filter)
        
        no_results = False
    
    # Get project IDs for the filtered set
    project_ids = fetchProjectDetails.values_list('id', flat=True)
    
    # Get investment data for filtered projects
    investments = Investment.objects.filter(
        project_id__in=project_ids,
        status__in=['pending', 'released']
    ).values('project_id').annotate(
        total_pledged=Sum('amount'),
        backers_count=Count('user_id', distinct=True),
    )
    
    # Create dictionary for quick lookup
    investment_data = {item['project_id']: item for item in investments}
    
    # Fetch the user's wishlist
    user_id = request.session.get("log_id")
    user_wishlist = []
    if user_id:
        user_wishlist = Wishlist.objects.filter(user_id=user_id, status=1).values_list('project_id', flat=True)
    
    # Calculate project metrics for display
    for project in fetchProjectDetails:
        days_remaining = (project.campaign_end_date - today).days
        project.days_remaining = max(days_remaining, 0)  # Ensure it's not negative
        
        # Add investment metrics
        project_investment = investment_data.get(project.id, {})
        project.total_pledged = project_investment.get('total_pledged', 0)
        if project.total_pledged is None:  # Handle None values
            project.total_pledged = 0
            
        project.backers_count = project_investment.get('backers_count', 0)
        if project.backers_count is None:  # Handle None values
            project.backers_count = 0
        
        # Calculate funding percentage for display
        funding_goal = project.startup_id.amount_to_raise
        if funding_goal > 0 and project.total_pledged > 0:
            raw_percentage = (project.total_pledged / funding_goal) * 100
            project.funding_percentage = min(round(raw_percentage, 2), 100)
        else:
            project.funding_percentage = 0

    fetchcatdata = Category.objects.all()
    
    context = {
        "allProjectData": fetchProjectDetails,
        "user_wishlist": user_wishlist,
        "category": fetchcatdata,
        "no_results": no_results,
        "search_query": search_query,
    }
    return render(request, "project-02.html", context)

def projectdetails(request, id):
    print(id)
    fetchProjectDetails = ProjectDetails.objects.select_related('startup_id').get(id=id)

    today = date.today()
    fetchProjectDetails.days_remaining = max((fetchProjectDetails.campaign_end_date - today).days, 0)

    # Fetch the photo from UserDetails associated with the user_id in ProjectDetails
    user = UserDetails.objects.filter(user_id=fetchProjectDetails.user_id).first()
    photo = user.photo

    # Fetch pitch deck
    # startup = Document.objects.get(startup_id=fetchProjectDetails.startup_id)
    startup = Document.objects.filter(startup_id=fetchProjectDetails.startup_id).first()
    pitch_deck = startup.pitch_deck
    print(pitch_deck.url)

    # All Projects after details

    # Get the category of the current project's startup
    current_category = fetchProjectDetails.startup_id.cat_id

    # Filter projects by the same category
    data = ProjectDetails.objects.select_related('startup_id').filter(
        startup_id__cat_id=current_category,startup_id__status='approved',status='active').exclude(id=id)


    # Calculate days remaining for each project
    for i in data:
        today = date.today()
        days_remaining = (i.campaign_end_date - today).days
        i.days_remaining = max(days_remaining, 0)  # Ensure it's not negative

         # Calculate funding metrics for each project
        investments = Investment.objects.filter(
            project_id=i.id, 
            status__in=['pending', 'released']
        )
        total_pledged = investments.aggregate(total=Sum('amount'))['total'] or 0
        i.total_pledged = total_pledged
        i.backers_count = investments.count()
        
        # Calculate funding percentage
        funding_goal = i.startup_id.amount_to_raise
        if funding_goal > 0 and total_pledged > 0:
            raw_percentage = (total_pledged / funding_goal) * 100
            i.funding_percentage = min(round(raw_percentage, 2), 100)
        else:
            i.funding_percentage = 0

    # Fetch the user's wishlist
    user_id = request.session.get("log_id")
    user_wishlist = Wishlist.objects.filter(user_id=user_id, status=1).values_list('project_id', flat=True)

    # fetch updates & faqs given by entrepreneur
    update = UpdateDetails.objects.filter(project_id=fetchProjectDetails.id)
    for i in update:
        # Combine update_date and update_time into a datetime object
        update_datetime = datetime.combine(i.update_date, i.update_time)

        # Calculate the time difference
        time_difference = datetime.now() - update_datetime

        # Convert the time difference into a human-readable format
        if time_difference.days > 0:
            i.time_elapsed = f"{time_difference.days} days ago"
        elif time_difference.seconds // 3600 > 0:
            i.time_elapsed = f"{time_difference.seconds // 3600} hours ago"
        else:
            i.time_elapsed = f"{time_difference.seconds // 60} minutes ago"

    faq = FAQ.objects.filter(project_id=fetchProjectDetails.id)

    # Feedback with photos
    feedbacks = Feedback.objects.filter(project_id=fetchProjectDetails.id).select_related('user_id')
    feedback_with_photos = []
    for feedback in feedbacks:
        user_details = UserDetails.objects.filter(user_id=feedback.user_id).first()
        feedback_with_photos.append({
            'feedback': feedback,
            'user_photo': user_details.photo if user_details else None
        })

    # Check if the current user has already submitted feedback for this project
    user_has_feedback = False
    user_has_invested = False
    if user_id:
        user_has_feedback = Feedback.objects.filter(user_id=user_id, project_id=fetchProjectDetails.id).exists()
        # Check if user has an investment in this project
        user_has_invested = Investment.objects.filter(
            user_id=user_id, 
            project_id=fetchProjectDetails.id,
            status__in=['pending', 'released']  # Consider both pending and released investments
        ).exists()

    # Calculate total pledged amount and number of backers
    investments = Investment.objects.filter(
        project_id=id, 
        status__in=['pending', 'released']  # Count both pending and released investments
    )
    total_pledged = investments.aggregate(total=Sum('amount'))['total'] or 0
    backers_count = investments.count()

    # Calculate funding percentage (use maximum_investment as the goal)
    funding_goal = fetchProjectDetails.startup_id.amount_to_raise
    if funding_goal > 0 and total_pledged > 0:
        raw_percentage = (total_pledged / funding_goal) * 100
        funding_percentage = min(round(raw_percentage, 2), 100)
        # In the projectdetails view, after calculating funding_percentage
        is_fully_funded = funding_percentage >= 100
    else:
        funding_percentage = 0
        is_fully_funded = False
   
    
    context = {
        "data": fetchProjectDetails,
        "photo": photo,
        "pitch_deck": pitch_deck,
        "project": data,
        "user_wishlist": user_wishlist,
        "updates": update,
        "faqs": faq,
        "feedback": feedback_with_photos,
        "user_has_feedback": user_has_feedback,
        "total_pledged": total_pledged,
        "backers_count": backers_count,
        "funding_percentage": funding_percentage,
        "user_has_invested": user_has_invested,
        "is_fully_funded": is_fully_funded,
    }
    return render(request, "project-details.html", context)

def wishlist(request):
    user_id = request.session.get("log_id")
    if not user_id:
        messages.error(request, "Register First")
        return redirect("/register")

    # user = UserDetails.objects.get(user_id=user_id)
    # if user.status != "approved":
    #     messages.error(request, "You cannot add anything to wishlist cause your account is not verified yet.")
    #     return redirect("/user_validity")
    
    wishlist_items = Wishlist.objects.filter(user_id=user_id, status=1).select_related('project_id')

     # Calculate days remaining, amount raised, and percentage for each project
    for item in wishlist_items:
        project = item.project_id
        
        # Calculate days remaining
        today = timezone.now().date()
        if project.campaign_end_date > today:
            item.days_remaining = (project.campaign_end_date - today).days
        else:
            item.days_remaining = 0
        
        # Calculate amount raised (sum of investments for this project)
        investments = Investment.objects.filter(project_id=project.id, status__in=['pending', 'released'])
        amount_raised = investments.aggregate(Sum('amount'))['amount__sum'] or 0
        item.amount_raised = amount_raised
        
        # Calculate percentage of funding goal achieved
        goal_amount = project.startup_id.amount_to_raise
        if goal_amount > 0:
            item.percentage_raised = min(float((amount_raised / goal_amount) * 100), 100)
        else:
            item.percentage_raised = 0
    
    context = {
        "wishlist_items": wishlist_items
    }

    return render(request, "wishlist.html", context)

def toggle_wishlist(request, project_id):
    user_id = request.session.get("log_id")

    if not user_id:
        messages.error(request, "Register First")
        return redirect("/register")

    try:
        project = ProjectDetails.objects.get(id=project_id)
    except ProjectDetails.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)

    try:
        wishlist_item = Wishlist.objects.get(user_id=user_id, project_id=project_id)
        wishlist_item.status = 1 if wishlist_item.status == 0 else 0
        wishlist_item.save()
        action = 'removed' if wishlist_item.status == 0 else 'added'
    except Wishlist.DoesNotExist:
        Wishlist.objects.create(user_id=Register(id=user_id), project_id=project, status=1)
        action = 'added'

    return JsonResponse({'status': 'success', 'action': action,
                         'is_in_wishlist': wishlist_item.status if 'wishlist_item' in locals() else 1})

def manage_campaign(request):
    user_id = request.session.get("log_id")
    try:
        fetchProjectDetails = ProjectDetails.objects.get(user_id=user_id)
        if fetchProjectDetails.status != "active":
            messages.success(request, "Your project is not active.")
            return redirect("/project_status")
    except ProjectDetails.DoesNotExist:
        messages.error(request, "No project found for the logged-in user.")
        return redirect("/project")

    # today = date.today()
    # fetchProjectDetails.days_remaining = max((fetchProjectDetails.campaign_end_date - fetchProjectDetails.campaign_start_date).days, 0)

    today = date.today()
    
    # Calculate days remaining (campaign end date minus today's date)
    if fetchProjectDetails.campaign_end_date >= today:
        fetchProjectDetails.days_remaining = (fetchProjectDetails.campaign_end_date - today).days
    else:
        fetchProjectDetails.days_remaining = 0  # Campaign has ended


    # Fetch the photo from UserDetails associated with the user_id in ProjectDetails
    user = UserDetails.objects.filter(user_id=fetchProjectDetails.user_id).first()
    photo = user.photo

    # Fetch pitch deck
    startup = Document.objects.filter(startup_id=fetchProjectDetails.startup_id).first()
    pitch_deck = startup.pitch_deck
    print(pitch_deck.url)

    # Updates and FAQS
    update = UpdateDetails.objects.filter(project_id=fetchProjectDetails.id)
    for i in update:
        # Combine update_date and update_time into a datetime object
        update_datetime = datetime.combine(i.update_date, i.update_time)

        # Calculate the time difference
        time_difference = datetime.now() - update_datetime

        # Convert the time difference into a human-readable format
        if time_difference.days > 0:
            i.time_elapsed = f"{time_difference.days} days ago"
        elif time_difference.seconds // 3600 > 0:
            i.time_elapsed = f"{time_difference.seconds // 3600} hours ago"
        else:
            i.time_elapsed = f"{time_difference.seconds // 60} minutes ago"


    faqs = FAQ.objects.filter(project_id=fetchProjectDetails.id)

    # Feedback with photos
    feedbacks = Feedback.objects.filter(project_id=fetchProjectDetails.id).select_related('user_id')
    feedback_with_photos = []
    for feedback in feedbacks:
        user_details = UserDetails.objects.filter(user_id=feedback.user_id).first()
        feedback_with_photos.append({
            'feedback': feedback,
            'user_photo': user_details.photo if user_details else None
        })

    # Calculate total pledged amount and number of backers
    investments = Investment.objects.filter(
        project_id=fetchProjectDetails.id, 
        status__in=['pending', 'released']  # Count both pending and released investments
    )
    total_pledged = investments.aggregate(total=Sum('amount'))['total'] or 0
    backers_count = investments.values('user_id').distinct().count()  # Count unique backers

    # Calculate funding percentage (use startup's amount_to_raise as the goal)
    funding_goal = fetchProjectDetails.startup_id.amount_to_raise
    funding_percentage = min(round((total_pledged / funding_goal) * 100, 2) if funding_goal > 0 else 0, 100)

    context = {
        "data": fetchProjectDetails,
        "photo": photo,
        "pitch_deck": pitch_deck,
        "updates": update,
        "faqs": faqs,
        "feedback": feedback_with_photos,
        "total_pledged": total_pledged,
        "backers_count": backers_count,
        "funding_percentage": funding_percentage,
    }
    return render(request, "manage-campaign.html", context)

def update(request):
    title = request.POST.get("title")
    update = request.POST.get("update")
    project_id = request.POST.get("project_id")
    user_id = request.session["log_id"]

    errors = {}

    if not title:
        errors["title"] = "Title is required."
    elif len(title) < 3 or len(title) > 50: 
        errors["title"] = "Title must be 3-50 characters long."

    if not update:
        errors["updates"] = "Update is required."
    elif len(update) < 3 or len(update) > 500:
        errors["updates"] = "Update must be 3-500 characters long."

    if errors:
        return redirect("/manage_campaign", {"errors": errors})
    
    
    insert = UpdateDetails(user_id=Register(id=user_id), project_id=ProjectDetails(id=project_id), content=update,
                           title=title)
    insert.save()
    print("Redirecting to projectdetails with ID:", project_id)
    return redirect("/manage_campaign")

def faq(request):
    question = request.POST.get("question")
    answer = request.POST.get("answer")
    project_id = request.POST.get("pid")

    user_id = request.session["log_id"]

    insert = FAQ(user_id=Register(id=user_id), project_id=ProjectDetails(id=project_id), question=question,
                 answer=answer)
    insert.save()

    print("Redirecting to projectdetails with ID:", project_id)
    # return redirect("projectdetails", id=project_id)
    return redirect("/manage_campaign")

def edit(request, model_type):
    if model_type == 'update':
        id = request.POST.get('update_id')
        update = UpdateDetails.objects.get(id=id)
        update.title = request.POST.get('title')
        update.content = request.POST.get('content')
        update.save()
    elif model_type == 'faq':
        id = request.POST.get('faq_id')
        faq = FAQ.objects.get(id=id)
        faq.question = request.POST.get('question')
        faq.answer = request.POST.get('answer')
        faq.save()
    return redirect("/manage_campaign")

def delete(request, id, model_type):
    if model_type == 'update':
        fetchdata = UpdateDetails.objects.get(id=id)
        fetchdata.delete()
    elif model_type == 'faq':
        fetchfaq = FAQ.objects.get(id=id)
        fetchfaq.delete()
    return redirect("/manage_campaign")

def feedback(request):
    user_id = request.session.get("log_id")
    if not user_id:
        return redirect("/login")

    user = UserDetails.objects.get(user_id=user_id)
    if not user:
        messages.error(request, "Please create your account.")
        return redirect("/userdetail")

    if user.status != "approved":
        messages.error(request, "You cannot give feedback cause your account is not verified yet.")
        return redirect("/user_validity")

    project_id = request.POST.get("pid")

    # Check if user has invested in this project
    has_invested = Investment.objects.filter(
        user_id=user_id,
        project_id=project_id,
        status__in=['pending', 'released']
    ).exists()
    
    if not has_invested:
        messages.error(request, "Only investors in this project can provide feedback.")
        return redirect("projectdetails", id=project_id)

    comment = request.POST.get("comment")
    rating = float(request.POST.get("rating"))

    if rating < 1 or rating > 5:
        messages.error(request, 'Rating must be between 1 and 5.')
        return redirect('projectdetails', id=project_id)

    insert = Feedback(user_id=Register(id=user_id), project_id=ProjectDetails(id=project_id), comment=comment, rating=rating)
    insert.save()

    return redirect("projectdetails", id=project_id)

def admin_dashboard(request):
    return render(request, "admin-dashboard.html")

def categorywiseproject(request, id):
    # Fetch the category object
    category = Category.objects.get(id=id)

    # Fetch startups related to the category
    startups_in_category = Startup.objects.filter(cat_id=id)
    
    # Fetch projects related to the startups in the category
    projects_in_category = ProjectDetails.objects.filter(startup_id__in=startups_in_category)

    # Calculate days remaining for each project
    for project in projects_in_category:
        today = date.today()
        days_remaining = (project.campaign_end_date - today).days
        project.days_remaining = max(days_remaining, 0)  # Ensure it's not negative

        # Get all successful investments for this project (excluding failed payments)
        investments = Investment.objects.filter(
            project_id=project,
            status__in=['pending', 'released', 'refunded']
        )

        # Calculate total pledged amount
        project.total_pledged = investments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Count number of unique backers
        project.backers_count = investments.values('user_id').distinct().count()
        
        # Calculate funding percentage
        funding_goal = project.startup_id.amount_to_raise
        if funding_goal > 0:
            raw_percentage = (project.total_pledged / funding_goal) * 100
            project.funding_percentage = min(round(raw_percentage, 2), 100)
        else:
            project.funding_percentage = 0

    context = {
        "data": projects_in_category,
        "category": category.category
    }
    
    return render(request, "categorywiseproject.html", context)

def user_profile(request):
    user_id = request.session.get("log_id")
    if not user_id:
        messages.error(request, "Please log in first.")
        return redirect("/login")

    try:
        user = Register.objects.get(id=user_id)
        user_details = UserDetails.objects.get(user_id=user)
    except UserDetails.DoesNotExist:
        messages.error(request, "Please fill out your user details first.")
        return redirect("/userdetail")
    
    
    context = {
        "user": user,
        "user_details": user_details,
    }
    
    return render(request, "profile.html", context)

def newsletter(request):
    email = request.POST.get("email")
    insert = Newsletter(email=email)
    insert.save()
    return redirect("/")

def submitContact(request):
    name = request.POST.get("name")
    email = request.POST.get("email")
    phone = request.POST.get("phone")
    subject = request.POST.get("subject")
    message = request.POST.get("message")

    insert = Contact(name=name, email=email, phone=phone, subject=subject, message=message)
    insert.save()
    return redirect("/")

def review(request):
    return render(request, "review.html")

def privacypolicy(request):
    return render(request, "privacypolicy.html")

def investment(request, id):
    # Check and update campaign status first
    status_message = check_and_update_campaign_status(id)
    if status_message != "No status update needed.":
        messages.info(request, status_message)

    try:
        project = ProjectDetails.objects.get(id=id)
        # Check if project is fully funded
        funding_goal = project.startup_id.amount_to_raise
        investments = Investment.objects.filter(
            project_id=id, 
            status__in=['pending', 'released']
        )
        total_pledged = investments.aggregate(total=Sum('amount'))['total'] or 0
        
        if total_pledged >= funding_goal:
            messages.error(request, "This project has already reached its funding goal and is no longer accepting investments.")
            return redirect(f"/projectdetails/{id}")
            
    except ProjectDetails.DoesNotExist:
        messages.error(request, "Project not found")
        return redirect("/projects")

    # Check if user is logged in
    user_id = request.session.get("log_id")
    if not user_id:
        messages.error(request, "Please login first to invest.")
        return redirect("/login")
    
    # Check if user is approved investor
    try:
        user_details = UserDetails.objects.get(user_id=user_id)
        if user_details.role != 'investor':
            messages.error(request, "Only investors can invest in projects.")
            return redirect("/")
        if user_details.status != 'approved':
            messages.error(request, "Your account must be approved before investing.")
            return redirect("/user_validity")
    except UserDetails.DoesNotExist:
        messages.error(request, "Please complete your profile first.")
        return redirect("/userdetail")
    
    # Check if project is still active
    if project.status != 'active':
        messages.error(request, "This project is no longer accepting investments.")
        return redirect(f"/projectdetails/{id}")

    # Check if user has already invested in this project
    existing_investment = Investment.objects.filter(
        user_id=user_id, 
        project_id=id, 
        status__in=['pending', 'released']  # Consider both pending and released investments
    ).exists()
    
    if existing_investment:
        messages.error(request, "You have already invested in this project.")
        return redirect(f"/projectdetails/{id}")

    context = {
        "project": project,
        "errors": {},
        "submitted": False,
    }
    return render(request, "investment.html", context)

def confirminvestment(request):
    if request.method == 'POST':
        # Retrieve form data
        userid = request.session["log_id"]
        pid = request.POST.get('pid')
        pancard = request.POST.get('pancard')
        amount = float(request.POST.get('amount'))
        terms_accepted = request.POST.get('login-register__policy') == 'on'
        print(pid)

        projectData = ProjectDetails.objects.get(id=pid)
        startup = projectData.startup_id  # Assuming ForeignKey from ProjectDetails to Startup

        # Equity calculation
        equity_offered = (amount / startup.amount_to_raise) * startup.equity_offer

        # Create a Razorpay instance (replace with your actual Razorpay API keys)
        razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))

        order_amount = int(amount * 100)  # Amount in paisa
        order_currency = 'INR'
        order_receipt = 'order_rcptid_' + str(pid)
        razorpay_order = razorpay_client.order.create(
            dict(amount=order_amount, currency=order_currency, receipt=order_receipt))
        razorpay_order_id = razorpay_order['id']


        # Save investment details to database
        investment = Investment.objects.create(
            user_id=Register(id=userid),  # Assuming you have authentication and user details available
            project_id=ProjectDetails(id=pid),
            pancard=pancard,
            amount=amount,
            equity_offered=equity_offered,
            razorpay_order_id=razorpay_order_id,
            status='pending',  # Initial status
            terms_accepted=terms_accepted
        )
        investment.save()

        # After saving the investment, check if this investment met the funding goal
        check_and_update_campaign_status(pid)

        # Redirect user to Razorpay payment page
        return render(request, "payment.html", {
            "razorpay_order_id": razorpay_order['id'],
            "amount": amount,
            "key": settings.RAZORPAY_KEY_ID,
            "currency": "INR",
        })

    return redirect("/")

def payment_success(request):
    return redirect("/")

    
def manageinvestment(request):
    userid = request.session["log_id"]
    investments = Investment.objects.filter(user_id=userid)
    context = {
        'investments': investments
    }
    return render(request,"manageinvestment.html",context)

def search_redirect(request):
    if request.method == 'GET':
        search_query = request.GET.get('q', '').strip()
        if search_query:
            try:
                # Try to resolve the URL directly
                resolve(search_query)
                return redirect(search_query)
            except Resolver404:
                # If direct resolution fails, try common patterns
                common_prefixes = ['/', '/projects',]
                for prefix in common_prefixes:
                    try:
                        url = f"{prefix}{search_query}"
                        resolve(url)
                        return redirect(url)
                    except Resolver404:
                        continue
                
                # If still not found, show error message
                # messages.error(request, f"Page '{search_query}' not found")
                return redirect('404_test' if settings.DEBUG else '404')
    
    return redirect('home')  # Fallback redirect
