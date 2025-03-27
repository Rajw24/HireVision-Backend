import os
import PyPDF2
from typing import Dict, List
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import ChatPromptTemplate
from gtts import gTTS
import pygame
import assemblyai as aai
import pyaudio
import wave
import time
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from django.conf import settings

class VoiceHandler:
    def __init__(self):
        # Audio recording parameters
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        
        # Initialize pygame for audio playback
        pygame.mixer.init()
        
        # Initialize AssemblyAI
        self.aai_key = settings.AAI_KEY  # Replace with your AssemblyAI API key
        aai.settings.api_key = self.aai_key
        self.transcriber = aai.Transcriber()

    def speak_text(self, text):
        """Convert text to speech using Google TTS"""
        print(f"\nInterviewer: {text}")
        
        # Create a temporary file for the speech
        tts = gTTS(text=text, lang='en')
        temp_file = "temp_speech.mp3"
        tts.save(temp_file)
        
        # Play the audio
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        # Clean up the temporary file
        pygame.mixer.music.stop()
        try:
            os.remove(temp_file)
        except:
            pass

    def record_audio(self, filename, duration=10):
        """Record audio from microphone"""
        p = pyaudio.PyAudio()
        
        print("Recording will start in 3 seconds...")
        time.sleep(3)
        print("Recording... Speak your answer")

        stream = p.open(format=self.FORMAT,
                       channels=self.CHANNELS,
                       rate=self.RATE,
                       input=True,
                       frames_per_buffer=self.CHUNK)

        frames = []
        
        for i in range(0, int(self.RATE / self.CHUNK * duration)):
            data = stream.read(self.CHUNK)
            frames.append(data)

        print("Recording finished!")

        stream.stop_stream()
        stream.close()
        p.terminate()

        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

    def transcribe_audio(self, audio_file):
        """Transcribe audio file using AssemblyAI"""
        try:
            transcript = self.transcriber.transcribe(audio_file)
            return transcript.text
        except Exception as e:
            print(f"Transcription error: {str(e)}")
            return ""
        

class ResumeInterviewAgent:
    def __init__(self, groq_api_key: str):
        self.llm = ChatGroq(
            api_key=groq_api_key,
            model_name="mixtral-8x7b-32768"
        )

        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        self.question_schema = ResponseSchema(
            name="question",
            description="The interview question to ask"
        )

        self.parser = StructuredOutputParser.from_response_schemas([self.question_schema])
        self.format_instructions = self.parser.get_format_instructions()
        
        # Initialize voice handler
        self.voice_handler = VoiceHandler()

    def get_pdf_path(self):
        """Open file dialog to select PDF resume"""
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        file_path = filedialog.askopenfilename(
            title="Select your PDF resume",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if not file_path:
            raise Exception("No file selected")
            
        return file_path

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from a PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            raise Exception(f"Error reading PDF file: {str(e)}")

    def parse_resume(self) -> Dict[str, List[str]]:
        """Get PDF from user and parse it using LangChain and Groq"""
        try:
            print("Please select your PDF resume when the file dialog appears...")
            pdf_path = self.get_pdf_path()

            print("\nReading your resume...")
            resume_text = self.extract_text_from_pdf(pdf_path)

            print("Analyzing resume content...")
            parse_prompt = ChatPromptTemplate.from_template(
                """You are a resume parser. Please analyze this resume and organize it into
                sections (education, experience, skills, projects). Return the organized content.

                Resume:
                {resume_text}
                """
            )

            parse_chain = parse_prompt | self.llm
            parsed_resume = parse_chain.invoke({"resume_text": resume_text})
            self.resume_content = parsed_resume.content
            return parsed_resume.content

        except Exception as e:
            raise Exception(f"Error processing resume: {str(e)}")

    def generate_question(self, previous_answer: str = None) -> str:
        """Generate a contextual interview question using LangChain and Groq"""
        if previous_answer:
            self.memory.save_context(
                {"input": "Previous answer"},
                {"output": previous_answer}
            )

        question_prompt = ChatPromptTemplate.from_template(
            """You are an expert technical interviewer. Based on the resume content and
            previous conversation, generate a relevant, specific, and probing interview
            question. The question should:
            1. Be directly related to the candidate's experience or skills
            2. Require detailed technical or situational answers
            3. Help assess the candidate's expertise
            4. Not repeat previously asked questions
            5. Follow up on interesting points from their previous answer if available

            Resume Content:
            {resume_content}

            Previous Conversation:
            {chat_history}

            {format_instructions}
            """
        )

        question_chain = question_prompt | self.llm

        response = question_chain.invoke({
            "resume_content": self.resume_content,
            "chat_history": self.memory.load_memory_variables({})["chat_history"],
            "format_instructions": self.format_instructions
        })

        parsed_response = self.parser.parse(response.content)
        return parsed_response["question"]
    

class TechnicalInterviewAgent:
    def __init__(self, position="software_engineer", difficulty="medium"):
        self.groq_api_key = settings.GROQ_API_KEY
        self.interview_agent = ResumeInterviewAgent(self.groq_api_key)
        self.position = position
        self.difficulty = difficulty
        self.questions_asked = 0
        self.score = {
            'accuracy': 0,
            'fluency': 0,
            'rhythm': 0
        }

    def start_interview(self):
        """Initialize interview and return first question"""
        question = self.interview_agent.generate_question()
        self.questions_asked += 1
        return question

    def process_response(self, answer):
        """Process user's answer and return next question"""
        if not self.is_interview_complete():
            question = self.interview_agent.generate_question(answer)
            self.questions_asked += 1
            # Update mock scores for demo
            self.score = {
                'accuracy': min(100, 75 + self.questions_asked * 5),
                'fluency': min(100, 70 + self.questions_asked * 4),
                'rhythm': min(100, 80 + self.questions_asked * 3)
            }
            return question
        return "Interview complete. Thank you for your participation."

    def is_interview_complete(self):
        """Check if interview should end"""
        return self.questions_asked >= 5  # Limit to 5 questions for demo

    def get_score(self):
        """Return current interview scores"""
        return self.score


def conduct_interview():
    """Main function to conduct the voice-based interview"""
    try:
        # Use the API key directly
        GROQ_API_KEY = settings.GROQ_API_KEY

        print("Welcome to the AI Voice Resume Interviewer!")
        print("This program will analyze your PDF resume and conduct a voice-based interview.\n")

        agent = ResumeInterviewAgent(GROQ_API_KEY)

        # Parse resume from user input
        agent.parse_resume()

        print("\nGreat! I've analyzed your resume. Let's begin the interview.")
        print("(Say 'quit' or 'end interview' to finish)\n")

        question = agent.generate_question()
        interview_active = True

        while interview_active:
            # Convert question to speech
            agent.voice_handler.speak_text(question)

            # Record and transcribe answer
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_file = f"answer_{timestamp}.wav"
            
            # Record audio (default 10 seconds)
            agent.voice_handler.record_audio(audio_file)
            
            # Transcribe the answer
            print("\nTranscribing your answer...")
            answer = agent.voice_handler.transcribe_audio(audio_file)
            print(f"\nYour answer (transcribed): {answer}")

            # Clean up the audio file
            try:
                os.remove(audio_file)
            except:
                pass

            if any(word in answer.lower() for word in ['quit', 'exit', 'end interview']):
                interview_active = False
                agent.voice_handler.speak_text("Thank you for participating in the interview!")
                break

            question = agent.generate_question(answer)

    except KeyboardInterrupt:
        print("\n\nInterview terminated by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print("Please try again.")

if __name__ == "__main__":
    conduct_interview()