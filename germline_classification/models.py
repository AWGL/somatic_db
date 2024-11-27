from django.db import models
from auditlog.registry import auditlog

#todo criteria
#todo strength-criteria
#todo classification

class ClassificationCriteriaStrength(models.Model):
    """
    Strengths at which the ACMG/ACGS criteria can be applied at
    """
    id = models.AutoField(primary_key=True)
    strength = models.CharField(max_length=20)
    evidence_points = models.IntegerField()

    class Meta:
        unique_together = ["strength", "evidence_points"]

    def __str__(self):
        return f"{self.strength} {str(self.evidence_points)}"

class ClassificationCriteriaCode(models.Model):
    """
    Codes that can be applied in the ACMG/ACGS criteria
    """
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=10, unique=True)
    pathogenic_or_benign = models.CharField(max_length=1)
    description = models.TextField(null=True, blank=True)
    links = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.code

class ClassificationCriteria(models.Model):
    """
    All available combinations of codes and strengths
    """
    id = models.AutoField(primary_key=True)
    code = models.ForeignKey("ClassificationCriteriaCode", on_delete=models.CASCADE)
    strength = models.ForeignKey("ClassificationCriteriaStrength", on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ["code", "strength"]

class Classification(models.Model):
    """
    A classification of a single variant
    """
    id = models.AutoField(primary_key=True)
    #todo variant
    criteria_applied = models.ManyToManyField("ClassificationCriteria", related_name="criteria_applied")

