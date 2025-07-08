from django.db import models
from django.utils.safestring import mark_safe


# Create your models here.
class Register(models.Model):
    username = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    phone = models.BigIntegerField(unique=True)
    password = models.CharField(max_length=8)

    def __str__(self):
        return self.username

class Location(models.Model):
    location = models.CharField(max_length=30)

    def __str__(self):
        return self.location

class UserDetails(models.Model):
    ROLE_CHOICES = [
        ('entrepreneur', 'Entrepreneur'),
        ('investor', 'Investor')
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
    loc_id = models.ForeignKey(Location, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to="photos/UserPhoto", blank=True, null=True)
    linkedin_url = models.URLField(max_length=100, blank=True, null=True)
    dob = models.DateField()
    aadhar_card = models.ImageField(upload_to="photos/AadharCardPhoto", blank=False, null=False, help_text="Upload a clear image of your Aadhar card")
    role = models.CharField(max_length=15, choices=ROLE_CHOICES)
    experience = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def user_photo(self):
        if self.photo:
            return mark_safe('<img src="{}" width="100"/>'.format(self.photo.url))

    user_photo.allow_tags = True

    def aadhar_photo(self):
        return mark_safe('<img src="{}" width="100"/>'.format(self.aadhar_card.url))

    aadhar_photo.allow_tags = True


class Category(models.Model):
    category = models.CharField(max_length=50)

    def __str__(self):
        return self.category

class Startup(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]
    user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
    cat_id = models.ForeignKey(Category, on_delete=models.CASCADE)
    loc_id = models.ForeignKey(Location, on_delete=models.CASCADE)
    startup_name = models.CharField(max_length=50)
    creation_date = models.DateField()
    phone = models.BigIntegerField()
    website_url = models.URLField(max_length=100, blank=False, null=False)
    startup_email = models.EmailField(unique=True)
    amount_to_raise = models.FloatField()
    equity_offer = models.FloatField()
    funding_goal = models.TextField()
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    def __str__(self):
        return self.startup_name
    
class Document(models.Model):
    user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
    startup_id = models.ForeignKey(Startup, on_delete=models.CASCADE)
    financial_statements = models.FileField(upload_to="startup_documents/financial_statements", max_length=200)
    business_plan = models.FileField(upload_to="startup_documents/business_plan", max_length=200)
    pitch_deck = models.FileField(upload_to="startup_documents/pitch_deck", max_length=200)


class ProjectDetails(models.Model):
    STATUS = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('funded', 'Funded')
    ]
    user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
    startup_id = models.ForeignKey(Startup, on_delete=models.CASCADE)
    title = models.CharField(max_length=30)
    description = models.TextField()
    image_url = models.ImageField(upload_to="photos/ProjectPhoto")
    campaign_start_date = models.DateField()
    campaign_end_date = models.DateField()
    minimum_investment = models.FloatField()
    maximum_investment = models.FloatField()
    status = models.CharField(max_length=10, choices=STATUS, default="active")

    def project_image(self):
        return mark_safe('<img src="{}" width="100"/>'.format(self.image_url.url))

    project_image.allow_tags = True

    def __str__(self):
        return self.title

class UpdateDetails(models.Model):
    user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
    project_id = models.ForeignKey(ProjectDetails, on_delete=models.CASCADE)
    content = models.TextField()
    update_date = models.DateField(auto_now_add=True)
    update_time = models.TimeField(auto_now_add=True)
    title = models.CharField(max_length=30)

class FAQ(models.Model):
    user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
    project_id = models.ForeignKey(ProjectDetails, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()

class Wishlist(models.Model):
    user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
    project_id = models.ForeignKey(ProjectDetails, on_delete=models.CASCADE)
    status = models.IntegerField(default=1)  # 0 - remove from wishlist, 1 - in the wishlist

class Feedback(models.Model):
    user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
    project_id = models.ForeignKey(ProjectDetails, on_delete=models.CASCADE)
    comment = models.TextField()
    rating = models.FloatField(default=0)
    date = models.DateTimeField(auto_now_add=True)

class Newsletter(models.Model):
    email = models.EmailField()

class Review(models.Model):
    user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
    review = models.TextField()
    rating = models.FloatField(default=0)
    date = models.DateTimeField(auto_now_add=True)

class Contact(models.Model):
    name = models.CharField(max_length=30)
    email = models.EmailField()
    phone = models.BigIntegerField()
    subject = models.CharField(max_length=50)
    message = models.TextField()

class Investment(models.Model):
    INVESTMENT_STATUS = [
        ('pending', 'Pending in Escrow'),
        ('released', 'Released to Entrepreneur'),
        ('refunded', 'Refunded to Investor'),
        ('failed', 'Payment Failed')
    ]
    
    user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
    project_id = models.ForeignKey(ProjectDetails, on_delete=models.CASCADE)
    pancard = models.CharField(max_length=10)
    amount = models.FloatField()
    equity_offered = models.FloatField()  # Expected equity at time of investment
    date = models.DateTimeField(auto_now_add=True)
    razorpay_order_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=INVESTMENT_STATUS, default='pending')
    terms_accepted = models.BooleanField(default=False)
    fund_total_amount = models.FloatField(null=True, blank=True)  # Total amount after platform fee deduction
    funds_released_date = models.DateTimeField(null=True, blank=True)
    refund_date = models.DateTimeField(null=True, blank=True)


# class EquityDistribution(models.Model):
#     investment_id = models.ForeignKey(Investment, on_delete=models.CASCADE, null=True) 
#     user_id = models.ForeignKey(Register, on_delete=models.CASCADE)
#     startup_id = models.ForeignKey(Startup, on_delete=models.CASCADE)
#     amount = models.FloatField()
#     equity_percentage = models.FloatField()
#     timestamp = models.DateTimeField(auto_now_add=True)
#     is_active = models.BooleanField(default=True)  # For future equity transfers

# class EscrowRelease(models.Model):
#     project_id = models.ForeignKey(ProjectDetails, on_delete=models.CASCADE)
#     total_amount = models.FloatField()
#     released_to_entrepreneur = models.BooleanField(default=False)
#     release_date = models.DateTimeField(null=True, blank=True)
#     admin_verified = models.BooleanField(default=False)