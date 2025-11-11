from django.db import models
from restaurants.models import Restaurant

# Create your models here.

STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('resolved', 'Resolved'),
    ]


class Support(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    issue = models.CharField(max_length=255)  
    issue_details = models.TextField()       
    uploaded_file = models.FileField(upload_to='media/support_files/', null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.issue
