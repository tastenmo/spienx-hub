from django.db import models
from django.contrib.auth.models import User


class Document(models.Model):
    title = models.CharField(max_length=255)
    
    source = models.ForeignKey('repositories.GitRepository', on_delete=models.CASCADE, related_name='documents')

    reference = models.CharField(max_length=255, help_text="Branch, tag, or commit hash")

    workdir = models.CharField(max_length=255, help_text="Path to the working directory in the repository")

    conf_path = models.CharField(max_length=255, help_text="Path to the configuration file in the repository")

    last_build_at = models.DateTimeField(auto_now=True)

    global_context = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-last_build_at']

    def __str__(self) -> str:
        return self.title
    
class Page(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='pages')
    
    current_page_name = models.CharField(max_length=255)

    title = models.CharField(max_length=255)
    
    context = models.JSONField(default=dict, blank=True)
        
    class Meta:
        unique_together = ('document', 'current_page_name')
        ordering = ['current_page_name']

    def __str__(self) -> str:
        return f"{self.document.title} - {self.current_page_name}"
    
class Section(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='sections')
    
    title = models.CharField(max_length=255)

    sphinx_id = models.CharField(max_length=255)

    hash = models.CharField(max_length=255)

    source_path = models.CharField(max_length=255)

    start_line = models.IntegerField()

    end_line = models.IntegerField()
    
    body = models.TextField()

    class Meta:
        unique_together = ('page', 'hash')

    def __str__(self) -> str:
        return f"{self.page.current_page_name} - {self.title}"
    

class StaticAsset(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='static_assets')
    
    path = models.CharField(max_length=255)

    hash = models.CharField(max_length=255)

    class Meta:
        unique_together = ('document', 'path')

    def __str__(self) -> str:
        return f"{self.document.title} - {self.path}"