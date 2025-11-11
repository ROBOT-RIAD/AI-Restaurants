from django.db import models
from django.contrib.auth.models import AbstractUser
from .constants import ROLE_CHOICES
import random
import os
from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError


SECRET_KEY = os.getenv('FERNET_KEY')
if not SECRET_KEY:
    raise ValueError("FERNET_KEY environment variable not set.")
fernet = Fernet(SECRET_KEY.encode())

# Create your models here.


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="Owner")
    approved = models.BooleanField(default=False)
    adminapproved = models.BooleanField(default=False)
    extrapassword = models.CharField(max_length=1000, blank=True, null=True)  # New field
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def clean(self):
        """Ensure that the extrapassword field is encrypted properly."""
        if self.extrapassword:
            if not self.extrapassword.strip():
                raise ValidationError("extrapassword cannot be empty.")
    
    def clean(self):
        if self.extrapassword and not self.extrapassword.strip():
            raise ValidationError("extrapassword cannot be empty.")

    def save(self, *args, **kwargs):
        if self.extrapassword and not self._is_encrypted(self.extrapassword):
            self.extrapassword = self.encrypt(self.extrapassword)
        self.clean()
        super().save(*args, **kwargs)

    def _is_encrypted(self, value):
        """Check if value is already encrypted."""
        try:
            fernet.decrypt(value.encode())
            return True
        except Exception:
            return False

    def encrypt(self, key):
        return fernet.encrypt(key.encode()).decode()

    def decrypt(self, key):
        return fernet.decrypt(key.encode()).decode()

    def get_decrypted_extrapassword(self):
        if self.extrapassword:
            try:
                return self.decrypt(self.extrapassword)
            except Exception:
                return None
        return None





class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User , on_delete=models.CASCADE)
    otp= models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def save(self,*args, **kwargs):
        if not self.otp:
            self.otp = str(random.randint(1000,9999))
        super().save(*args,**kwargs)

    def __str__(self):
       return f"{self.user.email} - {self.otp}" 

