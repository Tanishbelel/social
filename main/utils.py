import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Avg, Sum, Count
from .models import *
import re

def generate_sample_posts(account, count=30):
    post_types = ['reel', 'carousel', 'static', 'story', 'video']
    
    captions = [
        "Check out this amazing content! #viral #trending",
        "New day, new opportunities! 🚀 #motivation",
        "Behind the scenes of our latest project",
        "Throwback to better times 📸 #memories",
        "Product launch coming soon! Stay tuned",
        "Tips and tricks you need to know",
        "Collaborating with amazing people",
        "Sunday vibes ✨ #weekend",
        "The secret to success is... #business",
        "Transform your life in 30 days"
    ]
    
    for i in range(count):
        days_ago = random.randint(0, 90)
        posted_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        likes = random.randint(100, 10000)
        comments = random.randint(10, 500)
        shares = random.randint(5, 200)
        views = likes * random.randint(3, 10)
        reach = int(views * 0.8)
        
        post = Post.objects.create(
            account=account,
            post_id=f"{account.platform}_{account.username}_{i}_{int(time.time())}",
            post_type=random.choice(post_types),
            caption=random.choice(captions),
            url=f"https://{account.platform}.com/{account.username}/post/{i}",
            likes=likes,
            comments=comments,
            shares=shares,
            views=views,
            reach=reach,
            posted_at=posted_at
        )
        
        post.calculate_engagement_rate()
        post.save()
        
        hashtags = re.findall(r'#(\w+)', post.caption)
        for tag in hashtags:
            hashtag, created = Hashtag.objects.get_or_create(tag=tag)
            hashtag.total_uses += 1
            hashtag.save()
            PostHashtag.objects.get_or_create(post=post, hashtag=hashtag)
        
        PostAnalytics.objects.create(
            post=post,
            hour_0=int(likes * 0.1),
            hour_1=int(likes * 0.2),
            hour_3=int(likes * 0.4),
            hour_6=int(likes * 0.6),
            hour_12=int(likes * 0.8),
            hour_24=likes,
            hour_48=int(likes * 1.1),
            hour_72=int(likes * 1.15),
            sentiment_score=random.uniform(0.5, 1.0),
            viral_score=random.uniform(30, 95)
        )

import time

