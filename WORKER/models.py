from django.db import models
from django.utils import timezone
class ScheduledTaskLog(models.Model):
    task_name = models.CharField(max_length=255)
    status = models.CharField(max_length=50)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.task_name} - {self.status}"

    class Meta:
        verbose_name = "Task Execution Log"
        verbose_name_plural = "Task Execution Logs"