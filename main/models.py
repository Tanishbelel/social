from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class SocialAccount(models.Model):
    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('twitter', 'Twitter'),
        ('facebook', 'Facebook'),
        ('tiktok', 'TikTok'),
        ('linkedin', 'LinkedIn'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    username = models.CharField(max_length=100)
    access_token = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    followers_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'platform', 'username']
    
    def __str__(self):
        return f"{self.username} - {self.platform}"

class Post(models.Model):
    POST_TYPE_CHOICES = [
        ('reel', 'Reel'),
        ('carousel', 'Carousel'),
        ('static', 'Static Post'),
        ('story', 'Story'),
        ('video', 'Video'),
    ]
    
    account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE)
    post_id = models.CharField(max_length=200)
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES)
    caption = models.TextField(blank=True)
    url = models.URLField()
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    reach = models.IntegerField(default=0)
    engagement_rate = models.FloatField(default=0.0)
    posted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['account', 'post_id']
        ordering = ['-posted_at']
    
    def calculate_engagement_rate(self):
        if self.account.followers_count > 0:
            engagement = self.likes + self.comments + self.shares
            self.engagement_rate = (engagement / self.account.followers_count) * 100
        return self.engagement_rate

class PostAnalytics(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    hour_0 = models.IntegerField(default=0)
    hour_1 = models.IntegerField(default=0)
    hour_3 = models.IntegerField(default=0)
    hour_6 = models.IntegerField(default=0)
    hour_12 = models.IntegerField(default=0)
    hour_24 = models.IntegerField(default=0)
    hour_48 = models.IntegerField(default=0)
    hour_72 = models.IntegerField(default=0)
    sentiment_score = models.FloatField(default=0.0)
    viral_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

class Hashtag(models.Model):
    tag = models.CharField(max_length=100, unique=True)
    total_uses = models.IntegerField(default=0)
    avg_engagement = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

class PostHashtag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    hashtag = models.ForeignKey(Hashtag, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['post', 'hashtag']

class AIInsight(models.Model):
    INSIGHT_TYPE_CHOICES = [
        ('recommendation', 'Recommendation'),
        ('warning', 'Warning'),
        ('opportunity', 'Opportunity'),
        ('trend', 'Trend'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.IntegerField(default=1)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']

class BestTimeToPost(models.Model):
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    hour = models.IntegerField()
    avg_engagement = models.FloatField()
    post_count = models.IntegerField()
    
    class Meta:
        unique_together = ['account', 'day_of_week', 'hour']

class CompetitorAnalysis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    competitor_username = models.CharField(max_length=100)
    platform = models.CharField(max_length=20)
    followers = models.IntegerField()
    avg_engagement_rate = models.FloatField()
    posting_frequency = models.FloatField()
    top_content_type = models.CharField(max_length=50)
    analyzed_at = models.DateTimeField(auto_now=True)

class QueryLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.TextField()
    response = models.TextField()
    execution_time = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)