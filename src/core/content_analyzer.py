"""
Content analysis module for detecting viral moments and highlights in video transcripts
"""

import re
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from loguru import logger

from ..ai.llm_analyzer import LLMAnalyzer
from ..utils.config import Config


class ContentAnalyzer:
    """Analyzes video content to identify viral moments and create highlights"""
    
    def __init__(self, config: Config):
        """Initialize content analyzer with configuration"""
        self.config = config
        self.ai_config = config.get_ai_config()
        self.analysis_config = self.ai_config.get("analysis", {})
        
        # Initialize LLM analyzer
        self.llm_analyzer = LLMAnalyzer(config)
        
        # Viral indicators and patterns
        self.emotion_keywords = {
            'funny': [
                'funny', 'hilarious', 'laugh', 'lol', 'comedy', 'joke', 'humor',
                'ridiculous', 'absurd', 'crazy', 'weird', 'bizarre', 'silly'
            ],
            'shocking': [
                'shocking', 'unbelievable', 'incredible', 'amazing', 'wow',
                'surprised', 'unexpected', 'mind-blowing', 'insane', 'wtf'
            ],
            'inspirational': [
                'inspiring', 'motivational', 'success', 'achievement', 'dream',
                'goal', 'overcome', 'struggle', 'victory', 'triumph', 'hope'
            ],
            'educational': [
                'learn', 'tutorial', 'how to', 'explain', 'science', 'fact',
                'research', 'study', 'theory', 'knowledge', 'understand'
            ],
            'controversial': [
                'controversial', 'debate', 'argument', 'opinion', 'disagree',
                'wrong', 'right', 'politics', 'religion', 'sensitive'
            ]
        }
        
        # Hook patterns that grab attention
        self.hook_patterns = [
            r"you won't believe",
            r"secret that",
            r"nobody tells you",
            r"shocking truth",
            r"never knew",
            r"mind blown",
            r"this changes everything",
            r"most people don't know",
            r"hidden truth",
            r"real reason why"
        ]
        
        # Engagement boost keywords
        self.boost_keywords = self.analysis_config.get("keywords_boost", [])
    
    async def find_highlights(self, transcript: Dict[str, Any], video_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Find viral highlights in video transcript
        
        Args:
            transcript: Video transcript with segments and timestamps
            video_metadata: Video metadata for context
            
        Returns:
            List of highlight segments with metadata
        """
        try:
            logger.info("🧠 Analyzing content for viral highlights...")
            
            segments = transcript.get('segments', [])
            if not segments:
                logger.warning("⚠️ No transcript segments found")
                return []
            
            # Step 1: Score all segments
            scored_segments = await self._score_segments(segments)
            
            # Step 2: Use LLM for intelligent analysis
            llm_highlights = await self.llm_analyzer.analyze_content(
                transcript['text'],
                segments,
                video_metadata
            )
            
            # Step 3: Combine scoring approaches
            combined_highlights = await self._combine_analyses(
                scored_segments,
                llm_highlights,
                segments
            )
            
            # Step 4: Filter and rank highlights
            filtered_highlights = await self._filter_highlights(combined_highlights)
            
            # Step 5: Generate titles and metadata
            final_highlights = await self._enrich_highlights(filtered_highlights, video_metadata)
            
            logger.success(f"✨ Found {len(final_highlights)} viral highlights")
            return final_highlights
            
        except Exception as e:
            logger.error(f"❌ Error analyzing content: {e}")
            return []
    
    async def _score_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Score segments based on viral indicators"""
        scored_segments = []
        
        for i, segment in enumerate(segments):
            text = segment['text'].lower()
            score = 0.0
            emotions = []
            
            # Emotion detection
            for emotion, keywords in self.emotion_keywords.items():
                emotion_score = sum(1 for keyword in keywords if keyword in text)
                if emotion_score > 0:
                    emotions.append(emotion)
                    weight = self.analysis_config.get("emotion_weights", {}).get(emotion, 1.0)
                    score += emotion_score * weight
            
            # Hook pattern detection
            hook_score = sum(1 for pattern in self.hook_patterns if re.search(pattern, text, re.IGNORECASE))
            score += hook_score * 2.0  # Hooks are very important
            
            # Boost keywords
            boost_score = sum(1 for keyword in self.boost_keywords if keyword.lower() in text)
            score += boost_score * 1.5
            
            # Length penalty (very short or very long segments are less viral)
            text_length = len(text.split())
            if text_length < 5:
                score *= 0.5
            elif text_length > 100:
                score *= 0.7
            
            # Position bonus (beginning and end segments often contain hooks)
            if i < len(segments) * 0.1:  # First 10%
                score *= 1.2
            elif i > len(segments) * 0.9:  # Last 10%
                score *= 1.1
            
            scored_segments.append({
                'segment_index': i,
                'start_time': segment['start'],
                'end_time': segment['end'],
                'text': segment['text'],
                'score': score,
                'emotions': emotions,
                'duration': segment['end'] - segment['start']
            })
        
        return scored_segments
    
    async def _combine_analyses(self, scored_segments: List[Dict[str, Any]], 
                               llm_highlights: List[Dict[str, Any]], 
                               original_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine rule-based scoring with LLM analysis"""
        combined = []
        
        # Create highlights from high-scoring segments
        min_score = self.analysis_config.get("min_engagement_score", 0.6)
        clip_min_duration = self.config.get("video.clip_duration_min", 25)
        clip_max_duration = self.config.get("video.clip_duration_max", 65)
        
        for segment in scored_segments:
            if segment['score'] >= min_score:
                # Extend segment to meet minimum duration
                start_idx = segment['segment_index']
                end_idx = start_idx
                total_duration = segment['duration']
                
                # Extend forward if needed
                while (end_idx < len(original_segments) - 1 and 
                       total_duration < clip_min_duration):
                    end_idx += 1
                    total_duration = original_segments[end_idx]['end'] - original_segments[start_idx]['start']
                
                # Extend backward if still too short
                while (start_idx > 0 and 
                       total_duration < clip_min_duration):
                    start_idx -= 1
                    total_duration = original_segments[end_idx]['end'] - original_segments[start_idx]['start']
                
                # Trim if too long
                while total_duration > clip_max_duration and end_idx > start_idx:
                    end_idx -= 1
                    total_duration = original_segments[end_idx]['end'] - original_segments[start_idx]['start']
                
                # Combine text from all segments in range
                combined_text = ' '.join([
                    original_segments[i]['text'] 
                    for i in range(start_idx, end_idx + 1)
                ])
                
                combined.append({
                    'start_time': original_segments[start_idx]['start'],
                    'end_time': original_segments[end_idx]['end'],
                    'text': combined_text,
                    'score': segment['score'],
                    'emotions': segment['emotions'],
                    'source': 'rule_based',
                    'confidence': min(segment['score'] / 3.0, 1.0)  # Normalize confidence
                })
        
        # Add LLM highlights
        for llm_highlight in llm_highlights:
            # Check for overlap with existing highlights
            overlap_found = False
            for existing in combined:
                if (abs(llm_highlight['start_time'] - existing['start_time']) < 10 or
                    abs(llm_highlight['end_time'] - existing['end_time']) < 10):
                    # Merge with existing highlight (take higher confidence)
                    if llm_highlight.get('confidence', 0) > existing.get('confidence', 0):
                        existing.update(llm_highlight)
                        existing['source'] = 'combined'
                    overlap_found = True
                    break
            
            if not overlap_found:
                llm_highlight['source'] = 'llm'
                combined.append(llm_highlight)
        
        return combined
    
    async def _filter_highlights(self, highlights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and rank highlights by quality"""
        # Remove duplicates and overlaps
        filtered = []
        highlights.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        for highlight in highlights:
            # Check for significant overlap with existing highlights
            overlap_found = False
            for existing in filtered:
                overlap_start = max(highlight['start_time'], existing['start_time'])
                overlap_end = min(highlight['end_time'], existing['end_time'])
                overlap_duration = max(0, overlap_end - overlap_start)
                
                highlight_duration = highlight['end_time'] - highlight['start_time']
                overlap_ratio = overlap_duration / highlight_duration
                
                if overlap_ratio > 0.5:  # More than 50% overlap
                    overlap_found = True
                    break
            
            if not overlap_found:
                filtered.append(highlight)
        
        # Limit to top highlights
        max_highlights = 5
        filtered = filtered[:max_highlights]
        
        # Ensure minimum quality threshold
        min_confidence = 0.3
        filtered = [h for h in filtered if h.get('confidence', 0) >= min_confidence]
        
        return filtered
    
    async def _enrich_highlights(self, highlights: List[Dict[str, Any]], 
                                video_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Add titles, descriptions, and hashtags to highlights"""
        enriched = []
        
        for i, highlight in enumerate(highlights):
            try:
                # Generate engaging title
                title = await self._generate_title(highlight['text'], highlight.get('emotions', []))
                
                # Generate description
                description = await self._generate_description(highlight['text'], video_metadata)
                
                # Generate hashtags
                hashtags = await self._generate_hashtags(highlight['text'], highlight.get('emotions', []))
                
                # Determine primary emotion
                primary_emotion = self._get_primary_emotion(highlight.get('emotions', []))
                
                enriched_highlight = {
                    **highlight,
                    'title': title,
                    'description': description,
                    'hashtags': hashtags,
                    'emotion': primary_emotion,
                    'engagement_score': highlight.get('confidence', 0.5),
                    'clip_number': i + 1
                }
                
                enriched.append(enriched_highlight)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to enrich highlight {i}: {e}")
                # Add basic version
                enriched.append({
                    **highlight,
                    'title': f"Viral Moment {i + 1}",
                    'description': highlight['text'][:100] + "...",
                    'hashtags': ['#viral', '#trending'],
                    'emotion': 'neutral',
                    'engagement_score': highlight.get('confidence', 0.5),
                    'clip_number': i + 1
                })
        
        return enriched
    
    async def _generate_title(self, text: str, emotions: List[str]) -> str:
        """Generate an engaging title for the highlight"""
        # Simple rule-based title generation (can be enhanced with LLM)
        words = text.split()
        
        # Title templates based on emotions
        if 'funny' in emotions:
            templates = [
                "This Will Make You Laugh",
                "Hilarious Moment",
                "Comedy Gold",
                "You Won't Stop Laughing"
            ]
        elif 'shocking' in emotions:
            templates = [
                "You Won't Believe This",
                "Shocking Truth Revealed",
                "Mind-Blowing Moment",
                "This Changes Everything"
            ]
        elif 'inspirational' in emotions:
            templates = [
                "This Will Inspire You",
                "Motivational Moment",
                "Life-Changing Advice",
                "Inspiring Truth"
            ]
        else:
            templates = [
                "Viral Moment",
                "Must-See Clip",
                "Trending Now",
                "Watch This"
            ]
        
        # Try to extract key phrases
        for keyword in self.boost_keywords:
            if keyword.lower() in text.lower():
                return f"The {keyword.title()} Secret"
        
        # Look for question patterns
        if '?' in text:
            question_start = text.find('?')
            if question_start > 0:
                question = text[:question_start + 1].strip()
                if len(question.split()) <= 8:
                    return question.title()
        
        # Fallback to template
        import random
        return random.choice(templates)
    
    async def _generate_description(self, text: str, video_metadata: Dict[str, Any]) -> str:
        """Generate description for the highlight"""
        # Truncate and clean text
        description = text.strip()
        if len(description) > 150:
            description = description[:147] + "..."
        
        # Add context from video metadata
        if video_metadata.get('title'):
            description += f"\n\nFrom: {video_metadata['title']}"
        
        return description
    
    async def _generate_hashtags(self, text: str, emotions: List[str]) -> List[str]:
        """Generate relevant hashtags for the highlight"""
        hashtags = []
        hashtag_config = self.config.get_hashtag_config()
        
        # Base hashtags
        base_tags = ['#viral', '#trending', '#fyp']
        hashtags.extend(base_tags)
        
        # Emotion-based hashtags
        emotion_tags = {
            'funny': ['#comedy', '#humor', '#laugh'],
            'shocking': ['#mindblown', '#incredible', '#wow'],
            'inspirational': ['#motivation', '#inspiration', '#success'],
            'educational': ['#learning', '#facts', '#knowledge'],
            'controversial': ['#debate', '#opinion', '#discussion']
        }
        
        for emotion in emotions:
            if emotion in emotion_tags:
                hashtags.extend(emotion_tags[emotion])
        
        # Extract topic-related hashtags from text
        text_lower = text.lower()
        
        # Common topic keywords
        topic_keywords = {
            'business': '#business', 'money': '#money', 'success': '#success',
            'health': '#health', 'fitness': '#fitness', 'food': '#food',
            'technology': '#tech', 'ai': '#ai', 'science': '#science',
            'travel': '#travel', 'lifestyle': '#lifestyle', 'tips': '#tips'
        }
        
        for keyword, tag in topic_keywords.items():
            if keyword in text_lower:
                hashtags.append(tag)
        
        # Remove duplicates and limit count
        hashtags = list(dict.fromkeys(hashtags))  # Remove duplicates preserving order
        max_count = hashtag_config.get("max_count", 10)
        min_count = hashtag_config.get("min_count", 5)
        
        if len(hashtags) > max_count:
            hashtags = hashtags[:max_count]
        elif len(hashtags) < min_count:
            # Add generic hashtags to reach minimum
            generic_tags = ['#content', '#video', '#shorts', '#reels', '#tiktok']
            for tag in generic_tags:
                if tag not in hashtags and len(hashtags) < min_count:
                    hashtags.append(tag)
        
        return hashtags
    
    def _get_primary_emotion(self, emotions: List[str]) -> str:
        """Get the primary emotion from a list of emotions"""
        if not emotions:
            return 'neutral'
        
        # Priority order for emotions
        emotion_priority = ['funny', 'shocking', 'inspirational', 'controversial', 'educational']
        
        for emotion in emotion_priority:
            if emotion in emotions:
                return emotion
        
        return emotions[0] if emotions else 'neutral'
