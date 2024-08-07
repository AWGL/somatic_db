from django.db import models

class PanelManager(models.Manager):
    """
    Manager for the Panel class
    """
    def get_by_natural_key(self, panel_name, panel_version):
        return self.get(panel_name=panel_name, panel_version=panel_version)
    
class QCMessageManager(models.Manager):
    """
    Manager for the QCMessage class
    """
    def get_by_natural_key(self, message):
        return self.get(message=message)
    
class VEPAnnotationsClinvarClinsigManager(models.Manager):
    """
    Manager for the VEPAnnotationsClinvarClinsigManager class
    """
    def get_by_natural_key(self, clinvar_clinsig):
        return self.get(clinvar_clinsig=clinvar_clinsig)
    
class VEPAnnotationsClinvarClinsigConfManager(models.Manager):
    """
    Manager for the VEPAnnotationsClinvarClinsigManager class
    """
    def get_by_natural_key(self, clinvar_clinsig_conf):
        return self.get(clinvar_clinsig_conf=clinvar_clinsig_conf)
    
class VEPAnnotationsClinvar(models.Manager):
    """
    Manager for the VEPAnnotationsClinvar class
    """
    def get_by_natural_key(self, clinvar_id):
        return self.get(clinvar_id=clinvar_id)