def process_natural_language_query(user, query):
    query_lower = query.lower()
    
    posts = Post.objects.filter(account__user=user)
    
    if 'best' in query_lower and 'post' in query_lower:
        top_post = posts.order_by('-engagement_rate').first()
        if top_post:
            return f"Your best performing post was on {top_post.account.platform} with {top_post.engagement_rate:.2f}% engagement rate. It received {top_post.likes} likes, {top_post.comments} comments, and {top_post.shares} shares. Posted on {top_post.posted_at.strftime('%B %d, %Y')}."
        return "No posts found."
    
    if 'worst' in query_lower and 'post' in query_lower:
        worst_post = posts.order_by('engagement_rate').first()
        if worst_post:
            return f"Your lowest performing post was on {worst_post.account.platform} with {worst_post.engagement_rate:.2f}% engagement rate. Consider analyzing what went wrong - was it the timing, content type, or hashtags?"
        return "No posts found."
    
    if 'engagement' in query_lower and 'rate' in query_lower:
        avg_engagement = posts.aggregate(avg=Avg('engagement_rate'))['avg']
        if avg_engagement:
            return f"Your average engagement rate across all posts is {avg_engagement:.2f}%. Industry average is typically 3-6%, so you're {'performing well!' if avg_engagement > 4 else 'below average. Consider improving your content strategy.'}"
        return "No engagement data available."
    
    if 'total' in query_lower and 'likes' in query_lower:
        total_likes = posts.aggregate(total=Sum('likes'))['total'] or 0
        return f"You have received a total of {total_likes:,} likes across all your posts! Keep up the great work."
    
    if 'last' in query_lower and ('month' in query_lower or 'week' in query_lower):
        if 'month' in query_lower:
            date_threshold = timezone.now() - timedelta(days=30)
            period = "last month"
        else:
            date_threshold = timezone.now() - timedelta(days=7)
            period = "last week"
        
        recent_posts = posts.filter(posted_at__gte=date_threshold)
        count = recent_posts.count()
        total_engagement = recent_posts.aggregate(
            likes=Sum('likes'),
            comments=Sum('comments'),
            shares=Sum('shares')
        )
        return f"In the {period}, you posted {count} times with {total_engagement['likes']} likes, {total_engagement['comments']} comments, and {total_engagement['shares']} shares."
    
    if 'reel' in query_lower or 'carousel' in query_lower or 'static' in query_lower:
        post_type = 'reel' if 'reel' in query_lower else 'carousel' if 'carousel' in query_lower else 'static'
        type_posts = posts.filter(post_type=post_type)
        avg_eng = type_posts.aggregate(avg=Avg('engagement_rate'))['avg']
        count = type_posts.count()
        if avg_eng:
            return f"Your {post_type} posts have an average engagement rate of {avg_eng:.2f}% across {count} posts. {'Reels' if post_type == 'reel' else 'Carousels' if post_type == 'carousel' else 'Static posts'} are {'performing excellently!' if avg_eng > 5 else 'performing average.'}"
        return f"No {post_type} posts found."
    
    if 'hashtag' in query_lower:
        top_hashtags = Hashtag.objects.filter(
            posthashtag__post__account__user=user
        ).annotate(
            uses=Count('posthashtag'),
            avg_eng=Avg('posthashtag__post__engagement_rate')
        ).order_by('-avg_eng')[:3]
        
        if top_hashtags:
            result = "Your top performing hashtags are: "
            for ht in top_hashtags:
                result += f"#{ht.tag} ({ht.avg_eng:.2f}% avg engagement), "
            return result[:-2]
        return "No hashtag data available."
    
    if 'when' in query_lower and 'post' in query_lower:
        hourly_performance = {}
        for post in posts:
            hour = post.posted_at.hour
            if hour not in hourly_performance:
                hourly_performance[hour] = []
            hourly_performance[hour].append(post.engagement_rate)
        
        best_hour = max(hourly_performance.items(), key=lambda x: sum(x[1])/len(x[1]))
        return f"Based on your historical data, the best time to post is around {best_hour[0]:02d}:00 hours with an average engagement rate of {sum(best_hour[1])/len(best_hour[1]):.2f}%."
    
    if 'instagram' in query_lower or 'twitter' in query_lower or 'facebook' in query_lower:
        platform = 'instagram' if 'instagram' in query_lower else 'twitter' if 'twitter' in query_lower else 'facebook'
        platform_posts = posts.filter(account__platform=platform)
        stats = platform_posts.aggregate(
            count=Count('id'),
            avg_eng=Avg('engagement_rate'),
            total_likes=Sum('likes')
        )
        if stats['count']:
            return f"On {platform.capitalize()}, you have {stats['count']} posts with an average engagement rate of {stats['avg_eng']:.2f}% and {stats['total_likes']:,} total likes."
        return f"No posts found on {platform.capitalize()}."
    
    return "I analyzed your query but need more specific information. Try asking about: 'best post', 'engagement rate', 'total likes', 'last week performance', 'reel vs carousel', 'best hashtags', or 'when to post'."

def generate_ai_insights(user):
    posts = Post.objects.filter(account__user=user)
    
    if not posts.exists():
        return
    
    AIInsight.objects.filter(user=user, is_read=False).delete()
    
    avg_engagement = posts.aggregate(avg=Avg('engagement_rate'))['avg']
    if avg_engagement and avg_engagement < 3:
        AIInsight.objects.create(
            user=user,
            insight_type='warning',
            title='Low Engagement Rate Detected',
            description=f'Your average engagement rate is {avg_engagement:.2f}%, which is below the industry standard of 3-6%. Consider experimenting with different content types, posting times, and hashtags.',
            priority=5
        )
    
    post_type_performance = posts.values('post_type').annotate(
        avg_eng=Avg('engagement_rate'),
        count=Count('id')
    ).order_by('-avg_eng')
    
    if len(post_type_performance) > 1:
        best_type = post_type_performance[0]
        AIInsight.objects.create(
            user=user,
            insight_type='recommendation',
            title=f'{best_type["post_type"].title()}s Are Your Best Performers',
            description=f'Your {best_type["post_type"]} posts have {best_type["avg_eng"]:.2f}% average engagement rate. Consider creating more {best_type["post_type"]} content to maximize reach.',
            priority=4
        )
    
    recent_posts = posts.filter(posted_at__gte=timezone.now() - timedelta(days=7))
    if recent_posts.count() < 3:
        AIInsight.objects.create(
            user=user,
            insight_type='opportunity',
            title='Posting Frequency Is Low',
            description='You have posted less than 3 times in the last week. Consistent posting (3-5 times per week) can significantly improve your reach and engagement.',
            priority=3
        )
    
    top_posts = posts.order_by('-engagement_rate')[:5]
    common_hashtags = {}
    for post in top_posts:
        tags = re.findall(r'#(\w+)', post.caption)
        for tag in tags:
            common_hashtags[tag] = common_hashtags.get(tag, 0) + 1
    
    if common_hashtags:
        top_tag = max(common_hashtags.items(), key=lambda x: x[1])
        AIInsight.objects.create(
            user=user,
            insight_type='trend',
            title=f'#{top_tag[0]} Is Your Top Hashtag',
            description=f'The hashtag #{top_tag[0]} appears in {top_tag[1]} of your top performing posts. Continue using this hashtag and explore related tags.',
            priority=2
        )

