from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import User

@receiver(post_save, sender=User)
def send_approval_email(sender, instance, created, **kwargs):
    """
    Send approval email when a user is approved.
    Skip during superuser creation to prevent errors.
    """
    # Skip if this is a new user creation (handled in register view)
    if created:
        return
    
    # Check if is_approved was changed to True
    try:
        # Method 1: Compare with original if available
        original = User.objects.get(pk=instance.pk)
        if not original.is_approved and instance.is_approved:
            send_approval_notification(instance)
    except User.DoesNotExist:
        # Method 2: Check if is_approved is in update_fields
        update_fields = kwargs.get('update_fields') or []
        if 'is_approved' in update_fields and instance.is_approved:
            send_approval_notification(instance)

def send_approval_notification(user):
    """Helper function to send approval email"""
    send_mail(
        'Your Account Has Been Approved',
        f'Hello {user.username},\n\n'
        'Your account has been approved by the administrator.\n\n'
        'You can now log in to your account using your credentials.\n\n'
        'Thank you!',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True
    )