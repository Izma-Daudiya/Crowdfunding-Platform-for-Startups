def check_and_update_campaign_status(project_id):
    """
    Function to check campaign status and update investments accordingly.
    This should be called from views that show project details or handle investments.
    """
    from django.utils import timezone
    from django.db.models import Sum
    from pro.models import ProjectDetails, Investment
    
    try:
        # Get the project
        project = ProjectDetails.objects.get(id=project_id)
        
        # Calculate total investment amount
        investments = Investment.objects.filter(
            project_id=project_id, 
            status__in=['pending', 'released']
        )
        total_invested = investments.aggregate(total=Sum('amount'))['total'] or 0
        
        # Check if funding goal is met
        funding_goal = project.startup_id.amount_to_raise
        campaign_ended = project.campaign_end_date < timezone.now().date()
        
        if total_invested >= funding_goal:
            # Funding goal is met - mark as funded and release investments
            if project.status != 'funded':
                project.status = 'funded'
                project.save()
                
                # Release all pending investments
                pending_investments = Investment.objects.filter(
                    project_id=project_id,
                    status='pending'
                )

                for investment in pending_investments:
                    # Calculate 1% platform fee
                    platform_fee = investment.amount * 0.01
                    # Amount to be released is original amount minus fee
                    investment.fund_total_amount = investment.amount - platform_fee
                    investment.status = 'released'
                    investment.funds_released_date = timezone.now()
                    investment.save()
                
                return "Project funded successfully. Investments released."
        
        elif campaign_ended and project.status == 'active':
            # Campaign ended without meeting goal - mark as closed and refund
            project.status = 'closed'
            project.save()
            
            # Refund all pending investments
            pending_investments = Investment.objects.filter(
                project_id=project_id,
                status='pending'
            )
            
            for investment in pending_investments:
                investment.status = 'refunded'
                investment.refund_date = timezone.now()
                investment.save()
                # Here you would integrate with your payment gateway for actual refunds
                
            return "Campaign ended without reaching funding goal. Investments refunded."
        
        return "No status update needed."
    
    except ProjectDetails.DoesNotExist:
        return "Project not found"