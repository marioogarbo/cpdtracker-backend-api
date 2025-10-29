

class RenewalPeriodFormatter:
    """Utility class for formatting renewal periods."""
    
    @staticmethod
    def format_renewal_period(months):
        """
        Return human-readable renewal period.
        """
        if months == 1:
            return "Monthly"
        elif months == 2:
            return "Bi-Monthly"
        elif months == 3:
            return "Quarterly"
        elif months == 4:
            return "Every 4 Months"
        elif months == 6:
            return "Semi-Annual"
        elif months == 9:
            return "Every 9 Months"
        elif months == 12:
            return "Annual"
        elif months == 18:
            return "Every 18 Months"
        elif months == 24:
            return "Bi-Annual (Every 2 Years)"
        elif months == 36:
            return "Triennial (Every 3 Years)"
        elif months == 48:
            return "Every 4 Years"
        elif months == 60:
            return "Every 5 Years"
        else:
            # For custom periods
            if months < 12:
                return f"Every {months} Month{'s' if months != 1 else ''}"
            elif months % 12 == 0:
                years = months // 12
                return f"Every {years} Year{'s' if years != 1 else ''}"
            else:
                years = months // 12
                remaining_months = months % 12
                if years == 1:
                    return f"Every {years} Year and {remaining_months} Month{'s' if remaining_months != 1 else ''}"
                else:
                    return f"Every {years} Years and {remaining_months} Month{'s' if remaining_months != 1 else ''}"


class ValidationHelper:
    """Utility class for common validation operations."""
    
    @staticmethod
    def validate_future_date(date_value, current_date=None):
        """
        Validate that a date is not in the future.
        Returns (is_valid, error_message)
        """
        from django.utils import timezone
        
        if current_date is None:
            current_date = timezone.now().date()
        
        if date_value > current_date:
            return False, "Date cannot be in the future"
        
        return True, None
    
    @staticmethod
    def validate_date_format(date_string):
        """
        Validate date string format.
        Returns (is_valid, parsed_date, error_message)
        """
        try:
            from datetime import datetime
            parsed_date = datetime.strptime(date_string, '%Y-%m-%d').date()
            return True, parsed_date, None
        except ValueError:
            return False, None, "Invalid date format. Use YYYY-MM-DD format" 