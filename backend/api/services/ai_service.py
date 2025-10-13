import openai
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            logger.warning("OpenAI API key not found, AI features will use fallback mode")
            self.client = None
    
    async def generate_test_questions(self, test_type: str, job_title: str = None, skills: List[str] = None) -> List[Dict[str, Any]]:
        """Generate AI-powered test questions based on test type and job requirements."""
        try:
            if not self.client:
                logger.warning("OpenAI client not available, using fallback questions")
                return self._get_fallback_questions(test_type)
            
            # Create context for question generation
            context = f"Generate 20 {test_type} questions for a job interview"
            if job_title:
                context += f" for a {job_title} position"
            if skills:
                context += f" requiring skills: {', '.join(skills)}"
            
            prompt = f"""
            {context}. 
            
            For each question, provide:
            - A clear, professional question
            - 4 multiple choice options (A, B, C, D)
            - The correct answer (for technical questions)
            - Question type: {test_type}
            
            Return the response as a JSON array with this structure:
            [
                {{
                    "id": 1,
                    "question": "Question text here?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Option A" (only for technical questions),
                    "question_type": "{test_type}"
                }}
            ]
            
            Make questions relevant, challenging, and professional.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert HR professional creating interview questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse the response
            content = response.choices[0].message.content
            questions = json.loads(content)
            
            # Validate and clean questions
            cleaned_questions = []
            for i, q in enumerate(questions[:20]):  # Limit to 20 questions
                if self._validate_question(q):
                    q['id'] = i + 1
                    cleaned_questions.append(q)
            
            return cleaned_questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            return self._get_fallback_questions(test_type)
    
    async def analyze_test_answers(self, questions: List[Dict], answers: Dict[str, str], test_type: str) -> Dict[str, Any]:
        """Analyze test answers using AI for more intelligent scoring."""
        try:
            if not self.client:
                return self._get_fallback_scoring(questions, answers, test_type)
            
            # Prepare question-answer pairs for analysis
            qa_pairs = []
            for q in questions:
                q_id = str(q['id'])
                if q_id in answers:
                    qa_pairs.append({
                        "question": q['question'],
                        "options": q['options'],
                        "user_answer": answers[q_id],
                        "correct_answer": q.get('correct_answer'),
                        "question_type": q['question_type']
                    })
            
            prompt = f"""
            Analyze these {test_type} interview answers and provide detailed scoring:
            
            {json.dumps(qa_pairs, indent=2)}
            
            Provide analysis in JSON format:
            {{
                "overall_score": 0-20,
                "skills_score": 0-10,
                "test_score": 0-10,
                "strengths": ["list of strengths"],
                "weaknesses": ["list of areas for improvement"],
                "detailed_feedback": "comprehensive feedback",
                "recommendations": ["specific recommendations"]
            }}
            
            Consider:
            - Answer quality and relevance
            - Problem-solving approach
            - Communication skills
            - Technical accuracy (for technical questions)
            - Professional judgment
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert HR analyst evaluating interview responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            analysis = json.loads(content)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing answers: {e}")
            return self._get_fallback_scoring(questions, answers, test_type)
    
    async def calculate_job_match(self, job_requirements: Dict, candidate_profile: Dict, test_score: float) -> Dict[str, Any]:
        """Calculate AI-powered job-candidate matching score."""
        try:
            if not self.client:
                return self._get_fallback_matching(job_requirements, candidate_profile, test_score)
            
            prompt = f"""
            Analyze the match between this job and candidate:
            
            Job Requirements:
            {json.dumps(job_requirements, indent=2)}
            
            Candidate Profile:
            {json.dumps(candidate_profile, indent=2)}
            
            Test Score: {test_score}/20
            
            Provide matching analysis in JSON format:
            {{
                "match_score": 0-100,
                "skills_match": 0-100,
                "experience_match": 0-100,
                "culture_fit": 0-100,
                "overall_recommendation": "strong_match|good_match|moderate_match|weak_match",
                "strengths": ["key strengths"],
                "concerns": ["potential concerns"],
                "recommendations": ["specific recommendations"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert recruiter analyzing job-candidate matches."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            match_analysis = json.loads(content)
            
            return match_analysis
            
        except Exception as e:
            logger.error(f"Error calculating job match: {e}")
            return self._get_fallback_matching(job_requirements, candidate_profile, test_score)
    
    async def generate_interview_insights(self, facial_analysis: List[Dict], interview_duration: int) -> Dict[str, Any]:
        """Generate AI insights from facial analysis data."""
        try:
            if not self.client:
                return self._get_fallback_insights(facial_analysis, interview_duration)
            
            # Calculate summary statistics
            total_analyses = len(facial_analysis)
            if total_analyses == 0:
                return {"insights": "No facial analysis data available"}
            
            # Aggregate emotion data
            emotions = {}
            face_detection_rate = 0
            for analysis in facial_analysis:
                if analysis.get('face_detected', False):
                    face_detection_rate += 1
                    for emotion, score in analysis.get('emotions', {}).items():
                        if emotion not in emotions:
                            emotions[emotion] = []
                        emotions[emotion].append(score)
            
            face_detection_rate = (face_detection_rate / total_analyses) * 100
            
            # Calculate average emotions
            avg_emotions = {}
            for emotion, scores in emotions.items():
                avg_emotions[emotion] = sum(scores) / len(scores)
            
            prompt = f"""
            Analyze this interview facial expression data and provide professional insights:
            
            Interview Duration: {interview_duration} minutes
            Face Detection Rate: {face_detection_rate:.1f}%
            Average Emotions: {json.dumps(avg_emotions, indent=2)}
            Total Analysis Points: {total_analyses}
            
            Provide analysis in JSON format:
            {{
                "overall_assessment": "positive|neutral|negative",
                "confidence_level": "high|medium|low",
                "key_insights": ["main observations"],
                "communication_style": "description of communication approach",
                "engagement_level": "high|medium|low",
                "stress_indicators": ["any stress signs"],
                "professional_recommendation": "hire|consider|reject",
                "detailed_feedback": "comprehensive analysis"
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert psychologist analyzing interview behavior."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            insights = json.loads(content)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return self._get_fallback_insights(facial_analysis, interview_duration)
    
    async def chat_assistant(self, user_message: str, user_context: Dict = None) -> str:
        """AI chatbot assistant for user support."""
        try:
            if not self.client:
                return "I'm sorry, the AI assistant is currently unavailable. Please contact support."
            
            # Build context-aware prompt
            context_info = ""
            if user_context:
                context_info = f"""
                User Context:
                - Role: {user_context.get('role', 'unknown')}
                - Current Page: {user_context.get('page', 'unknown')}
                - Previous Actions: {user_context.get('actions', [])}
                """
            
            prompt = f"""
            You are AskTrabaajo's AI assistant, helping users with our HRTech platform.
            
            {context_info}
            
            User Question: {user_message}
            
            Provide a helpful, professional response about:
            - Job searching and applications
            - Assessment tests
            - Video interviews
            - Profile management
            - Platform features
            - Technical support
            
            Keep responses concise, friendly, and actionable.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are AskTrabaajo's helpful AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in chat assistant: {e}")
            return "I'm sorry, I'm having trouble processing your request. Please try again later."
    
    def _validate_question(self, question: Dict) -> bool:
        """Validate question structure."""
        required_fields = ['question', 'options', 'question_type']
        return all(field in question for field in required_fields) and len(question.get('options', [])) == 4
    
    def _get_fallback_questions(self, test_type: str) -> List[Dict[str, Any]]:
        """Fallback questions when OpenAI is unavailable."""
        if test_type == "technical":
            return [
                {
                    "id": 1,
                    "question": "What is the time complexity of binary search?",
                    "options": ["O(1)", "O(log n)", "O(n)", "O(n²)"],
                    "correct_answer": "O(log n)",
                    "question_type": "technical"
                },
                {
                    "id": 2,
                    "question": "Which data structure uses LIFO?",
                    "options": ["Queue", "Stack", "Tree", "Graph"],
                    "correct_answer": "Stack",
                    "question_type": "technical"
                }
            ]
        else:
            return [
                {
                    "id": 1,
                    "question": "How do you handle tight deadlines?",
                    "options": ["I thrive under pressure", "I prefer to plan ahead", "I get stressed but manage", "I avoid them"],
                    "question_type": "general"
                },
                {
                    "id": 2,
                    "question": "What motivates you most in a work environment?",
                    "options": ["Recognition and praise", "Financial rewards", "Learning new skills", "Helping others"],
                    "question_type": "general"
                }
            ]
    
    def _get_fallback_scoring(self, questions: List[Dict], answers: Dict[str, str], test_type: str) -> Dict[str, Any]:
        """Fallback scoring when OpenAI is unavailable."""
        total_questions = len(questions)
        correct_answers = 0
        
        if test_type == "technical":
            for q in questions:
                q_id = str(q['id'])
                if q_id in answers and q.get('correct_answer') == answers[q_id]:
                    correct_answers += 1
        else:
            for q in questions:
                q_id = str(q['id'])
                if q_id in answers:
                    answer = answers[q_id]
                    if answer in ["I thrive under pressure", "Learning new skills", "As a collaborator"]:
                        correct_answers += 1
                    else:
                        correct_answers += 0.5
        
        score = (correct_answers / total_questions) * 20 if total_questions > 0 else 0
        
        return {
            "overall_score": score,
            "skills_score": score * 0.5,
            "test_score": score * 0.5,
            "strengths": ["Good understanding of basic concepts"],
            "weaknesses": ["Could improve in some areas"],
            "detailed_feedback": "Standard assessment completed",
            "recommendations": ["Continue learning and practicing"]
        }
    
    def _get_fallback_matching(self, job_requirements: Dict, candidate_profile: Dict, test_score: float) -> Dict[str, Any]:
        """Fallback matching when OpenAI is unavailable."""
        # Simple matching based on test score
        match_score = min(test_score * 5, 100)  # Convert 0-20 score to 0-100
        
        return {
            "match_score": match_score,
            "skills_match": match_score * 0.8,
            "experience_match": match_score * 0.7,
            "culture_fit": match_score * 0.9,
            "overall_recommendation": "moderate_match",
            "strengths": ["Good test performance"],
            "concerns": ["Limited profile data"],
            "recommendations": ["Complete profile for better matching"]
        }
    
    def _get_fallback_insights(self, facial_analysis: List[Dict], interview_duration: int) -> Dict[str, Any]:
        """Fallback insights when OpenAI is unavailable."""
        return {
            "overall_assessment": "neutral",
            "confidence_level": "low",
            "key_insights": ["Basic facial analysis completed"],
            "communication_style": "Standard interview communication",
            "engagement_level": "medium",
            "stress_indicators": ["No significant stress detected"],
            "professional_recommendation": "consider",
            "detailed_feedback": "Standard interview analysis completed"
        } 