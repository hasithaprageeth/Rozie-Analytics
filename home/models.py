from __future__ import unicode_literals

from django.db import models

"""
class Clusters(models.Model):
    cluster_id = models.CharField(primary_key=True, max_length=10)
    summary = models.CharField(max_length = 100, blank=True, null=True)
    tweet_rate = models.IntegerField(default=0)

class Tweets(models.Model):
    tweet_id = models.CharField(primary_key=True, max_length=50)
    preprocessed_text = models.CharField(max_length = 200, blank=True, null=True)
    full_text = models.CharField(max_length = 400, blank=True, null=True)
    created_at = models.CharField(max_length = 50, blank=True, null=True)    
    cluster_id = models.ForeignKey(Clusters, on_delete=models.CASCADE, blank=True, null=True)
    assignment_time = models.CharField(max_length = 50, blank=True, null=True)
    tweet = models.CharField(max_length=1000, blank=True, null=True)
"""