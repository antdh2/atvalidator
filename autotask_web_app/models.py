from django.db import models
from account.conf import settings

# Create your models here.

class Company(models.Model):
    name = models.CharField(max_length=254)
    password = models.CharField(max_length=254)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Profile(models.Model):
    first_name = models.CharField(max_length=254)
    last_name = models.CharField(max_length=254)
    email = models.EmailField(max_length=254)
    autotask_username = models.CharField(max_length=254)
    autotask_password = models.CharField(max_length=254)
    about = models.TextField()
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    atresource_id = models.CharField(max_length=254)
    company = models.ForeignKey(Company)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.first_name + " " + self.last_name

class Picklist(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    key = models.CharField(max_length=254)
    value = models.CharField(max_length=254)

    def __str__(self):
        return str(self.id) + ": " + self.company.name

class Entity(models.Model):
    name = models.CharField(max_length=254)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)

    def __str__(self):
        return self.name + ": " + self.profile.first_name + " " + self.profile.last_name

class ValidationGroup(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=254)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)

    def __str__(self):
        return self.company.name + ": " + self.name

class ValidationGroupRule(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    key = models.CharField(max_length=254)
    operator = models.CharField(max_length=254)
    picklist_number = models.IntegerField()
    value = models.CharField(max_length=254)
    validation_group = models.ForeignKey(ValidationGroup, on_delete=models.CASCADE)
    company = models.ForeignKey(Company)

    def __str__(self):
        return self.company.name + ": " + self.key + " " + self.operator + " " + self.value

class Validation(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    key = models.CharField(max_length=254)
    operator = models.CharField(max_length=254)
    picklist_number = models.IntegerField()
    value = models.CharField(max_length=254)
    validation_group = models.ForeignKey(ValidationGroup, on_delete=models.CASCADE)
    mandatory = models.BooleanField(default=True)

    def __str__(self):
        return "Validation #" + str(self.id) + " for group " + self.validation_group.name
