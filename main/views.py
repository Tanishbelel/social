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
    accounts = SocialAccount.objects.filter(user=request.user)
    
    total_followers = accounts.aggregate(total=Sum('followers_count'))['total'] or 0
    
    all_posts = Post.objects.filter(account__user=request.user)
    total_posts = all_posts.count()
    
    total_engagement = all_posts.aggregate(
        likes=Sum('likes'),
        comments=Sum('comments'),
        shares=Sum('shares'),
        views=Sum('views')
    )
    
    avg_engagement_rate = all_posts.aggregate(avg=Avg('engagement_rate'))['avg'] or 0
    
    recent_posts = all_posts.order_by('-posted_at')[:10]
    
    top_posts = all_posts.order_by('-engagement_rate')[:5]
    
    platform_stats = accounts.values('platform').annotate(
        count=Count('id'),
        followers=Sum('followers_count')
    )
    
    post_type_performance = all_posts.values('post_type').annotate(
        count=Count('id'),
        avg_engagement=Avg('engagement_rate'),
        total_likes=Sum('likes')
    ).order_by('-avg_engagement')
    
    insights = AIInsight.objects.filter(user=request.user, is_read=False)[:5]
    
    last_7_days = timezone.now() - timedelta(days=7)
    weekly_posts = all_posts.filter(posted_at__gte=last_7_days)
    
    daily_engagement = []
    for i in range(7):
        day = timezone.now() - timedelta(days=i)
        day_posts = weekly_posts.filter(posted_at__date=day.date())
        daily_engagement.append({
            'date': day.strftime('%Y-%m-%d'),
            'engagement': day_posts.aggregate(total=Sum('likes'))['total'] or 0
        })
    
    context = {
        'accounts': accounts,
        'total_followers': total_followers,
        'total_posts': total_posts,
        'total_likes': total_engagement['likes'] or 0,
        'total_comments': total_engagement['comments'] or 0,
        'total_shares': total_engagement['shares'] or 0,
        'total_views': total_engagement['views'] or 0,
        'avg_engagement_rate': round(avg_engagement_rate, 2),
        'recent_posts': recent_posts,
        'top_posts': top_posts,
        'platform_stats': platform_stats,
        'post_type_performance': post_type_performance,
        'insights': insights,
        'daily_engagement': json.dumps(daily_engagement[::-1]),
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def add_account(request):
    if request.method == 'POST':
        platform = request.POST.get('platform')
        username = request.POST.get('username')
        
        account, created = SocialAccount.objects.get_or_create(
            user=request.user,
            platform=platform,
            username=username,
            defaults={'followers_count': random.randint(1000, 50000)}
        )
        
        if created:
            generate_sample_posts(account)
        
        return redirect('dashboard')
    
    return render(request, 'add_account.html')

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