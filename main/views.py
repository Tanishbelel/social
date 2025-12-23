from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Avg, Count, Q, F
from django.utils import timezone
from datetime import timedelta, datetime
import json
import random
import time
import csv
from .models import *
from .utils import *
from .insta import sync_public_instagram_account

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists'})
        
        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect('dashboard')
    
    return render(request, 'register.html')

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'login.html')

def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    selected_account_id = request.session.get('selected_account_id')
    
    if selected_account_id:
        account = SocialAccount.objects.filter(
            id=selected_account_id,
            user=request.user,
            is_active=True
        ).first()
    else:
        account = SocialAccount.objects.filter(
            user=request.user,
            is_active=True
        ).order_by("-created_at").first()
    
    if not account:
        return render(request, "dashboard.html", {
            "no_account": True
        })
    
    request.session['selected_account_id'] = account.id
    
    if account.platform == "instagram":
        post_count = Post.objects.filter(account=account).count()
        if post_count == 0:
            try:
                sync_public_instagram_account(
                    username=account.username,
                    user=request.user
                )
            except Exception as e:
                print(f"❌ Instagram sync error: {e}")
    
    if account.platform == "instagram":
        all_posts = Post.objects.filter(
            account=account
        ).exclude(
            post_type='story'
        ).filter(
            post_id__isnull=False,
            post_id__regex=r'^[A-Za-z0-9_-]{10,12}$'
        )
    else:
        all_posts = Post.objects.filter(
            account=account
        ).exclude(post_type='story')
    
    total_followers = account.followers_count or 0
    total_posts = all_posts.count()
    total_likes = all_posts.aggregate(Sum("likes"))["likes__sum"] or 0
    total_comments = all_posts.aggregate(Sum("comments"))["comments__sum"] or 0
    total_views = all_posts.aggregate(Sum("views"))["views__sum"] or 0
    avg_engagement_rate = all_posts.aggregate(Avg("engagement_rate"))["engagement_rate__avg"] or 0
    
    top_posts = all_posts.order_by("-engagement_rate")[:5]
    
    platform_stats = SocialAccount.objects.filter(
        user=request.user,
        is_active=True
    ).values('platform').annotate(
        count=Count('id'),
        followers=Sum('followers_count')
    ).order_by('-followers')
    
    post_type_performance = all_posts.values('post_type').annotate(
        count=Count('id'),
        avg_engagement=Avg('engagement_rate'),
        total_likes=Sum('likes')
    ).order_by('-avg_engagement')
    
    daily_engagement = []
    for i in range(6, -1, -1):
        day = timezone.now() - timedelta(days=i)
        day_posts = all_posts.filter(posted_at__date=day.date())
        
        daily_engagement.append({
            "date": day.strftime("%Y-%m-%d"),
            "engagement": (
                (day_posts.aggregate(Sum("likes"))["likes__sum"] or 0) +
                (day_posts.aggregate(Sum("comments"))["comments__sum"] or 0)
            )
        })
    
    all_accounts = SocialAccount.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-created_at')
    
    all_posts_display = all_posts.order_by('-posted_at')
    
    context = {
        "account": account,
        "all_accounts": all_accounts,
        "total_followers": total_followers,
        "total_posts": total_posts,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_views": total_views,
        "avg_engagement_rate": round(avg_engagement_rate, 2),
        "top_posts": top_posts,
        "platform_stats": platform_stats,
        "post_type_performance": post_type_performance,
        "daily_engagement": json.dumps(daily_engagement),
        "all_posts": all_posts_display,
        "insights": [],
    }
    
    return render(request, "dashboard.html", context)


@login_required
def switch_account(request, account_id):
    account = SocialAccount.objects.filter(
        id=account_id,
        user=request.user,
        is_active=True
    ).first()
    
    if account:
        request.session['selected_account_id'] = account.id
    
    return redirect('dashboard')


