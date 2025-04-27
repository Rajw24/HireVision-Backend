from django.conf import settings
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import spacy
import re
from collections import Counter
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate

# Download necessary NLTK data
nltk.download('vader_lexicon', quiet=True)

GROQ_API_KEY = settings.GROQ_API_KEY

class InterviewAnalyzer:
    def __init__(self, groq_api_key: str):
        self.llm = ChatGroq(
            api_key=groq_api_key,
            model_name="llama-3.1-8b-instant"
        )
        
        # Load spaCy model for NLP tasks
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            # If model isn't installed, download it
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")
        
        # Initialize sentiment analyzer
        self.sia = SentimentIntensityAnalyzer()
        
        # Interview data
        self.interview_data = None
        self.analysis_results = {}
    
    def load_interview_data(self, csv_file: str):
        """Load interview data from CSV file"""
        self.interview_data = pd.read_csv(csv_file)
        print(f"Loaded {len(self.interview_data)} questions from {csv_file}")
        return self.interview_data
    
    def analyze_sentiment(self) -> Dict:
        """Analyze sentiment of responses"""
        if self.interview_data is None:
            raise Exception("No interview data loaded")
        
        sentiment_scores = []
        for _, row in self.interview_data.iterrows():
            answer = row['answer']
            if not isinstance(answer, str) or not answer.strip():
                continue
                
            scores = self.sia.polarity_scores(answer)
            sentiment_scores.append({
                'question_number': row['question_number'],
                'question': row['question'],
                'negative': scores['neg'],
                'neutral': scores['neu'],
                'positive': scores['pos'],
                'compound': scores['compound']
            })
        
        sentiment_df = pd.DataFrame(sentiment_scores)
        self.analysis_results['sentiment'] = sentiment_df
        return sentiment_df
    
    def analyze_vocabulary(self) -> Dict:
        """Analyze vocabulary usage in responses"""
        if self.interview_data is None:
            raise Exception("No interview data loaded")
        
        # Combine all answers into one text
        all_text = " ".join(self.interview_data['answer'].dropna().astype(str))
        
        # Process with spaCy
        doc = self.nlp(all_text)
        
        # Get word frequency (excluding stopwords and punctuation)
        word_freq = Counter()
        for token in doc:
            if not token.is_stop and not token.is_punct and token.is_alpha:
                word_freq[token.text.lower()] += 1
        
        # Get part-of-speech distribution
        pos_dist = Counter()
        for token in doc:
            if token.is_alpha:
                pos_dist[token.pos_] += 1
        
        # Get named entities
        entities = []
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'type': ent.label_
            })
        
        vocab_analysis = {
            'word_frequency': dict(word_freq.most_common(30)),
            'pos_distribution': dict(pos_dist),
            'entities': entities
        }
        
        self.analysis_results['vocabulary'] = vocab_analysis
        return vocab_analysis
    
    def analyze_grammar(self) -> Dict:
        """Analyze grammar and language quality"""
        if self.interview_data is None:
            raise Exception("No interview data loaded")
        
        # We'll use the LLM to analyze grammar
        grammar_scores = []
        
        for _, row in self.interview_data.iterrows():
            answer = row['answer']
            if not isinstance(answer, str) or not answer.strip():
                continue
            
            grammar_prompt = ChatPromptTemplate.from_template(
                """Analyze the grammar, clarity, and professionalism of this interview response.
                Rate each aspect on a scale of 1-10 and provide specific feedback.
                
                Response to analyze:
                {response}
                
                Please provide a JSON object with the following structure:
                {{
                    "grammar_score": <number 1-10>,
                    "clarity_score": <number 1-10>,
                    "professionalism_score": <number 1-10>,
                    "strengths": ["list", "of", "strengths"],
                    "areas_for_improvement": ["list", "of", "areas", "to", "improve"],
                    "overall_impression": "brief overall impression"
                }}
                
                Return only the JSON object, no other text.
                """
            )
            
            grammar_chain = grammar_prompt | self.llm
            
            result = grammar_chain.invoke({
                "response": answer
            })
            
            # Extract the JSON content
            json_pattern = re.compile(r'\{.*\}', re.DOTALL)
            json_match = json_pattern.search(result.content)
            
            if json_match:
                import json
                try:
                    grammar_analysis = json.loads(json_match.group(0))
                    grammar_analysis['question_number'] = row['question_number']
                    grammar_analysis['question'] = row['question']
                    grammar_scores.append(grammar_analysis)
                except json.JSONDecodeError:
                    print(f"Error parsing JSON for question {row['question_number']}")
        
        self.analysis_results['grammar'] = grammar_scores
        return grammar_scores
    
    def analyze_technical_content(self) -> Dict:
        """Analyze technical content of responses"""
        if self.interview_data is None:
            raise Exception("No interview data loaded")
        
        technical_scores = []
        
        for _, row in self.interview_data.iterrows():
            answer = row['answer']
            if not isinstance(answer, str) or not answer.strip():
                continue
            
            technical_prompt = ChatPromptTemplate.from_template(
                """Analyze the technical content of this interview response.
                Rate each aspect on a scale of 1-10 and provide specific feedback.
                
                Question: {question}
                Response: {response}
                
                Please provide a JSON object with the following structure:
                {{
                    "technical_accuracy": <number 1-10>,
                    "depth_of_knowledge": <number 1-10>,
                    "relevance_to_question": <number 1-10>,
                    "technical_terms": ["list", "of", "technical", "terms", "used"],
                    "strengths": ["list", "of", "technical", "strengths"],
                    "areas_for_improvement": ["list", "of", "technical", "areas", "to", "improve"],
                    "overall_technical_impression": "brief overall technical impression"
                }}
                
                Return only the JSON object, no other text.
                """
            )
            
            technical_chain = technical_prompt | self.llm
            
            result = technical_chain.invoke({
                "question": row['question'],
                "response": answer
            })
            
            # Extract the JSON content
            json_pattern = re.compile(r'\{.*\}', re.DOTALL)
            json_match = json_pattern.search(result.content)
            
            if json_match:
                import json
                try:
                    technical_analysis = json.loads(json_match.group(0))
                    technical_analysis['question_number'] = row['question_number']
                    technical_analysis['question'] = row['question']
                    technical_scores.append(technical_analysis)
                except json.JSONDecodeError:
                    print(f"Error parsing JSON for question {row['question_number']}")
        
        self.analysis_results['technical'] = technical_scores
        return technical_scores
    
    def generate_summary_report(self) -> str:
        """Generate a comprehensive summary report"""
        if self.interview_data is None:
            raise Exception("No interview data loaded")
        
        # Combine all answers into one text
        all_text = " ".join(self.interview_data['answer'].dropna().astype(str))
        
        report_prompt = ChatPromptTemplate.from_template(
            """Generate a comprehensive HR interview summary report based on the following data:
            
            Interview Questions and Answers:
            {interview_data}
            
            Sentiment Analysis:
            {sentiment_data}
            
            Grammar Analysis:
            {grammar_data}
            
            Technical Analysis:
            {technical_data}
            
            Vocabulary Analysis:
            {vocab_data}
            
            The report should include:
            1. Executive Summary
            2. Communication Skills Assessment
            3. Technical Competency Assessment
            4. Behavioral Traits Analysis
            5. Strengths and Areas for Improvement
            6. Hiring Recommendation
            
            Format the report in Markdown.
            """
        )
        
        report_chain = report_prompt | self.llm
        
        # Convert analysis results to string representations
        sentiment_str = str(self.analysis_results.get('sentiment', 'Not analyzed'))
        grammar_str = str(self.analysis_results.get('grammar', 'Not analyzed'))
        technical_str = str(self.analysis_results.get('technical', 'Not analyzed'))
        vocab_str = str(self.analysis_results.get('vocabulary', 'Not analyzed'))
        
        result = report_chain.invoke({
            "interview_data": self.interview_data.to_string(),
            "sentiment_data": sentiment_str,
            "grammar_data": grammar_str,
            "technical_data": technical_str,
            "vocab_data": vocab_str
        })
        
        return result.content
    
    def visualize_results(self):
        """Create visualizations of the analysis results"""
        if not self.analysis_results:
            raise Exception("No analysis results available")
        
        # Set up the visualization style
        sns.set_style("whitegrid")
        
        # Create a figure with multiple subplots
        fig = plt.figure(figsize=(15, 10))
        
        # 1. Sentiment analysis plot
        if 'sentiment' in self.analysis_results:
            sentiment_df = self.analysis_results['sentiment']
            
            ax1 = fig.add_subplot(2, 2, 1)
            sentiment_df[['positive', 'neutral', 'negative']].mean().plot(
                kind='bar', 
                ax=ax1, 
                color=['green', 'gray', 'red']
            )
            ax1.set_title('Average Sentiment Scores')
            ax1.set_ylim(0, 1)
            
            # Sentiment by question
            ax2 = fig.add_subplot(2, 2, 2)
            sentiment_df.plot(
                x='question_number', 
                y='compound', 
                kind='line', 
                marker='o', 
                ax=ax2
            )
            ax2.set_title('Sentiment Compound Score by Question')
            ax2.set_ylim(-1, 1)
        
        # 2. Grammar and technical scores
        if 'grammar' in self.analysis_results and self.analysis_results['grammar']:
            grammar_df = pd.DataFrame(self.analysis_results['grammar'])
            
            ax3 = fig.add_subplot(2, 2, 3)
            grammar_df[['grammar_score', 'clarity_score', 'professionalism_score']].mean().plot(
                kind='bar',
                ax=ax3,
                color=['blue', 'purple', 'orange']
            )
            ax3.set_title('Average Language Quality Scores')
            ax3.set_ylim(0, 10)
        
        if 'technical' in self.analysis_results and self.analysis_results['technical']:
            tech_df = pd.DataFrame(self.analysis_results['technical'])
            
            ax4 = fig.add_subplot(2, 2, 4)
            tech_df[['technical_accuracy', 'depth_of_knowledge', 'relevance_to_question']].mean().plot(
                kind='bar',
                ax=ax4,
                color=['green', 'teal', 'lime']
            )
            ax4.set_title('Average Technical Scores')
            ax4.set_ylim(0, 10)
        
        # Adjust layout and save
        plt.tight_layout()
        plt.savefig('interview_analysis.png')
        plt.close()
        
        # 3. Word cloud of vocabulary
        if 'vocabulary' in self.analysis_results:
            try:
                from wordcloud import WordCloud
                
                word_freq = self.analysis_results['vocabulary']['word_frequency']
                
                # Generate the word cloud
                wordcloud = WordCloud(width=800, height=400, background_color='white').generate_from_frequencies(word_freq)
                
                plt.figure(figsize=(10, 5))
                plt.imshow(wordcloud, interpolation='bilinear')
                plt.axis('off')
                plt.title('Most Common Words in Responses')
                plt.tight_layout()
                plt.savefig('interview_wordcloud.png')
                plt.close()
            except ImportError:
                print("WordCloud library not installed, skipping word cloud visualization")
        
        print("Visualizations saved as 'interview_analysis.png' and 'interview_wordcloud.png'")
        return True
    
    def generate_analysis_json(self) -> dict:
        """Generate a JSON-formatted analysis result"""
        if not self.analysis_results:
            raise Exception("No analysis results available")

        # Calculate average scores from technical analysis
        tech_scores = pd.DataFrame(self.analysis_results.get('technical', []))
        tech_averages = {
            'technical_accuracy': tech_scores['technical_accuracy'].mean(),
            'depth_of_knowledge': tech_scores['depth_of_knowledge'].mean(),
            'relevance_score': tech_scores['relevance_to_question'].mean()
        }
        
        # Calculate average scores from grammar analysis
        grammar_scores = pd.DataFrame(self.analysis_results.get('grammar', []))
        grammar_averages = {
            'grammar_score': grammar_scores['grammar_score'].mean(),
            'clarity_score': grammar_scores['clarity_score'].mean(),
            'professionalism_score': grammar_scores['professionalism_score'].mean()
        }
        
        # Get sentiment averages
        sentiment_df = self.analysis_results.get('sentiment')
        sentiment_averages = {
            'positive_sentiment': sentiment_df['positive'].mean(),
            'neutral_sentiment': sentiment_df['neutral'].mean(),
            'negative_sentiment': sentiment_df['negative'].mean(),
            'compound_sentiment': sentiment_df['compound'].mean()
        }
        
        # Calculate overall scores
        overall_technical = sum(tech_averages.values()) / len(tech_averages)
        overall_communication = (
            sum(grammar_averages.values()) / len(grammar_averages) * 0.7 +
            sentiment_averages['compound_sentiment'] * 0.3
        )
        final_score = (overall_technical + overall_communication) / 2
        
        # Collect strengths and areas for improvement
        strengths = []
        areas_for_improvement = []
        
        for analysis in self.analysis_results.get('technical', []):
            strengths.extend(analysis.get('strengths', []))
            areas_for_improvement.extend(analysis.get('areas_for_improvement', []))
            
        for analysis in self.analysis_results.get('grammar', []):
            strengths.extend(analysis.get('strengths', []))
            areas_for_improvement.extend(analysis.get('areas_for_improvement', []))
        
        # Remove duplicates and limit to top items
        strengths = list(set(strengths))[:5]
        areas_for_improvement = list(set(areas_for_improvement))[:5]
        
        return {
            # Technical scores
            'technical_accuracy': tech_averages['technical_accuracy'],
            'depth_of_knowledge': tech_averages['depth_of_knowledge'],
            'relevance_score': tech_averages['relevance_score'],
            
            # Language quality scores
            'grammar_score': grammar_averages['grammar_score'],
            'clarity_score': grammar_averages['clarity_score'],
            'professionalism_score': grammar_averages['professionalism_score'],
            
            # Sentiment scores
            'positive_sentiment': sentiment_averages['positive_sentiment'],
            'neutral_sentiment': sentiment_averages['neutral_sentiment'],
            'negative_sentiment': sentiment_averages['negative_sentiment'],
            'compound_sentiment': sentiment_averages['compound_sentiment'],
            
            # Overall scores
            'overall_technical_score': overall_technical,
            'overall_communication_score': overall_communication,
            'final_score': final_score,
            
            # Feedback
            'technical_feedback': self.generate_technical_feedback(),
            'communication_feedback': self.generate_communication_feedback(),
            'strengths': strengths,
            'areas_for_improvement': areas_for_improvement,
            'vocabulary_analysis': self.analysis_results.get('vocabulary', {})
        }

    def generate_technical_feedback(self) -> str:
        """Generate technical feedback summary"""
        tech_scores = pd.DataFrame(self.analysis_results.get('technical', []))
        avg_technical = tech_scores[['technical_accuracy', 'depth_of_knowledge', 'relevance_to_question']].mean().mean()
        
        if avg_technical >= 8:
            return "Excellent technical proficiency demonstrated throughout the interview. Strong command of concepts and thorough explanations provided."
        elif avg_technical >= 6:
            return "Good technical knowledge shown. Some areas could be explained in more detail, but overall understanding is solid."
        else:
            return "Technical responses could be improved. Consider providing more detailed explanations and specific examples."

    def generate_communication_feedback(self) -> str:
        """Generate communication feedback summary"""
        grammar_scores = pd.DataFrame(self.analysis_results.get('grammar', []))
        avg_communication = grammar_scores[['grammar_score', 'clarity_score', 'professionalism_score']].mean().mean()
        
        if avg_communication >= 8:
            return "Excellent communication skills. Clear, professional, and well-articulated responses throughout the interview."
        elif avg_communication >= 6:
            return "Good communication overall. Some responses could be more concise and structured, but generally clear and professional."
        else:
            return "Communication could be improved. Focus on clarity, structure, and professional language in responses."

def analyze_interview(csv_file: str, groq_api_key: str):
    """Main function to analyze an interview from CSV file"""
    try:
        print(f"Analyzing interview data from {csv_file}...")
        analyzer = InterviewAnalyzer(groq_api_key)
        
        # Load data
        analyzer.load_interview_data(csv_file)
        
        # Run analyses
        print("Analyzing sentiment...")
        analyzer.analyze_sentiment()
        
        print("Analyzing vocabulary...")
        analyzer.analyze_vocabulary()
        
        print("Analyzing grammar and language quality...")
        analyzer.analyze_grammar()
        
        print("Analyzing technical content...")
        analyzer.analyze_technical_content()
        
        # Generate visualizations
        print("Generating visualizations...")
        analyzer.visualize_results()
        
        # Generate summary report
        print("Generating summary report...")
        report = analyzer.generate_summary_report()
        
        # Save report to file
        report_file = "interview_analysis_report.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"Analysis complete! Report saved to {report_file}")
        print("You can open the report in any Markdown viewer.")
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
