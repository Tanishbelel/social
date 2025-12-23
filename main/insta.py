import instaloader
from django.utils import timezone
from .models import SocialAccount, Post

def sync_public_instagram_account(username, user):
    from instaloader import Instaloader, Profile
    from django.utils import timezone

    L = Instaloader()
    
    try:
        profile = Profile.from_username(L.context, username)
    except Exception as e:
        print(f"Error fetching profile: {e}")
        return None

    account, _ = SocialAccount.objects.update_or_create(
        user=user,
        platform="instagram",
        username=username,
        defaults={
            "followers_count": profile.followers,
            "following_count": profile.followees,
            "posts_count": profile.mediacount,
            "last_synced": timezone.now(),
            "is_active": True
        }
    )

    # Fetch posts (limit to recent 50 for performance)
    post_count = 0
    for post in profile.get_posts():
        if post_count >= 50:  # Limit to avoid long sync times
            break
            
        try:
            # Determine post type based on your model choices
            if post.is_video:
                # Check if it's a reel or regular video
                if hasattr(post, 'is_reel') and post.is_reel:
                    post_type = "reel"
                else:
                    post_type = "video"
            elif post.mediacount > 1:
                post_type = "carousel"
            else:
                post_type = "photo"  # Changed from "static" to "photo"
            
            # Get thumbnail URL
            thumbnail_url = post.url
            
            Post.objects.update_or_create(
                account=account,
                post_id=post.shortcode,
                defaults={
                    "caption": post.caption or "",
                    "likes": post.likes,
                    "comments": post.comments,
                    "views": post.video_view_count or 0,
                    "shares": 0,
                    "reach": post.likes + post.comments,
                    "post_type": post_type,
                    "url": f"https://www.instagram.com/p/{post.shortcode}/",
                    "thumbnail_url": thumbnail_url,  # Save thumbnail URL
                    "posted_at": post.date_utc,
                    "engagement_rate": round(
                        ((post.likes + post.comments) / max(profile.followers, 1)) * 100,
                        2
                    ),
                }
            )
            post_count += 1
            
        except Exception as e:
            print(f"Error processing post {post.shortcode}: {e}")
            continue

    print(f"✅ Synced {post_count} posts for @{username}")
    return account