@login_required
def add_account(request):
    if request.method == 'POST':
        platform = request.POST.get('platform', '').lower()
        username = request.POST.get('username', '').strip()
        
        if not platform or not username:
            return render(request, 'add_account.html', {
                'error': 'Please provide both platform and username.',
                'platforms': ['instagram', 'twitter', 'facebook', 'youtube', 'tiktok']
            })
        
        existing = SocialAccount.objects.filter(
            user=request.user,
            platform=platform,
            username=username
        ).first()
        
        if existing:
            return render(request, 'add_account.html', {
                'error': f'Account @{username} on {platform} is already connected.',
                'platforms': ['instagram', 'twitter', 'facebook', 'youtube', 'tiktok']
            })
        
        account = SocialAccount.objects.create(
            user=request.user,
            platform=platform,
            username=username,
            followers_count=0,
            is_active=True
        )
        
        if platform == "instagram":
            try:
                synced_account = sync_public_instagram_account(
                    username=username,
                    user=request.user
                )
                
                if synced_account:
                    request.session['selected_account_id'] = synced_account.id
                    return render(request, 'add_account.html', {
                        'success': f'✅ Successfully synced @{username} from Instagram! Found {Post.objects.filter(account=synced_account).count()} posts.',
                        'platforms': ['instagram', 'twitter', 'facebook', 'youtube', 'tiktok']
                    })
                else:
                    account.delete()
                    return render(request, 'add_account.html', {
                        'error': f'❌ Could not find Instagram account @{username}. Make sure the account is public.',
                        'platforms': ['instagram', 'twitter', 'facebook', 'youtube', 'tiktok']
                    })
                    
            except Exception as e:
                account.delete()
                error_msg = str(e)
                if "login" in error_msg.lower() or "private" in error_msg.lower():
                    error_msg = f'Account @{username} is private or requires login. Please use a public Instagram account.'
                else:
                    error_msg = f'Error syncing @{username}: {error_msg}'
                
                return render(request, 'add_account.html', {
                    'error': f'❌ {error_msg}',
                    'platforms': ['instagram', 'twitter', 'facebook', 'youtube', 'tiktok']
                })
        else:
            account.followers_count = random.randint(1000, 50000)
            account.save()
            generate_sample_posts_for_platform(account)
            
            request.session['selected_account_id'] = account.id
            return render(request, 'add_account.html', {
                'success': f'✅ Successfully added @{username} on {platform.title()}!',
                'platforms': ['instagram', 'twitter', 'facebook', 'youtube', 'tiktok']
            })
    
    return render(request, 'add_account.html', {
        'platforms': ['instagram', 'twitter', 'facebook', 'youtube', 'tiktok']
    })


def generate_sample_posts_for_platform(account):
    if account.platform == "instagram":
        return
    
    post_types = ['photo', 'video', 'carousel']
    sample_captions = [
        "Check out our latest product! 🚀",
        "Behind the scenes content 🎬",
        "Thank you for all the support! ❤️",
        "New blog post is live! 📝",
        "Weekend vibes ✨",
        "Excited to announce... 🎉",
        "Throwback to this amazing moment 📸",
        "Stay tuned for more updates! 👀",
        "Loving this community! 🙌",
        "What's your favorite? Comment below! 💬"
    ]
    
    for i in range(15):
        Post.objects.create(
            account=account,
            post_id=f"{account.platform}_{account.id}_{i}_{random.randint(1000, 9999)}",
            post_type=random.choice(post_types),
            caption=random.choice(sample_captions),
            likes=random.randint(100, 10000),
            comments=random.randint(10, 500),
            shares=random.randint(5, 200),
            views=random.randint(1000, 50000) if random.choice([True, False]) else 0,
            engagement_rate=round(random.uniform(3, 15), 2),
            posted_at=timezone.now() - timedelta(days=random.randint(1, 60)),
            url=f"https://{account.platform}.com/p/{random.randint(100000, 999999)}"
        )


@login_required
def delete_account(request, account_id):
    account = SocialAccount.objects.filter(
        id=account_id,
        user=request.user
    ).first()
    
    if account:
        account.delete()
    
    return redirect('dashboard')

