"""
Engagement tracking and performance analytics
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import statistics

from loguru import logger

from ..utils.config import Config
from ..utils.file_handler import FileHandler


class EngagementTracker:
    """Tracks engagement metrics and analyzes performance patterns"""
    
    def __init__(self, config: Config):
        """Initialize engagement tracker"""
        self.config = config
        self.analytics_config = config.get_analytics_config()
        self.file_handler = FileHandler()
        
        # Data storage
        self.metrics_file = Path("analytics/engagement_metrics.json")
        self.performance_file = Path("analytics/performance_data.json")
        self.trends_file = Path("analytics/trends.json")
        
        # Ensure analytics directory exists
        Path("analytics").mkdir(exist_ok=True)
        
        # Load existing data
        self.metrics_data = self.file_handler.load_json(self.metrics_file) or {}
        self.performance_data = self.file_handler.load_json(self.performance_file) or {}
        
        # Tracking thresholds
        self.viral_threshold = self.analytics_config.get("viral_threshold_views", 10000)
        self.good_performance_ratio = self.analytics_config.get("good_performance_likes_ratio", 0.05)
        self.comment_engagement_ratio = self.analytics_config.get("comment_engagement_ratio", 0.02)
    
    async def track_post_performance(self, clip_data: Dict[str, Any], 
                                   platform_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Track performance of a posted clip
        
        Args:
            clip_data: Original clip metadata
            platform_results: Results from platform posting
            
        Returns:
            Performance tracking entry
        """
        try:
            clip_id = clip_data.get("clip_id")
            
            tracking_entry = {
                "clip_id": clip_id,
                "title": clip_data.get("title", ""),
                "emotion": clip_data.get("emotion", "neutral"),
                "engagement_score": clip_data.get("engagement_score", 0.0),
                "duration": clip_data.get("duration", 0),
                "posted_at": datetime.now().isoformat(),
                "platforms": platform_results,
                "metrics": {
                    "views": {},
                    "likes": {},
                    "comments": {},
                    "shares": {},
                    "saves": {}
                },
                "performance_score": 0.0,
                "is_viral": False,
                "last_updated": datetime.now().isoformat()
            }
            
            # Store in metrics data
            if clip_id not in self.metrics_data:
                self.metrics_data[clip_id] = tracking_entry
                await self._save_metrics()
            
            logger.info(f"📊 Started tracking performance for: {clip_id}")
            return tracking_entry
            
        except Exception as e:
            logger.error(f"❌ Error tracking post performance: {e}")
            return {}
    
    async def update_metrics(self, clip_id: str, platform: str, metrics: Dict[str, Any]):
        """Update metrics for a specific clip and platform"""
        try:
            if clip_id not in self.metrics_data:
                logger.warning(f"⚠️ Clip not found in tracking data: {clip_id}")
                return
            
            clip_metrics = self.metrics_data[clip_id]
            
            # Update platform-specific metrics
            for metric_type, value in metrics.items():
                if metric_type in clip_metrics["metrics"]:
                    clip_metrics["metrics"][metric_type][platform] = value
            
            # Update timestamp
            clip_metrics["last_updated"] = datetime.now().isoformat()
            
            # Calculate performance score
            clip_metrics["performance_score"] = await self._calculate_performance_score(clip_id)
            
            # Check if viral
            total_views = sum(clip_metrics["metrics"]["views"].values())
            clip_metrics["is_viral"] = total_views >= self.viral_threshold
            
            await self._save_metrics()
            logger.debug(f"📈 Updated metrics for {clip_id} on {platform}")
            
        except Exception as e:
            logger.error(f"❌ Error updating metrics: {e}")
    
    async def _calculate_performance_score(self, clip_id: str) -> float:
        """Calculate overall performance score for a clip"""
        try:
            clip_data = self.metrics_data.get(clip_id, {})
            metrics = clip_data.get("metrics", {})
            
            total_views = sum(metrics.get("views", {}).values())
            total_likes = sum(metrics.get("likes", {}).values())
            total_comments = sum(metrics.get("comments", {}).values())
            total_shares = sum(metrics.get("shares", {}).values())
            
            if total_views == 0:
                return 0.0
            
            # Calculate engagement ratios
            like_ratio = total_likes / total_views
            comment_ratio = total_comments / total_views
            share_ratio = total_shares / total_views
            
            # Weighted performance score
            score = (
                like_ratio * 40 +      # 40% weight on likes
                comment_ratio * 30 +   # 30% weight on comments
                share_ratio * 20 +     # 20% weight on shares
                min(total_views / self.viral_threshold, 1.0) * 10  # 10% weight on view count
            )
            
            return min(score * 100, 100)  # Scale to 0-100
            
        except Exception as e:
            logger.error(f"❌ Error calculating performance score: {e}")
            return 0.0
    
    async def analyze_trends(self) -> Dict[str, Any]:
        """Analyze performance trends and patterns"""
        try:
            logger.info("📊 Analyzing engagement trends...")
            
            if not self.metrics_data:
                return {"error": "No performance data available"}
            
            trends = {
                "emotion_performance": await self._analyze_emotion_trends(),
                "time_patterns": await self._analyze_time_patterns(),
                "platform_performance": await self._analyze_platform_performance(),
                "content_insights": await self._analyze_content_insights(),
                "recommendations": await self._generate_recommendations(),
                "last_analyzed": datetime.now().isoformat()
            }
            
            # Save trends
            self.file_handler.save_json(trends, self.trends_file)
            
            logger.success("✅ Trend analysis complete")
            return trends
            
        except Exception as e:
            logger.error(f"❌ Error analyzing trends: {e}")
            return {"error": str(e)}
    
    async def _analyze_emotion_trends(self) -> Dict[str, Any]:
        """Analyze which emotions perform best"""
        emotion_stats = {}
        
        for clip_data in self.metrics_data.values():
            emotion = clip_data.get("emotion", "neutral")
            performance_score = clip_data.get("performance_score", 0)
            
            if emotion not in emotion_stats:
                emotion_stats[emotion] = {
                    "count": 0,
                    "total_performance": 0,
                    "viral_count": 0,
                    "scores": []
                }
            
            emotion_stats[emotion]["count"] += 1
            emotion_stats[emotion]["total_performance"] += performance_score
            emotion_stats[emotion]["scores"].append(performance_score)
            
            if clip_data.get("is_viral", False):
                emotion_stats[emotion]["viral_count"] += 1
        
        # Calculate averages and statistics
        for emotion, stats in emotion_stats.items():
            if stats["count"] > 0:
                stats["average_performance"] = stats["total_performance"] / stats["count"]
                stats["viral_rate"] = stats["viral_count"] / stats["count"]
                stats["median_performance"] = statistics.median(stats["scores"])
                
                if len(stats["scores"]) > 1:
                    stats["performance_std"] = statistics.stdev(stats["scores"])
                else:
                    stats["performance_std"] = 0
        
        # Sort by average performance
        sorted_emotions = sorted(
            emotion_stats.items(),
            key=lambda x: x[1]["average_performance"],
            reverse=True
        )
        
        return {
            "best_emotion": sorted_emotions[0][0] if sorted_emotions else "neutral",
            "emotion_rankings": sorted_emotions,
            "emotion_stats": emotion_stats
        }
    
    async def _analyze_time_patterns(self) -> Dict[str, Any]:
        """Analyze when posts perform best"""
        time_performance = {}
        
        for clip_data in self.metrics_data.values():
            posted_at = clip_data.get("posted_at")
            if not posted_at:
                continue
            
            try:
                post_time = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
                hour = post_time.hour
                day_of_week = post_time.weekday()  # 0 = Monday
                
                performance_score = clip_data.get("performance_score", 0)
                
                # Hour analysis
                if hour not in time_performance:
                    time_performance[hour] = {"scores": [], "count": 0}
                time_performance[hour]["scores"].append(performance_score)
                time_performance[hour]["count"] += 1
                
            except Exception as e:
                logger.warning(f"⚠️ Error parsing post time: {e}")
        
        # Calculate hour averages
        hour_averages = {}
        for hour, data in time_performance.items():
            if data["count"] > 0:
                hour_averages[hour] = {
                    "average_performance": statistics.mean(data["scores"]),
                    "post_count": data["count"]
                }
        
        # Find best hours
        best_hours = sorted(
            hour_averages.items(),
            key=lambda x: x[1]["average_performance"],
            reverse=True
        )[:3]
        
        return {
            "best_hours": [hour for hour, _ in best_hours],
            "hour_performance": hour_averages,
            "recommendations": {
                "optimal_posting_times": [f"{hour:02d}:00" for hour, _ in best_hours]
            }
        }
    
    async def _analyze_platform_performance(self) -> Dict[str, Any]:
        """Analyze performance across platforms"""
        platform_stats = {}
        
        for clip_data in self.metrics_data.values():
            platforms = clip_data.get("platforms", {})
            performance_score = clip_data.get("performance_score", 0)
            
            for platform, result in platforms.items():
                if result.get("success"):
                    if platform not in platform_stats:
                        platform_stats[platform] = {
                            "successful_posts": 0,
                            "total_performance": 0,
                            "viral_count": 0,
                            "scores": []
                        }
                    
                    platform_stats[platform]["successful_posts"] += 1
                    platform_stats[platform]["total_performance"] += performance_score
                    platform_stats[platform]["scores"].append(performance_score)
                    
                    if clip_data.get("is_viral", False):
                        platform_stats[platform]["viral_count"] += 1
        
        # Calculate platform averages
        for platform, stats in platform_stats.items():
            if stats["successful_posts"] > 0:
                stats["average_performance"] = stats["total_performance"] / stats["successful_posts"]
                stats["viral_rate"] = stats["viral_count"] / stats["successful_posts"]
        
        # Sort platforms by performance
        sorted_platforms = sorted(
            platform_stats.items(),
            key=lambda x: x[1].get("average_performance", 0),
            reverse=True
        )
        
        return {
            "best_platform": sorted_platforms[0][0] if sorted_platforms else "unknown",
            "platform_rankings": sorted_platforms,
            "platform_stats": platform_stats
        }
    
    async def _analyze_content_insights(self) -> Dict[str, Any]:
        """Analyze content patterns that drive engagement"""
        insights = {
            "duration_analysis": {},
            "title_patterns": {},
            "viral_characteristics": {}
        }
        
        # Duration analysis
        duration_groups = {
            "short": (0, 30),
            "medium": (30, 45), 
            "long": (45, 65)
        }
        
        duration_performance = {}
        for group_name, (min_dur, max_dur) in duration_groups.items():
            matching_clips = [
                clip for clip in self.metrics_data.values()
                if min_dur <= clip.get("duration", 0) < max_dur
            ]
            
            if matching_clips:
                scores = [clip.get("performance_score", 0) for clip in matching_clips]
                duration_performance[group_name] = {
                    "count": len(matching_clips),
                    "average_performance": statistics.mean(scores),
                    "viral_count": sum(1 for clip in matching_clips if clip.get("is_viral", False))
                }
        
        insights["duration_analysis"] = duration_performance
        
        # Viral characteristics
        viral_clips = [clip for clip in self.metrics_data.values() if clip.get("is_viral", False)]
        if viral_clips:
            viral_emotions = [clip.get("emotion") for clip in viral_clips]
            viral_durations = [clip.get("duration", 0) for clip in viral_clips]
            
            insights["viral_characteristics"] = {
                "count": len(viral_clips),
                "common_emotions": list(set(viral_emotions)),
                "average_duration": statistics.mean(viral_durations) if viral_durations else 0,
                "median_duration": statistics.median(viral_durations) if viral_durations else 0
            }
        
        return insights
    
    async def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        # Emotion recommendations
        emotion_trends = await self._analyze_emotion_trends()
        best_emotion = emotion_trends.get("best_emotion")
        if best_emotion and best_emotion != "neutral":
            recommendations.append(f"Focus on {best_emotion} content - it performs {emotion_trends['emotion_stats'][best_emotion]['average_performance']:.1f}% better on average")
        
        # Time recommendations
        time_patterns = await self._analyze_time_patterns()
        best_hours = time_patterns.get("best_hours", [])
        if best_hours:
            recommendations.append(f"Post during optimal hours: {', '.join(f'{h:02d}:00' for h in best_hours[:3])}")
        
        # Platform recommendations
        platform_performance = await self._analyze_platform_performance()
        best_platform = platform_performance.get("best_platform")
        if best_platform:
            recommendations.append(f"Prioritize {best_platform} - it shows the best engagement rates")
        
        # Content recommendations
        viral_clips = [clip for clip in self.metrics_data.values() if clip.get("is_viral", False)]
        if viral_clips:
            avg_viral_duration = statistics.mean([clip.get("duration", 0) for clip in viral_clips])
            recommendations.append(f"Target {avg_viral_duration:.0f}-second clips for viral potential")
        
        # General recommendations
        total_clips = len(self.metrics_data)
        viral_count = len(viral_clips)
        
        if total_clips > 0:
            viral_rate = viral_count / total_clips
            if viral_rate < 0.1:
                recommendations.append("Experiment with more hook-heavy titles and trending topics")
            
            avg_performance = statistics.mean([clip.get("performance_score", 0) for clip in self.metrics_data.values()])
            if avg_performance < 30:
                recommendations.append("Focus on stronger emotional content and better timing")
        
        return recommendations
    
    async def _save_metrics(self):
        """Save metrics data to file"""
        try:
            self.file_handler.save_json(self.metrics_data, self.metrics_file)
        except Exception as e:
            logger.error(f"❌ Error saving metrics: {e}")
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        try:
            total_clips = len(self.metrics_data)
            viral_clips = [clip for clip in self.metrics_data.values() if clip.get("is_viral", False)]
            
            if total_clips == 0:
                return {"error": "No performance data available"}
            
            all_scores = [clip.get("performance_score", 0) for clip in self.metrics_data.values()]
            
            summary = {
                "total_clips": total_clips,
                "viral_clips": len(viral_clips),
                "viral_rate": len(viral_clips) / total_clips,
                "average_performance": statistics.mean(all_scores),
                "median_performance": statistics.median(all_scores),
                "best_performing_clip": max(self.metrics_data.values(), key=lambda x: x.get("performance_score", 0)),
                "recent_trends": await self.analyze_trends(),
                "last_updated": datetime.now().isoformat()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating performance summary: {e}")
            return {"error": str(e)}
