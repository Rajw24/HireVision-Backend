import os
import PyPDF2
import csv
from typing import Dict, List, Optional
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

# LLM components
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain.prompts import ChatPromptTemplate

# Audio components
import pyaudio
import wave
import pygame
from gtts import gTTS
import assemblyai as aai

# Video components
import cv2
import numpy as np

#django settings
from django.conf import settings

class HRInterviewAgent:
    def __init__(self, groq_api_key: str):
        self.llm = ChatGroq(
            api_key=groq_api_key,
            model_name="mixtral-8x7b-32768"
        )

        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

        # Schema for parsing LLM responses
        self.question_schema = ResponseSchema(
            name="question",
            description="The HR interview question to ask"
        )

        self.parser = StructuredOutputParser.from_response_schemas([self.question_schema])
        self.format_instructions = self.parser.get_format_instructions()
        
        # Initialize handlers
        self.voice_handler = VoiceHandler()
        self.video_handler = VideoHandler()
        
        # Interview data
        self.resume_content = ""
        self.interview_data = []
        self.question_count = 0
        self.max_questions = 10

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

    def parse_resume(self) -> str:
        """Get PDF from user and parse it using LangChain and Groq"""
        try:
            print("Please select your PDF resume when the file dialog appears...")
            pdf_path = self.get_pdf_path()

            print("\nReading your resume...")
            resume_text = self.extract_text_from_pdf(pdf_path)

            print("Analyzing resume content...")
            parse_prompt = ChatPromptTemplate.from_template(
                """You are an HR resume parser. Please analyze this resume and organize it into
                sections (personal information, education, experience, skills, achievements).
                Extract key details that would be relevant for an HR interview.

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

    def generate_question(self, previous_answer: str = None) -> Optional[str]:
        """Generate a contextual HR interview question using LLM"""
        # Check if we've reached the maximum number of questions
        if self.question_count >= self.max_questions:
            return None
        
        if previous_answer:
            self.memory.save_context(
                {"input": f"Question {self.question_count}"},
                {"output": previous_answer}
            )
            
            # Save the Q&A pair to our interview data
            if len(self.interview_data) > 0:  # There's at least one question asked
                self.interview_data[-1]["answer"] = previous_answer

        question_prompt = ChatPromptTemplate.from_template(
            """You are an expert HR interviewer. Based on the resume content and
            previous conversation, generate a relevant HR interview question. The question should:
            1. Assess the candidate's soft skills, communication abilities, and cultural fit
            2. Cover topics like teamwork, conflict resolution, career goals, and workplace values
            3. Be professional and appropriate for a formal interview setting
            4. Not repeat previously asked questions
            5. Follow up on interesting points from their previous answer if available

            Resume Content:
            {resume_content}

            Previous Conversation:
            {chat_history}

            This is question number {question_number} out of {max_questions}.

            {format_instructions}
            """
        )

        question_chain = question_prompt | self.llm

        response = question_chain.invoke({
            "resume_content": self.resume_content,
            "chat_history": self.memory.load_memory_variables({})["chat_history"],
            "format_instructions": self.format_instructions,
            "question_number": self.question_count + 1,
            "max_questions": self.max_questions
        })

        parsed_response = self.parser.parse(response.content)
        question = parsed_response["question"]
        
        # Increment question count and save to interview data
        self.question_count += 1
        self.interview_data.append({
            "question_number": self.question_count,
            "question": question,
            "answer": ""
        })
        
        return question

    def save_interview_data(self, filename: str = "interview_results.csv"):
        """Save the interview Q&A data to a CSV file"""
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['question_number', 'question', 'answer']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for item in self.interview_data:
                writer.writerow(item)
        
        print(f"Interview data saved to {filename}")
        return filename


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
    
    def record_audio(self, filename, duration=30):
        """Record audio from microphone"""
        p = pyaudio.PyAudio()
        
        print("Recording will start in 3 seconds...")
        time.sleep(3)
        print("Recording... Speak your answer (max 30 seconds)")
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


class VideoHandler:
    def __init__(self):
        self.cap = None
        self.width = 640
        self.height = 480
        self.avatar_img = None
        
        # Try to load avatar image
        try:
            self.avatar_img = cv2.imread("interviewer_avatar.png")
            if self.avatar_img is None:
                # Create a simple avatar if image not found
                self.avatar_img = np.ones((300, 300, 3), dtype=np.uint8) * 255
                cv2.circle(self.avatar_img, (150, 150), 100, (0, 120, 200), -1)
                cv2.circle(self.avatar_img, (120, 120), 15, (255, 255, 255), -1)
                cv2.circle(self.avatar_img, (180, 120), 15, (255, 255, 255), -1)
                cv2.ellipse(self.avatar_img, (150, 170), (50, 20), 0, 0, 180, (0, 0, 0), 5)
        except:
            # Create a simple avatar if loading fails
            self.avatar_img = np.ones((300, 300, 3), dtype=np.uint8) * 255
            cv2.circle(self.avatar_img, (150, 150), 100, (0, 120, 200), -1)
            cv2.circle(self.avatar_img, (120, 120), 15, (255, 255, 255), -1)
            cv2.circle(self.avatar_img, (180, 120), 15, (255, 255, 255), -1)
            cv2.ellipse(self.avatar_img, (150, 170), (50, 20), 0, 0, 180, (0, 0, 0), 5)
    
    def start_camera(self):
        """Start webcam capture"""
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        if not self.cap.isOpened():
            raise Exception("Could not open webcam")
    
    def display_avatar(self, speaking=False):
        """Display the avatar image"""
        # Create a copy of the avatar image
        display_img = self.avatar_img.copy()
        
        # If speaking, modify the avatar to simulate talking
        if speaking:
            cv2.ellipse(display_img, (150, 170), (50, 30), 0, 0, 180, (0, 0, 0), 5)
        
        return display_img
    
    def display_split_screen(self, speaking=False):
        """Display avatar and webcam feed side by side"""
        if self.cap is None:
            self.start_camera()
        
        ret, frame = self.cap.read()
        if not ret:
            raise Exception("Failed to grab frame from webcam")
        
        # Resize frame to match avatar size
        frame = cv2.resize(frame, (self.width//2, self.height))
        
        # Get avatar
        avatar = self.display_avatar(speaking)
        avatar = cv2.resize(avatar, (self.width//2, self.height))
        
        # Combine images side by side
        combined = np.hstack((avatar, frame))
        
        # Display
        cv2.imshow('HR Interview', combined)
        cv2.waitKey(1)
    
    def release(self):
        """Release camera and close windows"""
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()


def conduct_hr_interview():
    """Main function to conduct the HR interview"""
    try:
        # Replace with your API key
        GROQ_API_KEY = settings.GROQ_API_KEY
        
        print("Welcome to the AI HR Interview Assistant!")
        print("This program will analyze your PDF resume and conduct a voice-based HR interview.\n")
        
        agent = HRInterviewAgent(GROQ_API_KEY)
        
        # Parse resume from user input
        agent.parse_resume()
        
        print("\nGreat! I've analyzed your resume. Let's begin the interview.")
        print("(Say 'quit' or 'end interview' to finish)\n")
        
        # Start video
        agent.video_handler.start_camera()
        
        # Generate first question
        question = agent.generate_question()
        
        interview_active = True
        while interview_active and question:
            # Display avatar with speaking animation
            agent.video_handler.display_split_screen(speaking=True)
            
            # Convert question to speech
            agent.voice_handler.speak_text(question)
            
            # Display avatar without speaking animation
            agent.video_handler.display_split_screen(speaking=False)
            
            # Record and transcribe answer
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_file = f"answer_{timestamp}.wav"
            
            # Record audio
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
            
            # Generate next question
            question = agent.generate_question(answer)
            
            # Check if we've reached the maximum number of questions
            if question is None:
                agent.voice_handler.speak_text("We've completed all the questions. Thank you for participating in the interview!")
                interview_active = False
        
        # Save interview data
        csv_file = agent.save_interview_data()
        
        # Clean up
        agent.video_handler.release()
        
        print(f"\nInterview completed! Results saved to {csv_file}")
        print("You can now analyze the results using the analysis tool.")
        
    except KeyboardInterrupt:
        print("\n\nInterview terminated by user.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print("Please try again.")

if __name__ == "__main__":
    conduct_hr_interview()