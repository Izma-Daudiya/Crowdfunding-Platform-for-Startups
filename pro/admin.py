from django.contrib import admin
from .models import *


# Register your models here.
class showRegisterData(admin.ModelAdmin):
    list_display = ["username", "email", "phone", "password"]

class showLocation(admin.ModelAdmin):
    list_display = ["location"]

class showUserDetails(admin.ModelAdmin):
    list_display = ["user_id", "loc_id", "user_photo", "linkedin_url", "dob", "aadhar_photo", "role", "experience","status"]
    list_editable = ["status"]

class showCategory(admin.ModelAdmin):
    list_display = ["category"]

class showStartup(admin.ModelAdmin):
    list_display = ["user_id", "cat_id", "loc_id", "startup_name", "creation_date", "phone", "website_url",
                    "startup_email", "amount_to_raise", "equity_offer", "funding_goal", "description","status"]
    list_editable = ["status"]

class showDocuments(admin.ModelAdmin):
    list_display = ["user_id", "startup_id", "financial_statements", "business_plan", "pitch_deck"]

class showProjectDetails(admin.ModelAdmin):
    list_display = ["user_id", "startup_id", "title", "description", "image_url", "campaign_start_date",
                    "campaign_end_date", "minimum_investment", "maximum_investment", "status"]
    list_editable = ["status"]
    

class showUpdate(admin.ModelAdmin):
    list_display = ["user_id", "project_id", "title", "content", "update_date", "update_time"]

class showFAQ(admin.ModelAdmin):
    list_display = ["user_id", "project_id", "question", "answer"]

class showFeedback(admin.ModelAdmin):
    list_display = ["user_id", "project_id", "comment","rating", "date"]

class showNewsletter(admin.ModelAdmin):
    list_display = ["email"]

class showReview(admin.ModelAdmin):
    list_display = ["user_id", "review", "rating", "date"]

class showContact(admin.ModelAdmin):
    list_display = ["name", "email", "phone", "subject", "message"]

class showInvestment(admin.ModelAdmin):
    # list_display = ["user_id", "project_id", "pancard", "amount", "equity_offered", "date", "razorpay_order_id", "status", "terms_accepted", "funds_released_date", "refund_date"]
    list_display = ('user_id', 'project_id', 'amount', 'equity_offered', 'status', 'date', "funds_released_date", "fund_total_amount","refund_date")
    list_filter = ('status',)
    list_editable = ('status',)
    search_fields = ('user_id__username', 'project_id__title')

# class showEquityDistribution(admin.ModelAdmin):
#     # list_display = ["user_id", "investment_id", "startup_id", "amount", "equity_percentage", "timestamp", "is_active"]
#     list_display = ('user_id', 'startup_id', 'amount', 'equity_percentage', 'is_active')
#     list_filter = ('is_active',)
#     search_fields = ('user_id__username', 'startup_id__startup_name')

# class showEscrowRelease(admin.ModelAdmin):
    # list_display = ('project_id', 'total_amount', 'released_to_entrepreneur', 'release_date', 'admin_verified')
    # list_filter = ('released_to_entrepreneur', 'admin_verified')
    # actions = ['mark_verified', 'release_funds']
    
    # def mark_verified(self, request, queryset):
    #     queryset.update(admin_verified=True)
    # mark_verified.short_description = "Mark selected escrows as verified"
    
    # def release_funds(self, request, queryset):
    #     for escrow in queryset:
    #         if escrow.admin_verified and not escrow.released_to_entrepreneur:
    #             escrow.released_to_entrepreneur = True
    #             escrow.release_date = timezone.now()
    #             escrow.save()
                
    #             # Update all associated investments
    #             investments = Investment.objects.filter(
    #                 project_id=escrow.project_id, 
    #                 status='pending'
    #             )
                
    #             for investment in investments:
    #                 investment.status = 'released'
    #                 investment.funds_released_date = timezone.now()
    #                 investment.save()
    # release_funds.short_description = "Release funds to entrepreneurs"


admin.site.register(Register, showRegisterData)
admin.site.register(Location, showLocation)
admin.site.register(UserDetails, showUserDetails)
admin.site.register(Category, showCategory)
admin.site.register(Startup, showStartup)
admin.site.register(Document, showDocuments)
admin.site.register(ProjectDetails, showProjectDetails)
admin.site.register(UpdateDetails, showUpdate)
admin.site.register(FAQ, showFAQ)
admin.site.register(Feedback, showFeedback)
admin.site.register(Newsletter, showNewsletter)
admin.site.register(Review, showReview)
admin.site.register(Contact, showContact)
admin.site.register(Investment, showInvestment)
# admin.site.register(EquityDistribution, showEquityDistribution)
# admin.site.register(EscrowRelease, showEscrowRelease)
