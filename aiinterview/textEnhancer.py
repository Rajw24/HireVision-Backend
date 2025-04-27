# llm_enhancer.py

import torch
from transformers import AutoTokenizer, pipeline
from auto_gptq import AutoGPTQForCausalLM

class ResumeEnhancerLLM:
    _instance = None
    
    # Implement as singleton to avoid reloading model on each call
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResumeEnhancerLLM, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if self._initialized:
            return
            
        # Model configuration - Using a GPTQ quantized model
        self.model_name = "TheBloke/Llama-2-7B-GPTQ"  # Example GPTQ model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        self._initialized = False
        self.tokenizer = None
        self.model = None
        self.pipe = None
    
    def load_model(self):
        """
        Explicitly load the model (can be called separately to control when the 
        large model is loaded into memory)
        """
        if self._initialized:
            return
            
        print(f"Loading model: {self.model_name}")
        
        # Load the tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        
        # Load the GPTQ model
        self.model = AutoGPTQForCausalLM.from_quantized(
            self.model_name,
            use_safetensors=True,
            device=self.device,
            quantize_config=None
        )
        
        # Create a text generation pipeline
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            device=self.device
        )
        
        self._initialized = True
        print("Model loaded successfully")
    
    def enhance_resume(self, resume_text, enhancement_type="professional"):
        """
        Enhance the provided resume text based on the specified enhancement type.
        
        Args:
            resume_text (str): The original resume text to enhance
            enhancement_type (str): The type of enhancement to apply
                - "professional": Make the resume more professional
                - "technical": Enhance technical aspects
                - "concise": Make the resume more concise
                - "detailed": Add more details to the resume
                
        Returns:
            str: The enhanced resume text
        """
        # Make sure model is loaded
        if not self._initialized:
            self.load_model()
        
        # Create a prompt for the LLM based on enhancement type
        prompts = {
            "professional": f"""Enhance the following resume to make it more professional while maintaining its factual accuracy. 
                            Improve language, formatting, and presentation. Focus on achievements and results.
                            
                            RESUME:
                            {resume_text}
                            
                            Enhanced professional resume:""",
                            
            "technical": f"""Enhance the following resume to highlight technical skills and achievements better.
                        Emphasize technical competencies, projects, and accomplishments. Use industry-specific terminology.
                        
                        RESUME:
                        {resume_text}
                        
                        Technically enhanced resume:""",
                        
            "concise": f"""Make the following resume more concise and impactful while preserving key information.
                      Remove redundancies, consolidate bullet points, and use strong action verbs.
                      
                      RESUME:
                      {resume_text}
                      
                      Concise resume:""",
                      
            "detailed": f"""Enhance the following resume with more specific details and metrics.
                       Add quantifiable achievements, specific skills, and detailed examples of experience.
                       
                       RESUME:
                       {resume_text}
                       
                       Detailed resume:"""
        }
        
        prompt = prompts.get(enhancement_type, prompts["professional"])
        
        print(f"Enhancing resume with type: {enhancement_type}")
        
        # Generate enhanced text
        response = self.pipe(
            prompt,
            max_new_tokens=800,
            temperature=0.7,
            top_p=0.95,
            repetition_penalty=1.15
        )
        
        # Extract enhanced text from response
        enhanced_text = response[0]["generated_text"]
        
        # Clean up the response to return only the enhanced resume part
        marker_texts = {
            "professional": "Enhanced professional resume:",
            "technical": "Technically enhanced resume:",
            "concise": "Concise resume:",
            "detailed": "Detailed resume:"
        }
        
        marker = marker_texts.get(enhancement_type, marker_texts["professional"])
        if marker in enhanced_text:
            enhanced_text = enhanced_text.split(marker)[1].strip()
        
        print("Resume enhancement complete")
        return enhanced_text


# Example usage:
def enhance_resume_text(text, enhancement_type="professional"):
    """
    Function to call when button is clicked
    
    Args:
        text (str): Original resume text
        enhancement_type (str): Type of enhancement to apply
        
    Returns:
        str: Enhanced resume text
    """
    enhancer = ResumeEnhancerLLM()
    return enhancer.enhance_resume(text, enhancement_type)


# For testing directly
if __name__ == "__main__":
    # Sample resume for testing
    sample_resume = """
    John Doe
    Software Developer
    email@example.com | (123) 456-7890
    
    Experience:
    Software Developer at Tech Company
    - Developed web applications
    - Fixed bugs
    - Worked on user interface
    
    Education:
    Bachelor in Computer Science
    University Name, 2015-2019
    """
    
    # Test the enhancer
    enhanced = enhance_resume_text(sample_resume, "professional")
    print("\nEnhanced Resume:")
    print(enhanced)