@login_required
def analytics(request):
    accounts = SocialAccount.objects.filter(user=request.user)
    all_posts = Post.objects.filter(account__user=request.user)
    
    platform_filter = request.GET.get('platform')
    post_type_filter = request.GET.get('post_type')
    date_range = request.GET.get('date_range', '30')
    
    filtered_posts = all_posts
    
    if platform_filter:
        filtered_posts = filtered_posts.filter(account__platform=platform_filter)
    
    if post_type_filter:
        filtered_posts = filtered_posts.filter(post_type=post_type_filter)
    
    date_threshold = timezone.now() - timedelta(days=int(date_range))
    filtered_posts = filtered_posts.filter(posted_at__gte=date_threshold)
    
    engagement_over_time = []
    days = int(date_range)
    for i in range(days):
        day = timezone.now() - timedelta(days=i)
        day_posts = filtered_posts.filter(posted_at__date=day.date())
        engagement_over_time.append({
            'date': day.strftime('%Y-%m-%d'),
            'likes': day_posts.aggregate(total=Sum('likes'))['total'] or 0,
            'comments': day_posts.aggregate(total=Sum('comments'))['total'] or 0,
            'shares': day_posts.aggregate(total=Sum('shares'))['total'] or 0,
        })
    
    post_type_comparison = filtered_posts.values('post_type').annotate(
        count=Count('id'),
        avg_likes=Avg('likes'),
        avg_comments=Avg('comments'),
        avg_shares=Avg('shares'),
        avg_engagement=Avg('engagement_rate')
    )
    
    top_hashtags = Hashtag.objects.filter(
        posthashtag__post__account__user=request.user
    ).annotate(
        uses=Count('posthashtag'),
        avg_eng=Avg('posthashtag__post__engagement_rate')
    ).order_by('-avg_eng')[:10]
    
    hourly_performance = []
    for hour in range(24):
        hour_posts = filtered_posts.filter(posted_at__hour=hour)
        hourly_performance.append({
            'hour': hour,
            'avg_engagement': hour_posts.aggregate(avg=Avg('engagement_rate'))['avg'] or 0,
            'count': hour_posts.count()
        })
    
    display_posts = filtered_posts.order_by('-posted_at')[:50]
    
    context = {
        'accounts': accounts,
        'posts': display_posts,
        'total_posts': filtered_posts.count(),
        'avg_engagement': filtered_posts.aggregate(avg=Avg('engagement_rate'))['avg'] or 0,
        'engagement_over_time': json.dumps(engagement_over_time[::-1]),
        'post_type_comparison': post_type_comparison,
        'top_hashtags': top_hashtags,
        'hourly_performance': json.dumps(hourly_performance),
        'selected_platform': platform_filter,
        'selected_post_type': post_type_filter,
        'selected_date_range': date_range,
    }
    
    return render(request, 'analytics.html', context)

@login_required
def ai_query(request):
    if request.method == 'POST':
        query = request.POST.get('query')
        start_time = time.time()
        
        response = process_natural_language_query(request.user, query)
        
        execution_time = time.time() - start_time
        
        QueryLog.objects.create(
            user=request.user,
            query=query,
            response=response,
            execution_time=execution_time
        )
        
        return JsonResponse({
            'response': response,
            'execution_time': round(execution_time, 2)
        })
    
    recent_queries = QueryLog.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    return render(request, 'ai_query.html', {'recent_queries': recent_queries})

@login_required
def insights(request):
    all_insights = AIInsight.objects.filter(user=request.user)
    
    if request.method == 'POST':
        insight_id = request.POST.get('insight_id')
        insight = get_object_or_404(AIInsight, id=insight_id, user=request.user)
        insight.is_read = True
        insight.save()
        return JsonResponse({'status': 'success'})
    
    generate_ai_insights(request.user)
    
    context = {
        'insights': all_insights,
        'unread_count': all_insights.filter(is_read=False).count(),
    }
    
    return render(request, 'insights.html', context)

@login_required
def best_time_to_post(request):
    accounts = SocialAccount.objects.filter(user=request.user)
    
    best_times = []
    for account in accounts:
        times = calculate_best_posting_times(account)
        best_times.append({
            'account': account,
            'times': times
        })
    
    heatmap_data = generate_posting_heatmap(request.user)
    
    context = {
        'best_times': best_times,
        'heatmap_data': json.dumps(heatmap_data),
    }
    
    return render(request, 'best_time.html', context)

@login_required
def competitor_analysis(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        platform = request.POST.get('platform')
        
        analysis = analyze_competitor(request.user, username, platform)
        
        return JsonResponse(analysis)
    
    competitors = CompetitorAnalysis.objects.filter(user=request.user).order_by('-analyzed_at')
    
    context = {
        'competitors': competitors,
    }
    
    return render(request, 'competitor.html', context)

@login_required
def viral_predictor(request):
    all_posts = Post.objects.filter(account__user=request.user).order_by('-posted_at')[:50]
    
    predictions = []
    for post in all_posts:
        viral_score = calculate_viral_score(post)
        predictions.append({
            'post': post,
            'viral_score': viral_score,
            'prediction': 'High' if viral_score > 75 else 'Medium' if viral_score > 50 else 'Low'
        })
    
    predictions.sort(key=lambda x: x['viral_score'], reverse=True)
    
    context = {
        'predictions': predictions[:20],
    }
    
    return render(request, 'viral_predictor.html', context)

@login_required
def export_report(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="social_analytics_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Post ID', 'Platform', 'Type', 'Likes', 'Comments', 'Shares', 'Engagement Rate', 'Posted At'])
    
    posts = Post.objects.filter(account__user=request.user).order_by('-posted_at')
    
    for post in posts:
        writer.writerow([
            post.post_id,
            post.account.platform,
            post.post_type,
            post.likes,
            post.comments,
            post.shares,
            f"{post.engagement_rate:.2f}%",
            post.posted_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    return response