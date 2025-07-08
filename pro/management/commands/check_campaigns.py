# management/commands/check_campaigns.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from pro.models import ProjectDetails
from pro.views import check_campaign_status

class Command(BaseCommand):
    help = 'Check status of active campaigns and process accordingly'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Get all active campaigns that have reached end date
        ended_campaigns = ProjectDetails.objects.filter(
            status='active',
            campaign_end_date__lt=today
        )
        
        for campaign in ended_campaigns:
            self.stdout.write(f"Processing campaign: {campaign.title}")
            check_campaign_status(campaign.id)
            
        self.stdout.write(self.style.SUCCESS(f"Processed {ended_campaigns.count()} campaigns"))