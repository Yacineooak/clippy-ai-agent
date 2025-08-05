"""
Offline LLM analyzer for intelligent content analysis
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from loguru import logger

try:
    from gpt4all import GPT4All
    GPT4ALL_AVAILABLE = True
except ImportError:
    GPT4ALL_AVAILABLE = False
    logger.warning("⚠️ GPT4All not available. Install with: pip install gpt4all")

from ..utils.config import Config


class LLMAnalyzer:
    """Offline LLM for intelligent content analysis and highlight detection"""
    
    def __init__(self, config: Config):
        """Initialize LLM analyzer with configuration"""
        self.config = config
        self.ai_config = config.get_ai_config()
        self.llm_config = self.ai_config.get("llm", {})
        
        self.model = None
        self.model_path = Path("./models")
        self.model_path.mkdir(exist_ok=True)
        
        # Initialize model if available
        if GPT4ALL_AVAILABLE:
            self._initialize_model()
        else:
            logger.warning("⚠️ LLM analysis will use fallback rule-based methods")
    
    def _initialize_model(self):
        """Initialize the offline LLM model"""
        try:
            model_name = self.llm_config.get("model", "mistral-7b-instruct-v0.1.q4_0.gguf")
            
            # Check if model exists locally
            model_file = self.model_path / model_name
            
            if not model_file.exists():
                logger.info(f"📥 Downloading LLM model: {model_name}")
                # GPT4All will download automatically
            
            self.model = GPT4All(
                model_name=model_name,
                model_path=str(self.model_path),
                allow_download=True,
                n_threads=4
            )
            
            logger.success(f"✅ LLM model loaded: {model_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM model: {e}")
            self.model = None
    
    async def analyze_content(self, full_transcript: str, segments: List[Dict[str, Any]], 
                            video_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze content using LLM to find viral highlights
        
        Args:
            full_transcript: Complete video transcript
            segments: Transcript segments with timestamps
            video_metadata: Video metadata for context
            
        Returns:
            List of LLM-identified highlights
        """
        if not self.model:
            logger.warning("⚠️ LLM not available, using fallback analysis")
            return await self._fallback_analysis(full_transcript, segments)
        
        try:
            logger.info("🤖 Running LLM content analysis...")
            
            # Split transcript into analyzable chunks
            chunks = self._split_transcript(full_transcript, segments)
            
            highlights = []
            
            for chunk in chunks:
                chunk_highlights = await self._analyze_chunk(chunk, video_metadata)
                highlights.extend(chunk_highlights)
            
            # Rank and filter highlights
            ranked_highlights = await self._rank_highlights(highlights, video_metadata)
            
            logger.success(f"✨ LLM analysis complete: {len(ranked_highlights)} highlights found")
            return ranked_highlights
            
        except Exception as e:
            logger.error(f"❌ Error in LLM analysis: {e}")
            return await self._fallback_analysis(full_transcript, segments)
    
    def _split_transcript(self, transcript: str, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split transcript into analyzable chunks"""
        chunks = []
        chunk_size = 1000  # Characters per chunk
        overlap = 200      # Overlap between chunks
        
        # Group segments into chunks
        current_chunk = {
            'text': '',
            'segments': [],
            'start_time': 0,
            'end_time': 0
        }
        
        for segment in segments:
            segment_text = segment['text']
            
            # Check if adding this segment would exceed chunk size
            if len(current_chunk['text'] + segment_text) > chunk_size and current_chunk['text']:
                # Finalize current chunk
                current_chunk['end_time'] = current_chunk['segments'][-1]['end'] if current_chunk['segments'] else 0
                chunks.append(current_chunk.copy())
                
                # Start new chunk with overlap
                overlap_text = current_chunk['text'][-overlap:] if len(current_chunk['text']) > overlap else current_chunk['text']
                current_chunk = {
                    'text': overlap_text + ' ' + segment_text,
                    'segments': [segment],
                    'start_time': segment['start'],
                    'end_time': segment['end']
                }
            else:
                # Add to current chunk
                if not current_chunk['segments']:
                    current_chunk['start_time'] = segment['start']
                
                current_chunk['text'] += ' ' + segment_text
                current_chunk['segments'].append(segment)
                current_chunk['end_time'] = segment['end']
        
        # Add final chunk
        if current_chunk['text']:
            chunks.append(current_chunk)
        
        return chunks
    
    async def _analyze_chunk(self, chunk: Dict[str, Any], video_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze a single chunk with LLM"""
        try:
            # Prepare prompt for LLM
            prompt = self._create_analysis_prompt(chunk['text'], video_metadata)
            
            # Generate response
            response = self.model.generate(
                prompt,
                max_tokens=self.llm_config.get("max_tokens", 500),
                temp=self.llm_config.get("temperature", 0.7),
                streaming=False
            )
            
            # Parse LLM response
            highlights = self._parse_llm_response(response, chunk)
            
            return highlights
            
        except Exception as e:
            logger.warning(f"⚠️ Error analyzing chunk: {e}")
            return []
    
    def _create_analysis_prompt(self, text: str, video_metadata: Dict[str, Any]) -> str:
        """Create prompt for LLM analysis"""
        video_context = f"Video Title: {video_metadata.get('title', 'Unknown')}\n"
        if video_metadata.get('description'):
            video_context += f"Description: {video_metadata['description'][:200]}...\n"
        
        prompt = f"""You are an expert content analyst specializing in identifying viral moments for short-form video content (TikTok, YouTube Shorts, Instagram Reels).

{video_context}

Analyze the following transcript and identify the most engaging 30-60 second segments that would perform well as viral short-form content.

Transcript:
{text}

For each viral moment you identify, provide:
1. A compelling hook/title (5-8 words)
2. Why it would be viral (emotional impact, relatability, shock value, etc.)
3. Target emotion (funny, shocking, inspirational, educational, controversial)
4. Engagement score (0.0 to 1.0)
5. Key quotes or phrases

Look for:
- Surprising facts or revelations
- Emotional moments (funny, shocking, inspiring)
- Relatable experiences
- Strong opinions or controversial takes
- Educational insights or "aha" moments
- Personal stories with universal appeal
- Moments with natural hooks ("You won't believe...", "The secret is...", etc.)

Format your response as JSON:
{{
  "highlights": [
    {{
      "title": "Hook title here",
      "reason": "Why this would be viral",
      "emotion": "funny/shocking/inspirational/educational/controversial",
      "engagement_score": 0.8,
      "key_quotes": ["quote 1", "quote 2"],
      "viral_potential": "high/medium/low"
    }}
  ]
}}

Only identify segments with high viral potential. Quality over quantity."""
        
        return prompt
    
    def _parse_llm_response(self, response: str, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse LLM response and extract highlights"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger.warning("⚠️ No JSON found in LLM response")
                return []
            
            data = json.loads(json_match.group())
            highlights = data.get('highlights', [])
            
            # Convert to standard format
            converted_highlights = []
            
            for highlight in highlights:
                # Find best matching segment(s) based on key quotes
                matching_segments = self._find_matching_segments(
                    highlight.get('key_quotes', []),
                    chunk['segments']
                )
                
                if matching_segments:
                    start_time = matching_segments[0]['start']
                    end_time = matching_segments[-1]['end']
                    
                    # Ensure clip duration is within limits
                    duration = end_time - start_time
                    min_duration = self.config.get("video.clip_duration_min", 25)
                    max_duration = self.config.get("video.clip_duration_max", 65)
                    
                    if duration < min_duration:
                        # Extend clip
                        needed_time = min_duration - duration
                        start_time = max(chunk['start_time'], start_time - needed_time / 2)
                        end_time = min(chunk['end_time'], end_time + needed_time / 2)
                    elif duration > max_duration:
                        # Trim clip
                        excess_time = duration - max_duration
                        start_time += excess_time / 2
                        end_time -= excess_time / 2
                    
                    # Get text for this time range
                    highlight_text = ' '.join([
                        seg['text'] for seg in matching_segments
                    ])
                    
                    converted_highlights.append({
                        'start_time': start_time,
                        'end_time': end_time,
                        'text': highlight_text,
                        'title': highlight.get('title', 'Viral Moment'),
                        'emotion': highlight.get('emotion', 'neutral'),
                        'confidence': highlight.get('engagement_score', 0.5),
                        'viral_potential': highlight.get('viral_potential', 'medium'),
                        'reason': highlight.get('reason', ''),
                        'key_quotes': highlight.get('key_quotes', [])
                    })
            
            return converted_highlights
            
        except Exception as e:
            logger.warning(f"⚠️ Error parsing LLM response: {e}")
            return []
    
    def _find_matching_segments(self, key_quotes: List[str], segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find segments that match key quotes"""
        if not key_quotes:
            return segments[:3] if len(segments) >= 3 else segments  # Return first few segments as fallback
        
        matching_segments = []
        
        for quote in key_quotes:
            quote_lower = quote.lower()
            
            for segment in segments:
                segment_text = segment['text'].lower()
                
                # Check for quote match
                if quote_lower in segment_text or any(word in segment_text for word in quote_lower.split()):
                    if segment not in matching_segments:
                        matching_segments.append(segment)
        
        # Sort by timestamp
        matching_segments.sort(key=lambda x: x['start'])
        
        # If no matches found, return segments with highest word overlap
        if not matching_segments:
            quote_words = set(' '.join(key_quotes).lower().split())
            
            segment_scores = []
            for segment in segments:
                segment_words = set(segment['text'].lower().split())
                overlap = len(quote_words & segment_words)
                segment_scores.append((segment, overlap))
            
            # Sort by overlap score
            segment_scores.sort(key=lambda x: x[1], reverse=True)
            matching_segments = [seg for seg, score in segment_scores[:3] if score > 0]
        
        return matching_segments
    
    async def _rank_highlights(self, highlights: List[Dict[str, Any]], video_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rank highlights by viral potential"""
        try:
            # Score highlights based on multiple factors
            for highlight in highlights:
                score = highlight.get('confidence', 0.5)
                
                # Boost based on viral potential
                viral_potential = highlight.get('viral_potential', 'medium')
                if viral_potential == 'high':
                    score *= 1.3
                elif viral_potential == 'low':
                    score *= 0.8
                
                # Boost based on emotion
                emotion = highlight.get('emotion', 'neutral')
                emotion_boost = {
                    'funny': 1.2,
                    'shocking': 1.1,
                    'inspirational': 1.0,
                    'controversial': 1.1,
                    'educational': 0.9
                }.get(emotion, 1.0)
                
                score *= emotion_boost
                
                # Update confidence
                highlight['confidence'] = min(score, 1.0)
            
            # Sort by confidence and return top highlights
            highlights.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            # Return top 5 highlights
            return highlights[:5]
            
        except Exception as e:
            logger.warning(f"⚠️ Error ranking highlights: {e}")
            return highlights[:5]
    
    async def _fallback_analysis(self, full_transcript: str, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback analysis when LLM is not available"""
        logger.info("🔄 Using fallback rule-based analysis")
        
        # Simple rule-based highlight detection
        highlights = []
        
        # Look for segments with emotional keywords
        emotion_keywords = {
            'shocking': ['unbelievable', 'incredible', 'amazing', 'wow', 'surprised'],
            'funny': ['funny', 'hilarious', 'laugh', 'joke', 'comedy'],
            'inspirational': ['inspiring', 'motivational', 'success', 'achievement']
        }
        
        for i, segment in enumerate(segments):
            text_lower = segment['text'].lower()
            score = 0
            emotions = []
            
            # Check for emotional content
            for emotion, keywords in emotion_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    score += 0.3
                    emotions.append(emotion)
            
            # Check for questions (often engaging)
            if '?' in segment['text']:
                score += 0.2
            
            # Check for first-person stories
            if any(pronoun in text_lower for pronoun in ['i ', 'my ', 'me ']):
                score += 0.1
            
            # Check for superlatives
            superlatives = ['best', 'worst', 'biggest', 'smallest', 'most', 'least']
            if any(sup in text_lower for sup in superlatives):
                score += 0.2
            
            if score >= 0.4:  # Threshold for highlight
                # Extend to minimum duration
                start_idx = max(0, i - 1)
                end_idx = min(len(segments) - 1, i + 2)
                
                start_time = segments[start_idx]['start']
                end_time = segments[end_idx]['end']
                
                combined_text = ' '.join([
                    segments[j]['text'] for j in range(start_idx, end_idx + 1)
                ])
                
                highlights.append({
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': combined_text,
                    'confidence': score,
                    'emotions': emotions,
                    'emotion': emotions[0] if emotions else 'neutral'
                })
        
        return highlights[:3]  # Return top 3
    
    async def generate_title(self, text: str, emotion: str = 'neutral') -> str:
        """Generate a viral title using LLM"""
        if not self.model:
            return self._fallback_title_generation(text, emotion)
        
        try:
            prompt = f"""Create a viral, attention-grabbing title for a short-form video (TikTok/YouTube Shorts) based on this content:

Content: {text[:300]}...
Emotion: {emotion}

Requirements:
- 3-8 words maximum
- Creates curiosity or emotional reaction
- Uses power words when appropriate
- Avoids clickbait that misleads
- Matches the {emotion} emotion

Examples of good viral titles:
- "This Changed My Life"
- "You Won't Believe This"
- "Secret Nobody Tells You"
- "Biggest Mistake Ever"

Generate 3 title options and pick the best one. Response format:
TITLE: [your best title here]"""

            response = self.model.generate(prompt, max_tokens=100, temp=0.8)
            
            # Extract title from response
            title_match = re.search(r'TITLE:\s*(.+)', response)
            if title_match:
                return title_match.group(1).strip()
            
            # Fallback if no proper format found
            return self._fallback_title_generation(text, emotion)
            
        except Exception as e:
            logger.warning(f"⚠️ Error generating title with LLM: {e}")
            return self._fallback_title_generation(text, emotion)
    
    def _fallback_title_generation(self, text: str, emotion: str) -> str:
        """Fallback title generation without LLM"""
        templates = {
            'funny': ["This Will Make You Laugh", "Comedy Gold Right Here", "You'll Crack Up"],
            'shocking': ["You Won't Believe This", "This Is Unreal", "Mind = Blown"],
            'inspirational': ["This Changed Everything", "Pure Motivation", "Life Lesson Alert"],
            'educational': ["You Need To Know This", "Hidden Truth Revealed", "Mind-Blowing Fact"],
            'controversial': ["Hot Take Alert", "Unpopular Opinion", "This Is Controversial"]
        }
        
        import random
        emotion_templates = templates.get(emotion, templates['shocking'])
        return random.choice(emotion_templates)
