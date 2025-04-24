import base64
import assemblyai as aai
import pyaudio
import wave
import time
from datetime import datetime
import io
import PyPDF2
# from google.colab import files
from typing import Dict, List
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import ChatPromptTemplate
from gtts import gTTS
import pygame
import os
import tkinter as tk
from tkinter import filedialog
from django.conf import settings
from io import BytesIO
from .models import Interview

AAI_KEY = settings.AAI_KEY
GROQ_API_KEY = settings.GROQ_API_KEY


class VoiceHandler:
    def __init__(self):
        # Audio recording parameters
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100

        # Initialize pygame mixer for audio playback
        pygame.mixer.init()

        # Initialize AssemblyAI
        self.aai_key = AAI_KEY  # Replace with your key
        aai.settings.api_key = self.aai_key
        self.transcriber = aai.Transcriber()
        self.temp_files = []

    def cleanup(self):
        """Clean up any temporary files"""
        for file in self.temp_files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                print(f"Error cleaning up {file}: {e}")
        self.temp_files = []

    def speak_text(self, text):
        """Convert text to speech using Google TTS"""
        try:
            print(f"\nInterviewer: {text}")

            # Create a temporary file for the speech
            temp_file = f"temp_speech_{time.time()}.mp3"
            self.temp_files.append(temp_file)
            tts = gTTS(text=text, lang='en')
            tts.save(temp_file)

            # Play the audio
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

        finally:
            self.cleanup()

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
    def __init__(self, groq_api_key: str, interview_id: int = None, user_name: str = None):
        self.user_name = user_name
        self.interview_id = interview_id
        self.llm = ChatGroq(
            api_key=groq_api_key,
            model_name="llama-3.1-8b-instant"
            # model_name="llama-3.3-70b-versatile"
            # model_name="mixtral-8x7b-32768"
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
        
        #Initialize voice handler
        self.voice_handler = VoiceHandler()
        self.resume_content = None

    def load_resume_from_interview(self, interview_id: int = None):
        """Load resume content from Interview model"""
        from .models import Interview  # Import here to avoid circular imports
        
        interview_id = interview_id or self.interview_id
        if not interview_id:
            raise ValueError("Interview ID is required")
            
        try:
            interview = Interview.objects.get(id=interview_id)
            self.resume_file = interview.resume_file
            return self.resume_file
        except Interview.DoesNotExist:
            raise ValueError(f"Interview with ID {interview_id} not found")

    def extract_text_from_pdf(self, interview_id: int = None) -> str:
        """Extract text content from a PDF file object"""
        # if isinstance(resume_file, int):
        #     # If resume_file is an interview ID, load from database
        #     return self.load_resume_from_interview(resume_file)
            
        resume_file = self.load_resume_from_interview(interview_id)
        
        if not resume_file:
            raise ValueError("Resume file is required")
            
        try:
            # Handle different input types
            if isinstance(resume_file, str):
                if os.path.exists(resume_file):
                    # It's a file path
                    pdf_file = open(resume_file, 'rb')
                elif resume_file.startswith('data:application/pdf;base64,'):
                    # It's a base64 string
                    pdf_data = base64.b64decode(resume_file.split(',')[1])
                    pdf_file = BytesIO(pdf_data)
                else:
                    raise ValueError("Invalid resume file format")
            elif isinstance(resume_file, bytes):
                # It's bytes data
                pdf_file = BytesIO(resume_file)
            else:
                # Assume it's a file-like object
                pdf_file = resume_file

            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
                
            if hasattr(pdf_file, 'close'):
                pdf_file.close()
                
            return text.strip()
        except Exception as e:
            raise Exception(f"Error reading PDF file: {str(e)}")

    def parse_resume(self, interview_id: int = None) -> Dict[str, List[str]]:
        """Parse resume content using LangChain and Groq"""
        try:
            resume_text = self.extract_text_from_pdf(interview_id)

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
            
            if interview_id:
                # Save parsed resume content to Interview model
                interview = Interview.objects.get(id=interview_id)
                interview.resume_content = self.resume_content
                interview.save()
            
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
        
        # Check if this is the first question (no previous answer)
        if not previous_answer:
            return f"Hello {self.user_name}! Could you please introduce yourself and tell me a bit about your background and experience?"

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
