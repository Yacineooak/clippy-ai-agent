"""
Optimization engine for improving content performance based on analytics
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import statistics

from loguru import logger

from ..utils.config import Config
from .engagement_tracker import EngagementTracker


class OptimizationEngine:
    """Learns from performance data to optimize future content creation"""
    
    def __init__(self, config: Config):
        """Initialize optimization engine"""
        self.config = config
        self.analytics_config = config.get_analytics_config()
        
        # Initialize engagement tracker
        self.engagement_tracker = EngagementTracker(config)
        
        # Optimization settings
        self.optimization_interval = self.analytics_config.get("optimization_interval_days", 7)
        self.min_data_points = 10  # Minimum clips needed for optimization
        
        # Learning parameters
        self.learning_rate = 0.1
        self.confidence_threshold = 0.7
        
        # Optimization weights for different factors
        self.optimization_weights = {
            "emotion": 0.25,
            "timing": 0.20,
            "duration": 0.15,
            "platform": 0.15,
            "title_style": 0.15,
            "content_type": 0.10
        }
    
    async def optimize_content_strategy(self) -> Dict[str, Any]:
        """
        Analyze performance data and generate optimization recommendations
        
        Returns:
            Optimization recommendations and updated strategies
        """
        try:
            logger.info("🎯 Running content strategy optimization...")
            
            # Get performance trends
            trends = await self.engagement_tracker.analyze_trends()
            
            if "error" in trends:
                logger.warning("⚠️ Insufficient data for optimization")
                return {"status": "insufficient_data", "message": "Need more performance data"}
            
            # Generate optimizations
            optimizations = {
                "emotion_strategy": await self._optimize_emotion_strategy(trends),
                "timing_strategy": await self._optimize_timing_strategy(trends),
                "duration_strategy": await self._optimize_duration_strategy(trends),
                "platform_strategy": await self._optimize_platform_strategy(trends),
                "title_strategy": await self._optimize_title_strategy(trends),
                "content_recommendations": await self._generate_content_recommendations(trends),
                "updated_config": await self._generate_updated_config(trends),
                "confidence_score": await self._calculate_optimization_confidence(trends),
                "last_optimized": datetime.now().isoformat()
            }
            
            # Apply optimizations if confidence is high enough
            if optimizations["confidence_score"] >= self.confidence_threshold:
                await self._apply_optimizations(optimizations)
                logger.success("✅ Applied high-confidence optimizations to config")
            else:
                logger.info(f"📊 Generated recommendations (confidence: {optimizations['confidence_score']:.2f})")
            
            return optimizations
            
        except Exception as e:
            logger.error(f"❌ Error in optimization engine: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _optimize_emotion_strategy(self, trends: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize emotion targeting based on performance"""
        emotion_performance = trends.get("emotion_performance", {})
        emotion_rankings = emotion_performance.get("emotion_rankings", [])
        
        if not emotion_rankings:
            return {"status": "no_data"}
        
        # Get top performing emotions
        top_emotions = emotion_rankings[:3]
        worst_emotions = emotion_rankings[-2:] if len(emotion_rankings) > 2 else []
        
        recommendations = {
            "prioritize_emotions": [emotion for emotion, _ in top_emotions],
            "avoid_emotions": [emotion for emotion, _ in worst_emotions],
            "emotion_weights": {}
        }
        
        # Calculate new emotion weights
        total_performance = sum(stats["average_performance"] for _, stats in emotion_rankings)
        for emotion, stats in emotion_rankings:
            if total_performance > 0:
                weight = stats["average_performance"] / total_performance
                recommendations["emotion_weights"][emotion] = round(weight, 2)
        
        return recommendations
    
    async def _optimize_timing_strategy(self, trends: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize posting times based on performance"""
        time_patterns = trends.get("time_patterns", {})
        best_hours = time_patterns.get("best_hours", [])
        
        if not best_hours:
            return {"status": "no_data"}
        
        # Generate optimized posting schedule
        optimized_schedule = {}
        
        # For each platform, suggest best times
        for platform in ["youtube", "tiktok", "instagram"]:
            platform_times = []
            
            # Use best performing hours
            for hour in best_hours[:3]:
                platform_times.append(f"{hour:02d}:00")
            
            # Add platform-specific adjustments
            if platform == "tiktok":
                # TikTok performs well in evening
                if "19:00" not in platform_times and "20:00" not in platform_times:
                    platform_times.append("19:00")
            elif platform == "instagram":
                # Instagram Reels perform well during lunch and evening
                if "12:00" not in platform_times:
                    platform_times.append("12:00")
            
            optimized_schedule[platform] = platform_times[:4]  # Max 4 times per platform
        
        return {
            "optimal_hours": best_hours,
            "posting_schedule": optimized_schedule,
            "recommendations": [
                f"Post during peak hours: {', '.join(f'{h:02d}:00' for h in best_hours[:3])}",
                "Avoid posting during low-engagement hours",
                "Consider time zone differences for target audience"
            ]
        }
    
    async def _optimize_duration_strategy(self, trends: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize video duration based on performance"""
        content_insights = trends.get("content_insights", {})
        duration_analysis = content_insights.get("duration_analysis", {})
        
        if not duration_analysis:
            return {"status": "no_data"}
        
        # Find best performing duration range
        best_duration_group = max(
            duration_analysis.items(),
            key=lambda x: x[1].get("average_performance", 0)
        )
        
        duration_recommendations = {
            "optimal_range": best_duration_group[0],
            "performance_by_duration": duration_analysis
        }
        
        # Specific duration recommendations
        if best_duration_group[0] == "short":
            duration_recommendations["target_duration"] = "25-30 seconds"
            duration_recommendations["reasoning"] = "Short clips show best engagement"
        elif best_duration_group[0] == "medium":
            duration_recommendations["target_duration"] = "35-45 seconds"
            duration_recommendations["reasoning"] = "Medium-length clips balance content and attention"
        else:
            duration_recommendations["target_duration"] = "50-60 seconds"
            duration_recommendations["reasoning"] = "Longer clips show better performance"
        
        return duration_recommendations
    
    async def _optimize_platform_strategy(self, trends: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize platform prioritization"""
        platform_performance = trends.get("platform_performance", {})
        platform_rankings = platform_performance.get("platform_rankings", [])
        
        if not platform_rankings:
            return {"status": "no_data"}
        
        # Calculate platform priorities
        platform_priorities = {}
        total_performance = sum(stats["average_performance"] for _, stats in platform_rankings)
        
        for platform, stats in platform_rankings:
            if total_performance > 0:
                priority = stats["average_performance"] / total_performance
                platform_priorities[platform] = {
                    "priority_score": round(priority, 2),
                    "posting_frequency": "high" if priority > 0.4 else "medium" if priority > 0.25 else "low",
                    "focus_level": "primary" if priority > 0.4 else "secondary" if priority > 0.25 else "tertiary"
                }
        
        return {
            "platform_priorities": platform_priorities,
            "primary_platform": platform_rankings[0][0] if platform_rankings else "youtube",
            "recommendations": [
                f"Focus on {platform_rankings[0][0]} for best ROI",
                "Adjust posting frequency based on platform performance",
                "Consider platform-specific content optimization"
            ]
        }
    
    async def _optimize_title_strategy(self, trends: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize title and hook strategies"""
        # Analyze viral characteristics for title patterns
        content_insights = trends.get("content_insights", {})
        viral_characteristics = content_insights.get("viral_characteristics", {})
        
        title_recommendations = {
            "hook_types": [],
            "avoid_patterns": [],
            "title_templates": []
        }
        
        # Based on best performing emotions, suggest title styles
        emotion_performance = trends.get("emotion_performance", {})
        best_emotion = emotion_performance.get("best_emotion", "neutral")
        
        if best_emotion == "funny":
            title_recommendations["hook_types"] = ["humor", "relatable", "unexpected"]
            title_recommendations["title_templates"] = [
                "This Will Make You Laugh",
                "Wait For It...",
                "Plot Twist!"
            ]
        elif best_emotion == "shocking":
            title_recommendations["hook_types"] = ["surprise", "revelation", "unbelievable"]
            title_recommendations["title_templates"] = [
                "You Won't Believe This",
                "The Shocking Truth",
                "This Changes Everything"
            ]
        elif best_emotion == "inspirational":
            title_recommendations["hook_types"] = ["motivation", "success", "transformation"]
            title_recommendations["title_templates"] = [
                "This Changed My Life",
                "Life Lesson Alert",
                "Pure Motivation"
            ]
        
        return title_recommendations
    
    async def _generate_content_recommendations(self, trends: Dict[str, Any]) -> List[str]:
        """Generate specific content creation recommendations"""
        recommendations = []
        
        # Emotion recommendations
        emotion_performance = trends.get("emotion_performance", {})
        best_emotion = emotion_performance.get("best_emotion")
        if best_emotion:
            recommendations.append(f"Create more {best_emotion} content - it performs best")
        
        # Duration recommendations
        content_insights = trends.get("content_insights", {})
        viral_characteristics = content_insights.get("viral_characteristics", {})
        if viral_characteristics.get("average_duration"):
            avg_duration = viral_characteristics["average_duration"]
            recommendations.append(f"Target {avg_duration:.0f}-second clips for viral potential")
        
        # Platform-specific recommendations
        platform_performance = trends.get("platform_performance", {})
        best_platform = platform_performance.get("best_platform")
        if best_platform:
            recommendations.append(f"Prioritize content creation for {best_platform}")
        
        # Timing recommendations
        time_patterns = trends.get("time_patterns", {})
        optimal_times = time_patterns.get("recommendations", {}).get("optimal_posting_times", [])
        if optimal_times:
            recommendations.append(f"Schedule posts for {', '.join(optimal_times[:3])}")
        
        # Viral analysis recommendations
        if viral_characteristics.get("count", 0) > 0:
            common_emotions = viral_characteristics.get("common_emotions", [])
            if common_emotions:
                recommendations.append(f"Viral content often uses: {', '.join(common_emotions)}")
        
        return recommendations
    
    async def _generate_updated_config(self, trends: Dict[str, Any]) -> Dict[str, Any]:
        """Generate updated configuration based on optimization"""
        updated_config = {}
        
        # Update AI analysis weights
        emotion_performance = trends.get("emotion_performance", {})
        if emotion_performance.get("emotion_stats"):
            emotion_weights = {}
            for emotion, stats in emotion_performance["emotion_stats"].items():
                # Normalize performance to weight
                weight = min(stats.get("average_performance", 50) / 50, 2.0)
                emotion_weights[emotion] = round(weight, 2)
            
            updated_config["ai"] = {
                "analysis": {
                    "emotion_weights": emotion_weights
                }
            }
        
        # Update posting schedule
        time_patterns = trends.get("time_patterns", {})
        if time_patterns.get("best_hours"):
            posting_times = {}
            for platform in ["youtube", "tiktok", "instagram"]:
                times = []
                for hour in time_patterns["best_hours"][:3]:
                    times.append(f"{hour:02d}:00")
                posting_times[platform] = times
            
            updated_config["scheduler"] = {
                "posting_times": posting_times
            }
        
        # Update video duration targets
        content_insights = trends.get("content_insights", {})
        duration_analysis = content_insights.get("duration_analysis", {})
        if duration_analysis:
            best_duration = max(
                duration_analysis.items(),
                key=lambda x: x[1].get("average_performance", 0)
            )[0]
            
            duration_ranges = {
                "short": {"min": 25, "max": 35},
                "medium": {"min": 35, "max": 50}, 
                "long": {"min": 50, "max": 65}
            }
            
            if best_duration in duration_ranges:
                range_config = duration_ranges[best_duration]
                updated_config["video"] = {
                    "clip_duration_min": range_config["min"],
                    "clip_duration_max": range_config["max"]
                }
        
        return updated_config
    
    async def _calculate_optimization_confidence(self, trends: Dict[str, Any]) -> float:
        """Calculate confidence score for optimization recommendations"""
        confidence_factors = []
        
        # Data volume confidence
        emotion_stats = trends.get("emotion_performance", {}).get("emotion_stats", {})
        total_clips = sum(stats.get("count", 0) for stats in emotion_stats.values())
        data_confidence = min(total_clips / 50, 1.0)  # Full confidence at 50+ clips
        confidence_factors.append(data_confidence)
        
        # Performance variance confidence
        all_scores = []
        for stats in emotion_stats.values():
            all_scores.extend(stats.get("scores", []))
        
        if len(all_scores) > 1:
            variance = statistics.stdev(all_scores)
            variance_confidence = max(0, 1 - (variance / 100))  # Lower variance = higher confidence
            confidence_factors.append(variance_confidence)
        
        # Time range confidence (more recent data = higher confidence)
        # This would require timestamp analysis - simplified for now
        time_confidence = 0.8  # Assume reasonable time range
        confidence_factors.append(time_confidence)
        
        # Platform consistency confidence
        platform_stats = trends.get("platform_performance", {}).get("platform_stats", {})
        if len(platform_stats) > 1:
            platform_scores = [stats.get("average_performance", 0) for stats in platform_stats.values()]
            if platform_scores:
                consistency = 1 - (statistics.stdev(platform_scores) / statistics.mean(platform_scores))
                consistency_confidence = max(0, min(consistency, 1))
                confidence_factors.append(consistency_confidence)
        
        return statistics.mean(confidence_factors) if confidence_factors else 0.5
    
    async def _apply_optimizations(self, optimizations: Dict[str, Any]):
        """Apply high-confidence optimizations to configuration"""
        try:
            updated_config = optimizations.get("updated_config", {})
            
            if not updated_config:
                return
            
            # Update configuration
            for section, settings in updated_config.items():
                for key, value in settings.items():
                    config_key = f"{section}.{key}"
                    self.config.set(config_key, value)
            
            # Save updated configuration
            self.config.save_config()
            
            logger.success("✅ Applied optimization updates to configuration")
            
        except Exception as e:
            logger.error(f"❌ Error applying optimizations: {e}")
    
    async def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status and last run information"""
        try:
            # Get performance summary
            performance_summary = await self.engagement_tracker.get_performance_summary()
            
            status = {
                "optimization_enabled": self.analytics_config.get("enabled", True),
                "last_optimization": "never",  # Would track this in practice
                "next_optimization": "based_on_interval",
                "data_points": performance_summary.get("total_clips", 0),
                "viral_rate": performance_summary.get("viral_rate", 0),
                "average_performance": performance_summary.get("average_performance", 0),
                "optimization_confidence": 0.5,  # Would calculate based on data
                "ready_for_optimization": performance_summary.get("total_clips", 0) >= self.min_data_points
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Error getting optimization status: {e}")
            return {"error": str(e)}