def calculate_best_posting_times(account):
    posts = Post.objects.filter(account=account)
    
    hourly_performance = {}
    for hour in range(24):
        hour_posts = posts.filter(posted_at__hour=hour)
        if hour_posts.exists():
            avg_eng = hour_posts.aggregate(avg=Avg('engagement_rate'))['avg']
            hourly_performance[hour] = avg_eng
    
    sorted_hours = sorted(hourly_performance.items(), key=lambda x: x[1], reverse=True)
    
    return sorted_hours[:5]

def generate_posting_heatmap(user):
    posts = Post.objects.filter(account__user=user)
    
    heatmap = []
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    for day_num in range(7):
        day_data = {'day': days[day_num], 'hours': []}
        for hour in range(24):
            hour_posts = posts.filter(
                posted_at__week_day=day_num+2 if day_num < 6 else 1,
                posted_at__hour=hour
            )
            avg_eng = hour_posts.aggregate(avg=Avg('engagement_rate'))['avg'] or 0
            day_data['hours'].append(round(avg_eng, 2))
        heatmap.append(day_data)
    
    return heatmap

def analyze_competitor(user, username, platform):
    analysis, created = CompetitorAnalysis.objects.get_or_create(
        user=user,
        competitor_username=username,
        platform=platform,
        defaults={
            'followers': random.randint(5000, 100000),
            'avg_engagement_rate': random.uniform(2.5, 8.0),
            'posting_frequency': random.uniform(3, 15),
            'top_content_type': random.choice(['reel', 'carousel', 'static'])
        }
    )
    
    if not created:
        analysis.followers = random.randint(5000, 100000)
        analysis.avg_engagement_rate = random.uniform(2.5, 8.0)
        analysis.posting_frequency = random.uniform(3, 15)
        analysis.save()
    
    user_posts = Post.objects.filter(account__user=user, account__platform=platform)
    user_avg_eng = user_posts.aggregate(avg=Avg('engagement_rate'))['avg'] or 0
    
    comparison = {
        'competitor': username,
        'competitor_followers': analysis.followers,
        'competitor_engagement': round(analysis.avg_engagement_rate, 2),
        'competitor_frequency': round(analysis.posting_frequency, 1),
        'your_engagement': round(user_avg_eng, 2),
        'performance': 'Better' if user_avg_eng > analysis.avg_engagement_rate else 'Worse',
        'recommendation': f"{'Great job! You are outperforming this competitor.' if user_avg_eng > analysis.avg_engagement_rate else 'Focus on improving content quality and posting frequency to match competitor performance.'}"
    }
    
    return comparison

def calculate_viral_score(post):
    score = 0
    
    if post.likes > 1000:
        score += 30
    elif post.likes > 500:
        score += 20
    elif post.likes > 100:
        score += 10
    
    if post.engagement_rate > 8:
        score += 25
    elif post.engagement_rate > 5:
        score += 15
    elif post.engagement_rate > 3:
        score += 10
    
    if post.shares > 100:
        score += 20
    elif post.shares > 50:
        score += 15
    elif post.shares > 20:
        score += 10
    
    if post.comments > 100:
        score += 15
    elif post.comments > 50:
        score += 10
    elif post.comments > 20:
        score += 5
    
    time_diff = timezone.now() - post.posted_at
    if time_diff.days < 1:
        score += 10
    
    return min(score, 100)